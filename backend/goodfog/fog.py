"""Pure fog-inversion math ported 1:1 from the original index.html. No I/O, no clock."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .viewpoints import Viewpoint

MARINE_LAYER_MIN_LOW_CLOUD = 20  # below this % of low cloud we say "no marine layer"


def jsround(x: float) -> int:
    """JavaScript Math.round: halves round toward +infinity (Python's round() is banker's)."""
    return math.floor(x + 0.5)


def lcl_ft(temp_c: float | None, dew_c: float | None) -> int | None:
    """Lifted condensation level (fog-base height) in feet via the Espy/Bolton approximation:
    ~125 m of lift per °C of temperature–dewpoint spread."""
    if temp_c is None or dew_c is None:
        return None
    return max(0, jsround(125 * (temp_c - dew_c) * 3.281))


@dataclass(frozen=True)
class Hour:
    low_cloud: int
    mid_cloud: int
    high_cloud: int
    wind_mph: int
    rain_pct: int
    temp_f: int
    dewpoint_f: int | None
    lcl_ft: int | None


def hour_from_values(
    temp_c: float | None, dew_c: float | None, *, low, mid, high, wind_kmh: float, rain
) -> Hour:
    return Hour(
        low_cloud=int(low if low is not None else 0),
        mid_cloud=int(mid if mid is not None else 0),
        high_cloud=int(high if high is not None else 0),
        wind_mph=jsround(wind_kmh * 0.621371),
        rain_pct=int(rain if rain is not None else 0),
        temp_f=jsround(temp_c * 9 / 5 + 32) if temp_c is not None else 0,
        dewpoint_f=jsround(dew_c * 9 / 5 + 32) if dew_c is not None else None,
        lcl_ft=lcl_ft(temp_c, dew_c),
    )


@dataclass(frozen=True)
class Status:
    kind: str                 # none | green | yellow | red
    reason: str | None = None  # for red: low (socked in) | high (under the fog)


def lcl_status(vp: Viewpoint, hour: Hour) -> Status:
    if hour.low_cloud < MARINE_LAYER_MIN_LOW_CLOUD or hour.lcl_ft is None:
        return Status("none")
    lcl = hour.lcl_ft
    if lcl < vp.green_ft[0]:
        return Status("red", "low")
    if lcl <= vp.green_ft[1]:
        return Status("green")
    if lcl <= vp.yellow_ft[1]:
        return Status("yellow")
    return Status("red", "high")


@dataclass(frozen=True)
class Verdict:
    label: str
    emoji: str
    cls: str


def verdict(score: int) -> Verdict:
    if score >= 70:
        return Verdict("Go for it!", "🚀", "go")
    if score >= 50:
        return Verdict("Worth a try", "🤔", "try")
    if score >= 30:
        return Verdict("Maybe next time", "😶‍🌫️", "maybe")
    return Verdict("Stay home", "🛑", "no")
