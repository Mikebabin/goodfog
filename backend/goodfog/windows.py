"""The three viewing windows: tonight's sunset, tomorrow's sunrise, tomorrow's sunset.

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
    id: str          # tonight | tomorrow_am | tomorrow_pm
    title: str       # "Tonight Sunset"
    tab: str         # "🌅 Tonight"
    sun_label: str   # Sunset | Sunrise
    sun_event: str   # local ISO
    arrive_by: str   # local ISO
    hour: str        # forecast hour key


def _window(id: str, title: str, tab: str, label: str, event: str, arrive_offset: int) -> Window:
    return Window(id, title, tab, label, event, minus_minutes(event, arrive_offset), truncate_hour(event))


def build_windows(sunrise: list[str], sunset: list[str]) -> list[Window]:
    return [
        _window("tonight", "Tonight Sunset", "🌅 Tonight", "Sunset", sunset[0], 45),
        _window("tomorrow_am", "Tomorrow Sunrise", "🌄 Tom. AM", "Sunrise", sunrise[1], 30),
        _window("tomorrow_pm", "Tomorrow Sunset", "🌇 Tom. PM", "Sunset", sunset[1], 45),
    ]
