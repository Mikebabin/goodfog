from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from .fog import Hour, elevation_verdict, score, verdict
from .providers.open_meteo import Forecast
from .viewpoints import Viewpoint
from .windows import build_windows


def _result(vp: Viewpoint, hour: Hour | None) -> dict | None:
    if hour is None:
        return None
    r = score(vp, hour)
    return {
        "score": r.score,
        "verdict": asdict(verdict(r.score)),
        "status": asdict(r.status),
        "factors": [asdict(f) for f in r.factors],
        "explanation": r.explanation,
        "elevation": asdict(elevation_verdict(vp, hour)),
        "lcl_ft": r.lcl_ft,
        "wx": asdict(hour),
    }


def _viewpoint(vp: Viewpoint, fc: Forecast) -> dict:
    # Sunrise/sunset differ by up to a minute across points; the original app used the
    # selected spot's own sun times, so each viewpoint builds its windows from its own
    # forecast's daily block rather than sharing one set across all viewpoints.
    windows = build_windows(list(fc.sunrise), list(fc.sunset))
    return {
        "id": vp.id,
        "name": vp.name,
        "elev_ft": vp.elev_ft,
        "desc": vp.desc,
        "green_ft": list(vp.green_ft),
        "yellow_ft": list(vp.yellow_ft),
        "dawn_gated": vp.dawn_gated,
        "composition": vp.composition,
        "access": vp.access,
        "cam_tip": vp.cam_tip,
        "windows": [asdict(w) for w in windows],
        "results": {w.id: _result(vp, fc.hour_at(w.hour)) for w in windows},
    }


def build_snapshot(
    viewpoints, forecasts: list[Forecast], *, now: datetime, app_version: str, commit: str
) -> dict:
    # Top-level windows come from the first forecast and are used by the frontend only for
    # tab ids/labels; each viewpoint below carries its own windows built from its own sun times.
    windows = build_windows(list(forecasts[0].sunrise), list(forecasts[0].sunset))
    return {
        "app_version": app_version,
        "commit": commit,
        "generated_at": now.isoformat(timespec="seconds"),
        "windows": [asdict(w) for w in windows],
        "viewpoints": [_viewpoint(vp, fc) for vp, fc in zip(viewpoints, forecasts, strict=True)],
    }
