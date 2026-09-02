import pytest

from goodfog.fog import Status, elevation_verdict, fmt_ft, hour_from_values, score, verdict
from goodfog.viewpoints import viewpoint_by_id

# (viewpoint, temp_c, dew_c, low, mid, high, wind_kmh, rain) -> expected, computed by the original index.html JS.
PARITY = [
    ("east-peak", 14.2, 11.1, 85, 5, 0, 6.0, 0,
     100, Status("green"), "Go for it!", "Above the fog layer",
     ["Low cloud 85%|good", "Wind 4 mph|good", "Clear above 5%|good", "Rain 0%|good", "Fog base 1,271 ft — below you|good"],
     "Strong conditions at East Peak. Fog base ~1,271 ft sits below you — expect a clean view down onto the layer. Low cloud at 85%, winds calm at 4 mph."),
    ("hawk-hill", 14.2, 11.1, 85, 5, 0, 6.0, 0,
     35, Status("red", "high"), "Maybe next time", "Inside the layer",
     ["Low cloud 85%|good", "Wind 4 mph|good", "Clear above 5%|good", "Rain 0%|good", "Fog base 1,271 ft — above you|bad"],
     "Marginal at Hawk Hill. Fog base ~1,271 ft is above your viewpoint — you'd be in it."),
    ("hawk-hill", 15.0, 12.9, 60, 30, 10, 14.0, 10,
     59, Status("yellow"), "Worth a try", "Right at the edge",
     ["Low cloud 60%|ok", "Wind 9 mph|ok", "Some high cloud 30%|ok", "Rain 10%|ok", "Fog base 861 ft — at the edge|ok"],
     "Decent shot at Hawk Hill. Moderate marine layer with calm winds. Fog base ~861 ft — check the live cameras before heading out."),
    ("point-bonita", 13.0, 12.6, 90, 0, 0, 4.0, 0,
     100, Status("green"), "Go for it!", "Above the fog layer",
     ["Low cloud 90%|good", "Wind 2 mph|good", "Clear above 0%|good", "Rain 0%|good", "Fog base 164 ft — below you|good"],
     "Strong conditions at Point Bonita Lighthouse. Fog base ~164 ft sits below you — expect a clean view down onto the layer. Low cloud at 90%, winds calm at 2 mph."),
    ("twin-peaks-vantage", 16.0, 14.4, 70, 60, 20, 20.0, 25,
     41, Status("green"), "Maybe next time", "Above the fog layer",
     ["Low cloud 70%|ok", "Wind 12 mph|ok", "High cloud 60%|bad", "Rain 25%|bad", "Fog base 656 ft — below you|good"],
     "Marginal at Twin Peaks (Arguello & Jackson). Fog base ~656 ft."),
    ("battery-spencer", 18.0, 8.0, 10, 0, 0, 3.0, 0,
     15, Status("none"), "Stay home", "No marine layer",
     ["Low cloud 10%|bad", "Wind 2 mph|good", "Clear above 0%|good", "Rain 0%|good", "No marine layer|bad"],
     "Not worth the drive to Battery Spencer today. No marine layer. Save it for a better day."),
    ("trojan-point", 14.0, 13.0, 55, 10, 5, 8.0, 0,
     95, Status("green"), "Go for it!", "Above the fog layer",
     ["Low cloud 55%|ok", "Wind 5 mph|good", "Clear above 10%|good", "Rain 0%|good", "Fog base 410 ft — below you|good"],
     "Strong conditions at Trojan Point. Fog base ~410 ft sits below you — expect a clean view down onto the layer. Low cloud at 55%, winds calm at 5 mph."),
    ("west-peak", 12.0, 12.0, 95, 0, 0, 30.0, 5,
     35, Status("red", "low"), "Maybe next time", "Socked in",
     ["Low cloud 95%|good", "Wind 19 mph|bad", "Clear above 0%|good", "Rain 5%|good", "Fog base 0 ft — socked in|bad"],
     "Marginal at West Peak. Wind may break up the layer. Fog base ~0 ft is very low — a deep layer may sock you in."),
]


@pytest.mark.parametrize("case", PARITY, ids=[f"{c[0]}-{c[8]}" for c in PARITY])
def test_parity_with_original_js(case):
    vid, t, td, low, mid, high, wind, rain, exp_score, exp_status, exp_verdict, exp_elev, exp_factors, exp_expl = case
    vp = viewpoint_by_id(vid)
    h = hour_from_values(t, td, low=low, mid=mid, high=high, wind_kmh=wind, rain=rain)
    r = score(vp, h)
    assert r.score == exp_score
    assert r.status == exp_status
    assert verdict(r.score).label == exp_verdict
    assert elevation_verdict(vp, h).title == exp_elev
    assert [f"{f.label}|{f.rating}" for f in r.factors] == exp_factors
    assert r.explanation == exp_expl


def test_fmt_ft_thousands_separator():
    assert fmt_ft(1271) == "1,271"
    assert fmt_ft(0) == "0"
    assert fmt_ft(950) == "950"


def test_green_bonus_caps_at_100():
    vp = viewpoint_by_id("east-peak")
    h = hour_from_values(14.2, 11.1, low=85, mid=5, high=0, wind_kmh=6.0, rain=0)
    assert score(vp, h).score == 100  # 40+20+20+20 = 100, +10 capped


def test_no_layer_caps_at_15_and_result_lcl_is_none():
    vp = viewpoint_by_id("east-peak")
    h = hour_from_values(18.0, 8.0, low=10, mid=0, high=0, wind_kmh=3.0, rain=0)
    r = score(vp, h)
    assert r.score == 15
    assert r.lcl_ft is None  # gated: thin low cloud means no fog base to report


def test_elevation_verdict_texts():
    vp = viewpoint_by_id("hawk-hill")
    green = hour_from_values(15.0, 13.5, low=80, mid=0, high=0, wind_kmh=0.0, rain=0)  # lcl 615
    e = elevation_verdict(vp, green)
    assert (e.cls, e.icon) == ("above", "🏔️")
    assert e.detail.startswith("Fog base sits around 615 ft — comfortably below Hawk Hill (923 ft).")
    assert e.detail.endswith(vp.composition)
    none = hour_from_values(15.0, 13.5, low=5, mid=0, high=0, wind_kmh=0.0, rain=0)
    e = elevation_verdict(vp, none)
    assert (e.cls, e.icon, e.title) == ("clear", "🔭", "No marine layer")
    assert "Hawk Hill at 923 ft." in e.detail
    red_high = hour_from_values(20.0, 12.0, low=80, mid=0, high=0, wind_kmh=0.0, rain=0)  # lcl 3281
    e = elevation_verdict(vp, red_high)
    assert (e.cls, e.title) == ("below", "Inside the layer")
    assert e.detail == f"Fog base ~3,281 ft. {vp.too_high} Consider a higher viewpoint."
