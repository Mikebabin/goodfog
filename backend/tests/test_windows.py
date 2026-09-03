import pytest

from goodfog.windows import build_windows, minus_minutes, truncate_hour


def test_truncate_hour_drops_minutes():
    assert truncate_hour("2026-09-02T19:32") == "2026-09-02T19:00"
    assert truncate_hour("2026-09-03T06:52:10") == "2026-09-03T06:00"


def test_minus_minutes_crosses_hour():
    assert minus_minutes("2026-09-02T19:32", 45) == "2026-09-02T18:47"
    assert minus_minutes("2026-09-03T06:52", 30) == "2026-09-03T06:22"


SUNRISE = ["2026-09-02T06:51", "2026-09-03T06:52", "2026-09-04T06:53", "2026-09-05T06:54"]
SUNSET = ["2026-09-02T19:32", "2026-09-03T19:31", "2026-09-04T19:29", "2026-09-05T19:28"]


def test_build_windows_emits_seven_in_order():
    ws = build_windows(SUNRISE, SUNSET)
    assert [w.id for w in ws] == ["tonight", "d1_am", "d1_pm", "d2_am", "d2_pm", "d3_am", "d3_pm"]
    assert [w.day for w in ws] == [0, 1, 1, 2, 2, 3, 3]
    assert [w.sun_label for w in ws] == ["Sunset", "Sunrise", "Sunset", "Sunrise", "Sunset", "Sunrise", "Sunset"]
    assert [w.sun_event for w in ws] == [SUNSET[0], SUNRISE[1], SUNSET[1], SUNRISE[2], SUNSET[2], SUNRISE[3], SUNSET[3]]


def test_build_windows_labels_and_titles():
    ws = build_windows(SUNRISE, SUNSET)
    # 2026-09-02 is a Wednesday, so day 2 is Friday and day 3 is Saturday.
    assert [w.day_label for w in ws] == ["Tonight", "Tomorrow", "Tomorrow", "Fri", "Fri", "Sat", "Sat"]
    assert [w.tab for w in ws] == [w.day_label for w in ws]
    assert [w.title for w in ws] == [
        "Tonight Sunset", "Tomorrow Sunrise", "Tomorrow Sunset",
        "Friday Sunrise", "Friday Sunset", "Saturday Sunrise", "Saturday Sunset",
    ]


def test_build_windows_outlook_flag_from_day_two():
    ws = build_windows(SUNRISE, SUNSET)
    assert [w.outlook for w in ws] == [False, False, False, True, True, True, True]


def test_build_windows_arrive_by_and_hour():
    ws = build_windows(SUNRISE, SUNSET)
    t, am, pm = ws[0], ws[1], ws[2]
    assert (t.arrive_by, t.hour) == ("2026-09-02T18:47", "2026-09-02T19:00")
    assert (am.arrive_by, am.hour) == ("2026-09-03T06:22", "2026-09-03T06:00")
    assert (pm.arrive_by, pm.hour) == ("2026-09-03T18:46", "2026-09-03T19:00")
    d3pm = ws[6]
    assert (d3pm.arrive_by, d3pm.hour) == ("2026-09-05T18:43", "2026-09-05T19:00")


def test_build_windows_needs_four_days():
    with pytest.raises(IndexError):
        build_windows(SUNRISE[:3], SUNSET[:3])
