# Three-Day Outlook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Good Fog from three viewing windows to seven (tonight, then sunrise + sunset for the next three days) with day-tab navigation, a 4×2 Plan grid, and a lower-confidence label on day 2/3 windows.

**Architecture:** The backend's `build_windows` emits seven `Window`s with three new fields (`day`, `day_label`, `outlook`); Open-Meteo is fetched with `forecast_days=4`. The frontend groups windows by day for the tab strip, adds a Sunrise/Sunset toggle, shows an outlook line in the detail view, and reworks Plan into a days × halves grid whose cells select a window. Scores and the parity table are untouched.

**Tech Stack:** Python 3.12 + FastAPI + pytest (backend, run with `uv`); Svelte 5 + Vite + vitest + `@testing-library/svelte` (frontend).

**Spec:** `docs/superpowers/specs/2026-09-02-three-day-outlook-design.md` (amends `docs/superpowers/specs/2026-09-02-goodfog-design.md` §4.2, §4.4, §5)

## Global Constraints

- Work only inside the worktree at `/Users/mike/claudeprojects/goodfog/.claude/worktrees/three-day-outlook` on branch `worktree-three-day-outlook`. Never push to `main`.
- TDD: write the failing test first, watch it fail, then implement. Backend tests: `cd backend && uv run pytest -q -W error`. Frontend tests: `cd frontend && npm test`. Both must be green at every commit.
- `backend/tests/test_score.py` (parity table) must not change. `fog.py` stays pure (no I/O, no clock).
- Window ids, in order: `tonight, d1_am, d1_pm, d2_am, d2_pm, d3_am, d3_pm`. Arrive-by offsets: 30 min before sunrise, 45 min before sunset.
- New `Window` fields: `day: int` (0–3), `day_label: str` ("Tonight", "Tomorrow", else `strftime("%a")` e.g. "Fri"), `outlook: bool` (`day >= 2`). `title` = long day + sun label ("Friday Sunset"); `tab` = `day_label` (no emoji).
- `FORECAST_DAYS = 4`.
- Copy: Plan summary says "next three days"; outlook line reads exactly `Outlook · 2+ days out, lower confidence`.
- Feet with thousands separators, °F, mph (unchanged).
- Version bumps to `0.4.0` in `frontend/package.json` (+ lockfile) and `backend/pyproject.toml`.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_014TY4tXhGVEXQdcdsFbgasL
  ```

---

## File map

| File | Change | Responsibility |
|---|---|---|
| `backend/goodfog/windows.py` | modify | Seven windows, new fields, weekday labels |
| `backend/tests/test_windows.py` | modify | Window construction tests |
| `backend/goodfog/providers/open_meteo.py` | modify | `FORECAST_DAYS = 4`; extract `request_params()` |
| `scripts/fetch_fixture.py` | create | Re-download the Open-Meteo fixture with the provider's own params |
| `backend/tests/fixtures/open_meteo.json` | regenerate | 96 hourly rows, 4 daily rows per point |
| `backend/tests/test_open_meteo.py` | modify | Counts and `forecast_days` |
| `backend/tests/test_snapshot.py` | modify | Seven windows, new field set, `d3_pm` resolves |
| `frontend/src/lib/days.js` | create | `groupByDay`, `windowForDay` (pure) |
| `frontend/src/lib/days.test.js` | create | Tests for the above |
| `frontend/src/lib/plan.js` | modify | Copy: title in Best bet, "three days" |
| `frontend/src/lib/plan.test.js` | modify | Copy tests, seven-window fixtures |
| `frontend/src/components/fixtures.js` | modify | Seven windows with new fields |
| `frontend/src/components/HalfToggle.svelte` | create | Sunrise/Sunset segmented control |
| `frontend/src/components/HalfToggle.test.js` | create | |
| `frontend/src/components/Tabs.test.js` | create | Day strip + Plan, active state, click |
| `frontend/src/components/WindowView.svelte` | modify | Outlook line under the verdict banner |
| `frontend/src/components/WindowView.test.js` | create | Outlook line present/absent |
| `frontend/src/App.svelte` | modify | Day tabs, half toggle, plan cell selection |
| `frontend/src/components/PlanView.svelte` | modify | 4×2 grid, cell buttons, one conditions card |
| `frontend/src/components/PlanView.test.js` | modify | Grid tests |
| `frontend/package.json`, `package-lock.json`, `backend/pyproject.toml` | modify | 0.4.0 |
| `README.md`, `CLAUDE.md`, `docs/GETTING-STARTED.md`, base spec | modify | Copy and pointers |

---

### Task 1: Seven windows with day fields (backend)

**Files:**
- Modify: `backend/goodfog/windows.py`
- Test: `backend/tests/test_windows.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `build_windows(sunrise: list[str], sunset: list[str]) -> list[Window]` returning seven windows; `Window` dataclass gains `day: int`, `day_label: str`, `outlook: bool`. Field order in `asdict(w)`: `id, day, day_label, outlook, title, tab, sun_label, sun_event, arrive_by, hour`. Raises `IndexError` if either list has fewer than four entries.

- [ ] **Step 1: Replace `test_build_windows_three_windows` with the seven-window tests**

Replace the whole of `backend/tests/test_windows.py` from `def test_build_windows_three_windows` to the end of the file with:

```python
import pytest

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
```

