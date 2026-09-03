"""The seven viewing windows: tonight's sunset, then sunrise and sunset for the next three days.

Times are Open-Meteo local ISO strings without offset (timezone=America/Los_Angeles);
the frontend formats them as-is, so no timezone math happens anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

_FMT = "%Y-%m-%dT%H:%M"


def truncate_hour(iso: str) -> str:
    """Original JS floored the sun event to the hour to look up the forecast row."""
    return iso[:13] + ":00"


def minus_minutes(iso: str, minutes: int) -> str:
    return (datetime.fromisoformat(iso) - timedelta(minutes=minutes)).strftime(_FMT)


@dataclass(frozen=True)
class Window:
    id: str          # tonight | d1_am | d1_pm | d2_am | d2_pm | d3_am | d3_pm
    day: int         # 0 = today .. 3
    day_label: str   # "Tonight" | "Tomorrow" | "Fri" ... (tab strip)
    outlook: bool    # day >= 2: forecast skill drops past 48 h; label only, never changes scores
    title: str       # "Tonight Sunset", "Friday Sunrise"
    tab: str         # same as day_label; kept for the top-level windows list
    sun_label: str   # Sunset | Sunrise
    sun_event: str   # local ISO
    arrive_by: str   # local ISO
    hour: str        # forecast hour key


SUNRISE_OFFSET_MIN = 30
SUNSET_OFFSET_MIN = 45
OUTLOOK_FROM_DAY = 2


def day_labels(day: int, event: str) -> tuple[str, str]:
    """(short, long) labels for a day index: ("Tonight", "Tonight"), ("Tomorrow", "Tomorrow"), ("Fri", "Friday")."""
    if day == 0:
        return "Tonight", "Tonight"
    if day == 1:
        return "Tomorrow", "Tomorrow"
    d = datetime.fromisoformat(event)
    return d.strftime("%a"), d.strftime("%A")


def _window(id: str, day: int, sun_label: str, event: str) -> Window:
    short, long = day_labels(day, event)
    offset = SUNRISE_OFFSET_MIN if sun_label == "Sunrise" else SUNSET_OFFSET_MIN
    return Window(
        id=id, day=day, day_label=short, outlook=day >= OUTLOOK_FROM_DAY,
        title=f"{long} {sun_label}", tab=short, sun_label=sun_label,
        sun_event=event, arrive_by=minus_minutes(event, offset), hour=truncate_hour(event),
    )


def build_windows(sunrise: list[str], sunset: list[str]) -> list[Window]:
    """Tonight's sunset, then sunrise + sunset for days 1..3. Raises IndexError if the daily block is short."""
    ws = [_window("tonight", 0, "Sunset", sunset[0])]
    for day in (1, 2, 3):
        ws.append(_window(f"d{day}_am", day, "Sunrise", sunrise[day]))
        ws.append(_window(f"d{day}_pm", day, "Sunset", sunset[day]))
    return ws
