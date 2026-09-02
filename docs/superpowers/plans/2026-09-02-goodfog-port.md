# Good Fog Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the single-file Marin Inversion Checker (`index.html`) into a FastAPI backend + Svelte 5 PWA monorepo called Good Fog, deployable to Coolify with Docker Compose.

**Architecture:** The backend polls Open-Meteo once (all 8 viewpoints in one request) every `POLL_MINUTES`, runs the pure fog math (LCL, status, score, verdict, explanation) per viewpoint per window, and serves one immutable JSON snapshot at `/api/snapshot`. The Svelte frontend only renders that snapshot; its own logic is limited to small tested helpers (bar scale, time formatting, plan best-window). Everything mirrors the Mrs. Toasty repo at `/Users/mike/claudeprojects/mrstoasty`, which executors may read for reference but must not modify.

**Tech Stack:** Python 3.12, FastAPI 0.141.1, httpx 0.28.1, uvicorn, pytest + pytest-asyncio + respx, uv; Svelte 5.56.10, Vite 8.2.2, vite-plugin-pwa 1.3.0, vitest 4.1.11; nginx 1.27; Docker Compose; Coolify.

**Spec:** `docs/superpowers/specs/2026-09-02-goodfog-design.md`

## Global Constraints

- Repo root: `/Users/mike/claudeprojects/goodfog`. Work on the branch `port-to-stack` (create from `design-spec` in Task 1). Never push to `main`.
- Version is `0.1.0` in both `backend/pyproject.toml` and `frontend/package.json` (+ lockfile).
- Python: `uv`, exact `==` pins. Node: exact pins, no `^`/`~`, install with `npm ci --ignore-scripts` (or `npm install --ignore-scripts` the first time to create the lockfile). Pin npm versions that are at least 3 days old.
- No secrets. Only env vars: `POLL_MINUTES` (default 15), `OPEN_METEO_MODELS` (default `best_match`), `BUILD_COMMIT` (baked at build), `APP_VERSION` (optional override).
- All fog math is pure: no I/O, no clock reads. `now` is passed in.
- JS parity: use `jsround` (floor(x+0.5)) wherever the original used `Math.round`; format feet with thousands separators (`f"{n:,}"`) wherever the original used `toLocaleString()`.
- Text copy (viewpoint descriptions, factor labels, explanations, verdict labels, emoji) is copied verbatim from `index.html`; the only branding change is the app title "Good Fog".
- Commit after every task with the trailer:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01Uucw9EqwctfzAmKYxTpBpK
  ```
- Backend tests: `cd backend && uv run pytest`. Frontend tests: `cd frontend && npm test`. Build: `npm run build`.

---

## File structure

```
backend/
  pyproject.toml, uv.lock, Dockerfile
  goodfog/__init__.py
  goodfog/config.py           Settings.from_env (poll_minutes, open_meteo_models, app_version, commit)
  goodfog/viewpoints.py       Viewpoint dataclass + VIEWPOINTS tuple (verbatim data)
  goodfog/fog.py              jsround, lcl_ft, Hour, Status, lcl_status, Verdict, verdict,
                              Factor, Result, score, ElevationVerdict, elevation_verdict
  goodfog/windows.py          Window, truncate_hour, minus_minutes, build_windows
  goodfog/providers/__init__.py   ProviderError
  goodfog/providers/open_meteo.py Forecast, parse_open_meteo, OpenMeteoProvider
  goodfog/snapshot.py         build_snapshot(...) -> dict
  goodfog/poller.py           Poller (run_forever, snapshot, health)
  goodfog/app.py              create_app, /api/snapshot, /api/health
  tests/                      one test module per source module + fixtures/open_meteo.json
frontend/
  package.json, package-lock.json, vite.config.js, index.html, nginx.conf, Dockerfile
  public/favicon.svg, icon-192.png, icon-512.png
  src/main.js, app.css, App.svelte
  src/lib/api.js, version.js, time.js, colors.js, barScale.js, plan.js (+ .test.js each)
  src/components/Header, LocationPicker, Tabs, VerdictBanner, ElevationBanner, ElevationBar,
                 TimingCard, ConditionsCard, ShotNotesCard, WhyCard, WindowView, PlanView,
                 VerifyLinks, Footer (.svelte)
docker-compose.yml, docker-compose.override.yml, .env.example, .gitignore
CLAUDE.md, README.md, docs/GETTING-STARTED.md
```

---

### Task 1: Backend scaffold and settings

**Files:**
- Create: `backend/pyproject.toml`, `backend/goodfog/__init__.py`, `backend/goodfog/config.py`, `backend/tests/__init__.py`, `backend/tests/test_config.py`, `.gitignore`, `.env.example`

**Interfaces:**
- Produces: `Settings(poll_minutes: int, open_meteo_models: str, app_version: str, commit: str)` with `Settings.from_env(env: Mapping | None) -> Settings`.

- [ ] **Step 1: Create the branch**

```bash
cd /Users/mike/claudeprojects/goodfog && git checkout design-spec && git checkout -b port-to-stack
```

- [ ] **Step 2: Write pyproject, gitignore, env example**

`backend/pyproject.toml`:
```toml
[project]
name = "goodfog"
version = "0.1.0"
description = "Marin marine-layer inversion checker for photographers"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.141.1",
    "uvicorn[standard]==0.52.4",
    "httpx==0.28.1",
]

