import pytest

from goodfog.fog import Hour, Status, hour_from_values, jsround, lcl_ft, lcl_status, verdict
from goodfog.viewpoints import viewpoint_by_id


def test_jsround_matches_js_math_round():
    assert jsround(2.5) == 3
    assert jsround(-2.5) == -2
    assert jsround(3.728) == 4
    assert jsround(8.699) == 9


def test_lcl_ft_formula():
    assert lcl_ft(14.2, 11.1) == 1271   # 125 * 3.1 * 3.281 = 1271.39
    assert lcl_ft(12.0, 12.0) == 0
    assert lcl_ft(10.0, 12.0) == 0      # negative spread clamps to 0
    assert lcl_ft(None, 12.0) is None
    assert lcl_ft(12.0, None) is None


def test_hour_from_values_converts_units():
    h = hour_from_values(14.2, 11.1, low=85, mid=5, high=0, wind_kmh=6.0, rain=0)
    assert h.wind_mph == 4
    assert h.temp_f == 58
    assert h.dewpoint_f == 52
    assert h.lcl_ft == 1271
    assert (h.low_cloud, h.mid_cloud, h.high_cloud, h.rain_pct) == (85, 5, 0, 0)


def test_hour_from_values_nulls_default_to_zero():
    h = hour_from_values(14.2, None, low=None, mid=None, high=None, wind_kmh=6.0, rain=None)
    assert (h.low_cloud, h.mid_cloud, h.high_cloud, h.rain_pct) == (0, 0, 0, 0)
    assert h.dewpoint_f is None
    assert h.lcl_ft is None


@pytest.mark.parametrize(
    "lcl, expected",
    [
        (199, Status("red", "low")),
        (200, Status("green")),
        (850, Status("green")),
        (851, Status("yellow")),
        (950, Status("yellow")),
        (951, Status("red", "high")),
    ],
)
def test_lcl_status_boundaries_hawk_hill(lcl, expected):
    vp = viewpoint_by_id("hawk-hill")
    h = Hour(low_cloud=80, mid_cloud=0, high_cloud=0, wind_mph=0, rain_pct=0, temp_f=68, dewpoint_f=60, lcl_ft=lcl)
    assert lcl_status(vp, h) == expected


def test_lcl_status_none_when_thin_low_cloud_or_no_lcl():
    vp = viewpoint_by_id("hawk-hill")
    thin = Hour(low_cloud=19, mid_cloud=0, high_cloud=0, wind_mph=0, rain_pct=0, temp_f=68, dewpoint_f=60, lcl_ft=500)
    assert lcl_status(vp, thin) == Status("none")
    nolcl = Hour(low_cloud=90, mid_cloud=0, high_cloud=0, wind_mph=0, rain_pct=0, temp_f=68, dewpoint_f=None, lcl_ft=None)
    assert lcl_status(vp, nolcl) == Status("none")


def test_twin_peaks_green_band_is_above_its_own_elevation():
    vp = viewpoint_by_id("twin-peaks-vantage")
    h = Hour(low_cloud=80, mid_cloud=0, high_cloud=0, wind_mph=0, rain_pct=0, temp_f=68, dewpoint_f=60, lcl_ft=600)
    assert lcl_status(vp, h) == Status("green")


@pytest.mark.parametrize(
    "score, label, cls",
    [(100, "Go for it!", "go"), (70, "Go for it!", "go"), (69, "Worth a try", "try"), (50, "Worth a try", "try"),
     (49, "Maybe next time", "maybe"), (30, "Maybe next time", "maybe"), (29, "Stay home", "no"), (0, "Stay home", "no")],
)
def test_verdict_thresholds(score, label, cls):
    v = verdict(score)
    assert (v.label, v.cls) == (label, cls)