Move the `import pytest` line to the top of the file with the other import.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest -q tests/test_windows.py`
Expected: 5 failures (`AssertionError` on ids / `IndexError` not raised / `AttributeError: 'Window' object has no attribute 'day'`). The two helper tests still pass.

- [ ] **Step 3: Implement seven windows**

Replace `backend/goodfog/windows.py` from the `@dataclass(frozen=True)` line to the end of the file with:

```python
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
```

Also update the module docstring's first line to: `"""The seven viewing windows: tonight's sunset, then sunrise and sunset for the next three days.`

- [ ] **Step 4: Run the window tests and the full backend suite**

Run: `cd backend && uv run pytest -q -W error`
Expected: `test_windows.py` all pass. `test_snapshot.py` now fails in three places (`["tonight", "tomorrow_am", "tomorrow_pm"]` assertions and the field-set assertions) — that is expected and fixed in Task 2. Nothing else fails.

- [ ] **Step 5: Commit**

```bash
git add backend/goodfog/windows.py backend/tests/test_windows.py
git commit -m "feat(windows): seven windows through day 3 with day, day_label, outlook

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014TY4tXhGVEXQdcdsFbgasL"
```

---

### Task 2: forecast_days=4, fixture refresh script, snapshot tests

**Files:**
- Modify: `backend/goodfog/providers/open_meteo.py`
- Create: `scripts/fetch_fixture.py`
- Regenerate: `backend/tests/fixtures/open_meteo.json`
- Modify: `backend/tests/test_open_meteo.py`, `backend/tests/test_snapshot.py`

**Interfaces:**
- Produces: `request_params(points: list[tuple[float, float]], models: str) -> dict[str, str]` in `open_meteo.py`, used by both `OpenMeteoProvider.fetch` and the script. `FORECAST_DAYS == 4`.

- [ ] **Step 1: Update the provider tests**

In `backend/tests/test_open_meteo.py`:

Change in `test_parse_maps_by_index_and_exposes_daily`:
```python
    assert len(f.hourly_time) == 96
    assert len(f.sunrise) == 4 and len(f.sunset) == 4
```

Change in `test_fetch_builds_multi_point_query`:
```python
    assert q["forecast_days"] == "4"
```

Add after `test_fetch_builds_multi_point_query`:
```python
def test_request_params_is_the_single_source_of_the_query():
    from goodfog.providers.open_meteo import request_params
    q = request_params([(1.5, -2.5), (3.0, 4.0)], models="best_match")
    assert q["latitude"] == "1.5,3.0" and q["longitude"] == "-2.5,4.0"
    assert q["forecast_days"] == "4" and q["timezone"] == "America/Los_Angeles"
    assert q["daily"] == "sunrise,sunset" and "cloudcover_low" in q["hourly"]
```

- [ ] **Step 2: Update the snapshot tests**

In `backend/tests/test_snapshot.py`, add near the top (after `NOW = ...`):

```python
WINDOW_IDS = ["tonight", "d1_am", "d1_pm", "d2_am", "d2_pm", "d3_am", "d3_pm"]
WINDOW_KEYS = {"id", "day", "day_label", "outlook", "title", "tab", "sun_label", "sun_event", "arrive_by", "hour"}
```

Then:
- In `test_top_level_shape`: replace the ids assertion with `assert [w["id"] for w in s["windows"]] == WINDOW_IDS` and the field-set assertion with `assert set(s["windows"][0]) == WINDOW_KEYS`.
- In `test_viewpoint_entry_shape`: replace the field-set assertion with `assert set(v["windows"][0]) == WINDOW_KEYS`.
- In `test_each_viewpoint_gets_windows_from_its_own_daily_block`: replace the body of the loop with:
  ```python
        ws = vp_entry["windows"]
        assert [w["id"] for w in ws] == WINDOW_IDS
        assert ws[0]["sun_event"] == fc.sunset[0]
        assert ws[1]["sun_event"] == fc.sunrise[1]
        assert ws[2]["sun_event"] == fc.sunset[1]
        assert ws[6]["sun_event"] == fc.sunset[3]
        assert set(vp_entry["results"]) == {w["id"] for w in ws}
  ```
- In `test_missing_hour_gives_null_result`: replace the results assertion with `assert s["viewpoints"][0]["results"] == {wid: None for wid in WINDOW_IDS}`.
- Add a new test:
  ```python
  def test_day_three_sunset_has_a_forecast_row():
      # forecast_days=4 exists so that d3_pm lands on a real hourly row; guard the fixture and the provider together.
      s = _snap()
      for v in s["viewpoints"]:
          assert v["results"]["d3_pm"] is not None
          assert v["windows"][6]["outlook"] is True and v["windows"][1]["outlook"] is False
  ```

- [ ] **Step 3: Run to verify failures**

Run: `cd backend && uv run pytest -q tests/test_open_meteo.py tests/test_snapshot.py`
Expected: failures on `96`/`4` counts, `forecast_days == "4"`, missing `request_params`, and `d3_pm is None` (old fixture has 3 days). Shape tests now pass.

- [ ] **Step 4: Bump `FORECAST_DAYS` and extract `request_params`**

In `backend/goodfog/providers/open_meteo.py`:

```python
FORECAST_DAYS = 4  # day-3 sunset needs an hourly row on the fourth calendar day
```

Add a module-level function above `class OpenMeteoProvider`:

```python
def request_params(points: list[tuple[float, float]], models: str) -> dict[str, str]:
    """The exact query the provider sends; scripts/fetch_fixture.py reuses it so the fixture cannot drift."""
    return {
        "latitude": ",".join(str(lat) for lat, _ in points),
        "longitude": ",".join(str(lon) for _, lon in points),
        "hourly": HOURLY_VARS,
        "daily": "sunrise,sunset",
        "timezone": "America/Los_Angeles",
        "forecast_days": str(FORECAST_DAYS),
        "models": models,
    }
```

And in `fetch`, replace the inline `params = {...}` block with `params = request_params(self.points, self.models)`.

- [ ] **Step 5: Write the fixture script**

Create `scripts/fetch_fixture.py`:

```python
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
```

- [ ] **Step 6: Regenerate the fixture**

Run from the worktree root: `uv run --project backend python scripts/fetch_fixture.py`
Expected output: `wrote backend/tests/fixtures/open_meteo.json: 8 points, 4 days, 96 hourly rows`

Sanity check: `git diff --stat backend/tests/fixtures/open_meteo.json` shows one changed file; `head -c 200 backend/tests/fixtures/open_meteo.json` starts with `[{"latitude":37.82`.

- [ ] **Step 7: Run the full backend suite**

Run: `cd backend && uv run pytest -q -W error`
Expected: all pass (was 111 + new tests). `test_score.py` untouched.

- [ ] **Step 8: Commit**

```bash
git add backend/goodfog/providers/open_meteo.py scripts/fetch_fixture.py backend/tests/fixtures/open_meteo.json backend/tests/test_open_meteo.py backend/tests/test_snapshot.py
git commit -m "feat(provider): forecast_days=4 and a fixture refresh script; snapshot carries seven windows

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014TY4tXhGVEXQdcdsFbgasL"
```

---

### Task 3: Frontend pure helpers — `days.js`, plan copy, shared fixtures

**Files:**
- Create: `frontend/src/lib/days.js`, `frontend/src/lib/days.test.js`
- Modify: `frontend/src/lib/plan.js`, `frontend/src/lib/plan.test.js`
- Modify: `frontend/src/components/fixtures.js`

**Interfaces:**
- Produces: `groupByDay(windows) -> [{day, label, am: Window|null, pm: Window|null}]` in day order; `windowForDay(group, current) -> Window` (keep current half if present, else the half the day has, preferring pm). `planSummary(best, result, vp)` now uses `best.title` and says "next three days".
- Produces: `fixtures.js` exports `windows` (seven, new fields) and everything else unchanged.

- [ ] **Step 1: Write `days.test.js`**

Create `frontend/src/lib/days.test.js`:

```js
import { describe, expect, it } from 'vitest';
import { groupByDay, windowForDay } from './days.js';

const w = (id, day, day_label, sun_label) => ({ id, day, day_label, sun_label, outlook: day >= 2 });
const windows = [
  w('tonight', 0, 'Tonight', 'Sunset'),
  w('d1_am', 1, 'Tomorrow', 'Sunrise'), w('d1_pm', 1, 'Tomorrow', 'Sunset'),
  w('d2_am', 2, 'Fri', 'Sunrise'), w('d2_pm', 2, 'Fri', 'Sunset'),
  w('d3_am', 3, 'Sat', 'Sunrise'), w('d3_pm', 3, 'Sat', 'Sunset'),
];

describe('groupByDay', () => {
  it('groups seven windows into four days in order', () => {
    const g = groupByDay(windows);
    expect(g.map((x) => [x.day, x.label])).toEqual([[0, 'Tonight'], [1, 'Tomorrow'], [2, 'Fri'], [3, 'Sat']]);
  });
  it('puts sunrise in am and sunset in pm; tonight has no am', () => {
    const g = groupByDay(windows);
    expect(g[0].am).toBeNull();
    expect(g[0].pm.id).toBe('tonight');
    expect(g[2].am.id).toBe('d2_am');
    expect(g[2].pm.id).toBe('d2_pm');
  });
  it('returns an empty list for no windows', () => {
    expect(groupByDay([])).toEqual([]);
  });
});

describe('windowForDay', () => {
  const g = groupByDay(windows);
  it('keeps the current half when the day has it', () => {
    expect(windowForDay(g[2], windows[1]).id).toBe('d2_am'); // current is a sunrise
    expect(windowForDay(g[2], windows[2]).id).toBe('d2_pm'); // current is a sunset
  });
  it('falls back to the half the day has', () => {
    expect(windowForDay(g[0], windows[1]).id).toBe('tonight'); // wanted sunrise, tonight only has sunset
  });
  it('prefers sunset when there is no current window', () => {
    expect(windowForDay(g[1], null).id).toBe('d1_pm');
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npm test -- src/lib/days.test.js`
Expected: FAIL, `Failed to resolve import "./days.js"`.

- [ ] **Step 3: Implement `days.js`**

Create `frontend/src/lib/days.js`:

```js
/** Group snapshot windows by day for the tab strip: [{day, label, am, pm}] in day order. Pure. */
export function groupByDay(windows) {
  const groups = [];
  for (const w of windows) {
    let g = groups.find((x) => x.day === w.day);
    if (!g) {
      g = { day: w.day, label: w.day_label, am: null, pm: null };
      groups.push(g);
    }
    if (w.sun_label === 'Sunrise') g.am = w;
    else g.pm = w;
  }
  return groups;
}

/** Window to show when a day is picked: keep the current half if that day has it, else the half it has (sunset first). */
export function windowForDay(group, current) {
  const wantAm = current?.sun_label === 'Sunrise';
  return (wantAm ? group.am : group.pm) ?? group.pm ?? group.am;
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd frontend && npm test -- src/lib/days.test.js`
Expected: 6 passed.

- [ ] **Step 5: Update `plan.test.js` for the copy changes**

Replace the `windows` constant at the top of `frontend/src/lib/plan.test.js` with:

```js
const windows = [
  { id: 'tonight', title: 'Tonight Sunset', tab: 'Tonight', sun_event: '2026-09-02T19:32' },
  { id: 'd1_am', title: 'Tomorrow Sunrise', tab: 'Tomorrow', sun_event: '2026-09-03T06:52' },
  { id: 'd1_pm', title: 'Tomorrow Sunset', tab: 'Tomorrow', sun_event: '2026-09-03T19:31' },
];
```

Replace every `tomorrow_am` with `d1_am` and `tomorrow_pm` with `d1_pm` in the `bestWindow` tests. Then in `describe('planSummary')`:

```js
  it('names the best bet by window title when score >= 40', () => {
    const s = planSummary(windows[1], { score: 80, lcl_ft: 615 }, vp);
    expect(s).toBe('Best bet: Tomorrow Sunrise at 6:52 AM — 80% likelihood. Fog base ~615 ft vs Hawk Hill at 923 ft.');
  });
  it('omits the fog-base clause when lcl is null', () => {
    expect(planSummary(windows[0], { score: 45, lcl_ft: null }, vp)).toBe('Best bet: Tonight Sunset at 7:32 PM — 45% likelihood.');
  });
  it('says no great windows below 40 or when null', () => {
    const msg = 'No great windows in the next three days for Hawk Hill. Check a higher viewpoint or wait for the next marine layer event.';
    expect(planSummary(windows[0], { score: 39, lcl_ft: 100 }, vp)).toBe(msg);
    expect(planSummary(windows[0], null, vp)).toBe(msg);
  });
```

- [ ] **Step 6: Run to verify failure**

Run: `cd frontend && npm test -- src/lib/plan.test.js`
Expected: the three `planSummary` tests fail on copy ("Tom. AM" vs "Tomorrow Sunrise"; "two days" vs "three days").

- [ ] **Step 7: Update `plan.js`**

In `frontend/src/lib/plan.js`, change `planSummary` to:

```js
export function planSummary(best, result, vp) {
  if (!result || result.score < 40) {
    return `No great windows in the next three days for ${vp.name}. Check a higher viewpoint or wait for the next marine layer event.`;
  }
  const fog = result.lcl_ft != null
    ? ` Fog base ~${result.lcl_ft.toLocaleString('en-US')} ft vs ${vp.name} at ${vp.elev_ft.toLocaleString('en-US')} ft.`
    : '';
  return `Best bet: ${best.title} at ${fmtTime(best.sun_event)} — ${result.score}% likelihood.${fog}`;
}
```

- [ ] **Step 8: Update the shared component fixtures**

In `frontend/src/components/fixtures.js`, replace the `windows` export with:

```js
const win = (id, day, day_label, long, sun_label, sun_event, arrive_by) => ({
  id, day, day_label, outlook: day >= 2, title: `${long} ${sun_label}`, tab: day_label,
  sun_label, sun_event, arrive_by, hour: `${sun_event.slice(0, 13)}:00`,
});

/** Seven windows as the backend emits them for a Wednesday (2026-09-02). */
export const windows = [
  win('tonight', 0, 'Tonight', 'Tonight', 'Sunset', '2026-09-02T19:32', '2026-09-02T18:47'),
  win('d1_am', 1, 'Tomorrow', 'Tomorrow', 'Sunrise', '2026-09-03T06:48', '2026-09-03T06:18'),
  win('d1_pm', 1, 'Tomorrow', 'Tomorrow', 'Sunset', '2026-09-03T19:30', '2026-09-03T18:45'),
  win('d2_am', 2, 'Fri', 'Friday', 'Sunrise', '2026-09-04T06:49', '2026-09-04T06:19'),
  win('d2_pm', 2, 'Fri', 'Friday', 'Sunset', '2026-09-04T19:29', '2026-09-04T18:44'),
  win('d3_am', 3, 'Sat', 'Saturday', 'Sunrise', '2026-09-05T06:50', '2026-09-05T06:20'),
  win('d3_pm', 3, 'Sat', 'Saturday', 'Sunset', '2026-09-05T19:27', '2026-09-05T18:42'),
];

/** Results keyed by window id; unspecified windows are null. */
export function resultsFor(spec) {
  return Object.fromEntries(windows.map((w) => [w.id, spec[w.id] ?? null]));
}
```

Keep `eastPeak`, `verdicts`, `elevations`, `wx`, and `result()` exactly as they are.

- [ ] **Step 9: Run the whole frontend suite**

Run: `cd frontend && npm test`
Expected: `days`, `plan`, and all `lib` tests pass. `PlanView.test.js` now fails (it still uses `tomorrow_am` keys and the three-column layout) — expected, fixed in Task 5. Everything else passes.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/lib/days.js frontend/src/lib/days.test.js frontend/src/lib/plan.js frontend/src/lib/plan.test.js frontend/src/components/fixtures.js
git commit -m "feat(frontend): day grouping helpers, plan copy for three days, seven-window fixtures

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014TY4tXhGVEXQdcdsFbgasL"
```

---

### Task 4: Day tabs, Sunrise/Sunset toggle, outlook line

**Files:**
- Create: `frontend/src/components/HalfToggle.svelte`, `frontend/src/components/HalfToggle.test.js`, `frontend/src/components/Tabs.test.js`, `frontend/src/components/WindowView.test.js`
- Modify: `frontend/src/components/WindowView.svelte`, `frontend/src/App.svelte`

**Interfaces:**
- Consumes: `groupByDay`, `windowForDay` from Task 3.
- Produces: `HalfToggle` props `{ group, active, onselect }` where `group` is a `groupByDay` entry, `active` a window id, `onselect(id)`. Renders nothing unless the group has both halves. `Tabs` is unchanged (props `{ tabs: [{id, label}], active, onselect }`); App passes day ids of the form `day${n}` plus `plan`. `WindowView` shows `<p class="outlook">` when `win.outlook`.

- [ ] **Step 1: Write the three component tests**

Create `frontend/src/components/Tabs.test.js`:

```js
// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import Tabs from './Tabs.svelte';

const tabs = [
  { id: 'day0', label: 'Tonight' }, { id: 'day1', label: 'Tomorrow' },
  { id: 'day2', label: 'Fri' }, { id: 'day3', label: 'Sat' }, { id: 'plan', label: '🔭 Plan' },
];

describe('Tabs', () => {
  it('renders one button per tab in order and marks the active one', () => {
    const { container } = render(Tabs, { tabs, active: 'day2', onselect: () => {} });
    const buttons = [...container.querySelectorAll('button.tab')];
    expect(buttons.map((b) => b.textContent)).toEqual(['Tonight', 'Tomorrow', 'Fri', 'Sat', '🔭 Plan']);
    expect(buttons.filter((b) => b.classList.contains('active')).map((b) => b.textContent)).toEqual(['Fri']);
  });

  it('reports the clicked tab id', async () => {
    const onselect = vi.fn();
    const { getByText } = render(Tabs, { tabs, active: 'day0', onselect });
    await fireEvent.click(getByText('Sat'));
    expect(onselect).toHaveBeenCalledWith('day3');
  });
});
```

Create `frontend/src/components/HalfToggle.test.js`:

```js
// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import HalfToggle from './HalfToggle.svelte';
import { groupByDay } from '../lib/days.js';
import { windows } from './fixtures.js';

const groups = groupByDay(windows);

describe('HalfToggle', () => {
  it('renders Sunrise and Sunset for a day with both, marking the active half', () => {
    const { container } = render(HalfToggle, { group: groups[1], active: 'd1_pm', onselect: () => {} });
    const buttons = [...container.querySelectorAll('button')];
    expect(buttons.map((b) => b.textContent.trim())).toEqual(['🌄 Sunrise', '🌇 Sunset']);
    expect(buttons.map((b) => b.getAttribute('aria-selected'))).toEqual(['false', 'true']);
  });

  it('reports the chosen window id', async () => {
    const onselect = vi.fn();
    const { getByText } = render(HalfToggle, { group: groups[2], active: 'd2_pm', onselect });
    await fireEvent.click(getByText('🌄 Sunrise'));
    expect(onselect).toHaveBeenCalledWith('d2_am');
  });

  it('renders nothing for Tonight, which has only a sunset', () => {
    const { container } = render(HalfToggle, { group: groups[0], active: 'tonight', onselect: () => {} });
    expect(container.querySelector('button')).toBeNull();
  });

  it('renders nothing when there is no group (Plan tab)', () => {
    const { container } = render(HalfToggle, { group: null, active: 'plan', onselect: () => {} });
    expect(container.querySelector('button')).toBeNull();
  });
});
```

Create `frontend/src/components/WindowView.test.js`:

```js
// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import WindowView from './WindowView.svelte';
import { eastPeak, windows, result } from './fixtures.js';

const OUTLOOK = 'Outlook · 2+ days out, lower confidence';

describe('WindowView', () => {
  it('shows the outlook line for a day-2 window, right after the verdict banner', () => {
    const win = windows.find((w) => w.id === 'd2_pm');
    const { container, getByText } = render(WindowView, { vp: eastPeak, win, result: result({ score: 72 }) });
    expect(getByText(OUTLOOK)).toBeTruthy();
    expect(container.querySelector('.verdict-banner + .outlook')).not.toBeNull();
  });

  it('shows no outlook line for tomorrow', () => {
    const win = windows.find((w) => w.id === 'd1_pm');
    const { queryByText } = render(WindowView, { vp: eastPeak, win, result: result({ score: 72 }) });
    expect(queryByText(OUTLOOK)).toBeNull();
  });

  it('shows the no-data card and no outlook line when the result is null', () => {
    const win = windows.find((w) => w.id === 'd3_am');
    const { getByText, queryByText } = render(WindowView, { vp: eastPeak, win, result: null });
    expect(getByText('No data for this window.')).toBeTruthy();
    expect(queryByText(OUTLOOK)).toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify failures**

Run: `cd frontend && npm test -- src/components/Tabs.test.js src/components/HalfToggle.test.js src/components/WindowView.test.js`
Expected: `Tabs` passes (component unchanged; the test pins its contract). `HalfToggle` fails to resolve the import. `WindowView` fails on the outlook line (two tests).

- [ ] **Step 3: Create `HalfToggle.svelte`**

```svelte
<script>
  let { group, active, onselect } = $props();
  const both = $derived(Boolean(group?.am && group?.pm));
</script>

{#if both}
  <div class="half" role="tablist" aria-label="Sunrise or sunset">
    <button role="tab" class:active={active === group.am.id} aria-selected={active === group.am.id} onclick={() => onselect(group.am.id)}>🌄 Sunrise</button>
    <button role="tab" class:active={active === group.pm.id} aria-selected={active === group.pm.id} onclick={() => onselect(group.pm.id)}>🌇 Sunset</button>
  </div>
{/if}

<style>
  .half { display: flex; justify-content: center; gap: 4px; margin: -8px 0 12px; }
  button { padding: 5px 14px; border-radius: 999px; border: 1px solid var(--border); background: transparent; color: var(--muted); font-size: 0.74rem; font-weight: 500; cursor: pointer; font-family: inherit; transition: all 0.15s; }
  button.active { background: var(--panel2); color: var(--text-strong); border-color: var(--panel2); }
</style>
```

- [ ] **Step 4: Add the outlook line to `WindowView.svelte`**

Directly after `<VerdictBanner verdict={result.verdict} score={result.score} />` add:

```svelte
  {#if win.outlook}
    <p class="outlook">Outlook · 2+ days out, lower confidence</p>
  {/if}
```

And add a `<style>` block at the end of the file:

```svelte
<style>
  .outlook { text-align: center; font-size: 0.75rem; color: var(--muted); margin: -6px 0 12px; }
</style>
```

- [ ] **Step 5: Run the three tests**

Run: `cd frontend && npm test -- src/components/Tabs.test.js src/components/HalfToggle.test.js src/components/WindowView.test.js`
Expected: all 9 pass.

- [ ] **Step 6: Wire `App.svelte`**

In `frontend/src/App.svelte`:

Add imports:
```js
  import HalfToggle from './components/HalfToggle.svelte';
  import { groupByDay, windowForDay } from './lib/days.js';
```

Change the `tab` comment: `let tab = $state('tonight'); // a window id (tonight, d1_am, …) | plan`

Replace the `tabs` derived line with:
```js
  const groups = $derived(groupByDay(snapshot?.windows ?? []));
  const tabs = $derived([...groups.map((g) => ({ id: `day${g.day}`, label: g.label })), { id: 'plan', label: '🔭 Plan' }]);
  const window_ = $derived(vp?.windows.find((w) => w.id === tab) ?? null);
  const group = $derived(window_ ? groups.find((g) => g.day === window_.day) ?? null : null);
  const activeTab = $derived(tab === 'plan' ? 'plan' : group ? `day${group.day}` : null);

  function selectTab(id) {
    if (id === 'plan') { tab = 'plan'; return; }
    const g = groups.find((x) => `day${x.day}` === id);
    if (g) tab = windowForDay(g, window_).id;
  }
```
(Delete the old `const window_ = ...` line so it is not defined twice.)

Replace the `<Tabs .../>` line and the view block with:
```svelte
    <Tabs {tabs} active={activeTab} onselect={selectTab} />
    <HalfToggle {group} active={tab} onselect={(id) => (tab = id)} />

    {#if tab === 'plan'}
      <PlanView {vp} windows={vp.windows} drive={selectedDrive} onselect={(id) => (tab = id)} />
    {:else if window_}
      <WindowView {vp} win={window_} result={vp.results[window_.id]} drive={selectedDrive} />
    {/if}
```

- [ ] **Step 7: Build and run the suite**

Run: `cd frontend && npm run build && npm test`
Expected: build succeeds with no Svelte warnings about `window_` or unused props. All tests pass except `PlanView.test.js` (still on the old grid; Task 5).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.svelte frontend/src/components/HalfToggle.svelte frontend/src/components/HalfToggle.test.js frontend/src/components/Tabs.test.js frontend/src/components/WindowView.svelte frontend/src/components/WindowView.test.js
git commit -m "feat(frontend): day tab strip with sunrise/sunset toggle; outlook line on day 2+ windows

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014TY4tXhGVEXQdcdsFbgasL"
```

---

### Task 5: Plan grid (days × halves) with tappable cells

**Files:**
- Modify: `frontend/src/components/PlanView.svelte`
- Modify: `frontend/src/components/PlanView.test.js`

**Interfaces:**
- Consumes: `groupByDay` (Task 3), `bestWindow`/`planSummary` (Task 3), `resultsFor` and seven-window `windows` from `fixtures.js` (Task 3).
- Produces: `PlanView` props `{ vp, windows, drive = null, onselect }`; `onselect(windowId)` fires when a cell is tapped.

- [ ] **Step 1: Rewrite `PlanView.test.js`**

Replace the whole file with:

```js
// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import PlanView from './PlanView.svelte';
import { eastPeak, windows, result, resultsFor } from './fixtures.js';

const vpWith = (spec) => ({ ...eastPeak, results: resultsFor(spec) });
const cells = (container) => [...container.querySelectorAll('.cell')];

describe('PlanView grid', () => {
  it('lays out four day columns by two half rows, with a dash for today\'s sunrise', () => {
    const vp = vpWith({ tonight: result({ score: 72 }) });
    const { container } = render(PlanView, { vp, windows });
    const heads = [...container.querySelectorAll('.day-head')].map((h) => h.textContent);
    expect(heads).toEqual(['Today', 'Tomorrow', 'Fri', 'Sat']);
    const rows = [...container.querySelectorAll('.row-head')].map((h) => h.textContent);
    expect(rows).toEqual(['Sunrise', 'Sunset']);
    const all = cells(container);
    expect(all).toHaveLength(8);
    expect(all[0].classList.contains('empty')).toBe(true); // today's sunrise
    expect(all[0].textContent.trim()).toBe('—');
    expect(container.querySelectorAll('button.cell')).toHaveLength(7);
  });

  it('outlines only the best-scoring window cell', () => {
    const vp = vpWith({
      tonight: result({ score: 45 }), d1_am: result({ score: 61 }), d1_pm: result({ score: 78 }),
      d2_am: result({ score: 44 }), d2_pm: result({ score: 55 }), d3_am: result({ score: 30 }), d3_pm: result({ score: 25 }),
    });
    const { container } = render(PlanView, { vp, windows });
    const best = cells(container).filter((c) => c.classList.contains('best'));
    expect(best).toHaveLength(1);
    expect(best[0].getAttribute('aria-label')).toBe('Tomorrow Sunset, 78%');
    expect(best[0].querySelector('.compare-score').textContent).toBe('78%');
  });

  it('marks day 2 and 3 cells as outlook and leaves day 0 and 1 unmarked', () => {
    const vp = vpWith({});
    const { container } = render(PlanView, { vp, windows });
    const buttons = [...container.querySelectorAll('button.cell')];
    expect(buttons.map((b) => b.classList.contains('outlook'))).toEqual([false, false, false, true, true, true, true]);
    expect(container.querySelectorAll('.cell .tag')).toHaveLength(4);
  });

  it('shows a dash and no-data label for a window with no result', () => {
    const vp = vpWith({ tonight: result({ score: 72 }) });
    const { container } = render(PlanView, { vp, windows });
    const d1am = container.querySelector('button.cell[aria-label="Tomorrow Sunrise, no data"]');
    expect(d1am).not.toBeNull();
    expect(d1am.querySelector('.compare-score').textContent).toBe('—');
  });

  it('reports the tapped window id', async () => {
    const onselect = vi.fn();
    const vp = vpWith({ d2_am: result({ score: 50 }) });
    const { container } = render(PlanView, { vp, windows, onselect });
    await fireEvent.click(container.querySelector('button.cell[aria-label="Friday Sunrise, 50%"]'));
    expect(onselect).toHaveBeenCalledWith('d2_am');
  });
});

describe('PlanView summary and cards', () => {
  it('writes the best-bet summary with fog base and viewpoint elevation', () => {
    const vp = vpWith({ tonight: result({ score: 72, lcl_ft: 1394 }), d1_pm: result({ score: 40 }) });
    const { getByText } = render(PlanView, { vp, windows });
    expect(getByText('Best bet: Tonight Sunset at 7:32 PM — 72% likelihood. Fog base ~1,394 ft vs East Peak at 2,571 ft.')).toBeTruthy();
  });

  it('drops the fog-base clause when the best window has no marine layer', () => {
    const vp = vpWith({ tonight: result({ score: 30 }), d1_am: result({ score: 55, lcl_ft: null }) });
    const { getByText } = render(PlanView, { vp, windows });
    expect(getByText('Best bet: Tomorrow Sunrise at 6:48 AM — 55% likelihood.')).toBeTruthy();
  });

  it('writes the no-great-windows summary when every score is under 40', () => {
    const vp = vpWith({ tonight: result({ score: 12 }), d1_am: result({ score: 25 }), d3_pm: result({ score: 39 }) });
    const { getByText } = render(PlanView, { vp, windows });
    expect(getByText(/No great windows in the next three days for East Peak/)).toBeTruthy();
  });

  it('writes the no-great-windows summary when every result is null and still outlines one cell', () => {
    const vp = vpWith({});
    const { container, getByText } = render(PlanView, { vp, windows });
    expect(getByText(/No great windows in the next three days for East Peak/)).toBeTruthy();
    expect(container.querySelectorAll('.cell.best')).toHaveLength(1);
  });

  it('renders exactly one conditions card, for the best window', () => {
    const vp = vpWith({ tonight: result({ score: 72 }), d1_pm: result({ score: 78 }), d2_pm: result({ score: 60 }) });
    const { container, getByText } = render(PlanView, { vp, windows });
    expect(container.querySelectorAll('.card')).toHaveLength(2); // plan card + one conditions card
    expect(getByText('Tomorrow Sunset — 7:30 PM')).toBeTruthy();
  });

  it('renders no conditions card when every result is null', () => {
    const { container } = render(PlanView, { vp: vpWith({}), windows });
    expect(container.querySelectorAll('.card')).toHaveLength(1);
  });

  it('shows the drive line only when a drive is supplied', () => {
    const vp = vpWith({ tonight: result({ score: 72 }) });
    const without = render(PlanView, { vp, windows });
    expect(without.container.querySelector('.drive')).toBeNull();
    const withDrive = render(PlanView, { vp, windows, drive: { seconds: 2700 } });
    expect(withDrive.container.querySelector('.drive').textContent).toContain('drive · no traffic');
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npm test -- src/components/PlanView.test.js`
Expected: most tests fail (`.day-head` not found, 3 `.compare-col` instead of 8 `.cell`, old copy).

- [ ] **Step 3: Rewrite `PlanView.svelte`**

Replace the whole file with:

```svelte
<script>
  import { fmtTime } from '../lib/time.js';
  import { scoreColor } from '../lib/colors.js';
  import { fmtDrive } from '../lib/drive.js';
  import { bestWindow, planSummary } from '../lib/plan.js';
  import { groupByDay } from '../lib/days.js';
  import ConditionsCard from './ConditionsCard.svelte';

  let { vp, windows, drive = null, onselect = () => {} } = $props();
  const groups = $derived(groupByDay(windows));
  const best = $derived(bestWindow(windows, vp.results));
  const bestResult = $derived(vp.results[best.id] ?? null);
  const halves = [['Sunrise', 'am'], ['Sunset', 'pm']];
  const header = (g) => (g.day === 0 ? 'Today' : g.label);
  const label = (w, r) => `${w.title}, ${r ? `${r.score}%` : 'no data'}`;
</script>

<div class="card">
  <h3>Best Window for {vp.name}</h3>
  {#if drive}
    <p class="drive">🚗 {fmtDrive(drive.seconds)} drive · no traffic</p>
  {/if}
  <div class="grid" style="grid-template-columns: auto repeat({groups.length}, 1fr)">
    <div class="corner"></div>
    {#each groups as g (g.day)}
      <div class="day-head">{header(g)}</div>
    {/each}
    {#each halves as [rowLabel, half] (half)}
      <div class="row-head">{rowLabel}</div>
      {#each groups as g (g.day)}
        {@const w = g[half]}
        {@const r = w ? vp.results[w.id] : null}
        {#if !w}
          <div class="cell empty" aria-hidden="true">—</div>
        {:else}
          <button class="cell" class:best={w.id === best.id} class:outlook={w.outlook} aria-label={label(w, r)} onclick={() => onselect(w.id)}>
            <div class="compare-score" style="color:{scoreColor(r?.score)}">{r ? `${r.score}%` : '—'}</div>
            <div class="compare-verdict">{r ? `${r.verdict.emoji} ${r.verdict.label}` : ''}</div>
            <div class="when">{fmtTime(w.sun_event)}</div>
            {#if w.outlook}<div class="tag">outlook</div>{/if}
          </button>
        {/if}
      {/each}
    {/each}
  </div>
  <p class="explanation summary">{planSummary(best, bestResult, vp)}</p>
</div>

{#if bestResult}
  <ConditionsCard title={`${best.title} — ${fmtTime(best.sun_event)}`} result={bestResult} />
{/if}

<style>
  .grid { display: grid; gap: 6px; align-items: stretch; }
  .day-head, .row-head { font-size: 0.72rem; color: var(--muted); align-self: center; }
  .day-head { text-align: center; }
  .row-head { padding-right: 4px; }
  .cell { background: var(--bg); border-radius: 8px; padding: 8px 4px; border: 1px solid transparent; text-align: center; color: inherit; font-family: inherit; cursor: pointer; position: relative; min-height: 64px; }
  .cell.best { border-color: #238636; }
  .cell.outlook { opacity: 0.8; }
  .cell.empty { color: var(--muted); display: flex; align-items: center; justify-content: center; cursor: default; }
  .compare-score { font-size: 1.15rem; font-weight: 700; margin-bottom: 2px; }
  .compare-verdict { font-size: 0.66rem; line-height: 1.2; }
  .when { font-size: 0.66rem; color: var(--muted); margin-top: 3px; }
  .tag { position: absolute; top: 3px; right: 4px; font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
  .summary { margin-top: 12px; }
  .drive { font-size: 0.8rem; color: var(--muted); margin: -6px 0 10px; }
</style>
```

- [ ] **Step 4: Run the Plan tests, then the whole suite and the build**

Run: `cd frontend && npm test -- src/components/PlanView.test.js && npm test && npm run build`
Expected: 12 Plan tests pass; whole suite green; build clean with no unused-CSS or a11y warnings. (If Svelte warns that `.corner` is unused, that is fine — it is a grid placeholder; if it warns about unused selectors, delete them.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PlanView.svelte frontend/src/components/PlanView.test.js
git commit -m "feat(plan): days-by-halves grid with tappable cells and one conditions card

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014TY4tXhGVEXQdcdsFbgasL"
```

---

### Task 6: Version bump, docs, and a real-app check

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`, `backend/pyproject.toml`
- Modify: `README.md`, `CLAUDE.md`, `docs/GETTING-STARTED.md`, `docs/superpowers/specs/2026-09-02-goodfog-design.md`

**Interfaces:** none.

- [ ] **Step 1: Bump versions**

```bash
cd frontend && npm version 0.4.0 --no-git-tag-version && cd ..
```
Then in `backend/pyproject.toml` change `version = "0.3.0"` to `version = "0.4.0"`.

Verify: `grep -n '"version"' frontend/package.json frontend/package-lock.json | head -3` shows `0.4.0` on the first two lockfile hits (root and `packages[""]`); `cd backend && uv run pytest -q tests/test_config.py` passes (it checks `app_version` equals the pyproject version).

- [ ] **Step 2: Update copy and pointers**

`README.md` lines 5–6: change `for tonight's sunset, tomorrow's sunrise, and tomorrow's sunset.` to `for tonight's sunset and every sunrise and sunset through three days out. Day 2 and 3 are labelled as a lower-confidence outlook.`

`CLAUDE.md`:
- Line 3: after the design spec path add ` · three-day outlook: `docs/superpowers/specs/2026-09-02-three-day-outlook-design.md``.
- Line 8 (frontend layout): append ` Navigation is a day strip (Tonight · Tomorrow · Fri · Sat · Plan) plus a Sunrise/Sunset toggle; window grouping lives in `src/lib/days.js`.`
- Add a Rules bullet after the "frontend never computes scores" line: `- Window ids are `tonight, d1_am, d1_pm, d2_am, d2_pm, d3_am, d3_pm`; `outlook` (day ≥ 2) is set by the backend and only ever changes labels, never scores. Refresh the Open-Meteo fixture with `uv run --project backend python scripts/fetch_fixture.py`.`

`docs/GETTING-STARTED.md` line 57: change `the Tonight / Tom. AM / Tom. PM / Plan tabs` to `the Tonight / Tomorrow / Fri / Sat / Plan tabs`.

`docs/superpowers/specs/2026-09-02-goodfog-design.md`: add this line directly under the `build_windows` bullet in §4.2, under the JSON block in §4.4, and under the **Plan tab** bullet in §5:
```
  *Superseded by `2026-09-02-three-day-outlook-design.md`: seven windows, day fields, days × halves Plan grid.*
```

- [ ] **Step 3: Full verification**

```bash
cd backend && uv run pytest -q -W error && cd ../frontend && npm test && npm run build
```
Expected: all green. Then confirm the parity table is untouched: `git diff main --stat -- backend/tests/test_score.py` prints nothing.

- [ ] **Step 4: See it in the real app**

Run the backend (`cd backend && uv run uvicorn goodfog.app:app --port 8000`) and frontend (`cd frontend && npm run dev`) and open http://localhost:5173. Check, at 520 px wide:
- Strip shows Tonight · Tomorrow · Fri · Sat · 🔭 Plan (weekday names will be whatever today+2/+3 are).
- Tonight: no toggle. Tomorrow: toggle appears, defaults to Sunset, tapping Sunrise switches the verdict and timing card.
- Fri Sunset: "Outlook · 2+ days out, lower confidence" sits under the verdict banner.
- Plan: 4×2 grid, dash top-left, one outlined cell, "outlook" tags on the right two columns, tapping a cell opens that window with the correct day tab highlighted.
- Map dots recolour when switching windows.
Stop both servers afterwards.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json backend/pyproject.toml README.md CLAUDE.md docs/GETTING-STARTED.md docs/superpowers/specs/2026-09-02-goodfog-design.md
git commit -m "chore: bump to 0.4.0; document the three-day outlook

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014TY4tXhGVEXQdcdsFbgasL"
```

---

## After the last task

Push the branch and open a PR against `main` that closes #5, then request code review (superpowers:requesting-code-review). CI must be green before asking Mike to merge.
