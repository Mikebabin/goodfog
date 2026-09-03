"""Pure helpers for the drive-time feature. No I/O, no clock: `now` is always passed in."""
from __future__ import annotations

import math
from collections import OrderedDict

from .providers.ors import Leg

ROUND_DECIMALS = 3  # ~100 m; cache-key granularity and the only origin precision the server keeps


def validate_origin(lat, lon) -> tuple[float, float]:
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        raise ValueError("lat/lon must be numbers") from None
    if not (math.isfinite(lat_f) and math.isfinite(lon_f)):
        raise ValueError("lat/lon must be finite")
    if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lon_f <= 180.0):
        raise ValueError("lat/lon out of range")
    return lat_f, lon_f


def round_origin(lat: float, lon: float) -> tuple[float, float]:
    return round(lat, ROUND_DECIMALS), round(lon, ROUND_DECIMALS)


def build_drive_response(viewpoints, legs: list[Leg | None], origin: tuple[float, float]) -> dict:
    if len(legs) != len(viewpoints):
        raise ValueError("one leg per viewpoint required")
    return {
        "origin": {"lat": origin[0], "lon": origin[1]},
        "drives": {
            vp.id: None if leg is None else {"seconds": leg.seconds, "meters": leg.meters}
            for vp, leg in zip(viewpoints, legs, strict=True)
        },
    }


class DriveCache:
    """Tiny TTL cache keyed on a rounded origin. Insertion-ordered; oldest evicted when full."""

    def __init__(self, ttl_seconds: float = 3600.0, max_entries: int = 500) -> None:
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._items: OrderedDict[tuple[float, float], tuple[float, dict]] = OrderedDict()

    def get(self, key: tuple[float, float], now: float) -> dict | None:
        item = self._items.get(key)
        if item is None:
            return None
        stored_at, value = item
        if now - stored_at > self.ttl:
            del self._items[key]
            return None
        return value

    def put(self, key: tuple[float, float], value: dict, now: float) -> None:
        if key in self._items:
            del self._items[key]
        self._items[key] = (now, value)
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)

    def __len__(self) -> int:
        return len(self._items)
