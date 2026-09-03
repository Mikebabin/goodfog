# Good Fog — Drive Time Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user enter an address or use browser geolocation and see the drive time to each of the eight viewpoints plus a "Leave by" time, powered by OpenRouteService through a backend proxy.

**Architecture:** The FastAPI backend gains an `OrsProvider` (geocode + one matrix call), two proxied endpoints (`GET /api/geocode`, `POST /api/drive`) with a rounded-origin TTL cache, and a `features.drive` flag in the snapshot. The Svelte frontend gains pure helpers (`drive.js`, `origin.js`, `geolocate.js`), an `OriginPicker` component, and drive labels on the picker cards, Timing card and Plan tab. The ORS key lives only in the `ORS_API_KEY` env var; without it the whole feature is hidden.

**Tech Stack:** Python 3.12, FastAPI, httpx, pydantic (already present), pytest + respx; Svelte 5, Vite, vitest. **No new dependencies on either side.**

**Spec:** `docs/superpowers/specs/2026-09-02-goodfog-drive-time-design.md`

## Global Constraints

- Secrets only via env vars. The ORS key is read from `ORS_API_KEY` and must never appear in logs, error messages, responses, or the frontend bundle.
- Origins (user coordinates / address text) are never logged or persisted server-side; the cache holds coordinates rounded to 3 decimals only.
- All coordinates are `(lat, lon)` tuples inside our code; the ORS provider flips to `[lon, lat]` at the HTTP boundary and nowhere else.
- One upstream matrix request per (rounded) origin; cache TTL 3600 s, max 500 entries.
- Endpoint error contract: `503 {"detail": "routing_unavailable"}` (no provider / upstream failure), `404 {"detail": "no_match"}` (geocode miss), `422` (bad input).
- Frontend helpers are pure and tested; times stay local ISO strings (`YYYY-MM-DDTHH:MM`), no timezone math. Drive minutes round **up**.
- UI copy, exact: placeholder "Your address or neighborhood"; resolved line "From **{label}** · drive times, no traffic"; errors "Address not found", "Location blocked or unavailable", "Drive times unavailable right now"; geolocation label "My location"; card badge `~{fmtDrive} drive` or `—`; Plan line `🚗 {fmtDrive} drive · no traffic`.
- No new npm or Python dependencies. If one seems needed, stop and report.
- Version 0.3.0 in `frontend/package.json`, `frontend/package-lock.json` and `backend/pyproject.toml` (Task 8 only).
- Commands: backend tests `cd backend && uv run pytest`; frontend tests `cd frontend && npm test`; frontend build `cd frontend && npm run build`.
- Work on branch `drive-time`. Commit after each task.

---

## File map

| File | Responsibility |
|---|---|
| `backend/goodfog/config.py` | `Settings.ors_api_key` from env |
| `backend/goodfog/providers/ors.py` | **new** — `OrsProvider.geocode` / `.matrix`, `Place`, `Leg`, `RoutingError` |
| `backend/goodfog/drive.py` | **new** — pure: `validate_origin`, `round_origin`, `build_drive_response`, `DriveCache` |
| `backend/goodfog/snapshot.py` | `features` echoed into snapshot |
| `backend/goodfog/poller.py` | carries `features`, exposes `drive` in health |
| `backend/goodfog/app.py` | `/api/geocode`, `/api/drive`, provider wiring |
| `backend/tests/fixtures/ors_geocode.json`, `ors_matrix.json` | **new** fixtures |
| `backend/tests/test_ors.py`, `test_drive.py` | **new** tests; additions to `test_app.py`, `test_config.py`, `test_snapshot.py` |
| `frontend/src/lib/api.js` | `geocode`, `fetchDrive` |
| `frontend/src/lib/drive.js` | **new** — `driveMinutes`, `fmtDrive`, `leaveBy` |
| `frontend/src/lib/origin.js` | **new** — `loadOrigin`, `saveOrigin`, `ORIGIN_KEY` |
| `frontend/src/lib/geolocate.js` | **new** — `getPosition` (promise wrapper, injectable) |
| `frontend/src/components/OriginPicker.svelte` | **new** — input / 📍 / resolved label |
| `frontend/src/components/LocationPicker.svelte`, `TimingCard.svelte`, `PlanView.svelte`, `WindowView.svelte` | drive props |
| `frontend/src/App.svelte` | origin state, drive fetching, wiring |
| `docker-compose.yml`, `README.md`, `CLAUDE.md` | `ORS_API_KEY` documented |

---

### Task 1: `ORS_API_KEY` setting, compose env, docs

**Files:**
- Modify: `backend/goodfog/config.py`
- Modify: `backend/tests/test_config.py`
- Modify: `docker-compose.yml`
- Modify: `README.md`, `CLAUDE.md`

**Interfaces:**
- Produces: `Settings.ors_api_key: str | None` (defaulted field, so existing `Settings(...)` calls keep working).

- [ ] **Step 1: Write the failing test** — append to `backend/tests/test_config.py`:

```python
def test_ors_api_key_optional_and_stripped():
    assert Settings.from_env({}).ors_api_key is None
    assert Settings.from_env({"ORS_API_KEY": "   "}).ors_api_key is None
    assert Settings.from_env({"ORS_API_KEY": " abc123 "}).ors_api_key == "abc123"
```

- [ ] **Step 2: Run it** — `cd backend && uv run pytest tests/test_config.py -v` → FAIL (`AttributeError: ors_api_key` / `TypeError`).

- [ ] **Step 3: Implement** — in `backend/goodfog/config.py`, add the field (last, with a default) and the env read:

```python
@dataclass(frozen=True)
class Settings:
    poll_minutes: int
    open_meteo_models: str
    app_version: str
    commit: str
    ors_api_key: str | None = None  # OpenRouteService; drive times are disabled when unset

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        if env is None:
            env = os.environ
        # BUILD_COMMIT is baked into the image by backend/Dockerfile from the SOURCE_COMMIT build
        # arg. The runtime SOURCE_COMMIT env var is deliberately ignored: Coolify's compose parser
        # injects its own (empty/"dev") copy into the container, which is never the real sha.
        commit = (env.get("BUILD_COMMIT") or "").strip()[:7] or "dev"
        return cls(
            poll_minutes=_positive_int(env, "POLL_MINUTES", "15"),
            open_meteo_models=env.get("OPEN_METEO_MODELS", "best_match"),
            app_version=(env.get("APP_VERSION") or "").strip() or _pyproject_version(),
            commit=commit,
            ors_api_key=(env.get("ORS_API_KEY") or "").strip() or None,
        )
```

- [ ] **Step 4: Run** — `uv run pytest tests/test_config.py -v` → PASS.

- [ ] **Step 5: Compose + docs.**

`docker-compose.yml`, `api` service `environment` block becomes:

```yaml
    environment:
      POLL_MINUTES: ${POLL_MINUTES:-15}
      OPEN_METEO_MODELS: ${OPEN_METEO_MODELS:-best_match}
      # Optional. OpenRouteService key (https://openrouteservice.org, free plan). Enables the
      # drive-time feature; the UI hides it entirely when this is empty.
      ORS_API_KEY: ${ORS_API_KEY:-}
```

`README.md`: after the `## Running it` code block, add:

```markdown
### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `POLL_MINUTES` | `15` | Forecast refresh interval |
| `OPEN_METEO_MODELS` | `best_match` | Open-Meteo model selection |
| `ORS_API_KEY` | _(unset)_ | Optional [OpenRouteService](https://openrouteservice.org) key. Enables "drive time from your location"; the feature is hidden without it. Free plan is plenty. |

Put secrets in a local `.env` (git-ignored); in production set them in the Coolify app.
```

