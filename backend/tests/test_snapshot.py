import json
from datetime import datetime, timezone
from pathlib import Path

from goodfog.providers.open_meteo import parse_open_meteo
from goodfog.snapshot import build_snapshot
from goodfog.viewpoints import VIEWPOINTS

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "open_meteo.json").read_text())
NOW = datetime(2026, 9, 2, 23, 15, tzinfo=timezone.utc)


def _snap():
    return build_snapshot(VIEWPOINTS, parse_open_meteo(FIXTURE, 8), now=NOW, app_version="0.1.0", commit="abc1234")


def test_top_level_shape():
    s = _snap()
    assert s["app_version"] == "0.1.0" and s["commit"] == "abc1234"
    assert s["generated_at"] == "2026-09-02T23:15:00+00:00"
    assert [w["id"] for w in s["windows"]] == ["tonight", "tomorrow_am", "tomorrow_pm"]
    assert set(s["windows"][0]) == {"id", "title", "tab", "sun_label", "sun_event", "arrive_by", "hour"}
    assert [v["id"] for v in s["viewpoints"]] == [v.id for v in VIEWPOINTS]


def test_viewpoint_entry_shape():
    v = _snap()["viewpoints"][-1]
    assert v["name"] == "East Peak" and v["elev_ft"] == 2571
    assert v["green_ft"] == [200, 2400] and v["yellow_ft"] == [2400, 2571] and v["dawn_gated"] is True
    for key in ("desc", "composition", "access", "cam_tip"):
        assert isinstance(v[key], str) and v[key]
    assert "windows" in v
    assert set(v["windows"][0]) == {"id", "title", "tab", "sun_label", "sun_event", "arrive_by", "hour"}
    r = v["results"]["tonight"]
    assert set(r) == {"score", "verdict", "status", "factors", "explanation", "elevation", "lcl_ft", "wx"}
    assert set(r["verdict"]) == {"label", "emoji", "cls"}
    assert set(r["status"]) == {"kind", "reason"}
    assert set(r["factors"][0]) == {"label", "rating"}
    assert set(r["elevation"]) == {"cls", "icon", "title", "detail"}
    assert set(r["wx"]) == {"low_cloud", "mid_cloud", "high_cloud", "wind_mph", "rain_pct", "temp_f", "dewpoint_f", "lcl_ft"}
    assert 0 <= r["score"] <= 100


def test_each_viewpoint_gets_windows_from_its_own_daily_block():
    fcs = parse_open_meteo(FIXTURE, 8)
    s = _snap()
    for vp_entry, fc in zip(s["viewpoints"], fcs, strict=True):
        ws = vp_entry["windows"]
        assert [w["id"] for w in ws] == ["tonight", "tomorrow_am", "tomorrow_pm"]
        assert ws[0]["sun_event"] == fc.sunset[0]
        assert ws[1]["sun_event"] == fc.sunrise[1]
        assert ws[2]["sun_event"] == fc.sunset[1]
        assert set(vp_entry["results"]) == {w["id"] for w in ws}


def test_missing_hour_gives_null_result():
    fcs = parse_open_meteo(FIXTURE, 8)
    broken = fcs[0].__class__(hourly_time=(), hourly=fcs[0].hourly, sunrise=fcs[0].sunrise, sunset=fcs[0].sunset)
    s = build_snapshot(VIEWPOINTS, [broken] + fcs[1:], now=NOW, app_version="x", commit="y")
    assert s["viewpoints"][0]["results"] == {"tonight": None, "tomorrow_am": None, "tomorrow_pm": None}
    assert s["viewpoints"][1]["results"]["tonight"] is not None


def test_snapshot_is_json_serializable():
    json.dumps(_snap())


def test_viewpoint_entry_carries_coordinates():
    s = _snap()
    for entry, vp in zip(s["viewpoints"], VIEWPOINTS, strict=True):
        assert entry["lat"] == vp.lat
        assert entry["lon"] == vp.lon
