from goodfog.windows import build_windows, minus_minutes, truncate_hour


def test_truncate_hour_drops_minutes():
    assert truncate_hour("2026-09-02T19:32") == "2026-09-02T19:00"
    assert truncate_hour("2026-09-03T06:52:10") == "2026-09-03T06:00"


def test_minus_minutes_crosses_hour():
    assert minus_minutes("2026-09-02T19:32", 45) == "2026-09-02T18:47"
    assert minus_minutes("2026-09-03T06:52", 30) == "2026-09-03T06:22"


def test_build_windows_three_windows():
    ws = build_windows(
        sunrise=["2026-09-02T06:51", "2026-09-03T06:52", "2026-09-04T06:53"],
        sunset=["2026-09-02T19:32", "2026-09-03T19:31", "2026-09-04T19:29"],
    )
    assert [w.id for w in ws] == ["tonight", "tomorrow_am", "tomorrow_pm"]
    t, am, pm = ws
    assert (t.title, t.tab, t.sun_label, t.sun_event, t.arrive_by, t.hour) == (
        "Tonight Sunset", "🌅 Tonight", "Sunset", "2026-09-02T19:32", "2026-09-02T18:47", "2026-09-02T19:00")
    assert (am.title, am.tab, am.sun_label, am.sun_event, am.arrive_by, am.hour) == (
        "Tomorrow Sunrise", "🌄 Tom. AM", "Sunrise", "2026-09-03T06:52", "2026-09-03T06:22", "2026-09-03T06:00")
    assert (pm.title, pm.tab, pm.sun_label, pm.sun_event, pm.arrive_by, pm.hour) == (
        "Tomorrow Sunset", "🌇 Tom. PM", "Sunset", "2026-09-03T19:31", "2026-09-03T18:46", "2026-09-03T19:00")