[dependency-groups]
dev = [
    "pytest==9.1.1",
    "pytest-asyncio==1.4.0",
    "respx==0.23.1",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["goodfog"]
```

`.gitignore`:
```
.env
__pycache__/
.venv/
node_modules/
dist/
.DS_Store
.claude/worktrees/
```

`.env.example`:
```
# Open-Meteo poll interval (minutes). One request covers all viewpoints.
POLL_MINUTES=15
# Open-Meteo model: best_match (default) or e.g. gfs_hrrr
OPEN_METEO_MODELS=best_match
```

Create empty `backend/goodfog/__init__.py` and `backend/tests/__init__.py`.

- [ ] **Step 3: Write the failing settings test**

`backend/tests/test_config.py`:
```python
import tomllib
from pathlib import Path

from goodfog.config import Settings

ROOT = Path(__file__).resolve().parents[2]


def _pyproject_version() -> str:
    with (ROOT / "backend" / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def test_defaults_when_env_empty():
    s = Settings.from_env({})
    assert s.poll_minutes == 15
    assert s.open_meteo_models == "best_match"
    assert s.app_version == _pyproject_version()
    assert s.commit == "dev"


def test_reads_env():
    s = Settings.from_env({"POLL_MINUTES": "5", "OPEN_METEO_MODELS": "gfs_hrrr", "APP_VERSION": "9.9.9"})
    assert s.poll_minutes == 5
    assert s.open_meteo_models == "gfs_hrrr"
    assert s.app_version == "9.9.9"


def test_commit_from_build_commit_only():
    s = Settings.from_env({"BUILD_COMMIT": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0", "SOURCE_COMMIT": "dev"})
    assert s.commit == "a1b2c3d"
    assert Settings.from_env({"BUILD_COMMIT": "  "}).commit == "dev"
    assert Settings.from_env({"SOURCE_COMMIT": "1111111aaaa"}).commit == "dev"


def test_blank_app_version_falls_back_to_pyproject():
    assert Settings.from_env({"APP_VERSION": "  "}).app_version == _pyproject_version()
```

- [ ] **Step 4: Run to verify it fails**

Run: `cd backend && uv sync && uv run pytest tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'goodfog.config'`

- [ ] **Step 5: Implement config**

`backend/goodfog/config.py`:
```python
from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _pyproject_version() -> str:
    try:
        with _PYPROJECT.open("rb") as f:
            return tomllib.load(f)["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "unknown"


@dataclass(frozen=True)
class Settings:
    poll_minutes: int
    open_meteo_models: str
    app_version: str
    commit: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        if env is None:
            env = os.environ
        # BUILD_COMMIT is baked into the image by backend/Dockerfile from the SOURCE_COMMIT build
        # arg. The runtime SOURCE_COMMIT env var is deliberately ignored: Coolify's compose parser
        # injects its own (empty/"dev") copy into the container, which is never the real sha.
        commit = (env.get("BUILD_COMMIT") or "").strip()[:7] or "dev"
        return cls(
            poll_minutes=int(env.get("POLL_MINUTES", "15")),
            open_meteo_models=env.get("OPEN_METEO_MODELS", "best_match"),
            app_version=(env.get("APP_VERSION") or "").strip() or _pyproject_version(),
            commit=commit,
        )
```

- [ ] **Step 6: Run to verify it passes**

Run: `cd backend && uv run pytest -q`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add .gitignore .env.example backend
git commit -m "feat(backend): scaffold goodfog package with settings"
```

---

### Task 2: Viewpoints and core fog math

**Files:**
- Create: `backend/goodfog/viewpoints.py`, `backend/goodfog/fog.py`, `backend/tests/test_viewpoints.py`, `backend/tests/test_fog.py`

**Interfaces:**
- Produces: `Viewpoint` frozen dataclass and `VIEWPOINTS: tuple[Viewpoint, ...]`, `viewpoint_by_id(id) -> Viewpoint`.
- Produces in `fog.py`: `jsround(x) -> int`, `lcl_ft(temp_c, dew_c) -> int | None`, `Hour` dataclass, `hour_from_values(temp_c, dew_c, low, mid, high, wind_kmh, rain) -> Hour`, `Status(kind, reason)`, `lcl_status(vp, hour) -> Status`, `Verdict(label, emoji, cls)`, `verdict(score) -> Verdict`.

- [ ] **Step 1: Write failing viewpoint tests**

`backend/tests/test_viewpoints.py`:
```python
from goodfog.viewpoints import VIEWPOINTS, viewpoint_by_id


def test_eight_viewpoints_in_original_order():
    assert [v.id for v in VIEWPOINTS] == [
        "hawk-hill", "battery-spencer", "conzelman-pullouts", "twin-peaks-vantage",
        "point-bonita", "trojan-point", "west-peak", "east-peak",
    ]


def test_east_peak_values():
    v = viewpoint_by_id("east-peak")
    assert v.elev_ft == 2571
    assert v.green_ft == (200, 2400)
    assert v.yellow_ft == (2400, 2571)
    assert v.dawn_gated is True
    assert v.desc == "2,571 ft · Mt. Tamalpais"


def test_only_tam_summits_are_dawn_gated():
    assert {v.id for v in VIEWPOINTS if v.dawn_gated} == {"trojan-point", "west-peak", "east-peak"}


def test_bands_are_contiguous():
    for v in VIEWPOINTS:
        assert v.green_ft[0] < v.green_ft[1] == v.yellow_ft[0] < v.yellow_ft[1]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_viewpoints.py -q`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: Implement viewpoints (data verbatim from index.html)**

`backend/goodfog/viewpoints.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Viewpoint:
    id: str
    name: str
    lat: float
    lon: float
    elev_ft: int
    desc: str
    green_ft: tuple[int, int]   # fog base (LCL) range: above the layer with it in frame
    yellow_ft: tuple[int, int]  # right at the edge
    too_low: str
    too_high: str
    composition: str
    access: str
    cam_tip: str
    dawn_gated: bool = False


VIEWPOINTS: tuple[Viewpoint, ...] = (
    Viewpoint(
        id="hawk-hill", name="Hawk Hill", lat=37.8283, lon=-122.4997, elev_ft=923,
        desc="923 ft · Golden Gate Headlands", green_ft=(200, 850), yellow_ft=(850, 950),
        too_low="Fog base very low — the layer is likely thick enough to sock you in.",
        too_high="Fog base above Hawk Hill — you'd be inside the clouds, not above them.",
        composition="Shoot south into Rodeo Valley. Wide angle (24–35mm) for the fog-wave texture between ridgelines.",
        access="24hr access via Conzelman Rd (one-way). No gate.",
        cam_tip="Sweet spot is a fog base of 200–850 ft. Above ~950 ft you'll be under the layer, not above it.",
    ),
    Viewpoint(
        id="battery-spencer", name="Battery Spencer", lat=37.8278, lon=-122.4818, elev_ft=790,
        desc="790 ft · Golden Gate Headlands", green_ft=(200, 700), yellow_ft=(700, 800),
        too_low="Fog base very low — you'd be buried in the layer.",
        too_high="Fog base above the battery — the bridge and towers disappear.",
        composition="Shoot east at the Golden Gate Bridge with fog swirling around the towers. Longer focal length (100–200mm) compresses the layer.",
        access="24hr Tue–Sun. 6am–5pm Mon. Hit it on the way down from Hawk Hill.",
        cam_tip="Lower than Hawk Hill, so it works when the fog base is a touch lower. Bridge towers are ~746 ft — fog needs to sit near or below that.",
    ),
    Viewpoint(
        id="conzelman-pullouts", name="Conzelman Pullouts", lat=37.8270, lon=-122.4900, elev_ft=600,
        desc="~600 ft · Conzelman Rd", green_ft=(150, 550), yellow_ft=(550, 650),
        too_low="Fog base very low — pullouts will be inside the layer.",
        too_high="Fog base above the road — you're under the fog here.",
        composition="Intermediate elevations between Battery Spencer and Hawk Hill. Different angles at each pullout — scout in daylight first.",
        access="24hr access. Flexible stop when the fog base is sitting low.",
        cam_tip="Use these when the fog base is too low even for Hawk Hill — the lower pullouts get you back above it.",
    ),
    Viewpoint(
        id="twin-peaks-vantage", name="Twin Peaks (Arguello & Jackson)", lat=37.7874, lon=-122.4581, elev_ft=370,
        desc="370 ft vantage · shoot toward Twin Peaks", green_ft=(400, 750), yellow_ft=(750, 850),
        too_low="Fog below your vantage — you're in it rather than looking across at it.",
        too_high="Fog above Twin Peaks (922 ft) — the peaks vanish into the layer.",
        composition="From Arguello & Jackson (~370 ft) shoot SE toward Twin Peaks (922 ft) emerging above the fog, city glowing below. Best at sunset.",
        access="Street parking, no gates. This is a narrow window — the fog must sit between you (370 ft) and the peaks (922 ft).",
        cam_tip="Different geometry: you want the fog ABOVE your vantage but BELOW the peaks — a 400–750 ft fog base. Too low = you're socked in; too high = peaks gone.",
    ),
    Viewpoint(
        id="point-bonita", name="Point Bonita Lighthouse", lat=37.8156, lon=-122.5295, elev_ft=100,
        desc="100 ft · coastal", green_ft=(50, 200), yellow_ft=(200, 300),
        too_low="Completely socked in at the coast.",
        too_high="Fog base too high — loses the low, dramatic coastal fog.",
        composition="Suspension-bridge footbridge as foreground with fog rolling off the Pacific. Only works with a very low fog base.",
        access="Check NPS hours — intermittently closed for renovations. Verify before going.",
        cam_tip="A low-elevation, different shot entirely. Best when fog is hugging the coast below ~200 ft.",
    ),
    Viewpoint(
        id="trojan-point", name="Trojan Point", lat=37.9170, lon=-122.5980, elev_ft=1750,
        desc="~1,750 ft · Mt. Tamalpais", green_ft=(200, 1550), yellow_ft=(1550, 1750), dawn_gated=True,
        too_low="Fog base very low — a deep layer may reach up around you.",
        too_high="Fog base above Trojan Point — you're inside the clouds.",
        composition="Mid-mountain sea-of-clouds looking south/southwest. The layer wraps dramatically below without obscuring the view.",
        access="Gate on the summit road opens 7am — sunrise not viable. Short hike from parking.",
        cam_tip="Great when the fog base sits 1,200–1,700 ft. Note the 7am gate: shoot this at sunset, not dawn.",
    ),
    Viewpoint(
        id="west-peak", name="West Peak", lat=37.9279, lon=-122.6017, elev_ft=2560,
        desc="2,560 ft · Mt. Tamalpais", green_ft=(200, 2400), yellow_ft=(2400, 2560), dawn_gated=True,
        too_low="Fog base extremely low — a very deep layer could still reach you.",
        too_high="Fog base above West Peak — you're in the clouds.",
        composition="Faces the coast — ideal for fog rolling in. Trees as silhouette foreground over a sea of cloud.",
        access="Gate opens 7am — sunrise not viable. ~20 min hike from Rock Spring / $9 parking. Confirm which summit road is open.",
        cam_tip="Sits above nearly all marine-layer events. Almost always above the fog when a layer is present.",
    ),
    Viewpoint(
        id="east-peak", name="East Peak", lat=37.9236, lon=-122.5800, elev_ft=2571,
        desc="2,571 ft · Mt. Tamalpais", green_ft=(200, 2400), yellow_ft=(2400, 2571), dawn_gated=True,
        too_low="Fog base extremely low — a very deep layer could still reach you.",
        too_high="Fog base above East Peak — you're in the clouds.",
        composition="Highest vantage — 360° sea of cloud over all of Marin and SF. Trees/ridgeline as foreground.",
        access="Gate opens 7am — sunrise not viable. Parking currently restricted; confirm access before driving up.",
        cam_tip="The nuclear option: if everything lower is socked in, you'll almost certainly be above the fog here.",
    ),
)

DEFAULT_VIEWPOINT_ID = "east-peak"

_BY_ID = {v.id: v for v in VIEWPOINTS}


def viewpoint_by_id(vid: str) -> Viewpoint:
    return _BY_ID[vid]
```

- [ ] **Step 4: Run viewpoint tests**

Run: `cd backend && uv run pytest tests/test_viewpoints.py -q`
Expected: 4 passed

- [ ] **Step 5: Write failing core fog tests**

`backend/tests/test_fog.py`:
```python
import pytest

from goodfog.fog import Hour, Status, hour_from_values, jsround, lcl_ft, lcl_status, verdict
from goodfog.viewpoints import viewpoint_by_id


def test_jsround_matches_js_math_round():
    assert jsround(2.5) == 3
    assert jsround(-2.5) == -2
    assert jsround(3.728) == 4
    assert jsround(8.699) == 9


def test_lcl_ft_formula():
    assert lcl_ft(14.2, 11.1) == 1271   # 125 * 3.1 * 3.281 = 1271.39
    assert lcl_ft(12.0, 12.0) == 0
    assert lcl_ft(10.0, 12.0) == 0      # negative spread clamps to 0
    assert lcl_ft(None, 12.0) is None
    assert lcl_ft(12.0, None) is None


def test_hour_from_values_converts_units():
    h = hour_from_values(14.2, 11.1, low=85, mid=5, high=0, wind_kmh=6.0, rain=0)
    assert h.wind_mph == 4
    assert h.temp_f == 58
    assert h.dewpoint_f == 52
    assert h.lcl_ft == 1271
    assert (h.low_cloud, h.mid_cloud, h.high_cloud, h.rain_pct) == (85, 5, 0, 0)


def test_hour_from_values_nulls_default_to_zero():
    h = hour_from_values(14.2, None, low=None, mid=None, high=None, wind_kmh=6.0, rain=None)
    assert (h.low_cloud, h.mid_cloud, h.high_cloud, h.rain_pct) == (0, 0, 0, 0)
    assert h.dewpoint_f is None
    assert h.lcl_ft is None


@pytest.mark.parametrize(
    "lcl, expected",
    [
        (199, Status("red", "low")),
        (200, Status("green")),
        (850, Status("green")),
        (851, Status("yellow")),
        (950, Status("yellow")),
        (951, Status("red", "high")),
    ],
)
def test_lcl_status_boundaries_hawk_hill(lcl, expected):
    vp = viewpoint_by_id("hawk-hill")
    h = Hour(low_cloud=80, mid_cloud=0, high_cloud=0, wind_mph=0, rain_pct=0, temp_f=68, dewpoint_f=60, lcl_ft=lcl)
    assert lcl_status(vp, h) == expected


def test_lcl_status_none_when_thin_low_cloud_or_no_lcl():
    vp = viewpoint_by_id("hawk-hill")
    thin = Hour(low_cloud=19, mid_cloud=0, high_cloud=0, wind_mph=0, rain_pct=0, temp_f=68, dewpoint_f=60, lcl_ft=500)
    assert lcl_status(vp, thin) == Status("none")
    nolcl = Hour(low_cloud=90, mid_cloud=0, high_cloud=0, wind_mph=0, rain_pct=0, temp_f=68, dewpoint_f=None, lcl_ft=None)
    assert lcl_status(vp, nolcl) == Status("none")


def test_twin_peaks_green_band_is_above_its_own_elevation():
    vp = viewpoint_by_id("twin-peaks-vantage")
    h = Hour(low_cloud=80, mid_cloud=0, high_cloud=0, wind_mph=0, rain_pct=0, temp_f=68, dewpoint_f=60, lcl_ft=600)
    assert lcl_status(vp, h) == Status("green")


@pytest.mark.parametrize(
    "score, label, cls",
    [(100, "Go for it!", "go"), (70, "Go for it!", "go"), (69, "Worth a try", "try"), (50, "Worth a try", "try"),
     (49, "Maybe next time", "maybe"), (30, "Maybe next time", "maybe"), (29, "Stay home", "no"), (0, "Stay home", "no")],
)
def test_verdict_thresholds(score, label, cls):
    v = verdict(score)
    assert (v.label, v.cls) == (label, cls)
```

- [ ] **Step 6: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_fog.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'goodfog.fog'`

- [ ] **Step 7: Implement core fog math**

`backend/goodfog/fog.py`:
```python
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
```

- [ ] **Step 8: Run all tests**

Run: `cd backend && uv run pytest -q`
Expected: all pass

- [ ] **Step 9: Commit**

```bash
git add backend
git commit -m "feat(backend): viewpoints data and core fog math (LCL, status, verdict)"
```

---

### Task 3: Scoring, explanation, and elevation verdict with JS parity table

**Files:**
- Modify: `backend/goodfog/fog.py` (append)
- Create: `backend/tests/test_score.py`

**Interfaces:**
- Consumes: `Viewpoint`, `Hour`, `Status`, `lcl_status`, `verdict` from Task 2.
- Produces: `Factor(label, rating)`, `Result(score, factors, explanation, lcl_ft, status)`, `score(vp, hour) -> Result`, `ElevationVerdict(cls, icon, title, detail)`, `elevation_verdict(vp, hour) -> ElevationVerdict`, `fmt_ft(n) -> str`.

- [ ] **Step 1: Write failing tests (parity values were produced by running the original JS)**

`backend/tests/test_score.py`:
```python
import pytest

from goodfog.fog import Status, elevation_verdict, fmt_ft, hour_from_values, score, verdict
from goodfog.viewpoints import viewpoint_by_id

# (viewpoint, temp_c, dew_c, low, mid, high, wind_kmh, rain) -> expected, computed by the original index.html JS.
PARITY = [
    ("east-peak", 14.2, 11.1, 85, 5, 0, 6.0, 0,
     100, Status("green"), "Go for it!", "Above the fog layer",
     ["Low cloud 85%|good", "Wind 4 mph|good", "Clear above 5%|good", "Rain 0%|good", "Fog base 1,271 ft — below you|good"],
     "Strong conditions at East Peak. Fog base ~1,271 ft sits below you — expect a clean view down onto the layer. Low cloud at 85%, winds calm at 4 mph."),
    ("hawk-hill", 14.2, 11.1, 85, 5, 0, 6.0, 0,
     35, Status("red", "high"), "Maybe next time", "Inside the layer",
     ["Low cloud 85%|good", "Wind 4 mph|good", "Clear above 5%|good", "Rain 0%|good", "Fog base 1,271 ft — above you|bad"],
     "Marginal at Hawk Hill. Fog base ~1,271 ft is above your viewpoint — you'd be in it."),
    ("hawk-hill", 15.0, 12.9, 60, 30, 10, 14.0, 10,
     59, Status("yellow"), "Worth a try", "Right at the edge",
     ["Low cloud 60%|ok", "Wind 9 mph|ok", "Some high cloud 30%|ok", "Rain 10%|ok", "Fog base 861 ft — at the edge|ok"],
     "Decent shot at Hawk Hill. Moderate marine layer with calm winds. Fog base ~861 ft — check the live cameras before heading out."),
    ("point-bonita", 13.0, 12.6, 90, 0, 0, 4.0, 0,
     100, Status("green"), "Go for it!", "Above the fog layer",
     ["Low cloud 90%|good", "Wind 2 mph|good", "Clear above 0%|good", "Rain 0%|good", "Fog base 164 ft — below you|good"],
     "Strong conditions at Point Bonita Lighthouse. Fog base ~164 ft sits below you — expect a clean view down onto the layer. Low cloud at 90%, winds calm at 2 mph."),
    ("twin-peaks-vantage", 16.0, 14.4, 70, 60, 20, 20.0, 25,
     41, Status("green"), "Maybe next time", "Above the fog layer",
     ["Low cloud 70%|ok", "Wind 12 mph|ok", "High cloud 60%|bad", "Rain 25%|bad", "Fog base 656 ft — below you|good"],
     "Marginal at Twin Peaks (Arguello & Jackson). Fog base ~656 ft."),
    ("battery-spencer", 18.0, 8.0, 10, 0, 0, 3.0, 0,
     15, Status("none"), "Stay home", "No marine layer",
     ["Low cloud 10%|bad", "Wind 2 mph|good", "Clear above 0%|good", "Rain 0%|good", "No marine layer|bad"],
     "Not worth the drive to Battery Spencer today. No marine layer. Save it for a better day."),
    ("trojan-point", 14.0, 13.0, 55, 10, 5, 8.0, 0,
     95, Status("green"), "Go for it!", "Above the fog layer",
     ["Low cloud 55%|ok", "Wind 5 mph|good", "Clear above 10%|good", "Rain 0%|good", "Fog base 410 ft — below you|good"],
     "Strong conditions at Trojan Point. Fog base ~410 ft sits below you — expect a clean view down onto the layer. Low cloud at 55%, winds calm at 5 mph."),
    ("west-peak", 12.0, 12.0, 95, 0, 0, 30.0, 5,
     35, Status("red", "low"), "Maybe next time", "Socked in",
     ["Low cloud 95%|good", "Wind 19 mph|bad", "Clear above 0%|good", "Rain 5%|good", "Fog base 0 ft — socked in|bad"],
     "Marginal at West Peak. Wind may break up the layer. Fog base ~0 ft is very low — a deep layer may sock you in."),
]


@pytest.mark.parametrize("case", PARITY, ids=[f"{c[0]}-{c[8]}" for c in PARITY])
def test_parity_with_original_js(case):
    vid, t, td, low, mid, high, wind, rain, exp_score, exp_status, exp_verdict, exp_elev, exp_factors, exp_expl = case
    vp = viewpoint_by_id(vid)
    h = hour_from_values(t, td, low=low, mid=mid, high=high, wind_kmh=wind, rain=rain)
    r = score(vp, h)
    assert r.score == exp_score
    assert r.status == exp_status
    assert verdict(r.score).label == exp_verdict
    assert elevation_verdict(vp, h).title == exp_elev
    assert [f"{f.label}|{f.rating}" for f in r.factors] == exp_factors
    assert r.explanation == exp_expl


def test_fmt_ft_thousands_separator():
    assert fmt_ft(1271) == "1,271"
    assert fmt_ft(0) == "0"
    assert fmt_ft(950) == "950"


def test_green_bonus_caps_at_100():
    vp = viewpoint_by_id("east-peak")
    h = hour_from_values(14.2, 11.1, low=85, mid=5, high=0, wind_kmh=6.0, rain=0)
    assert score(vp, h).score == 100  # 40+20+20+20 = 100, +10 capped


def test_no_layer_caps_at_15_and_result_lcl_is_none():
    vp = viewpoint_by_id("east-peak")
    h = hour_from_values(18.0, 8.0, low=10, mid=0, high=0, wind_kmh=3.0, rain=0)
    r = score(vp, h)
    assert r.score == 15
    assert r.lcl_ft is None  # gated: thin low cloud means no fog base to report


def test_elevation_verdict_texts():
    vp = viewpoint_by_id("hawk-hill")
    green = hour_from_values(15.0, 13.5, low=80, mid=0, high=0, wind_kmh=0.0, rain=0)  # lcl 615
    e = elevation_verdict(vp, green)
    assert (e.cls, e.icon) == ("above", "🏔️")
    assert e.detail.startswith("Fog base sits around 615 ft — comfortably below Hawk Hill (923 ft).")
    assert e.detail.endswith(vp.composition)
    none = hour_from_values(15.0, 13.5, low=5, mid=0, high=0, wind_kmh=0.0, rain=0)
    e = elevation_verdict(vp, none)
    assert (e.cls, e.icon, e.title) == ("clear", "🔭", "No marine layer")
    assert "Hawk Hill at 923 ft." in e.detail
    red_high = hour_from_values(20.0, 12.0, low=80, mid=0, high=0, wind_kmh=0.0, rain=0)  # lcl 3281
    e = elevation_verdict(vp, red_high)
    assert (e.cls, e.title) == ("below", "Inside the layer")
    assert e.detail == f"Fog base ~3,281 ft. {vp.too_high} Consider a higher viewpoint."
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_score.py -q`
Expected: FAIL, `ImportError: cannot import name 'score'`

- [ ] **Step 3: Append scoring and elevation verdict to fog.py**

Append to `backend/goodfog/fog.py`:
```python


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
```

- [ ] **Step 4: Run all tests**

Run: `cd backend && uv run pytest -q`
Expected: all pass. If a parity case fails on the explanation string, the Python is wrong (the expected values came from the JS); fix Python, not the test.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(backend): scoring, explanation, and elevation verdict with JS parity tests"
```

---

### Task 4: Windows and Open-Meteo provider

**Files:**
- Create: `backend/goodfog/windows.py`, `backend/goodfog/providers/__init__.py`, `backend/goodfog/providers/open_meteo.py`, `backend/tests/test_windows.py`, `backend/tests/test_open_meteo.py`, `backend/tests/fixtures/open_meteo.json`

**Interfaces:**
- Produces: `Window(id, title, tab, sun_label, sun_event, arrive_by, hour)`, `build_windows(sunrise: list[str], sunset: list[str]) -> list[Window]`, `truncate_hour(iso) -> str`, `minus_minutes(iso, mins) -> str`.
- Produces: `ProviderError`, `Forecast(hourly_time: tuple[str,...], hourly: dict[str, tuple], sunrise: tuple[str,...], sunset: tuple[str,...])` with `Forecast.hour_at(iso) -> Hour | None`, `parse_open_meteo(payload, expected_points) -> list[Forecast]`, `OpenMeteoProvider(points, client, models).fetch() -> list[Forecast]`, `HOURLY_VARS`.

- [ ] **Step 1: Write failing windows tests**

`backend/tests/test_windows.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_windows.py -q`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: Implement windows**

`backend/goodfog/windows.py`:
```python
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
```

- [ ] **Step 4: Run windows tests**

Run: `cd backend && uv run pytest tests/test_windows.py -q`
Expected: 3 passed

- [ ] **Step 5: Download the real fixture (exact production query)**

```bash
cd /Users/mike/claudeprojects/goodfog/backend && mkdir -p tests/fixtures && curl -sS "https://api.open-meteo.com/v1/forecast?latitude=37.8283,37.8278,37.827,37.7874,37.8156,37.917,37.9279,37.9236&longitude=-122.4997,-122.4818,-122.49,-122.4581,-122.5295,-122.598,-122.6017,-122.58&hourly=cloudcover_low,cloudcover_mid,cloudcover_high,windspeed_10m,precipitation_probability,temperature_2m,dewpoint_2m&daily=sunrise,sunset&timezone=America%2FLos_Angeles&forecast_days=3&models=best_match" -o tests/fixtures/open_meteo.json && python3 -c "import json;d=json.load(open('tests/fixtures/open_meteo.json'));print(type(d).__name__, len(d), d[0]['hourly']['time'][0], d[0]['daily']['sunset'][0])"
```
Expected output like `list 8 2026-09-02T00:00 2026-09-02T19:3x`. If a list is not returned, stop and report; the parser assumes Open-Meteo's multi-location array shape.

- [ ] **Step 6: Write failing provider tests**

`backend/tests/test_open_meteo.py`:
```python
import json
from pathlib import Path

import httpx
import pytest
import respx

from goodfog.providers import ProviderError
from goodfog.providers.open_meteo import URL, OpenMeteoProvider, parse_open_meteo
from goodfog.viewpoints import VIEWPOINTS

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "open_meteo.json").read_text())


def test_parse_maps_by_index_and_exposes_daily():
    fcs = parse_open_meteo(FIXTURE, expected_points=8)
    assert len(fcs) == 8
    f = fcs[0]
    assert len(f.hourly_time) == 72
    assert len(f.sunrise) == 3 and len(f.sunset) == 3
    assert f.sunset[0].startswith(f.hourly_time[0][:10])  # same local day


def test_hour_at_returns_hour_or_none():
    f = parse_open_meteo(FIXTURE, expected_points=8)[7]
    key = f.hourly_time[20]
    h = f.hour_at(key)
    assert h is not None
    assert 0 <= h.low_cloud <= 100
    assert f.hour_at("1999-01-01T00:00") is None


def test_hour_at_handles_null_dewpoint():
    payload = json.loads(json.dumps(FIXTURE[:1]))
    payload[0]["hourly"]["dewpoint_2m"][5] = None
    payload[0]["hourly"]["cloudcover_low"][5] = None
    f = parse_open_meteo(payload, expected_points=1)[0]
    h = f.hour_at(f.hourly_time[5])
    assert h.lcl_ft is None and h.dewpoint_f is None and h.low_cloud == 0


def test_parse_rejects_wrong_count_and_malformed():
    with pytest.raises(ProviderError):
        parse_open_meteo(FIXTURE[:3], expected_points=8)
    with pytest.raises(ProviderError):
        parse_open_meteo([{"hourly": {}}], expected_points=1)


@respx.mock
async def test_fetch_builds_multi_point_query():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    async with httpx.AsyncClient() as client:
        p = OpenMeteoProvider([(v.lat, v.lon) for v in VIEWPOINTS], client, models="best_match")
        fcs = await p.fetch()
    assert len(fcs) == 8
    q = route.calls.last.request.url.params
    assert q["latitude"] == ",".join(str(v.lat) for v in VIEWPOINTS)
    assert q["timezone"] == "America/Los_Angeles"
    assert q["forecast_days"] == "3"
    assert q["models"] == "best_match"
    assert "dewpoint_2m" in q["hourly"]


@respx.mock
async def test_fetch_http_error_is_provider_error():
    respx.get(URL).mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as client:
        p = OpenMeteoProvider([(1.0, 2.0)], client, models="best_match")
        with pytest.raises(ProviderError):
            await p.fetch()
```

- [ ] **Step 7: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_open_meteo.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'goodfog.providers'`

- [ ] **Step 8: Implement provider**

`backend/goodfog/providers/__init__.py`:
```python
class ProviderError(Exception):
    """Upstream fetch or parse failed; the poller keeps the previous snapshot."""
```

`backend/goodfog/providers/open_meteo.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..fog import Hour, hour_from_values
from . import ProviderError

URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = (
    "cloudcover_low,cloudcover_mid,cloudcover_high,windspeed_10m,"
    "precipitation_probability,temperature_2m,dewpoint_2m"
)
FORECAST_DAYS = 3


@dataclass(frozen=True)
class Forecast:
    hourly_time: tuple[str, ...]
    hourly: dict[str, tuple]
    sunrise: tuple[str, ...]
    sunset: tuple[str, ...]

    def hour_at(self, iso_hour: str) -> Hour | None:
        try:
            i = self.hourly_time.index(iso_hour)
        except ValueError:
            return None
        h = self.hourly
        return hour_from_values(
            h["temperature_2m"][i], h["dewpoint_2m"][i],
            low=h["cloudcover_low"][i], mid=h["cloudcover_mid"][i], high=h["cloudcover_high"][i],
            wind_kmh=float(h["windspeed_10m"][i] or 0.0), rain=h["precipitation_probability"][i],
        )


def _parse_one(obj: dict) -> Forecast:
    try:
        hourly = obj["hourly"]
        daily = obj["daily"]
        return Forecast(
            hourly_time=tuple(hourly["time"]),
            hourly={k: tuple(hourly[k]) for k in HOURLY_VARS.split(",")},
            sunrise=tuple(daily["sunrise"]),
            sunset=tuple(daily["sunset"]),
        )
    except (KeyError, TypeError) as e:
        raise ProviderError(f"malformed Open-Meteo payload: {e!r}") from e


def parse_open_meteo(payload, expected_points: int) -> list[Forecast]:
    objs = [payload] if isinstance(payload, dict) else list(payload)
    if len(objs) != expected_points:
        raise ProviderError(f"expected {expected_points} points, got {len(objs)}")
    return [_parse_one(o) for o in objs]


class OpenMeteoProvider:
    name = "open_meteo"

    def __init__(self, points: list[tuple[float, float]], client: httpx.AsyncClient, models: str) -> None:
        self.points = points
        self.client = client
        self.models = models

    async def fetch(self) -> list[Forecast]:
        params = {
            "latitude": ",".join(str(lat) for lat, _ in self.points),
            "longitude": ",".join(str(lon) for _, lon in self.points),
            "hourly": HOURLY_VARS,
            "daily": "sunrise,sunset",
            "timezone": "America/Los_Angeles",
            "forecast_days": str(FORECAST_DAYS),
            "models": self.models,
        }
        try:
            r = await self.client.get(URL, params=params, timeout=15.0)
            r.raise_for_status()
            return parse_open_meteo(r.json(), len(self.points))
        except httpx.HTTPError as e:
            raise ProviderError(f"Open-Meteo request failed: {e!r}") from e
```

- [ ] **Step 9: Run all tests**

Run: `cd backend && uv run pytest -q`
Expected: all pass

- [ ] **Step 10: Commit**

```bash
git add backend
git commit -m "feat(backend): viewing windows and Open-Meteo multi-point provider"
```

---

### Task 5: Snapshot builder and poller

**Files:**
- Create: `backend/goodfog/snapshot.py`, `backend/goodfog/poller.py`, `backend/tests/test_snapshot.py`, `backend/tests/test_poller.py`

**Interfaces:**
- Consumes: `VIEWPOINTS`, `Forecast`, `build_windows`, `score`, `verdict`, `elevation_verdict`, `ProviderError`.
- Produces: `build_snapshot(viewpoints, forecasts, *, now: datetime, app_version: str, commit: str) -> dict` (JSON-ready, shape per spec §4.4 plus result-level `lcl_ft`).
- Produces: `Poller(provider, poll_minutes, app_version, commit)` with `.snapshot: dict | None`, `.last_error: str | None`, `.generated_at: datetime | None`, `async poll_once(now=None)`, `async run_forever()`, `health(now) -> dict`.

- [ ] **Step 1: Write failing snapshot test**

`backend/tests/test_snapshot.py`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path

from goodfog.providers.open_meteo import parse_open_meteo
from goodfog.snapshot import build_snapshot
from goodfog.viewpoints import VIEWPOINTS

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "open_meteo.json").read_text())
NOW = datetime(2026, 9, 2, 23, 15, tzinfo=timezone.utc)


def _snap():
    return build_snapshot(VIEWPOINTS, parse_open_meteo(FIXTURE, 8), now=NOW, app_version="0.1.0", commit="abc1234")


def test_top_level_shape():
    s = _snap()
    assert s["app_version"] == "0.1.0" and s["commit"] == "abc1234"
    assert s["generated_at"] == "2026-09-02T23:15:00+00:00"
    assert [w["id"] for w in s["windows"]] == ["tonight", "tomorrow_am", "tomorrow_pm"]
    assert set(s["windows"][0]) == {"id", "title", "tab", "sun_label", "sun_event", "arrive_by", "hour"}
    assert [v["id"] for v in s["viewpoints"]] == [v.id for v in VIEWPOINTS]


def test_viewpoint_entry_shape():
    v = _snap()["viewpoints"][-1]
    assert v["name"] == "East Peak" and v["elev_ft"] == 2571
    assert v["green_ft"] == [200, 2400] and v["yellow_ft"] == [2400, 2571] and v["dawn_gated"] is True
    for key in ("desc", "composition", "access", "cam_tip"):
        assert isinstance(v[key], str) and v[key]
    r = v["results"]["tonight"]
    assert set(r) == {"score", "verdict", "status", "factors", "explanation", "elevation", "lcl_ft", "wx"}
    assert set(r["verdict"]) == {"label", "emoji", "cls"}
    assert set(r["status"]) == {"kind", "reason"}
    assert set(r["factors"][0]) == {"label", "rating"}
    assert set(r["elevation"]) == {"cls", "icon", "title", "detail"}
    assert set(r["wx"]) == {"low_cloud", "mid_cloud", "high_cloud", "wind_mph", "rain_pct", "temp_f", "dewpoint_f", "lcl_ft"}
    assert 0 <= r["score"] <= 100


def test_missing_hour_gives_null_result():
    fcs = parse_open_meteo(FIXTURE, 8)
    broken = fcs[0].__class__(hourly_time=(), hourly=fcs[0].hourly, sunrise=fcs[0].sunrise, sunset=fcs[0].sunset)
    s = build_snapshot(VIEWPOINTS, [broken] + fcs[1:], now=NOW, app_version="x", commit="y")
    assert s["viewpoints"][0]["results"] == {"tonight": None, "tomorrow_am": None, "tomorrow_pm": None}
    assert s["viewpoints"][1]["results"]["tonight"] is not None


def test_snapshot_is_json_serializable():
    json.dumps(_snap())
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_snapshot.py -q`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: Implement snapshot**

`backend/goodfog/snapshot.py`:
```python
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


def _viewpoint(vp: Viewpoint, fc: Forecast, windows) -> dict:
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
        "results": {w.id: _result(vp, fc.hour_at(w.hour)) for w in windows},
    }


def build_snapshot(
    viewpoints, forecasts: list[Forecast], *, now: datetime, app_version: str, commit: str
) -> dict:
    # Sunrise/sunset differ by seconds across these points; use the first viewpoint's daily block
    # for the shared window definitions, exactly as the original app used the selected spot's.
    windows = build_windows(list(forecasts[0].sunrise), list(forecasts[0].sunset))
    return {
        "app_version": app_version,
        "commit": commit,
        "generated_at": now.isoformat(timespec="seconds"),
        "windows": [asdict(w) for w in windows],
        "viewpoints": [_viewpoint(vp, fc, windows) for vp, fc in zip(viewpoints, forecasts, strict=True)],
    }
```

- [ ] **Step 4: Run snapshot tests**

Run: `cd backend && uv run pytest tests/test_snapshot.py -q`
Expected: 4 passed

- [ ] **Step 5: Write failing poller tests**

`backend/tests/test_poller.py`:
```python
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from goodfog.poller import Poller
from goodfog.providers import ProviderError
from goodfog.providers.open_meteo import parse_open_meteo

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "open_meteo.json").read_text())
T0 = datetime(2026, 9, 2, 23, 0, tzinfo=timezone.utc)


class FakeProvider:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = 0

    async def fetch(self):
        self.calls += 1
        if self.fail:
            raise ProviderError("boom")
        return parse_open_meteo(FIXTURE, 8)


async def test_poll_once_builds_snapshot():
    p = Poller(FakeProvider(), poll_minutes=15, app_version="0.1.0", commit="dev")
    assert p.snapshot is None
    await p.poll_once(now=T0)
    assert p.snapshot["app_version"] == "0.1.0"
    assert p.generated_at == T0
    assert p.last_error is None


async def test_failure_keeps_previous_snapshot_and_records_error():
    prov = FakeProvider()
    p = Poller(prov, poll_minutes=15, app_version="0.1.0", commit="dev")
    await p.poll_once(now=T0)
    prov.fail = True
    await p.poll_once(now=T0 + timedelta(minutes=15))
    assert p.snapshot is not None and p.generated_at == T0
    assert "boom" in p.last_error


async def test_health_stale_after_three_missed_polls():
    p = Poller(FakeProvider(), poll_minutes=15, app_version="0.1.0", commit="dev")
    h = p.health(now=T0)
    assert h["status"] == "warming_up" and h["stale"] is True
    await p.poll_once(now=T0)
    assert p.health(now=T0 + timedelta(minutes=44))["stale"] is False
    assert p.health(now=T0 + timedelta(minutes=46))["stale"] is True
    h = p.health(now=T0)
    assert h["status"] == "ok" and h["app_version"] == "0.1.0" and h["generated_at"] == T0.isoformat(timespec="seconds")
```

- [ ] **Step 6: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_poller.py -q`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 7: Implement poller**

`backend/goodfog/poller.py`:
```python
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .providers import ProviderError
from .snapshot import build_snapshot
from .viewpoints import VIEWPOINTS

log = logging.getLogger(__name__)

STALE_AFTER_POLLS = 3


class Poller:
    def __init__(self, provider, poll_minutes: int, app_version: str, commit: str) -> None:
        self.provider = provider
        self.interval = timedelta(minutes=poll_minutes)
        self.app_version = app_version
        self.commit = commit
        self.snapshot: dict | None = None
        self.generated_at: datetime | None = None
        self.last_error: str | None = None

    async def poll_once(self, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        try:
            forecasts = await self.provider.fetch()
        except ProviderError as e:
            self.last_error = str(e)
            log.warning("poll failed, keeping previous snapshot: %s", e)
            return
        self.snapshot = build_snapshot(VIEWPOINTS, forecasts, now=now, app_version=self.app_version, commit=self.commit)
        self.generated_at = now
        self.last_error = None
        log.info("snapshot updated")

    async def run_forever(self) -> None:
        while True:
            try:
                await self.poll_once()
            except Exception:  # never let the loop die
                log.exception("unexpected poll error")
            await asyncio.sleep(self.interval.total_seconds())

    def health(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        stale = self.generated_at is None or now - self.generated_at > STALE_AFTER_POLLS * self.interval
        return {
            "status": "ok" if self.snapshot is not None else "warming_up",
            "app_version": self.app_version,
            "commit": self.commit,
            "generated_at": self.generated_at.isoformat(timespec="seconds") if self.generated_at else None,
            "stale": stale,
            "last_error": self.last_error,
        }
```

- [ ] **Step 8: Run all tests**

Run: `cd backend && uv run pytest -q`
Expected: all pass

- [ ] **Step 9: Commit**

```bash
git add backend
git commit -m "feat(backend): snapshot builder and scheduled poller"
```

---

### Task 6: FastAPI app and backend Dockerfile

**Files:**
- Create: `backend/goodfog/app.py`, `backend/tests/test_app.py`, `backend/Dockerfile`

**Interfaces:**
- Consumes: `Settings`, `Poller`, `OpenMeteoProvider`, `VIEWPOINTS`.
- Produces: `create_app(settings=None, poller=None) -> FastAPI`, module-level `app`; routes `GET /api/snapshot` (200 dict or 503 `{"status":"warming_up"}`), `GET /api/health`.

- [ ] **Step 1: Write failing app tests**

`backend/tests/test_app.py` (no lifespan runs under `httpx.ASGITransport`, so the test injects a pre-built poller; do not add `asgi-lifespan`):
```python
import json
from pathlib import Path

import httpx

from goodfog.app import create_app
from goodfog.config import Settings
from goodfog.poller import Poller
from goodfog.providers.open_meteo import parse_open_meteo

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "open_meteo.json").read_text())


class FakeProvider:
    async def fetch(self):
        return parse_open_meteo(FIXTURE, 8)


def _settings():
    return Settings(poll_minutes=15, open_meteo_models="best_match", app_version="0.1.0", commit="abc1234")


def _client(poller):
    app = create_app(_settings(), poller=poller)
    app.state.poller = poller  # lifespan does not run under ASGITransport
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_snapshot_503_while_warming_up():
    poller = Poller(FakeProvider(), 15, "0.1.0", "abc1234")
    async with _client(poller) as c:
        r = await c.get("/api/snapshot")
    assert r.status_code == 503 and r.json() == {"status": "warming_up"}


async def test_snapshot_and_health_after_poll():
    poller = Poller(FakeProvider(), 15, "0.1.0", "abc1234")
    await poller.poll_once()
    async with _client(poller) as c:
        s = await c.get("/api/snapshot")
        h = await c.get("/api/health")
    assert s.status_code == 200
    assert s.headers["cache-control"] == "no-cache"
    assert len(s.json()["viewpoints"]) == 8
    assert h.status_code == 200
    body = h.json()
    assert body["status"] == "ok" and body["app_version"] == "0.1.0" and body["commit"] == "abc1234"
    assert body["stale"] is False
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_app.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'goodfog.app'`

- [ ] **Step 3: Implement app**

`backend/goodfog/app.py`:
```python
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .poller import Poller
from .providers.open_meteo import OpenMeteoProvider
from .viewpoints import VIEWPOINTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def build_poller(settings: Settings, client: httpx.AsyncClient) -> Poller:
    provider = OpenMeteoProvider([(v.lat, v.lon) for v in VIEWPOINTS], client, models=settings.open_meteo_models)
    return Poller(provider, settings.poll_minutes, settings.app_version, settings.commit)


def create_app(settings: Settings | None = None, poller: Poller | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = httpx.AsyncClient()
        app.state.poller = poller or build_poller(settings, client)
        task = asyncio.create_task(app.state.poller.run_forever())
        try:
            yield
        finally:
            task.cancel()
            await client.aclose()

    app = FastAPI(title="Good Fog", lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    @app.get("/api/snapshot")
    async def snapshot():
        snap = app.state.poller.snapshot
        if snap is None:
            return JSONResponse({"status": "warming_up"}, status_code=503, headers={"Cache-Control": "no-cache"})
        return JSONResponse(snap, headers={"Cache-Control": "no-cache"})

    @app.get("/api/health")
    async def health():
        return app.state.poller.health()

    return app


app = create_app()
```

- [ ] **Step 4: Run all tests**

Run: `cd backend && uv run pytest -q`
Expected: all pass

- [ ] **Step 5: Write the Dockerfile**

`backend/Dockerfile`:
```dockerfile
# Build context is the repo root (see docker-compose.yml).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/goodfog ./goodfog
ENV PYTHONPATH=/app PATH="/app/.venv/bin:$PATH"
# Baked in at build time (Coolify passes SOURCE_COMMIT as a build arg); reported by /api/health.
# Stored under a different name on purpose: Coolify's compose parser auto-creates an (empty)
# SOURCE_COMMIT app variable for any ${SOURCE_COMMIT} reference and injects it into the container's
# runtime env, which would override an image ENV of the same name. Settings falls back to BUILD_COMMIT.
ARG SOURCE_COMMIT=dev
ENV BUILD_COMMIT=${SOURCE_COMMIT}
RUN useradd -r -u 10001 app && chown -R app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"
CMD ["uvicorn", "goodfog.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Smoke-run the server**

```bash
cd /Users/mike/claudeprojects/goodfog/backend && (uv run uvicorn goodfog.app:app --port 8000 & echo $! > /tmp/gf.pid) && sleep 6 && curl -s localhost:8000/api/health && echo && curl -s localhost:8000/api/snapshot | head -c 400; kill $(cat /tmp/gf.pid)
```
Expected: health JSON with `"status":"ok"` and a snapshot beginning with `{"app_version":"0.1.0"`.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat(backend): FastAPI app with snapshot/health routes and Dockerfile"
```

---

### Task 7: Frontend scaffold and pure helpers

**Files:**
- Create: `frontend/package.json`, `frontend/package-lock.json` (generated), `frontend/vite.config.js`, `frontend/index.html`, `frontend/src/main.js`, `frontend/src/app.css`, `frontend/src/App.svelte` (placeholder), `frontend/public/favicon.svg`, `frontend/public/icon-192.png`, `frontend/public/icon-512.png`, `frontend/src/lib/{api,version,time,colors,barScale,plan}.js` and matching `.test.js`
- Modify: `backend/tests/test_config.py` (add version-match test)

**Interfaces:**
- Produces: `fetchSnapshot(fetchImpl) -> {status:'ok',data}|{status:'warming_up'}|{status:'error',error}`; `formatVersion(version, sha)`; `fmtTime(iso) -> 'h:mm AM'`; `scoreColor(score)`; `niceMax(v)`, `barModel(vp, lclFt) -> {maxFt, locPct, lclPct, bandL, bandW, bandCenter}`; `bestWindow(windows, results) -> window|null`, `planSummary(best, bestResult, vp) -> string`.

- [ ] **Step 1: Write package.json, vite config, index.html, main.js, app.css, placeholder App**

`frontend/package.json`:
```json
{
  "name": "goodfog-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "svelte": "5.56.10"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "7.3.0",
    "vite": "8.2.2",
    "vite-plugin-pwa": "1.3.0",
    "vitest": "4.1.11"
  }
}
```

`frontend/vite.config.js`:
```js
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { VitePWA } from 'vite-plugin-pwa';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(fs.readFileSync(path.resolve(here, 'package.json'), 'utf8'));

export default defineConfig({
  // Footer build label; VITE_COMMIT is set by frontend/Dockerfile from Coolify's SOURCE_COMMIT.
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  plugins: [
    svelte(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'Good Fog',
        short_name: 'Good Fog',
        description: 'Will you be above the marine layer or inside it?',
        theme_color: '#0d1117',
        background_color: '#0d1117',
        display: 'standalone',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname === '/api/snapshot',
            handler: 'NetworkFirst',
            options: { cacheName: 'snapshot', networkTimeoutSeconds: 8, expiration: { maxEntries: 1 } },
          },
        ],
      },
    }),
  ],
  server: { proxy: { '/api': 'http://localhost:8000' } },
  test: { environment: 'node', include: ['src/**/*.test.js'] },
});
```

`frontend/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#0d1117" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <title>Good Fog — Marin inversion checker</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

`frontend/src/main.js`:
```js
import { registerSW } from 'virtual:pwa-register';
import { mount } from 'svelte';
import './app.css';
import App from './App.svelte';

registerSW({ immediate: true });

export default mount(App, { target: document.getElementById('app') });
```

`frontend/src/app.css` (global styles ported from the original `<style>` block; component-scoped styles come later):
```css
* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0d1117;
  --panel: #161b22;
  --panel2: #21262d;
  --border: #30363d;
  --text: #e6edf3;
  --text-strong: #f0f6fc;
  --muted: #8b949e;
  --body: #c9d1d9;
  --green: #238636;
  --green-text: #3fb950;
  --blue: #58a6ff;
  --fog: #79c0ff;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  padding: 16px;
}

.container { max-width: 520px; margin: 0 auto; }

.card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}

.card h3 {
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin-bottom: 12px;
}

.explanation { font-size: 0.86rem; line-height: 1.6; color: var(--body); }

.timing-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--panel2);
  font-size: 0.88rem;
}
.timing-row:last-child { border-bottom: none; }
.timing-label { color: var(--muted); }
.timing-value { font-weight: 600; }

.wx-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.wx-label { font-size: 0.73rem; color: var(--muted); margin-bottom: 2px; }
.wx-value { font-size: 1rem; font-weight: 600; }

.factors { display: flex; flex-wrap: wrap; gap: 8px; }
.factor { background: var(--panel2); border-radius: 20px; padding: 5px 11px; font-size: 0.8rem; }
.factor.good { border-left: 3px solid #238636; }
.factor.ok   { border-left: 3px solid #9e6a03; }
.factor.bad  { border-left: 3px solid #8b2020; }

.error-box {
  background: #3d0d12;
  border: 1px solid #8b2020;
  border-radius: 10px;
  padding: 16px;
  font-size: 0.88rem;
  color: #ffa7a7;
  margin-bottom: 16px;
}
```

`frontend/src/App.svelte` placeholder (replaced in Task 8):
```svelte
<div class="container"><h1>Good Fog</h1></div>
```

Icons: copy Mrs. Toasty's PNGs as placeholders and write a fog favicon:
```bash
cd /Users/mike/claudeprojects/goodfog/frontend && mkdir -p public && cp /Users/mike/claudeprojects/mrstoasty/frontend/public/icon-192.png /Users/mike/claudeprojects/mrstoasty/frontend/public/icon-512.png public/ && cat > public/favicon.svg <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0d1117"/><path d="M8 40h48M8 48h40M16 32h40" stroke="#79c0ff" stroke-width="5" stroke-linecap="round"/><circle cx="46" cy="18" r="8" fill="#d29922"/></svg>
SVG
```

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/mike/claudeprojects/goodfog/frontend && npm install --ignore-scripts && npm audit signatures
```
Expected: lockfile created, "verified" signatures. If npm reports `pkg@undefined`, a pinned version is newer than the 3-day cooldown; pick the previous release of that package and stay exact-pinned.

- [ ] **Step 3: Write failing helper tests**

`frontend/src/lib/api.test.js`:
```js
import { describe, it, expect } from 'vitest';
import { fetchSnapshot } from './api.js';

const mk = (status, body) => async () => ({ status, ok: status >= 200 && status < 300, json: async () => body });

describe('fetchSnapshot', () => {
  it('returns ok with data', async () => {
    expect(await fetchSnapshot(mk(200, { a: 1 }))).toEqual({ status: 'ok', data: { a: 1 } });
  });
  it('maps 503 to warming_up', async () => {
    expect(await fetchSnapshot(mk(503, {}))).toEqual({ status: 'warming_up' });
  });
  it('maps other errors and thrown fetches to error', async () => {
    expect((await fetchSnapshot(mk(500, {}))).status).toBe('error');
    expect((await fetchSnapshot(async () => { throw new Error('offline'); })).status).toBe('error');
  });
});
```

`frontend/src/lib/version.test.js`:
```js
import { it, expect } from 'vitest';
import { formatVersion } from './version.js';

it('formats version and short sha', () => {
  expect(formatVersion('0.1.0', 'a1b2c3d4e5f6')).toBe('v0.1.0 · a1b2c3d');
  expect(formatVersion('0.1.0', '')).toBe('v0.1.0 · dev');
  expect(formatVersion('0.1.0', undefined)).toBe('v0.1.0 · dev');
});
```

`frontend/src/lib/time.test.js`:
```js
import { it, expect } from 'vitest';
import { fmtTime } from './time.js';

it('formats local ISO strings as 12-hour times', () => {
  expect(fmtTime('2026-09-02T19:32')).toBe('7:32 PM');
  expect(fmtTime('2026-09-03T06:05')).toBe('6:05 AM');
  expect(fmtTime('2026-09-03T00:00')).toBe('12:00 AM');
});
```

`frontend/src/lib/colors.test.js`:
```js
import { it, expect } from 'vitest';
import { scoreColor } from './colors.js';

it('maps score bands to colors', () => {
  expect(scoreColor(70)).toBe('#3fb950');
  expect(scoreColor(50)).toBe('#d29922');
  expect(scoreColor(30)).toBe('#e3812c');
  expect(scoreColor(29)).toBe('#f85149');
  expect(scoreColor(null)).toBe('#8b949e');
});
```

`frontend/src/lib/barScale.test.js`:
```js
import { describe, it, expect } from 'vitest';
import { barModel, niceMax } from './barScale.js';

const hawk = { elev_ft: 923, green_ft: [200, 850], yellow_ft: [850, 950] };
const bonita = { elev_ft: 100, green_ft: [50, 200], yellow_ft: [200, 300] };

describe('niceMax', () => {
  it('rounds up to a clean maximum by band', () => {
    expect(niceMax(360)).toBe(400);
    expect(niceMax(500)).toBe(500);
    expect(niceMax(1140)).toBe(1250);
    expect(niceMax(1500)).toBe(1500);
    expect(niceMax(3085)).toBe(3500);
  });
});

describe('barModel', () => {
  it('scales the axis to the viewpoint and fog base', () => {
    const m = barModel(hawk, 1271);
    expect(m.maxFt).toBe(2000); // max(923, 950, 1271) * 1.2 = 1525.2 -> ceil to 500s -> 2000
    expect(m.locPct).toBeCloseTo((923 / 2000) * 100, 5);
    expect(m.lclPct).toBeCloseTo((1271 / 2000) * 100, 5);
    expect(m.bandL).toBeCloseTo((200 / 2000) * 100, 5);
    expect(m.bandW).toBeCloseTo(((850 - 200) / 2000) * 100, 5);
    expect(m.bandCenter).toBeCloseTo((525 / 2000) * 100, 5);
  });
  it('omits the fog marker when there is no layer', () => {
    const m = barModel(bonita, null);
    expect(m.maxFt).toBe(400); // max(100, 300, 0) * 1.2 = 360 -> 400
    expect(m.lclPct).toBeNull();
  });
  it('clamps percentages to 0..100', () => {
    expect(barModel(hawk, 100000).lclPct).toBe(100);
  });
});
```

`frontend/src/lib/plan.test.js`:
```js
import { describe, it, expect } from 'vitest';
import { bestWindow, planSummary } from './plan.js';

const windows = [
  { id: 'tonight', tab: '🌅 Tonight', sun_event: '2026-09-02T19:32' },
  { id: 'tomorrow_am', tab: '🌄 Tom. AM', sun_event: '2026-09-03T06:52' },
  { id: 'tomorrow_pm', tab: '🌇 Tom. PM', sun_event: '2026-09-03T19:31' },
];
const vp = { name: 'Hawk Hill', elev_ft: 923 };

describe('bestWindow', () => {
  it('picks the highest score, earliest on ties', () => {
    const results = { tonight: { score: 50 }, tomorrow_am: { score: 80 }, tomorrow_pm: { score: 80 } };
    expect(bestWindow(windows, results).id).toBe('tomorrow_am');
  });
  it('treats null results as -1', () => {
    const results = { tonight: null, tomorrow_am: null, tomorrow_pm: { score: 0 } };
    expect(bestWindow(windows, results).id).toBe('tomorrow_pm');
  });
  it('returns the first window when everything is null', () => {
    expect(bestWindow(windows, { tonight: null, tomorrow_am: null, tomorrow_pm: null }).id).toBe('tonight');
  });
});

describe('planSummary', () => {
  it('names the best bet when score >= 40', () => {
    const s = planSummary(windows[1], { score: 80, lcl_ft: 615 }, vp);
    expect(s).toBe('Best bet: 🌄 Tom. AM at 6:52 AM — 80% likelihood. Fog base ~615 ft vs Hawk Hill at 923 ft.');
  });
  it('omits the fog-base clause when lcl is null', () => {
    expect(planSummary(windows[0], { score: 45, lcl_ft: null }, vp)).toBe('Best bet: 🌅 Tonight at 7:32 PM — 45% likelihood.');
  });
  it('says no great windows below 40 or when null', () => {
    const msg = 'No great windows in the next two days for Hawk Hill. Check a higher viewpoint or wait for the next marine layer event.';
    expect(planSummary(windows[0], { score: 39, lcl_ft: 100 }, vp)).toBe(msg);
    expect(planSummary(windows[0], null, vp)).toBe(msg);
  });
});
```

- [ ] **Step 4: Run to verify failure**

Run: `cd frontend && npm test`
Expected: FAIL, modules not found

- [ ] **Step 5: Implement helpers**

`frontend/src/lib/api.js`:
```js
/** Fetch /api/snapshot. Never throws; returns a tagged result. */
export async function fetchSnapshot(fetchImpl = fetch) {
  try {
    const r = await fetchImpl('/api/snapshot', { headers: { Accept: 'application/json' } });
    if (r.status === 503) return { status: 'warming_up' };
    if (!r.ok) return { status: 'error', error: `HTTP ${r.status}` };
    return { status: 'ok', data: await r.json() };
  } catch (e) {
    return { status: 'error', error: String(e) };
  }
}
```

`frontend/src/lib/version.js`:
```js
/** Footer build label: 'v0.1.0 · a1b2c3d', or 'v0.1.0 · dev' when no commit sha is known. */
export function formatVersion(version, sha) {
  const short = (sha ?? '').trim().slice(0, 7) || 'dev';
  return `v${version} · ${short}`;
}
```

`frontend/src/lib/time.js`:
```js
/** Format a local ISO string (no offset, as Open-Meteo returns) as '7:32 PM'. Pure string math, no Date. */
export function fmtTime(iso) {
  const [h, m] = iso.slice(11, 16).split(':').map(Number);
  const suffix = h >= 12 ? 'PM' : 'AM';
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return `${hour12}:${String(m).padStart(2, '0')} ${suffix}`;
}
```

`frontend/src/lib/colors.js`:
```js
export function scoreColor(score) {
  if (score == null) return '#8b949e';
  if (score >= 70) return '#3fb950';
  if (score >= 50) return '#d29922';
  if (score >= 30) return '#e3812c';
  return '#f85149';
}
```

`frontend/src/lib/barScale.js`:
```js
/** Round up to a clean axis maximum with headroom, so low spots aren't crushed against the left edge. */
export function niceMax(v) {
  if (v <= 500) return Math.ceil(v / 100) * 100;
  if (v <= 1500) return Math.ceil(v / 250) * 250;
  return Math.ceil(v / 500) * 500;
}

/**
 * Geometry for the fog-base-vs-elevation bar. `lclFt` is null when there is no marine layer.
 * Percentages are 0..100 along the bar.
 */
export function barModel(vp, lclFt) {
  const topFt = Math.max(vp.elev_ft, vp.yellow_ft[1], lclFt != null ? lclFt : 0);
  const maxFt = niceMax(topFt * 1.2);
  const pct = (ft) => Math.min(100, Math.max(0, (ft / maxFt) * 100));
  const [g0, g1] = vp.green_ft;
  return {
    maxFt,
    locPct: pct(vp.elev_ft),
    lclPct: lclFt != null ? pct(lclFt) : null,
    bandL: pct(g0),
    bandW: pct(g1) - pct(g0),
    bandCenter: pct((g0 + g1) / 2),
  };
}
```

`frontend/src/lib/plan.js`:
```js
import { fmtTime } from './time.js';

const scoreOf = (r) => r?.score ?? -1;

/** Highest-scoring window; earliest wins ties (original reduce used strict >). */
export function bestWindow(windows, results) {
  return windows.reduce((a, b) => (scoreOf(results[b.id]) > scoreOf(results[a.id]) ? b : a));
}

export function planSummary(best, result, vp) {
  if (!result || result.score < 40) {
    return `No great windows in the next two days for ${vp.name}. Check a higher viewpoint or wait for the next marine layer event.`;
  }
  const fog = result.lcl_ft != null
    ? ` Fog base ~${result.lcl_ft.toLocaleString('en-US')} ft vs ${vp.name} at ${vp.elev_ft.toLocaleString('en-US')} ft.`
    : '';
  return `Best bet: ${best.tab} at ${fmtTime(best.sun_event)} — ${result.score}% likelihood.${fog}`;
}
```

- [ ] **Step 6: Run frontend tests and build**

Run: `cd frontend && npm test && npm run build`
Expected: all tests pass; `dist/` produced with a service worker.

- [ ] **Step 7: Add the version-match test to the backend**

Append to `backend/tests/test_config.py`:
```python


def test_frontend_and_backend_versions_match():
    # Footer shows package.json's version; /api/health shows pyproject's. Bump both together.
    import json

    pkg = json.loads((ROOT / "frontend" / "package.json").read_text())
    assert pkg["version"] == _pyproject_version()
```

Run: `cd backend && uv run pytest -q` → all pass.

- [ ] **Step 8: Commit**

```bash
git add frontend backend/tests/test_config.py
git commit -m "feat(frontend): Svelte/Vite PWA scaffold and tested pure helpers"
```

---

### Task 8: App shell, picker, tabs, verdict, elevation banner and bar

**Files:**
- Modify: `frontend/src/App.svelte`
- Create: `frontend/src/components/Header.svelte`, `LocationPicker.svelte`, `Tabs.svelte`, `VerdictBanner.svelte`, `ElevationBanner.svelte`, `ElevationBar.svelte`, `WindowView.svelte`

**Interfaces:**
- Consumes: `fetchSnapshot`, `barModel`, `fmtTime`; snapshot shape from Task 5.
- Produces: `WindowView` props `{ vp, win, result }` (`win` is a snapshot window; named to avoid shadowing the global `window`) which Task 9 extends with more cards; `App.svelte` state `selectedId`, `tab`; `TABS` constant `[...snapshot.windows.map(w => ({id: w.id, label: w.tab})), {id:'plan', label:'🔭 Plan'}]`.

- [ ] **Step 1: Write the components**

`frontend/src/components/Header.svelte`:
```svelte
<header>
  <h1>🌁 Good Fog</h1>
  <p>Marine layer viewer — above or in the clouds?</p>
</header>

<style>
  header { text-align: center; padding: 24px 0 16px; }
  h1 { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; color: var(--text-strong); }
  p { color: var(--muted); font-size: 0.85rem; margin-top: 4px; }
</style>
```

`frontend/src/components/LocationPicker.svelte`:
```svelte
<script>
  let { viewpoints, selectedId, onselect } = $props();
</script>

<p class="loc-label">Choose your viewpoint</p>
<div class="loc-grid">
  {#each viewpoints as vp (vp.id)}
    <button class="loc-btn" class:active={vp.id === selectedId} onclick={() => onselect(vp.id)}>
      <div class="loc-name">{vp.name}</div>
      <div class="loc-elev">{vp.desc}</div>
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
</style>
```

`frontend/src/components/Tabs.svelte`:
```svelte
<script>
  let { tabs, active, onselect } = $props();
</script>

<div class="tabs">
  {#each tabs as t (t.id)}
    <button class="tab" class:active={t.id === active} onclick={() => onselect(t.id)}>{t.label}</button>
  {/each}
</div>

<style>
  .tabs { display: flex; gap: 4px; background: var(--panel); border-radius: 12px; padding: 4px; margin-bottom: 16px; border: 1px solid var(--border); }
  .tab { flex: 1; padding: 8px 2px; border-radius: 8px; border: none; background: transparent; color: var(--muted); font-size: 0.72rem; font-weight: 500; cursor: pointer; transition: all 0.15s; font-family: inherit; }
  .tab.active { background: var(--panel2); color: var(--text-strong); }
</style>
```

`frontend/src/components/VerdictBanner.svelte`:
```svelte
<script>
  let { verdict, score } = $props();
</script>

<div class="verdict-banner {verdict.cls}">
  <div class="verdict-emoji">{verdict.emoji}</div>
  <div class="verdict-label">{verdict.label}</div>
  <div class="verdict-score">{score}% inversion likelihood</div>
</div>

<style>
  .verdict-banner { border-radius: 12px; padding: 20px; margin-bottom: 12px; text-align: center; }
  .go    { background: #0d4429; border: 1px solid #238636; }
  .try   { background: #3d2400; border: 1px solid #9e6a03; }
  .maybe { background: #2d1b00; border: 1px solid #7d4e00; }
  .no    { background: #3d0d12; border: 1px solid #8b2020; }
  .verdict-emoji { font-size: 2.2rem; margin-bottom: 6px; }
  .verdict-label { font-size: 1.3rem; font-weight: 700; }
  .verdict-score { font-size: 0.88rem; color: var(--muted); margin-top: 4px; }
</style>
```

`frontend/src/components/ElevationBanner.svelte`:
```svelte
<script>
  let { elevation } = $props();
</script>

<div class="elevation-banner {elevation.cls}">
  <div class="elev-icon">{elevation.icon}</div>
  <div class="elev-body">
    <div class="elev-title">{elevation.title}</div>
    <div class="elev-detail">{elevation.detail}</div>
  </div>
</div>

<style>
  .elevation-banner { border-radius: 10px; padding: 14px 16px; margin-bottom: 12px; display: flex; align-items: flex-start; gap: 12px; }
  .above { background: #0d2d0d; border: 1px solid #238636; }
  .edge  { background: #2d2200; border: 1px solid #9e6a03; }
  .below { background: #1a1a2e; border: 1px solid #4a4a8a; }
  .clear { background: var(--panel); border: 1px solid var(--border); }
  .elev-icon { font-size: 1.6rem; flex-shrink: 0; }
  .elev-body { flex: 1; }
  .elev-title { font-size: 0.9rem; font-weight: 700; margin-bottom: 4px; }
  .elev-detail { font-size: 0.8rem; color: var(--muted); line-height: 1.5; }
</style>
```

`frontend/src/components/ElevationBar.svelte`:
```svelte
<script>
  import { barModel } from '../lib/barScale.js';

  let { vp, lclFt } = $props();
  const m = $derived(barModel(vp, lclFt));
  const ft = (n) => n.toLocaleString('en-US');
</script>

<div class="card">
  <h3>Fog Base (LCL) vs Your Elevation</h3>
  <div class="axis"><span>0 ft</span><span>{ft(m.maxFt)} ft</span></div>
  <div class="elev-bar-wrap">
    <div class="elev-bar-track">
      <div class="band" style="left:{m.bandL}%; width:{m.bandW}%"></div>
    </div>
    <div class="elev-marker-label sweet" style="left:{m.bandCenter}%">✓ sweet spot</div>
    <div class="elev-marker loc" style="left:{m.locPct}%">
      <div class="elev-marker-label" style="top:-18px; left:-10px;">{vp.name}</div>
      <div class="elev-marker-label" style="bottom:-18px; left:-10px;">{ft(vp.elev_ft)} ft</div>
    </div>
    {#if m.lclPct !== null}
      <div class="elev-marker ceil" style="left:{m.lclPct}%">
        <div class="elev-marker-label fog" style="top:-18px; left:6px;">🌫️ fog base</div>
        <div class="elev-marker-label fog" style="bottom:-18px; left:6px;">{ft(lclFt)} ft</div>
      </div>
    {/if}
  </div>
  {#if m.lclPct === null}
    <p class="none">🔭 No marine layer this hour — no fog base to place on the bar yet.</p>
  {/if}
  <p class="legend">
    The <span class="g">green band</span> is where the fog base needs to sit for a good {vp.name} shot
    ({ft(vp.green_ft[0])}–{ft(vp.green_ft[1])} ft). When there's a marine layer, the
    <span class="f">🌫️ fog base</span> marker appears — if it lands in the green, you're above the layer.
    LCL is derived from temperature and dewpoint — a guide, not a precise ceiling. Verify with the live cameras and Windy.
  </p>
</div>

<style>
  .axis { display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--muted); margin-bottom: 4px; }
  .elev-bar-wrap { margin: 12px 0 4px; position: relative; height: 48px; }
  .elev-bar-track { position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%); height: 6px; background: var(--panel2); border-radius: 3px; }
  .band { position: absolute; top: 0; bottom: 0; background: rgba(35, 134, 54, 0.35); border-radius: 3px; }
  .elev-marker { position: absolute; top: 50%; transform: translate(-50%, -50%); width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--bg); }
  .elev-marker.loc { background: var(--text-strong); }
  .elev-marker.ceil { background: var(--fog); }
  .elev-marker-label { position: absolute; font-size: 0.68rem; white-space: nowrap; color: var(--muted); }
  .elev-marker-label.sweet { top: -16px; transform: translateX(-50%); color: var(--green-text); font-weight: 600; }
  .elev-marker-label.fog { color: var(--fog); }
  .none { text-align: center; font-size: 0.79rem; color: var(--muted); margin-top: 12px; }
  .legend { font-size: 0.75rem; color: var(--muted); margin-top: 8px; }
  .g { color: var(--green-text); }
  .f { color: var(--fog); }
</style>
```

`frontend/src/components/WindowView.svelte` (Task 9 adds the remaining cards here):
```svelte
<script>
  import VerdictBanner from './VerdictBanner.svelte';
  import ElevationBanner from './ElevationBanner.svelte';
  import ElevationBar from './ElevationBar.svelte';

  let { vp, win, result } = $props();
</script>

{#if !result}
  <div class="card"><p class="explanation">No data for this window.</p></div>
{:else}
  <VerdictBanner verdict={result.verdict} score={result.score} />
  <ElevationBanner elevation={result.elevation} />
  <ElevationBar {vp} lclFt={result.lcl_ft} />
{/if}
```

- [ ] **Step 2: Write App.svelte**

`frontend/src/App.svelte`:
```svelte
<script>
  import { onMount } from 'svelte';
  import { fetchSnapshot } from './lib/api.js';
  import Header from './components/Header.svelte';
  import LocationPicker from './components/LocationPicker.svelte';
  import Tabs from './components/Tabs.svelte';
  import WindowView from './components/WindowView.svelte';

  const STORAGE_KEY = 'goodfog.viewpoint';
  const DEFAULT_ID = 'east-peak';
  const REFRESH_MS = 5 * 60 * 1000;

  function loadSelected() {
    try { return globalThis.localStorage?.getItem(STORAGE_KEY) || DEFAULT_ID; } catch { return DEFAULT_ID; }
  }

  let snapshot = $state(null);
  let status = $state('loading'); // loading | ok | warming_up | error
  let error = $state(null);
  let selectedId = $state(loadSelected());
  let tab = $state('tonight'); // tonight | tomorrow_am | tomorrow_pm | plan

  const viewpoints = $derived(snapshot?.viewpoints ?? []);
  const vp = $derived(viewpoints.find((v) => v.id === selectedId) ?? viewpoints[0] ?? null);
  const tabs = $derived([...(snapshot?.windows ?? []).map((w) => ({ id: w.id, label: w.tab })), { id: 'plan', label: '🔭 Plan' }]);
  const window_ = $derived(snapshot?.windows.find((w) => w.id === tab) ?? null);

  function select(id) {
    selectedId = id;
    try { globalThis.localStorage?.setItem(STORAGE_KEY, id); } catch {}
  }

  async function load() {
    const r = await fetchSnapshot();
    if (r.status === 'ok') {
      snapshot = r.data;
      status = 'ok';
      error = null;
    } else if (!snapshot) {
      status = r.status;
      error = r.error ?? null;
    }
  }

  onMount(() => {
    load();
    const timer = setInterval(() => { if (document.visibilityState === 'visible') load(); }, REFRESH_MS);
    const onVisible = () => { if (document.visibilityState === 'visible') load(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', onVisible); };
  });
</script>

<div class="container">
  <Header />

  {#if status === 'loading'}
    <p class="spinner">Fetching weather data…</p>
  {:else if status === 'warming_up'}
    <p class="spinner">Warming up — first forecast arriving shortly…</p>
  {:else if status === 'error'}
    <div class="error-box">Error fetching weather: {error}. Check your connection and try again.</div>
  {/if}

  {#if snapshot && vp}
    <LocationPicker {viewpoints} {selectedId} onselect={select} />
    <Tabs {tabs} active={tab} onselect={(id) => (tab = id)} />

    {#if tab === 'plan'}
      <div class="card"><p class="explanation">Plan view coming in the next task.</p></div>
    {:else if window_}
      <WindowView {vp} win={window_} result={vp.results[window_.id]} />
    {/if}
  {/if}
</div>

<style>
  .spinner { text-align: center; padding: 24px; color: var(--muted); }
</style>
```

- [ ] **Step 3: Run the app against the backend and compare visually**

```bash
cd /Users/mike/claudeprojects/goodfog/backend && (uv run uvicorn goodfog.app:app --port 8000 & echo $! > /tmp/gf.pid) && cd ../frontend && (npm run dev -- --port 5173 & echo $! > /tmp/gfv.pid) && sleep 6 && curl -s localhost:5173 | head -5
```
Open http://localhost:5173 and the original `index.html` (open the file directly, click a viewpoint, click Check Conditions). For the same viewpoint and tab, the verdict banner, elevation banner, and bar must show the same numbers. Then `kill $(cat /tmp/gf.pid) $(cat /tmp/gfv.pid)`.

- [ ] **Step 4: Build and test**

Run: `cd frontend && npm test && npm run build`
Expected: pass, build succeeds with no Svelte warnings about unused props.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): app shell, viewpoint picker, tabs, verdict and elevation cards"
```

---

### Task 9: Remaining cards, plan view, verify links, footer

**Files:**
- Modify: `frontend/src/components/WindowView.svelte`, `frontend/src/App.svelte`
- Create: `frontend/src/components/TimingCard.svelte`, `ConditionsCard.svelte`, `ShotNotesCard.svelte`, `WhyCard.svelte`, `PlanView.svelte`, `VerifyLinks.svelte`, `Footer.svelte`

**Interfaces:**
- Consumes: `fmtTime`, `scoreColor`, `bestWindow`, `planSummary`, `formatVersion`; snapshot shape.

- [ ] **Step 1: Write the cards**

`frontend/src/components/TimingCard.svelte`:
```svelte
<script>
  import { fmtTime } from '../lib/time.js';

  let { vp, win } = $props();
  const isDawn = $derived(win.sun_label === 'Sunrise');
</script>

<div class="card">
  <h3>{win.title} Timing</h3>
  <div class="timing-row"><span class="timing-label">{win.sun_label}</span><span class="timing-value">{fmtTime(win.sun_event)}</span></div>
  <div class="timing-row"><span class="timing-label">Arrive by</span><span class="timing-value">{fmtTime(win.arrive_by)}</span></div>
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
</style>
```

`frontend/src/components/ConditionsCard.svelte`:
```svelte
<script>
  let { title, result } = $props();
  const ft = (n) => n.toLocaleString('en-US');
</script>

<div class="card">
  <h3>{title}</h3>
  <div class="wx-grid grid">
    <div><div class="wx-label">Low cloud</div><div class="wx-value">{result.wx.low_cloud}%</div></div>
    <div><div class="wx-label">Wind</div><div class="wx-value">{result.wx.wind_mph} mph</div></div>
    <div><div class="wx-label">Fog base (LCL)</div><div class="wx-value">{result.lcl_ft != null ? `${ft(result.lcl_ft)} ft` : 'None'}</div></div>
    <div><div class="wx-label">Rain</div><div class="wx-value">{result.wx.rain_pct}%</div></div>
  </div>
  <div class="factors">
    {#each result.factors as f}
      <span class="factor {f.rating}">{f.label}</span>
    {/each}
  </div>
</div>

<style>
  .grid { margin-bottom: 12px; }
</style>
```

`frontend/src/components/ShotNotesCard.svelte`:
```svelte
<script>
  let { vp } = $props();
</script>

<div class="card">
  <h3>Shot Notes</h3>
  <div class="timing-row"><span class="timing-label">Composition</span></div>
  <p class="explanation gap">{vp.composition}</p>
  <div class="timing-row"><span class="timing-label">Access</span></div>
  <p class="explanation">{vp.access}</p>
</div>

<style>
  .gap { margin: 2px 0 12px; }
</style>
```

`frontend/src/components/WhyCard.svelte`:
```svelte
<script>
  let { explanation } = $props();
</script>

<div class="card">
  <h3>Why</h3>
  <p class="explanation">{explanation}</p>
</div>
```

Update `frontend/src/components/WindowView.svelte` to:
```svelte
<script>
  import VerdictBanner from './VerdictBanner.svelte';
  import ElevationBanner from './ElevationBanner.svelte';
  import ElevationBar from './ElevationBar.svelte';
  import TimingCard from './TimingCard.svelte';
  import ConditionsCard from './ConditionsCard.svelte';
  import ShotNotesCard from './ShotNotesCard.svelte';
  import WhyCard from './WhyCard.svelte';

  let { vp, win, result } = $props();
</script>

{#if !result}
  <div class="card"><p class="explanation">No data for this window.</p></div>
{:else}
  <VerdictBanner verdict={result.verdict} score={result.score} />
  <ElevationBanner elevation={result.elevation} />
  <ElevationBar {vp} lclFt={result.lcl_ft} />
  <TimingCard {vp} {win} />
  <ConditionsCard title={`Conditions at ${win.sun_label}`} {result} />
  <ShotNotesCard {vp} />
  <WhyCard explanation={result.explanation} />
{/if}
```

`frontend/src/components/PlanView.svelte`:
```svelte
<script>
  import { fmtTime } from '../lib/time.js';
  import { scoreColor } from '../lib/colors.js';
  import { bestWindow, planSummary } from '../lib/plan.js';
  import ConditionsCard from './ConditionsCard.svelte';

  let { vp, windows } = $props();
  const best = $derived(bestWindow(windows, vp.results));
</script>

<div class="card">
  <h3>Best Window for {vp.name}</h3>
  <div class="compare-grid">
    {#each windows as w (w.id)}
      {@const r = vp.results[w.id]}
      <div class="compare-col" class:best={w.id === best.id}>
        <h4>{w.tab}</h4>
        <div class="compare-score" style="color:{scoreColor(r?.score)}">{r ? `${r.score}%` : '—'}</div>
        <div class="compare-verdict">{r ? `${r.verdict.emoji} ${r.verdict.label}` : ''}</div>
        <div class="when">{fmtTime(w.sun_event)}</div>
      </div>
    {/each}
  </div>
  <p class="explanation summary">{planSummary(best, vp.results[best.id], vp)}</p>
</div>

{#each windows as w (w.id)}
  {#if vp.results[w.id]}
    <ConditionsCard title={`${w.tab} — ${fmtTime(w.sun_event)}`} result={vp.results[w.id]} />
  {/if}
{/each}

<style>
  .compare-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .compare-col { background: var(--bg); border-radius: 8px; padding: 12px; border: 1px solid transparent; }
  .compare-col.best { border-color: #238636; }
  .compare-col h4 { font-size: 0.78rem; color: var(--muted); margin-bottom: 8px; }
  .compare-score { font-size: 1.7rem; font-weight: 700; margin-bottom: 4px; }
  .compare-verdict { font-size: 0.75rem; }
  .when { font-size: 0.7rem; color: var(--muted); margin-top: 4px; }
  .summary { margin-top: 12px; }
</style>
```

`frontend/src/components/VerifyLinks.svelte`:
```svelte
<script>
  const verify = [
    { icon: '☁️', name: 'Windy — Clouds', desc: 'Cloud layer height over Mt. Tam', href: 'https://www.windy.com/?clouds,37.923,-122.597,11' },
    { icon: '🌫️', name: 'Windy — Fog (West Tam)', desc: 'Watch fog rolling in from the coast', href: 'https://www.windy.com/?fog,37.923,-122.597,11' },
    { icon: '💨', name: 'Windy — Wind', desc: 'Strong wind disperses the layer', href: 'https://www.windy.com/?wind,37.923,-122.597,11' },
    { icon: '🛰️', name: 'fog.today', desc: 'NOAA GOES-16 satellite fog tracker', href: 'https://fog.today' },
    { icon: '🇳🇴', name: 'yr.no — Mt. Tam', desc: 'Hourly Norwegian Met forecast — great fog detail', href: 'https://www.yr.no/en/forecast/daily-table/2-5381438/United%20States/California/Marin%20County/Mt.%20Tamalpais%20State%20Park' },
  ];
  const cams = [
    { name: 'West Peak — ALERTCalifornia', desc: 'Above clouds = white sea below. In clouds = grey/white everywhere.', href: 'https://cameras.alertcalifornia.org/?pos=37.9691_-122.5971_11&id=Axis-TamWest' },
    { name: 'East Peak — ALERTCalifornia', desc: 'Clear horizon above fog = inversion confirmed.', href: 'https://cameras.alertcalifornia.org/?pos=37.9691_-122.5971_11&id=Axis-TamEast' },
    { name: 'Muir Beach Overlook — ALERTCalifornia', desc: 'Fog rolling in from the Pacific — shows layer thickness.', href: 'https://cameras.alertcalifornia.org/?pos=37.9691_-122.5971_11&id=Axis-MuirBeach' },
  ];
</script>

{#snippet link(icon, name, desc, href)}
  <a class="resource-link" {href} target="_blank" rel="noopener">
    <span class="resource-icon">{icon}</span>
    <div class="resource-info">
      <div class="resource-name">{name}</div>
      <div class="resource-desc">{desc}</div>
    </div>
  </a>
{/snippet}

<div class="card top">
  <h3>Verify the Forecast</h3>
  <div class="resource-grid">
    {#each verify as r (r.href)}{@render link(r.icon, r.name, r.desc, r.href)}{/each}
  </div>
</div>

<div class="card">
  <h3>Live Cameras</h3>
  <div class="resource-grid">
    {#each cams as r (r.href)}{@render link('📷', r.name, r.desc, r.href)}{/each}
  </div>
  <p class="cam-hint">
    <strong>Reading the cams:</strong> If the summit cams show a flat white layer below with blue sky above = you'd be above the inversion.
    If it's all grey = you're in it. Muir Beach shows how thick and active the marine layer is coming off the ocean.
  </p>
</div>

<style>
  .top { margin-top: 8px; }
  .resource-grid { display: flex; flex-direction: column; gap: 8px; }
  .resource-link { display: flex; align-items: center; gap: 10px; background: var(--panel2); border-radius: 8px; padding: 10px 12px; text-decoration: none; color: var(--text); font-size: 0.86rem; transition: background 0.15s; }
  .resource-link:hover { background: #2d333b; }
  .resource-icon { font-size: 1.1rem; flex-shrink: 0; }
  .resource-info { flex: 1; }
  .resource-name { font-weight: 600; }
  .resource-desc { font-size: 0.76rem; color: var(--muted); margin-top: 1px; }
  .cam-hint { font-size: 0.79rem; color: var(--muted); margin-top: 10px; line-height: 1.5; }
</style>
```

`frontend/src/components/Footer.svelte`:
```svelte
<script>
  import { formatVersion } from '../lib/version.js';

  let { generatedAt = null } = $props();
  const build = formatVersion(__APP_VERSION__, import.meta.env.VITE_COMMIT);
  const updated = $derived(generatedAt ? new Date(generatedAt).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : null);
</script>

<footer>
  Forecast by <a href="https://open-meteo.com/">Open-Meteo</a> (CC BY 4.0). Fog base is an LCL estimate from
  temperature and dewpoint — a heuristic guide, not a measurement. Always confirm on the live cameras.
  <span class="build">{build}{updated ? ` · forecast ${updated}` : ''}</span>
</footer>

<style>
  footer { margin: 2rem 0 1rem; padding: 0 1rem; font-size: 0.75rem; color: var(--muted); line-height: 1.5; }
  a { color: inherit; }
  .build { display: block; margin-top: 0.5rem; font-size: 0.7rem; opacity: 0.8; font-variant-numeric: tabular-nums; }
</style>
```

- [ ] **Step 2: Wire them into App.svelte**

In `frontend/src/App.svelte`, add imports:
```js
  import PlanView from './components/PlanView.svelte';
  import VerifyLinks from './components/VerifyLinks.svelte';
  import Footer from './components/Footer.svelte';
```
Replace the plan placeholder block with:
```svelte
    {#if tab === 'plan'}
      <PlanView {vp} windows={snapshot.windows} />
    {:else if window_}
      <WindowView {vp} win={window_} result={vp.results[window_.id]} />
    {/if}
```
And after the `{#if snapshot && vp} ... {/if}` block, still inside `.container`, add:
```svelte
  <VerifyLinks />
  <Footer generatedAt={snapshot?.generated_at} />
```

- [ ] **Step 3: Run, compare with the original, build**

Start backend and `npm run dev` as in Task 8 Step 3. Check for the default viewpoint on each of the 4 tabs that every card from the original appears with the same numbers and text (Timing incl. the ⚠ Gate row on Tom. AM for East Peak, Conditions grid + factor chips, Shot Notes, Why, Plan comparison with green outline on the best column, Verify and Cameras). Stop the servers.

Run: `cd frontend && npm test && npm run build`
Expected: pass, no warnings.

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat(frontend): timing, conditions, shot notes, why, plan view, verify links, footer"
```

---

### Task 10: Compose, nginx, docs, remove legacy index.html, PR

**Files:**
- Create: `docker-compose.yml`, `docker-compose.override.yml`, `frontend/Dockerfile`, `frontend/nginx.conf`, `CLAUDE.md`, `docs/GETTING-STARTED.md`
- Modify: `README.md`
- Delete: `index.html`

- [ ] **Step 1: Write compose, nginx, frontend Dockerfile**

`docker-compose.yml`:
```yaml
services:
  api:
    build:
      context: .
      dockerfile: backend/Dockerfile
      # Coolify supplies SOURCE_COMMIT at build time (app setting "Source commit availability" =
      # build time). Baked into the image, not passed as runtime env — see backend/Dockerfile.
      args:
        SOURCE_COMMIT: ${SOURCE_COMMIT:-dev}
    environment:
      POLL_MINUTES: ${POLL_MINUTES:-15}
      OPEN_METEO_MODELS: ${OPEN_METEO_MODELS:-best_match}
    restart: unless-stopped

  web:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      args:
        SOURCE_COMMIT: ${SOURCE_COMMIT:-dev}
    depends_on:
      - api
    # No host port here: Coolify's proxy routes to port 80 by domain.
    # Local runs get 8080:80 from docker-compose.override.yml automatically.
    expose:
      - "80"
    restart: unless-stopped
```

`docker-compose.override.yml`:
```yaml
# Local development only. `docker compose up` merges this automatically;
# Coolify reads docker-compose.yml alone, so no host port is published there.
services:
  web:
    ports:
      - "8080:80"
```

`frontend/Dockerfile`:
```dockerfile
# Build context is the repo root (see docker-compose.yml).
FROM node:22-alpine AS build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend .
# Coolify passes SOURCE_COMMIT as a build arg (see docker-compose.yml); the footer shows the short sha.
ARG SOURCE_COMMIT=dev
ENV VITE_COMMIT=${SOURCE_COMMIT}
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/frontend/dist /usr/share/nginx/html
EXPOSE 80
```

`frontend/nginx.conf`:
```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_types application/json application/javascript text/css image/svg+xml application/manifest+json;

    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 20s;
        add_header Cache-Control "no-cache";
    }

    location ~* \.(js|css|png|svg|woff2?)$ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }

    location = /sw.js { add_header Cache-Control "no-cache"; }
    location = /manifest.webmanifest { add_header Cache-Control "no-cache"; }

    location / {
        add_header Cache-Control "no-cache";
        try_files $uri /index.html;
    }
}
```

- [ ] **Step 2: Build and run the stack locally**

```bash
cd /Users/mike/claudeprojects/goodfog && docker compose build && docker compose up -d && sleep 15 && curl -s localhost:8080/api/health && echo && curl -s -o /dev/null -w "%{http_code}\n" localhost:8080/ && docker compose down
```
Expected: health JSON with `"status":"ok"`, then `200`. If Docker is not running, start Docker Desktop and retry once; if still unavailable, note it in the PR and continue.

- [ ] **Step 3: Write CLAUDE.md, README.md, GETTING-STARTED.md**

`CLAUDE.md`:
```markdown
# Good Fog — project rules for Claude Code

Marin marine-layer inversion checker for photographers. Design spec: `docs/superpowers/specs/2026-09-02-goodfog-design.md`.
New contributor? Read `docs/GETTING-STARTED.md`.

## Layout
- `backend/` — Python 3.12 + FastAPI. `viewpoints.py` (data), `fog.py` (pure math), `windows.py`, `providers/open_meteo.py`, `snapshot.py`, `poller.py`, `app.py`.
- `frontend/` — Svelte 5 + Vite PWA. Pure helpers in `src/lib/` (tested), components in `src/components/`.

## Commands
- Backend tests: `cd backend && uv run pytest`
- Frontend tests: `cd frontend && npm test` · build: `npm run build`
- Run locally: backend `cd backend && uv run uvicorn goodfog.app:app --port 8000`; frontend `cd frontend && npm run dev` (proxies `/api` to 8000)
- Full stack: `docker compose up --build` → http://localhost:8080

## Rules
- Work on a branch; open a PR. Never push to `main` — merging `main` auto-deploys to https://goodfog.babins.net.
- Write or update tests with every change (TDD: failing test first). Fog math in `fog.py` stays pure: no I/O, no clock; `now` is passed in.
- The scoring rubric, thresholds, and copy were ported 1:1 from the original single-file app; `tests/test_score.py` holds a parity table computed from that JS. Changing behavior means changing the table deliberately, in the same PR.
- The frontend never computes scores; it renders `/api/snapshot`. Only small pure helpers (bar geometry, time formatting, plan best-window) live in `src/lib/`.
- npm: pin exact versions, no `^`/`~`, commit `package-lock.json`, `npm ci --ignore-scripts`. Python: `uv`, exact pins in `pyproject.toml`.
- No secrets; only `POLL_MINUTES` and `OPEN_METEO_MODELS` env vars. Never commit `.env`.
- Feet, °F, mph everywhere; feet are shown with thousands separators.
- Version lives in both `frontend/package.json` (+ lockfile) and `backend/pyproject.toml`; bump both together in PRs that change what users see (a test enforces they match). The footer and `/api/health` show it alongside the deployed commit sha, which requires the Coolify app setting "Source commit availability" = build time; otherwise prod shows `dev`. The sha reaches both images as the `SOURCE_COMMIT` build arg; the backend bakes it as `BUILD_COMMIT` because Coolify injects an empty runtime `SOURCE_COMMIT` into the container.
```

`README.md` (replace entirely):
```markdown
# Good Fog

**Good Fog** tells you whether a Bay Area fog *inversion* is worth photographing from a
given Marin Headlands or Mt. Tamalpais viewpoint, and whether you'll be standing **above**
the marine layer or lost **inside** it — for tonight's sunset, tomorrow's sunrise, and
tomorrow's sunset.

Live: https://goodfog.babins.net

## How it works

1. **Forecast** — the backend polls hourly cloud cover, wind, temperature, dewpoint, and
   sunrise/sunset for all eight viewpoints from the free [Open-Meteo](https://open-meteo.com)
   API in one request. No API key.
2. **Fog base (LCL)** — computes the lifted condensation level from temperature and dewpoint
   using the Espy/Bolton approximation (~125 m of lift per °C of temp–dewpoint spread).
3. **Per-viewpoint thresholds** — every viewpoint has a calibrated "sweet spot" range for the
   fog base: **above the layer**, **right at the edge**, or **inside the fog / socked in**.
4. **Likelihood score** — combines low-cloud coverage, wind, clear sky above, and rain into
   an inversion-likelihood %. The fog-base position gates the score.

The numbers are a **heuristic guide, not a measurement** — always confirm against the live
cameras and Windy before setting the 4:30am alarm.

## Viewpoints

| Spot | Elevation | Notes |
|------|-----------|-------|
| Point Bonita Lighthouse | 100 ft | Coastal; only works with a very low fog base |
| Twin Peaks (from Arguello & Jackson) | 370 ft vantage | Shoot *toward* the 922 ft peaks emerging above the fog |
| Conzelman Pullouts | ~600 ft | Flexible stops when the fog base is low |
| Battery Spencer | 790 ft | Golden Gate Bridge framed in fog |
| Hawk Hill | 923 ft | Classic Marin valley inversion |
| Trojan Point | ~1,750 ft | Mid-mountain sea of clouds (summit gate opens 7am) |
| West Peak | 2,560 ft | Faces the coast (gate opens 7am) |
| East Peak | 2,571 ft | Highest vantage — above nearly all layers (gate opens 7am) |

## Stack

- `backend/` — Python 3.12 + FastAPI. Polls Open-Meteo, does all the fog math, serves `/api/snapshot`.
- `frontend/` — Svelte 5 + Vite PWA served by nginx. Renders the snapshot; no scoring in the browser.
- Deployed with Docker Compose on Coolify; merging `main` deploys.

## Running it

```sh
# backend
cd backend && uv sync && uv run uvicorn goodfog.app:app --port 8000
# frontend (separate terminal)
cd frontend && npm ci --ignore-scripts && npm run dev
# or the whole stack
docker compose up --build   # http://localhost:8080
```

Tests: `cd backend && uv run pytest` · `cd frontend && npm test`.

## Verify before you go

The app links out to Windy (cloud/fog/wind layers), [fog.today](https://fog.today)
(NOAA GOES satellite), yr.no, and ALERTCalifornia live cameras on Mt. Tam and at
Muir Beach so you can ground-truth the forecast with your own eyes.
```

`docs/GETTING-STARTED.md`: copy `/Users/mike/claudeprojects/mrstoasty/docs/GETTING-STARTED.md` and replace every `mrstoasty` with `goodfog` and `Mrs. Toasty` with `Good Fog`:
```bash
sed -e 's/mrstoasty/goodfog/g' -e 's/Mrs\. Toasty/Good Fog/g' /Users/mike/claudeprojects/mrstoasty/docs/GETTING-STARTED.md > /Users/mike/claudeprojects/goodfog/docs/GETTING-STARTED.md
```
Then read it once and remove any sentence that references PurpleAir, NWS, or an API key.

- [ ] **Step 4: Remove the legacy single-file app**

```bash
cd /Users/mike/claudeprojects/goodfog && grep -rn "index.html" --include="*.md" --include="*.yml" --include="*.py" --include="*.js" --include="*.svelte" . | grep -v node_modules | grep -v "frontend/index.html" | grep -v "dist/" 
```
Only spec/plan/README prose should match (fine). Then:
```bash
git rm index.html
```

- [ ] **Step 5: Full verification**

```bash
cd /Users/mike/claudeprojects/goodfog/backend && uv run pytest -q && cd ../frontend && npm test && npm run build
```
Expected: all green.

- [ ] **Step 6: Commit and open the PR**

```bash
cd /Users/mike/claudeprojects/goodfog && git add -A && git commit -m "feat: Docker Compose deploy, docs, remove legacy single-file app" && git push -u origin port-to-stack && gh pr create --title "Port to FastAPI + Svelte stack (Good Fog 0.1.0)" --body "$(cat <<'EOF'
## Summary
- FastAPI backend polls Open-Meteo (one multi-point call) and serves a precomputed snapshot; all fog math is pure Python with a parity table generated from the original JS
- Svelte 5 PWA renders the snapshot: same viewpoints, tabs, cards, and verify links as the single-file app; no Check button needed
- Docker Compose + nginx, version/commit in footer and /api/health, ready for Coolify at goodfog.babins.net
- Removes the legacy `index.html`

Spec: docs/superpowers/specs/2026-09-02-goodfog-design.md
Plan: docs/superpowers/plans/2026-09-02-goodfog-port.md

## Test plan
- [ ] `cd backend && uv run pytest`
- [ ] `cd frontend && npm test && npm run build`
- [ ] `docker compose up --build` → http://localhost:8080 shows East Peak / Tonight with all cards

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01Uucw9EqwctfzAmKYxTpBpK
EOF
)"
```

After the PR is open, Coolify setup is a manual step for the user (create app from `Mikebabin/goodfog`, compose build pack, domain `goodfog.babins.net`, "Source commit availability" = build time). Note it in the final report.
