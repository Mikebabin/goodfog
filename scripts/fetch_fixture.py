"""Refresh backend/tests/fixtures/open_meteo.json from the live Open-Meteo API.

Uses the provider's own request_params() so the fixture always matches what the app
requests (variables, timezone, forecast_days). Dates in the fixture are whatever "today"
is when you run it; tests only assert shapes and counts, never specific dates or values.

Run from repo root:  uv run --project backend python scripts/fetch_fixture.py
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

from goodfog.providers.open_meteo import URL, request_params
from goodfog.viewpoints import VIEWPOINTS

OUT = Path(__file__).resolve().parent.parent / "backend" / "tests" / "fixtures" / "open_meteo.json"


def main() -> None:
    params = request_params([(v.lat, v.lon) for v in VIEWPOINTS], models="best_match")
    r = httpx.get(URL, params=params, timeout=15.0)
    r.raise_for_status()
    payload = r.json()
    if len(payload) != len(VIEWPOINTS):
        raise SystemExit(f"expected {len(VIEWPOINTS)} points, got {len(payload)}")
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    days = len(payload[0]["daily"]["sunrise"])
    hours = len(payload[0]["hourly"]["time"])
    print(f"wrote {OUT.relative_to(OUT.parents[3])}: {len(payload)} points, {days} days, {hours} hourly rows")


if __name__ == "__main__":
    main()