`CLAUDE.md`: line 7 list gains `drive.py` (pure drive helpers + cache) and `providers/ors.py`; replace the "No secrets" bullet with:

```markdown
- Secrets only via env vars: `ORS_API_KEY` (optional; drive times hidden without it, never logged or sent to the browser). Non-secret config: `POLL_MINUTES`, `OPEN_METEO_MODELS`. Never commit `.env`.
```

- [ ] **Step 6: Full backend suite + commit**

```bash
cd backend && uv run pytest -q
cd .. && git add backend/goodfog/config.py backend/tests/test_config.py docker-compose.yml README.md CLAUDE.md
git commit -m "feat: optional ORS_API_KEY setting (#7)"
```

---

### Task 2: OpenRouteService provider

**Files:**
- Create: `backend/goodfog/providers/ors.py`
- Create: `backend/tests/fixtures/ors_geocode.json`, `backend/tests/fixtures/ors_matrix.json`
- Create: `backend/tests/test_ors.py`

**Interfaces:**
- Consumes: `ProviderError` from `goodfog/providers/__init__.py`; `VIEWPOINTS` (8 entries) from `goodfog/viewpoints.py`.
- Produces: `Place(label, lat, lon)`, `Leg(seconds: int, meters: int)`, `RoutingError(ProviderError)`, `OrsProvider(client, api_key)` with `async geocode(text) -> Place | None` and `async matrix(origin: (lat, lon), dests: list[(lat, lon)]) -> list[Leg | None]`; constants `GEOCODE_URL`, `MATRIX_URL`.

- [ ] **Step 1: Fixtures.**

`backend/tests/fixtures/ors_geocode.json`:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [-122.4194, 37.7749] },
      "properties": { "label": "San Francisco, CA, USA", "name": "San Francisco", "country_a": "USA" }
    }
  ]
}
```

`backend/tests/fixtures/ors_matrix.json` (one source, eight destinations, sixth unroutable):

```json
{
  "durations": [[1540.2, 1490.7, 1510.0, 900.5, 2400.0, null, 2000.0, 2600.9]],
  "distances": [[14830.1, 14200.0, 14500.0, 6000.0, 30000.0, null, 25000.0, 35000.0]],
  "metadata": { "service": "matrix" }
}
```

- [ ] **Step 2: Write the failing tests** — `backend/tests/test_ors.py`:

```python
import json
from pathlib import Path

import httpx
import pytest
import respx

from goodfog.providers.ors import GEOCODE_URL, MATRIX_URL, Leg, OrsProvider, Place, RoutingError
from goodfog.viewpoints import VIEWPOINTS

FIX = Path(__file__).parent / "fixtures"
GEOCODE = json.loads((FIX / "ors_geocode.json").read_text())
MATRIX = json.loads((FIX / "ors_matrix.json").read_text())
ORIGIN = (37.7749, -122.4194)
DESTS = [(v.lat, v.lon) for v in VIEWPOINTS]


@respx.mock
async def test_geocode_returns_first_place_with_focus_and_country():
    route = respx.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json=GEOCODE))
    async with httpx.AsyncClient() as client:
        place = await OrsProvider(client, "test-key").geocode("san francisco")
    assert place == Place(label="San Francisco, CA, USA", lat=37.7749, lon=-122.4194)
    q = route.calls.last.request.url.params
    assert q["api_key"] == "test-key" and q["text"] == "san francisco" and q["size"] == "1"
    assert q["focus.point.lat"] == "37.83" and q["focus.point.lon"] == "-122.48"
    assert q["boundary.country"] == "US"


@respx.mock
async def test_geocode_empty_features_is_none():
    respx.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []}))
    async with httpx.AsyncClient() as client:
        assert await OrsProvider(client, "k").geocode("zzzz") is None


@respx.mock
async def test_geocode_http_error_raises():
    respx.get(GEOCODE_URL).mock(return_value=httpx.Response(401, json={"error": "bad key"}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError, match="HTTP 401"):
            await OrsProvider(client, "k").geocode("x")


@respx.mock
async def test_geocode_malformed_raises():
    respx.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json={"features": [{"geometry": {}}]}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError):
            await OrsProvider(client, "k").geocode("x")


@respx.mock
async def test_matrix_returns_legs_in_order_with_none_for_null():
    route = respx.post(MATRIX_URL).mock(return_value=httpx.Response(200, json=MATRIX))
    async with httpx.AsyncClient() as client:
        legs = await OrsProvider(client, "test-key").matrix(ORIGIN, DESTS)
    assert len(legs) == 8
    assert legs[0] == Leg(seconds=1540, meters=14830)
    assert legs[5] is None
    assert legs[7] == Leg(seconds=2601, meters=35000)
    req = route.calls.last.request
    assert req.headers["authorization"] == "test-key"
    body = json.loads(req.content)
    assert body["locations"][0] == [-122.4194, 37.7749]  # ORS wants [lon, lat]
    assert body["locations"][1] == [VIEWPOINTS[0].lon, VIEWPOINTS[0].lat]
    assert body["sources"] == [0] and body["destinations"] == list(range(1, 9))
    assert body["metrics"] == ["duration", "distance"]


@respx.mock
async def test_matrix_wrong_leg_count_raises():
    respx.post(MATRIX_URL).mock(return_value=httpx.Response(200, json={"durations": [[1.0]], "distances": [[1.0]]}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError):
            await OrsProvider(client, "k").matrix(ORIGIN, DESTS)


@respx.mock
async def test_matrix_network_error_raises_without_leaking_key():
    respx.post(MATRIX_URL).mock(side_effect=httpx.ConnectTimeout("slow"))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError) as ei:
            await OrsProvider(client, "secret-key").matrix(ORIGIN, DESTS)
    assert "secret-key" not in str(ei.value)
