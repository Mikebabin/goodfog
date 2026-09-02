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


def fmt_ft(n: int) -> str:
    """JS Number.toLocaleString() for feet: thousands separators, no decimals."""
    return f"{n:,}"


@dataclass(frozen=True)
class Factor:
    label: str
    rating: str  # good | ok | bad


@dataclass(frozen=True)
class Result:
    score: int
    factors: tuple[Factor, ...]
    explanation: str
    lcl_ft: int | None  # None when there is no marine layer (low cloud below threshold)
    status: Status


def score(vp: Viewpoint, hour: Hour) -> Result:
    total = 0
    factors: list[Factor] = []
    lcl = hour.lcl_ft if hour.low_cloud >= MARINE_LAYER_MIN_LOW_CLOUD else None
    status = lcl_status(vp, hour)

    # 1. Low cloud (40 pts)
    lc = hour.low_cloud
    if lc >= 75:
        total += 40; factors.append(Factor(f"Low cloud {lc}%", "good"))
    elif lc >= 50:
        total += 25; factors.append(Factor(f"Low cloud {lc}%", "ok"))
    elif lc >= 30:
        total += 12; factors.append(Factor(f"Low cloud {lc}%", "ok"))
    else:
        factors.append(Factor(f"Low cloud {lc}%", "bad"))

    # 2. Wind (20 pts)
    w = hour.wind_mph
    if w <= 5:
        total += 20; factors.append(Factor(f"Wind {w} mph", "good"))
    elif w <= 10:
        total += 14; factors.append(Factor(f"Wind {w} mph", "ok"))
    elif w <= 18:
        total += 6; factors.append(Factor(f"Wind {w} mph", "ok"))
    else:
        factors.append(Factor(f"Wind {w} mph", "bad"))

    # 3. Clear sky above (20 pts)
    above = max(hour.mid_cloud, hour.high_cloud)
    if above <= 20:
        total += 20; factors.append(Factor(f"Clear above {above}%", "good"))
    elif above <= 50:
        total += 10; factors.append(Factor(f"Some high cloud {above}%", "ok"))
    else:
        factors.append(Factor(f"High cloud {above}%", "bad"))

    # 4. Rain (20 pts)
    r = hour.rain_pct
    if r <= 5:
        total += 20; factors.append(Factor(f"Rain {r}%", "good"))
    elif r <= 20:
        total += 10; factors.append(Factor(f"Rain {r}%", "ok"))
    else:
        factors.append(Factor(f"Rain {r}%", "bad"))

    # 5. Fog base position gates the final likelihood.
    if status.kind == "green":
        total = min(100, total + 10)
        factors.append(Factor(f"Fog base {fmt_ft(lcl)} ft — below you", "good"))
    elif status.kind == "yellow":
        factors.append(Factor(f"Fog base {fmt_ft(lcl)} ft — at the edge", "ok"))
    elif status.kind == "red":
        total = min(total, 35)
        where = "socked in" if status.reason == "low" else "above you"
        factors.append(Factor(f"Fog base {fmt_ft(lcl)} ft — {where}", "bad"))
    else:
        total = min(total, 15)
        factors.append(Factor("No marine layer", "bad"))

    lcl_str = f"~{fmt_ft(lcl)} ft" if lcl is not None else "n/a"
    winds = "calm" if w <= 10 else "moderate"
    if total >= 70:
        if status.kind == "green":
            mid = f"Fog base {lcl_str} sits below you — expect a clean view down onto the layer."
        elif status.kind == "yellow":
            mid = f"Fog base {lcl_str} is near your elevation — swirling fog and dramatic light."
        else:
            mid = f"The marine layer is strong but the fog base {lcl_str} may put you inside it."
        explanation = f"Strong conditions at {vp.name}. {mid} Low cloud at {lc}%, winds {winds} at {w} mph."
    elif total >= 50:
        layer = "Moderate marine layer" if lc >= 50 else "Thin layer"
        explanation = f"Decent shot at {vp.name}. {layer} with {winds} winds. Fog base {lcl_str} — check the live cameras before heading out."
    elif total >= 30:
        parts = [f"Marginal at {vp.name}. "]
        if lc < 30:
            parts.append("Low cloud cover is thin. ")
        if w > 15:
            parts.append("Wind may break up the layer. ")
        if status.kind == "red":
            if status.reason == "high":
                parts.append(f"Fog base {lcl_str} is above your viewpoint — you'd be in it. ")
            else:
                parts.append(f"Fog base {lcl_str} is very low — a deep layer may sock you in. ")
        else:
            parts.append(f"Fog base {lcl_str}.")
        explanation = "".join(parts)
    else:
        parts = [f"Not worth the drive to {vp.name} today. "]
        if r > 20:
            parts.append("Rain in forecast. ")
        if lc < 20:
            parts.append("No marine layer. ")
        if w > 20:
            parts.append("Too windy. ")
        parts.append("Save it for a better day.")
        explanation = "".join(parts)

    return Result(score=total, factors=tuple(factors), explanation=explanation.strip(), lcl_ft=lcl, status=status)


@dataclass(frozen=True)
class ElevationVerdict:
    cls: str    # clear | above | edge | below
    icon: str
    title: str
    detail: str


def elevation_verdict(vp: Viewpoint, hour: Hour) -> ElevationVerdict:
    status = lcl_status(vp, hour)
    lcl_str = f"{fmt_ft(hour.lcl_ft)} ft" if hour.lcl_ft is not None else "—"
    elev = fmt_ft(vp.elev_ft)
    if status.kind == "none":
        return ElevationVerdict(
            "clear", "🔭", "No marine layer",
            f"{vp.name} at {elev} ft. Low cloud is thin — no significant marine layer expected. Clear views, but no inversion to shoot.",
        )
    if status.kind == "green":
        return ElevationVerdict(
            "above", "🏔️", "Above the fog layer",
            f"Fog base sits around {lcl_str} — comfortably below {vp.name} ({elev} ft). You should be looking down onto the layer. {vp.composition}",
        )
    if status.kind == "yellow":
        return ElevationVerdict(
            "edge", "⚡", "Right at the edge",
            f"Fog base near {lcl_str} — close to {vp.name} ({elev} ft). The layer may swirl around you: dramatic but unpredictable. Check the live cameras before committing.",
        )
    reason_text = vp.too_low if status.reason == "low" else vp.too_high
    return ElevationVerdict(
        "below", "🌫️", "Socked in" if status.reason == "low" else "Inside the layer",
        f"Fog base ~{lcl_str}. {reason_text} Consider a higher viewpoint.",
    )