```

- [ ] **Step 3: Run** — `cd backend && uv run pytest tests/test_ors.py -v` → FAIL (`ModuleNotFoundError: goodfog.providers.ors`).

- [ ] **Step 4: Implement** — `backend/goodfog/providers/ors.py`:

```python
"""OpenRouteService client: Pelias geocoding and a driving-car duration/distance matrix.

Coordinates are (lat, lon) everywhere in goodfog; ORS speaks [lon, lat], so the flip happens
only inside this module. Error messages carry status codes / exception names only — never the
key, the query text, or coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from . import ProviderError

BASE = "https://api.openrouteservice.org"
GEOCODE_URL = f"{BASE}/geocode/search"
MATRIX_URL = f"{BASE}/v2/matrix/driving-car"
FOCUS_LAT = 37.83   # Golden Gate: biases ambiguous addresses toward SF/Marin
FOCUS_LON = -122.48
TIMEOUT_S = 10.0


class RoutingError(ProviderError):
    """ORS request failed or returned an unexpected shape."""


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Leg:
    seconds: int
    meters: int


class OrsProvider:
    def __init__(self, client: httpx.AsyncClient, api_key: str) -> None:
        self.client = client
        self.api_key = api_key

    async def geocode(self, text: str) -> Place | None:
        params = {
            "api_key": self.api_key,
            "text": text,
            "size": 1,
            "focus.point.lat": FOCUS_LAT,
            "focus.point.lon": FOCUS_LON,
            "boundary.country": "US",
        }
        body = await self._request("GET", GEOCODE_URL, params=params)
        try:
            features = body["features"]
            if not features:
                return None
            f = features[0]
            lon, lat = f["geometry"]["coordinates"][:2]
            return Place(label=str(f["properties"]["label"]), lat=float(lat), lon=float(lon))
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise RoutingError(f"malformed geocode response: {type(e).__name__}") from e

    async def matrix(self, origin: tuple[float, float], dests: list[tuple[float, float]]) -> list[Leg | None]:
        locations = [[origin[1], origin[0]]] + [[lon, lat] for lat, lon in dests]
        payload = {
            "locations": locations,
            "sources": [0],
            "destinations": list(range(1, len(locations))),
            "metrics": ["duration", "distance"],
        }
        body = await self._request("POST", MATRIX_URL, json=payload, headers={"Authorization": self.api_key})
        try:
            durations = body["durations"][0]
            distances = body["distances"][0]
        except (KeyError, IndexError, TypeError) as e:
            raise RoutingError(f"malformed matrix response: {type(e).__name__}") from e
        if len(durations) != len(dests) or len(distances) != len(dests):
            raise RoutingError("matrix returned wrong number of legs")
        try:
            return [
                None if d is None or m is None else Leg(seconds=int(round(d)), meters=int(round(m)))
                for d, m in zip(durations, distances, strict=True)
            ]
        except (TypeError, ValueError) as e:
            raise RoutingError(f"malformed matrix cell: {type(e).__name__}") from e

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            r = await self.client.request(method, url, timeout=TIMEOUT_S, **kwargs)
        except httpx.HTTPError as e:
            raise RoutingError(type(e).__name__) from e
        if r.status_code != 200:
            raise RoutingError(f"HTTP {r.status_code}")
        try:
            body = r.json()
        except ValueError as e:
            raise RoutingError("non-JSON response") from e
        if not isinstance(body, dict):
            raise RoutingError("unexpected response shape")
        return body
```

- [ ] **Step 5: Run** — `uv run pytest tests/test_ors.py -v` → all PASS. Then `uv run pytest -q`.

- [ ] **Step 6: Commit**

```bash
git add backend/goodfog/providers/ors.py backend/tests/test_ors.py backend/tests/fixtures/ors_geocode.json backend/tests/fixtures/ors_matrix.json
git commit -m "feat: OpenRouteService provider (geocode + matrix) (#7)"
```

---

### Task 3: Pure drive helpers and TTL cache

**Files:**
- Create: `backend/goodfog/drive.py`
- Create: `backend/tests/test_drive.py`

**Interfaces:**
- Consumes: `Leg` from `goodfog/providers/ors.py`; `VIEWPOINTS`.
- Produces: `validate_origin(lat, lon) -> tuple[float, float]` (raises `ValueError`), `round_origin(lat, lon) -> tuple[float, float]`, `build_drive_response(viewpoints, legs, origin) -> dict`, `DriveCache(ttl_seconds=3600.0, max_entries=500)` with `get(key, now) -> dict | None`, `put(key, value, now)`, `__len__`.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_drive.py`:

```python
import pytest

from goodfog.drive import DriveCache, build_drive_response, round_origin, validate_origin
from goodfog.providers.ors import Leg
from goodfog.viewpoints import VIEWPOINTS


def test_round_origin_three_decimals():
    assert round_origin(37.774929, -122.419416) == (37.775, -122.419)


def test_validate_origin_accepts_and_coerces():
    assert validate_origin("37.5", -122) == (37.5, -122.0)


@pytest.mark.parametrize(
    "lat,lon",
    [(91, 0), (-91, 0), (0, 181), (0, -181), (float("nan"), 0), (0, float("inf")), ("x", 0), (None, 0)],
)
def test_validate_origin_rejects(lat, lon):
    with pytest.raises(ValueError):
        validate_origin(lat, lon)


def test_build_drive_response_shape():
    legs = [Leg(seconds=100 * i, meters=1000 * i) for i in range(1, 8)] + [None]
    out = build_drive_response(VIEWPOINTS, legs, (37.775, -122.419))
    assert out["origin"] == {"lat": 37.775, "lon": -122.419}
    assert list(out["drives"]) == [v.id for v in VIEWPOINTS]
    assert out["drives"][VIEWPOINTS[0].id] == {"seconds": 100, "meters": 1000}
    assert out["drives"][VIEWPOINTS[-1].id] is None


def test_build_drive_response_requires_one_leg_per_viewpoint():
    with pytest.raises(ValueError):
        build_drive_response(VIEWPOINTS, [None], (0.0, 0.0))


def test_cache_miss_hit_and_expiry():
    c = DriveCache(ttl_seconds=60, max_entries=10)
    key = (37.775, -122.419)
    assert c.get(key, now=1000.0) is None
    c.put(key, {"x": 1}, now=1000.0)
    assert c.get(key, now=1059.0) == {"x": 1}
    assert c.get(key, now=1061.0) is None
    assert len(c) == 0


def test_cache_evicts_oldest_when_full():
    c = DriveCache(ttl_seconds=60, max_entries=2)
    c.put((1.0, 1.0), {"a": 1}, now=0.0)
    c.put((2.0, 2.0), {"b": 1}, now=1.0)
    c.put((3.0, 3.0), {"c": 1}, now=2.0)
    assert len(c) == 2
    assert c.get((1.0, 1.0), now=3.0) is None
    assert c.get((3.0, 3.0), now=3.0) == {"c": 1}


def test_cache_put_refreshes_existing_key():
    c = DriveCache(ttl_seconds=60, max_entries=2)
    c.put((1.0, 1.0), {"a": 1}, now=0.0)
    c.put((2.0, 2.0), {"b": 1}, now=1.0)
    c.put((1.0, 1.0), {"a": 2}, now=2.0)  # re-put moves it to newest
    c.put((3.0, 3.0), {"c": 1}, now=3.0)  # evicts (2.0, 2.0), the oldest
    assert c.get((1.0, 1.0), now=4.0) == {"a": 2}
    assert c.get((2.0, 2.0), now=4.0) is None
```

- [ ] **Step 2: Run** — `cd backend && uv run pytest tests/test_drive.py -v` → FAIL (`ModuleNotFoundError: goodfog.drive`).

- [ ] **Step 3: Implement** — `backend/goodfog/drive.py`:

```python
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
```

- [ ] **Step 4: Run** — `uv run pytest tests/test_drive.py -v` → PASS; `uv run pytest -q`.

- [ ] **Step 5: Commit**

```bash
git add backend/goodfog/drive.py backend/tests/test_drive.py
git commit -m "feat: pure drive helpers and rounded-origin TTL cache (#7)"
```

---

### Task 4: `features` in snapshot, poller and health

**Files:**
- Modify: `backend/goodfog/snapshot.py`
- Modify: `backend/goodfog/poller.py`
- Modify: `backend/goodfog/app.py` (only `build_poller`)
- Modify: `backend/tests/test_snapshot.py`, `backend/tests/test_poller.py`, `backend/tests/test_app.py`

**Interfaces:**
- Consumes: `Settings.ors_api_key` (Task 1).
- Produces: `build_snapshot(..., features: dict | None = None)` emitting `"features": {...}`; `Poller(provider, poll_minutes, app_version, commit, features: dict | None = None)` with `.features` dict and `health()["drive"]: bool`.

- [ ] **Step 1: Write the failing tests.**

Append to `backend/tests/test_snapshot.py`:

```python
def test_features_echoed_and_default_empty():
    fcs = parse_open_meteo(FIXTURE, 8)
    assert _snap()["features"] == {}
    s = build_snapshot(VIEWPOINTS, fcs, now=NOW, app_version="x", commit="y", features={"drive": True})
    assert s["features"] == {"drive": True}
```

Append to `backend/tests/test_poller.py`:

```python
async def test_poller_passes_features_to_snapshot_and_health():
    p = Poller(FakeProvider(), poll_minutes=15, app_version="0.1.0", commit="dev", features={"drive": True})
    await p.poll_once(now=T0)
    assert p.snapshot["features"] == {"drive": True}
    assert p.health(now=T0)["drive"] is True
    plain = Poller(FakeProvider(), poll_minutes=15, app_version="0.1.0", commit="dev")
    assert plain.health(now=T0)["drive"] is False
```

Append to `backend/tests/test_app.py`:

```python
async def test_build_poller_sets_drive_feature_from_key():
    async with httpx.AsyncClient() as client:
        without = build_poller(_settings(), client)
        with_key = build_poller(
            Settings(poll_minutes=15, open_meteo_models="best_match", app_version="0.1.0", commit="abc1234", ors_api_key="k"),
            client,
        )
    assert without.features == {"drive": False}
    assert with_key.features == {"drive": True}
```

- [ ] **Step 2: Run** — `cd backend && uv run pytest tests/test_snapshot.py tests/test_poller.py tests/test_app.py -v` → the three new tests FAIL.

- [ ] **Step 3: Implement.**

`backend/goodfog/snapshot.py` — change `build_snapshot`'s signature and return:

```python
def build_snapshot(
    viewpoints,
    forecasts: list[Forecast],
    *,
    now: datetime,
    app_version: str,
    commit: str,
    features: dict | None = None,
) -> dict:
    # Top-level windows come from the first forecast and are used by the frontend only for
    # tab ids/labels; each viewpoint below carries its own windows built from its own sun times.
    windows = build_windows(list(forecasts[0].sunrise), list(forecasts[0].sunset))
    return {
        "app_version": app_version,
        "commit": commit,
        "generated_at": now.isoformat(timespec="seconds"),
        "features": dict(features or {}),
        "windows": [asdict(w) for w in windows],
        "viewpoints": [_viewpoint(vp, fc) for vp, fc in zip(viewpoints, forecasts, strict=True)],
    }
```

`backend/goodfog/poller.py`:

```python
class Poller:
    def __init__(self, provider, poll_minutes: int, app_version: str, commit: str, features: dict | None = None) -> None:
        self.provider = provider
        self.interval = timedelta(minutes=poll_minutes)
        self.app_version = app_version
        self.commit = commit
        self.features = dict(features or {})
        self.snapshot: dict | None = None
        self.generated_at: datetime | None = None
        self.last_error: str | None = None
```

In `poll_once`, the `build_snapshot(...)` call gains `features=self.features`:

```python
        self.snapshot = build_snapshot(
            VIEWPOINTS, forecasts, now=now, app_version=self.app_version, commit=self.commit, features=self.features
        )
```

In `health()`, add after `"last_error"`:

```python
            "drive": bool(self.features.get("drive", False)),
```

`backend/goodfog/app.py` — `build_poller`:

```python
def build_poller(settings: Settings, client: httpx.AsyncClient) -> Poller:
    provider = OpenMeteoProvider([(v.lat, v.lon) for v in VIEWPOINTS], client, models=settings.open_meteo_models)
    features = {"drive": settings.ors_api_key is not None}
    return Poller(provider, settings.poll_minutes, settings.app_version, settings.commit, features=features)
```

`backend/tests/test_app.py` already imports `Settings`; confirm `build_poller` is imported (it is).

- [ ] **Step 4: Run** — `uv run pytest -q` → all PASS (existing snapshot shape tests still pass because they check specific keys, not the full set; if `test_top_level_shape` asserts an exact key set, add `"features"` to it).

- [ ] **Step 5: Commit**

```bash
git add backend/goodfog/snapshot.py backend/goodfog/poller.py backend/goodfog/app.py backend/tests/test_snapshot.py backend/tests/test_poller.py backend/tests/test_app.py
git commit -m "feat: features.drive flag in snapshot and health (#7)"
```

---

### Task 5: `/api/geocode` and `/api/drive` endpoints

**Files:**
- Modify: `backend/goodfog/app.py`
- Modify: `backend/tests/test_app.py`

**Interfaces:**
- Consumes: `OrsProvider`, `RoutingError`, `Place`, `Leg` (Task 2); `DriveCache`, `build_drive_response`, `round_origin`, `validate_origin` (Task 3); `Settings.ors_api_key` (Task 1).
- Produces: `create_app(settings=None, poller=None, ors: OrsProvider | None = None, drive_cache: DriveCache | None = None)`; `app.state.ors`, `app.state.drive_cache`; `GET /api/geocode?q=` and `POST /api/drive` per the Global Constraints error contract.

- [ ] **Step 1: Write the failing tests** — add to `backend/tests/test_app.py`. New imports at the top:

```python
import pytest

from goodfog.drive import DriveCache
from goodfog.providers.ors import Leg, OrsProvider, Place, RoutingError
from goodfog.viewpoints import VIEWPOINTS
```

Then append:

```python
class FakeOrs:
    def __init__(self, legs=None, place="default", fail=False):
        self.legs = legs
        self.place = place
        self.fail = fail
        self.matrix_calls = 0
        self.geocode_calls = []

    async def geocode(self, text):
        self.geocode_calls.append(text)
        if self.fail:
            raise RoutingError("HTTP 500")
        if self.place == "default":
            return Place(label="Somewhere, CA, USA", lat=37.7, lon=-122.4)
        return self.place

    async def matrix(self, origin, dests):
        self.matrix_calls += 1
        if self.fail:
            raise RoutingError("HTTP 500")
        if self.legs is not None:
            return self.legs
        return [Leg(seconds=600 + 60 * i, meters=10000 + 1000 * i) for i in range(len(dests))]


def _drive_client(ors, cache=None):
    poller = Poller(FakeProvider(), 15, "0.1.0", "abc1234")
    app = create_app(_settings(), poller=poller, ors=ors, drive_cache=cache)
    app.state.poller = poller
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_drive_and_geocode_503_without_provider():
    async with _drive_client(None) as c:
        d = await c.post("/api/drive", json={"lat": 37.7, "lon": -122.4})
        g = await c.get("/api/geocode", params={"q": "sf"})
    assert d.status_code == 503 and d.json() == {"detail": "routing_unavailable"}
    assert g.status_code == 503 and g.json() == {"detail": "routing_unavailable"}


async def test_drive_returns_legs_and_caches_by_rounded_origin():
    ors = FakeOrs()
    async with _drive_client(ors, DriveCache()) as c:
        r1 = await c.post("/api/drive", json={"lat": 37.77491, "lon": -122.41942})
        r2 = await c.post("/api/drive", json={"lat": 37.77499, "lon": -122.41939})
    assert r1.status_code == 200
    body = r1.json()
    assert body["origin"] == {"lat": 37.775, "lon": -122.419}
    assert set(body["drives"]) == {v.id for v in VIEWPOINTS}
    assert body["drives"][VIEWPOINTS[0].id] == {"seconds": 600, "meters": 10000}
    assert r2.json() == body
    assert ors.matrix_calls == 1


async def test_drive_null_leg_and_upstream_failure():
    legs = [None] + [Leg(seconds=1, meters=1)] * 7
    async with _drive_client(FakeOrs(legs=legs)) as c:
        r = await c.post("/api/drive", json={"lat": 37.7, "lon": -122.4})
    assert r.status_code == 200 and r.json()["drives"][VIEWPOINTS[0].id] is None
    async with _drive_client(FakeOrs(fail=True)) as c:
        r = await c.post("/api/drive", json={"lat": 37.7, "lon": -122.4})
    assert r.status_code == 503 and r.json() == {"detail": "routing_unavailable"}


@pytest.mark.parametrize("body", [{"lat": 91, "lon": 0}, {"lat": 0, "lon": -181}, {"lat": "x", "lon": 0}, {"lon": 0}])
async def test_drive_rejects_bad_coordinates(body):
    ors = FakeOrs()
    async with _drive_client(ors) as c:
        r = await c.post("/api/drive", json=body)
    assert r.status_code == 422
    assert ors.matrix_calls == 0


async def test_geocode_ok_no_match_blank_long_and_failure():
    ors = FakeOrs()
    async with _drive_client(ors) as c:
        ok = await c.get("/api/geocode", params={"q": "  24th st  "})
        blank = await c.get("/api/geocode", params={"q": "   "})
        long = await c.get("/api/geocode", params={"q": "x" * 201})
    assert ok.status_code == 200 and ok.json() == {"label": "Somewhere, CA, USA", "lat": 37.7, "lon": -122.4}
    assert ors.geocode_calls == ["24th st"]
    assert blank.status_code == 422 and long.status_code == 422
    async with _drive_client(FakeOrs(place=None)) as c:
        r = await c.get("/api/geocode", params={"q": "zzz"})
    assert r.status_code == 404 and r.json() == {"detail": "no_match"}
    async with _drive_client(FakeOrs(fail=True)) as c:
        r = await c.get("/api/geocode", params={"q": "zzz"})
    assert r.status_code == 503


async def test_lifespan_builds_ors_only_when_key_set():
    fake = FakePoller()
    keyed = Settings(poll_minutes=15, open_meteo_models="best_match", app_version="0.1.0", commit="abc1234", ors_api_key="k")

    async def run(settings, expect_provider):
        app = create_app(settings, poller=fake)
        async with app.router.lifespan_context(app):
            if expect_provider:
                assert isinstance(app.state.ors, OrsProvider) and app.state.ors.api_key == "k"
            else:
                assert app.state.ors is None

    await asyncio.wait_for(run(keyed, True), timeout=5)
    await asyncio.wait_for(run(_settings(), False), timeout=5)
```

- [ ] **Step 2: Run** — `cd backend && uv run pytest tests/test_app.py -v` → new tests FAIL (`TypeError: create_app() got an unexpected keyword argument 'ors'`).

- [ ] **Step 3: Implement** — `backend/goodfog/app.py` becomes:

```python
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import Settings
from .drive import DriveCache, build_drive_response, round_origin, validate_origin
from .poller import Poller
from .providers.open_meteo import OpenMeteoProvider
from .providers.ors import OrsProvider, RoutingError
from .viewpoints import VIEWPOINTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

DEST_POINTS = [(v.lat, v.lon) for v in VIEWPOINTS]


class DriveRequest(BaseModel):
    lat: float
    lon: float


def build_poller(settings: Settings, client: httpx.AsyncClient) -> Poller:
    provider = OpenMeteoProvider(DEST_POINTS, client, models=settings.open_meteo_models)
    features = {"drive": settings.ors_api_key is not None}
    return Poller(provider, settings.poll_minutes, settings.app_version, settings.commit, features=features)


def _unavailable() -> JSONResponse:
    return JSONResponse({"detail": "routing_unavailable"}, status_code=503)


def create_app(
    settings: Settings | None = None,
    poller: Poller | None = None,
    ors: OrsProvider | None = None,
    drive_cache: DriveCache | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = httpx.AsyncClient()
        app.state.poller = poller or build_poller(settings, client)
        if app.state.ors is None and settings.ors_api_key:
            app.state.ors = OrsProvider(client, settings.ors_api_key)
        task = asyncio.create_task(app.state.poller.run_forever())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await client.aclose()

    app = FastAPI(title="Good Fog", lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.state.ors = ors  # tests inject a fake; production builds one in lifespan when a key is set
    app.state.drive_cache = drive_cache or DriveCache()

    @app.get("/api/snapshot")
    async def snapshot():
        snap = app.state.poller.snapshot
        if snap is None:
            return JSONResponse({"status": "warming_up"}, status_code=503, headers={"Cache-Control": "no-cache"})
        return JSONResponse(snap, headers={"Cache-Control": "no-cache"})

    @app.get("/api/health")
    async def health():
        return app.state.poller.health()

    @app.get("/api/geocode")
    async def geocode(q: str = Query(..., min_length=1, max_length=200)):
        text = q.strip()
        if not text:
            return JSONResponse({"detail": "q must not be blank"}, status_code=422)
        provider = app.state.ors
        if provider is None:
            return _unavailable()
        try:
            place = await provider.geocode(text)
        except RoutingError as e:
            log.warning("geocode failed: %s", e)  # message carries status/type only, never the query
            return _unavailable()
        if place is None:
            return JSONResponse({"detail": "no_match"}, status_code=404)
        return {"label": place.label, "lat": place.lat, "lon": place.lon}

    @app.post("/api/drive")
    async def drive(req: DriveRequest):
        try:
            lat, lon = validate_origin(req.lat, req.lon)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=422)
        provider = app.state.ors
        if provider is None:
            return _unavailable()
        key = round_origin(lat, lon)
        now = time.monotonic()
        cached = app.state.drive_cache.get(key, now)
        if cached is not None:
            return cached
        try:
            legs = await provider.matrix(key, DEST_POINTS)
        except RoutingError as e:
            log.warning("drive lookup failed: %s", e)  # never log coordinates
            return _unavailable()
        body = build_drive_response(VIEWPOINTS, legs, key)
        app.state.drive_cache.put(key, body, now)
        return body

    return app


app = create_app()
```

Note: `test_build_poller_configures_provider` checks `len(poller.provider.points) == 8`; `DEST_POINTS` keeps that true.

- [ ] **Step 4: Run** — `uv run pytest -q` → all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/goodfog/app.py backend/tests/test_app.py
git commit -m "feat: /api/geocode and /api/drive proxied through ORS with origin cache (#7)"
```

---

### Task 6: Frontend pure helpers — `api.js`, `drive.js`, `origin.js`, `geolocate.js`

**Files:**
- Modify: `frontend/src/lib/api.js`, `frontend/src/lib/api.test.js`
- Create: `frontend/src/lib/drive.js`, `drive.test.js`, `origin.js`, `origin.test.js`, `geolocate.js`, `geolocate.test.js`

**Interfaces:**
- Consumes: backend contract from Task 5.
- Produces: `geocode(q, fetchImpl) -> {status:'ok', place} | {status:'no_match'} | {status:'unavailable'} | {status:'error', error}`; `fetchDrive(lat, lon, fetchImpl) -> {status:'ok', data} | {status:'unavailable'} | {status:'error', error}`; `driveMinutes(seconds)`, `fmtDrive(seconds)`, `leaveBy(arriveByIso, seconds)`; `ORIGIN_KEY`, `loadOrigin(storage)`, `saveOrigin(storage, origin)`; `getPosition(geo, timeoutMs) -> Promise<{lat, lon}>`.

- [ ] **Step 1: Write the failing tests.**

Append to `frontend/src/lib/api.test.js` (extend the import to `import { fetchSnapshot, geocode, fetchDrive } from './api.js';`):

```js
describe('geocode', () => {
  it('returns ok with the place and encodes the query', async () => {
    let url;
    const f = async (u) => { url = u; return { status: 200, ok: true, json: async () => ({ label: 'X', lat: 1, lon: 2 }) }; };
    expect(await geocode('24th & Noe', f)).toEqual({ status: 'ok', place: { label: 'X', lat: 1, lon: 2 } });
    expect(url).toBe('/api/geocode?q=24th%20%26%20Noe');
  });
  it('maps 404, 503, other errors and throws', async () => {
    expect(await geocode('x', mk(404, {}))).toEqual({ status: 'no_match' });
    expect(await geocode('x', mk(503, {}))).toEqual({ status: 'unavailable' });
    expect((await geocode('x', mk(500, {}))).status).toBe('error');
    expect((await geocode('x', async () => { throw new Error('offline'); })).status).toBe('error');
  });
});

describe('fetchDrive', () => {
  it('POSTs lat/lon as JSON and returns data', async () => {
    let call;
    const f = async (u, init) => { call = { u, init }; return { status: 200, ok: true, json: async () => ({ drives: {} }) }; };
    expect(await fetchDrive(37.7, -122.4, f)).toEqual({ status: 'ok', data: { drives: {} } });
    expect(call.u).toBe('/api/drive');
    expect(call.init.method).toBe('POST');
    expect(JSON.parse(call.init.body)).toEqual({ lat: 37.7, lon: -122.4 });
  });
  it('maps 503, other errors and throws', async () => {
    expect(await fetchDrive(0, 0, mk(503, {}))).toEqual({ status: 'unavailable' });
    expect((await fetchDrive(0, 0, mk(422, {}))).status).toBe('error');
    expect((await fetchDrive(0, 0, async () => { throw new Error('offline'); })).status).toBe('error');
  });
});
```

`frontend/src/lib/drive.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { driveMinutes, fmtDrive, leaveBy } from './drive.js';

describe('driveMinutes', () => {
  it('rounds up and rejects nonsense', () => {
    expect(driveMinutes(0)).toBe(0);
    expect(driveMinutes(59)).toBe(1);
    expect(driveMinutes(1540)).toBe(26);
    expect(driveMinutes(null)).toBeNull();
    expect(driveMinutes(undefined)).toBeNull();
    expect(driveMinutes(-5)).toBeNull();
    expect(driveMinutes(NaN)).toBeNull();
  });
});

describe('fmtDrive', () => {
  it('formats minutes and hours', () => {
    expect(fmtDrive(1540)).toBe('26 min');
    expect(fmtDrive(3600)).toBe('1 h 00 min');
    expect(fmtDrive(3900)).toBe('1 h 05 min');
    expect(fmtDrive(0)).toBe('0 min');
    expect(fmtDrive(null)).toBe('—');
  });
});

describe('leaveBy', () => {
  it('subtracts whole minutes from a local ISO string', () => {
    expect(leaveBy('2026-09-02T18:45', 1540)).toBe('2026-09-02T18:19');
    expect(leaveBy('2026-09-02T18:45', 0)).toBe('2026-09-02T18:45');
  });
  it('rolls over midnight and month boundaries', () => {
    expect(leaveBy('2026-09-03T06:20', 30 * 60)).toBe('2026-09-03T05:50');
    expect(leaveBy('2026-09-03T00:10', 20 * 60)).toBe('2026-09-02T23:50');
    expect(leaveBy('2026-10-01T00:05', 10 * 60)).toBe('2026-09-30T23:55');
  });
  it('returns null without a drive', () => {
    expect(leaveBy('2026-09-02T18:45', null)).toBeNull();
  });
});
```

`frontend/src/lib/origin.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { ORIGIN_KEY, loadOrigin, saveOrigin } from './origin.js';

function fakeStorage(initial = {}) {
  const m = new Map(Object.entries(initial));
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), m };
}

describe('loadOrigin', () => {
  it('round-trips a valid origin', () => {
    const s = fakeStorage();
    saveOrigin(s, { label: 'Home', lat: 37.7, lon: -122.4, extra: 'dropped' });
    expect(loadOrigin(s)).toEqual({ label: 'Home', lat: 37.7, lon: -122.4 });
    expect(JSON.parse(s.m.get(ORIGIN_KEY))).toEqual({ label: 'Home', lat: 37.7, lon: -122.4 });
  });
  it('returns null for missing, malformed or out-of-range values', () => {
    expect(loadOrigin(fakeStorage())).toBeNull();
    expect(loadOrigin(fakeStorage({ [ORIGIN_KEY]: 'not json' }))).toBeNull();
    expect(loadOrigin(fakeStorage({ [ORIGIN_KEY]: JSON.stringify({ label: '', lat: 1, lon: 2 }) }))).toBeNull();
    expect(loadOrigin(fakeStorage({ [ORIGIN_KEY]: JSON.stringify({ label: 'x', lat: 91, lon: 2 }) }))).toBeNull();
    expect(loadOrigin(fakeStorage({ [ORIGIN_KEY]: JSON.stringify({ label: 'x', lat: '1', lon: 2 }) }))).toBeNull();
    expect(loadOrigin(undefined)).toBeNull();
  });
});

describe('saveOrigin', () => {
  it('removes the key when origin is null and never throws', () => {
    const s = fakeStorage({ [ORIGIN_KEY]: '{}' });
    saveOrigin(s, null);
    expect(s.m.has(ORIGIN_KEY)).toBe(false);
    expect(() => saveOrigin({ setItem() { throw new Error('quota'); } }, { label: 'x', lat: 1, lon: 2 })).not.toThrow();
    expect(() => saveOrigin(undefined, null)).not.toThrow();
  });
});
```

`frontend/src/lib/geolocate.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { getPosition } from './geolocate.js';

describe('getPosition', () => {
  it('resolves lat/lon from the geolocation API with a timeout option', async () => {
    let opts;
    const geo = { getCurrentPosition: (ok, _err, o) => { opts = o; ok({ coords: { latitude: 37.7, longitude: -122.4 } }); } };
    expect(await getPosition(geo, 5000)).toEqual({ lat: 37.7, lon: -122.4 });
    expect(opts.timeout).toBe(5000);
  });
  it('rejects on error and when unsupported', async () => {
    const geo = { getCurrentPosition: (_ok, err) => err({ code: 1, message: 'denied' }) };
    await expect(getPosition(geo)).rejects.toBeTruthy();
    await expect(getPosition(undefined)).rejects.toThrow('unsupported');
  });
});
```

- [ ] **Step 2: Run** — `cd frontend && npm test` → new tests FAIL (missing modules / exports).

- [ ] **Step 3: Implement.**

Append to `frontend/src/lib/api.js`:

```js
/** GET /api/geocode?q=. Never throws; tagged result. */
export async function geocode(q, fetchImpl = fetch) {
  try {
    const r = await fetchImpl(`/api/geocode?q=${encodeURIComponent(q)}`, { headers: { Accept: 'application/json' } });
    if (r.status === 404) return { status: 'no_match' };
    if (r.status === 503) return { status: 'unavailable' };
    if (!r.ok) return { status: 'error', error: `HTTP ${r.status}` };
    return { status: 'ok', place: await r.json() };
  } catch (e) {
    return { status: 'error', error: String(e) };
  }
}

/** POST /api/drive with an origin. Never throws; tagged result. */
export async function fetchDrive(lat, lon, fetchImpl = fetch) {
  try {
    const r = await fetchImpl('/api/drive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ lat, lon }),
    });
    if (r.status === 503) return { status: 'unavailable' };
    if (!r.ok) return { status: 'error', error: `HTTP ${r.status}` };
    return { status: 'ok', data: await r.json() };
  } catch (e) {
    return { status: 'error', error: String(e) };
  }
}
```

`frontend/src/lib/drive.js`:

```js
/** Whole minutes for a drive, rounded UP so "leave by" is never too late. Invalid → null. */
export function driveMinutes(seconds) {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return null;
  return Math.ceil(seconds / 60);
}

/** '26 min' / '1 h 05 min' / '—' for no drive. */
export function fmtDrive(seconds) {
  const m = driveMinutes(seconds);
  if (m == null) return '—';
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')} min`;
}

/**
 * Subtract a drive from a local ISO string ('YYYY-MM-DDTHH:MM') and return the same shape.
 * Components go through Date.UTC so neither DST nor the viewer's zone can leak in.
 */
export function leaveBy(arriveByIso, seconds) {
  const m = driveMinutes(seconds);
  if (m == null) return null;
  const [date, time] = arriveByIso.slice(0, 16).split('T');
  const [Y, M, D] = date.split('-').map(Number);
  const [h, mi] = time.split(':').map(Number);
  const t = new Date(Date.UTC(Y, M - 1, D, h, mi) - m * 60_000);
  const p = (n) => String(n).padStart(2, '0');
  return `${t.getUTCFullYear()}-${p(t.getUTCMonth() + 1)}-${p(t.getUTCDate())}T${p(t.getUTCHours())}:${p(t.getUTCMinutes())}`;
}
```

`frontend/src/lib/origin.js`:

```js
export const ORIGIN_KEY = 'goodfog.origin';

function isValid(o) {
  return (
    o != null && typeof o === 'object' &&
    typeof o.label === 'string' && o.label.length > 0 &&
    Number.isFinite(o.lat) && Number.isFinite(o.lon) &&
    Math.abs(o.lat) <= 90 && Math.abs(o.lon) <= 180
  );
}

/** Read {label, lat, lon} from storage; anything missing or malformed → null. Never throws. */
export function loadOrigin(storage) {
  try {
    const raw = storage?.getItem(ORIGIN_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw);
    return isValid(o) ? { label: o.label, lat: o.lat, lon: o.lon } : null;
  } catch {
    return null;
  }
}

/** Persist an origin, or remove it when null. Never throws. */
export function saveOrigin(storage, origin) {
  try {
    if (origin == null) storage?.removeItem(ORIGIN_KEY);
    else storage?.setItem(ORIGIN_KEY, JSON.stringify({ label: origin.label, lat: origin.lat, lon: origin.lon }));
  } catch {
    /* storage full or blocked: the origin just won't persist */
  }
}
```

`frontend/src/lib/geolocate.js`:

```js
/** Resolve {lat, lon} from the Geolocation API, or reject. `geo` is injectable for tests. */
export function getPosition(geo = globalThis.navigator?.geolocation, timeoutMs = 10_000) {
  return new Promise((resolve, reject) => {
    if (!geo) return reject(new Error('unsupported'));
    geo.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      (err) => reject(err),
      { timeout: timeoutMs, maximumAge: 60_000 }
    );
  });
}
```

- [ ] **Step 4: Run** — `npm test` → all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.js frontend/src/lib/api.test.js frontend/src/lib/drive.js frontend/src/lib/drive.test.js frontend/src/lib/origin.js frontend/src/lib/origin.test.js frontend/src/lib/geolocate.js frontend/src/lib/geolocate.test.js
git commit -m "feat: drive-time API client and pure helpers (#7)"
```

---

### Task 7: Components — `OriginPicker`, drive props on picker, timing, plan

**Files:**
- Create: `frontend/src/components/OriginPicker.svelte`
- Modify: `frontend/src/components/LocationPicker.svelte`, `TimingCard.svelte`, `PlanView.svelte`, `WindowView.svelte`

**Interfaces:**
- Consumes: `fmtDrive`, `leaveBy` from `lib/drive.js`; `fmtTime` from `lib/time.js`.
- Produces: `OriginPicker` props `{ origin, busy = false, error = null, onsubmit(text), onlocate(), onclear() }`; `LocationPicker` prop `drives = null` (`{[id]: {seconds, meters} | null} | null`); `TimingCard`, `PlanView`, `WindowView` prop `drive = null` (`{seconds, meters} | null`).

- [ ] **Step 1: `OriginPicker.svelte`**

```svelte
<script>
  let { origin, busy = false, error = null, onsubmit, onlocate, onclear } = $props();
  let text = $state('');

  function submit(e) {
    e.preventDefault();
    const q = text.trim();
    if (q && !busy) onsubmit(q);
  }
</script>

<div class="origin">
  {#if origin}
    <div class="resolved">
      <span>From <strong>{origin.label}</strong> · drive times, no traffic</span>
      <button type="button" class="clear" onclick={onclear} aria-label="Clear origin" title="Clear origin">✕</button>
    </div>
  {:else}
    <form class="row" onsubmit={submit}>
      <input
        type="text"
        bind:value={text}
        placeholder="Your address or neighborhood"
        aria-label="Your starting address"
        autocomplete="street-address"
        disabled={busy}
      />
      <button type="submit" disabled={busy || !text.trim()}>Go</button>
      <button type="button" class="locate" onclick={onlocate} disabled={busy} aria-label="Use my location" title="Use my location">📍</button>
    </form>
  {/if}
  {#if busy}<p class="hint">Finding drive times…</p>{/if}
  {#if error}<p class="err" role="alert">{error}</p>{/if}
</div>

<style>
  .origin { margin-bottom: 16px; }
  .row { display: flex; gap: 8px; }
  input { flex: 1; min-width: 0; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; color: var(--text); font: inherit; }
  input:focus { outline: none; border-color: var(--blue); }
  button { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; color: var(--text); font: inherit; cursor: pointer; }
  button:hover:not(:disabled) { border-color: var(--blue); }
  button:disabled { opacity: 0.5; cursor: default; }
  .locate { padding: 10px 12px; }
  .resolved { display: flex; align-items: center; justify-content: space-between; gap: 8px; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; font-size: 0.85rem; }
  .clear { padding: 4px 8px; font-size: 0.8rem; }
  .hint { font-size: 0.78rem; color: var(--muted); margin-top: 6px; }
  .err { font-size: 0.78rem; color: #f85149; margin-top: 6px; }
</style>
```

- [ ] **Step 2: `LocationPicker.svelte`** — full file:

```svelte
<script>
  import { fmtDrive } from '../lib/drive.js';

  let { viewpoints, selectedId, onselect, drives = null } = $props();
</script>

<p class="loc-label">Choose your viewpoint</p>
<div class="loc-grid">
  {#each viewpoints as vp (vp.id)}
    <button class="loc-btn" class:active={vp.id === selectedId} onclick={() => onselect(vp.id)}>
      <div class="loc-name">{vp.name}</div>
      <div class="loc-elev">{vp.desc}</div>
      {#if drives}
        <div class="loc-drive">{drives[vp.id] ? `~${fmtDrive(drives[vp.id].seconds)} drive` : '—'}</div>
      {/if}
    </button>
  {/each}
</div>

<style>
  .loc-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-bottom: 8px; }
  .loc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
  .loc-btn { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; cursor: pointer; text-align: left; transition: all 0.15s; color: var(--text); font: inherit; }
  .loc-btn:hover { border-color: var(--blue); }
  .loc-btn.active { border-color: var(--blue); background: #0d2045; }
  .loc-name { font-size: 0.88rem; font-weight: 600; }
  .loc-elev { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }
  .loc-drive { font-size: 0.75rem; color: var(--blue); margin-top: 4px; }
</style>
```

- [ ] **Step 3: `TimingCard.svelte`** — full file:

```svelte
<script>
  import { fmtTime } from '../lib/time.js';
  import { fmtDrive, leaveBy } from '../lib/drive.js';

  let { vp, win, drive = null } = $props();
  const isDawn = $derived(win.sun_label === 'Sunrise');
  const leave = $derived(drive ? leaveBy(win.arrive_by, drive.seconds) : null);
</script>

<div class="card">
  <h3>{win.title} Timing</h3>
  <div class="timing-row"><span class="timing-label">{win.sun_label}</span><span class="timing-value">{fmtTime(win.sun_event)}</span></div>
  <div class="timing-row"><span class="timing-label">Arrive by</span><span class="timing-value">{fmtTime(win.arrive_by)}</span></div>
  {#if drive && leave}
    <div class="timing-row"><span class="timing-label">Drive</span><span class="timing-value muted">{fmtDrive(drive.seconds)} · no traffic</span></div>
    <div class="timing-row"><span class="timing-label">Leave by</span><span class="timing-value">{fmtTime(leave)}</span></div>
  {/if}
  {#if isDawn && vp.dawn_gated}
    <div class="timing-row gate">
      <span class="timing-label warn">⚠ Gate</span>
      <span class="timing-value warn small">Summit road opens 7am — sunrise not viable</span>
    </div>
  {/if}
</div>

<style>
  .gate { border-top: 1px solid var(--panel2); }
  .warn { color: #e3812c; }
  .small { font-size: 0.8rem; text-align: right; }
  .muted { color: var(--muted); font-weight: 500; }
</style>
```

- [ ] **Step 4: `PlanView.svelte`** — script and heading change only:

```svelte
<script>
  import { fmtTime } from '../lib/time.js';
  import { scoreColor } from '../lib/colors.js';
  import { fmtDrive } from '../lib/drive.js';
  import { bestWindow, planSummary } from '../lib/plan.js';
  import ConditionsCard from './ConditionsCard.svelte';

  let { vp, windows, drive = null } = $props();
  const best = $derived(bestWindow(windows, vp.results));
</script>

<div class="card">
  <h3>Best Window for {vp.name}</h3>
  {#if drive}
    <p class="drive">🚗 {fmtDrive(drive.seconds)} drive · no traffic</p>
  {/if}
  <div class="compare-grid">
```

(rest of the markup unchanged) and add to `<style>`:

```css
  .drive { font-size: 0.8rem; color: var(--muted); margin: -6px 0 10px; }
```

- [ ] **Step 5: `WindowView.svelte`** — accept and forward `drive`:

```svelte
  let { vp, win, result, drive = null } = $props();
```

and

```svelte
  <TimingCard {vp} {win} {drive} />
```

- [ ] **Step 6: Verify** — `cd frontend && npm test && npm run build` → tests pass, build succeeds with no Svelte warnings about unknown props.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/OriginPicker.svelte frontend/src/components/LocationPicker.svelte frontend/src/components/TimingCard.svelte frontend/src/components/PlanView.svelte frontend/src/components/WindowView.svelte
git commit -m "feat: OriginPicker and drive-time labels on picker, timing and plan (#7)"
```

---

### Task 8: Wire `App.svelte`, bump to 0.3.0

**Files:**
- Modify: `frontend/src/App.svelte`
- Modify: `frontend/package.json`, `frontend/package-lock.json`, `backend/pyproject.toml`

**Interfaces:**
- Consumes: everything from Tasks 6–7; `snapshot.features.drive` from Task 4.

- [ ] **Step 1: App state and handlers.** In the `<script>` of `frontend/src/App.svelte`, add imports after the existing ones:

```js
  import OriginPicker from './components/OriginPicker.svelte';
  import { fetchDrive, geocode } from './lib/api.js';
  import { getPosition } from './lib/geolocate.js';
  import { loadOrigin, saveOrigin } from './lib/origin.js';
```

(merge `fetchDrive, geocode` into the existing `import { fetchSnapshot } from './lib/api.js';` line as `import { fetchSnapshot, fetchDrive, geocode } from './lib/api.js';`.)

After the `tab` state declaration add:

```js
  let origin = $state(loadOrigin(globalThis.localStorage));
  let drives = $state(null);        // {[vpId]: {seconds, meters} | null} once fetched
  let driveBusy = $state(false);
  let driveError = $state(null);
  let drivesRequested = false;      // first snapshot triggers one fetch for a remembered origin

  const driveEnabled = $derived(snapshot?.features?.drive === true);
  const selectedDrive = $derived(driveEnabled && drives && vp ? (drives[vp.id] ?? null) : null);

  async function loadDrives(o) {
    if (!o) { drives = null; return; }
    driveBusy = true;
    const r = await fetchDrive(o.lat, o.lon);
    driveBusy = false;
    if (r.status === 'ok') { drives = r.data.drives; driveError = null; }
    else { drives = null; driveError = 'Drive times unavailable right now'; }
  }

  function setOrigin(o) {
    origin = o;
    saveOrigin(globalThis.localStorage, o);
    driveError = null;
    loadDrives(o);
  }

  async function submitAddress(text) {
    driveBusy = true;
    driveError = null;
    const r = await geocode(text);
    driveBusy = false;
    if (r.status === 'ok') setOrigin(r.place);
    else if (r.status === 'no_match') driveError = 'Address not found';
    else driveError = 'Drive times unavailable right now';
  }

  async function useMyLocation() {
    driveBusy = true;
    driveError = null;
    try {
      const { lat, lon } = await getPosition();
      setOrigin({ label: 'My location', lat, lon });
    } catch {
      driveBusy = false;
      driveError = 'Location blocked or unavailable';
    }
  }
```

In `load()`, inside the `r.status === 'ok'` branch after `error = null;`, add:

```js
      if (!drivesRequested && r.data.features?.drive && origin) {
        drivesRequested = true;
        loadDrives(origin);
      }
```

- [ ] **Step 2: Markup.** Inside `{#if snapshot && vp}` replace the picker and view lines with:

```svelte
    <LikelihoodMap {coast} {viewpoints} {selectedId} {tab} onselect={select} />
    {#if driveEnabled}
      <OriginPicker {origin} busy={driveBusy} error={driveError} onsubmit={submitAddress} onlocate={useMyLocation} onclear={() => setOrigin(null)} />
    {/if}
    <LocationPicker {viewpoints} {selectedId} onselect={select} drives={driveEnabled ? drives : null} />
    <Tabs {tabs} active={tab} onselect={(id) => (tab = id)} />

    {#if tab === 'plan'}
      <PlanView {vp} windows={vp.windows} drive={selectedDrive} />
    {:else if window_}
      <WindowView {vp} win={window_} result={vp.results[window_.id]} drive={selectedDrive} />
    {/if}
```

- [ ] **Step 3: Version bump.**

```bash
cd frontend && npm version 0.3.0 --no-git-tag-version
cd ../backend && sed -i '' 's/^version = "0.2.0"/version = "0.3.0"/' pyproject.toml
```

Confirm `frontend/package.json`, both `"version"` entries at the top of `frontend/package-lock.json`, and `backend/pyproject.toml` all read `0.3.0`.

- [ ] **Step 4: Verify everything**

```bash
cd frontend && npm test && npm run build
cd ../backend && uv run pytest -q
```

Then a manual smoke: `cd backend && ORS_API_KEY=dummy uv run uvicorn goodfog.app:app --port 8000` and `cd frontend && npm run dev`; open the dev URL. The origin box must appear (feature flag true). Entering an address will show "Drive times unavailable right now" because the key is fake — that is the expected 503 path. Stop the servers. Then run the backend **without** the key and confirm the origin box is absent.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.svelte frontend/package.json frontend/package-lock.json backend/pyproject.toml
git commit -m "feat: wire origin + drive times into the app; bump to 0.3.0 (#7)"
```

---

## Self-review

- **Spec coverage:** §3.1 → Task 1; §3.2 → Task 2; §3.3–3.4 → Task 3; §3.6 + health flag → Task 4; §3.5 → Task 5; §4.1–4.3 → Task 6; §4.4 → Tasks 7–8; §5 error table → Tasks 5, 6, 8; §6 tests → each task; §7 deployment is operational (Mike sets the Coolify env var).
- **Deviation from spec, deliberate:** §4.4 puts the geolocation call inside `OriginPicker`; the plan puts it in `lib/geolocate.js` (testable, injectable) called from `App.svelte`, with `OriginPicker` emitting a bare `onlocate()`. Same behaviour, better seam.
- **Placeholder scan:** none.
- **Type consistency:** `Leg(seconds, meters)` used identically in Tasks 2, 3, 5; drive dict `{seconds, meters}` matches the frontend's `drive.seconds`; tagged-result shapes in Task 6 match the handlers in Task 8; `create_app(..., ors=, drive_cache=)` matches Task 5 tests; `Poller(..., features=)` matches Tasks 4 and 5.
