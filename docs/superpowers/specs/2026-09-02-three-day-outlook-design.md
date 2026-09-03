# Three-day outlook — design

Extends Good Fog from three viewing windows (tonight, tomorrow AM, tomorrow PM) to seven,
covering sunrise and sunset through three days out, so a weekend shoot can be planned
early in the week. Resolves issue #5. Amends the base design in
`2026-09-02-goodfog-design.md` §4.2, §4.4, §5.

## 1. Goals and non-goals

**Goals**
- Seven windows: tonight's sunset, then sunrise and sunset for each of the next three days.
- Navigation that fits the 520 px column without a scrolling tab strip.
- Day 2 and 3 windows visibly marked as lower confidence, without changing any score.
- No change to the scoring rubric, thresholds, or parity table.

**Non-goals**
- Today's sunrise as a window (the original app never had it; unchanged).
- Hiding "Tonight" after sunset has passed (unchanged, separate issue if wanted).
- Forecast beyond day 3.

## 2. Backend

### 2.1 Windows (`windows.py`)

`build_windows(sunrise, sunset)` returns seven `Window`s in this order:

| id        | day | source       | sun_label | arrive offset |
|-----------|-----|--------------|-----------|---------------|
| `tonight` | 0   | `sunset[0]`  | Sunset    | 45 min        |
| `d1_am`   | 1   | `sunrise[1]` | Sunrise   | 30 min        |
| `d1_pm`   | 1   | `sunset[1]`  | Sunset    | 45 min        |
| `d2_am`   | 2   | `sunrise[2]` | Sunrise   | 30 min        |
| `d2_pm`   | 2   | `sunset[2]`  | Sunset    | 45 min        |
| `d3_am`   | 3   | `sunrise[3]` | Sunrise   | 30 min        |
| `d3_pm`   | 3   | `sunset[3]`  | Sunset    | 45 min        |

`Window` gains three fields:

- `day: int` — 0..3 as above.
- `day_label: str` — `"Tonight"` for day 0, `"Tomorrow"` for day 1, else the abbreviated
  weekday of the sun event's date (`"Fri"`, `"Sat"`), computed from the ISO string with
  `datetime.fromisoformat(...).strftime("%a")`. Pure; no clock.
- `outlook: bool` — `day >= 2`. This is the single source of the lower-confidence rule; the
  frontend never derives it from dates.

`title` becomes `f"{long_day} {sun_label}"` where `long_day` is `"Tonight"`, `"Tomorrow"`,
or the full weekday (`"Friday"`): "Tonight Sunset", "Tomorrow Sunrise", "Friday Sunset".
`tab` becomes `day_label` with no emoji (the strip now names days, not windows); it is kept
on the window for backward compatibility with the top-level `windows` list but the frontend
groups by `day` and uses `day_label`.

`truncate_hour`, `minus_minutes`, `arrive_by`, and `hour` are unchanged.

### 2.2 Provider (`providers/open_meteo.py`)

`FORECAST_DAYS = 4`. Day 3's sunset needs an hourly row on the fourth calendar day; with
`forecast_days=3` the hourly block ends at 23:00 on day 2. Everything else about the
request and parser is unchanged. A day whose hourly row is missing still yields a `null`
result for that window, as today.

### 2.3 Snapshot (`snapshot.py`)

No structural change. `windows` (top-level and per-viewpoint) now has seven entries, each
with the three new fields; `results` has seven keys. The JSON in the base spec §4.4 becomes:

```json
"windows": [
  {"id": "tonight", "day": 0, "day_label": "Tonight", "outlook": false,
   "title": "Tonight Sunset", "tab": "Tonight", "sun_label": "Sunset",
   "sun_event": "2026-09-02T19:32", "arrive_by": "2026-09-02T18:47", "hour": "2026-09-02T19:00"},
  {"id": "d1_am", "day": 1, "day_label": "Tomorrow", "outlook": false, ...},
  {"id": "d1_pm", "day": 1, ...}, {"id": "d2_am", "day": 2, "day_label": "Fri", "outlook": true, ...},
  {"id": "d2_pm", ...}, {"id": "d3_am", "day": 3, "day_label": "Sat", "outlook": true, ...}, {"id": "d3_pm", ...}
]
```

### 2.4 Fixture

`backend/tests/fixtures/open_meteo.json` is re-downloaded with `forecast_days=4` (same
eight points, same hourly/daily variables, same models default). A new
`scripts/fetch_fixture.py` does this so the next refresh is one command:
`uv run --project backend python scripts/fetch_fixture.py`. It reuses `OpenMeteoProvider`'s
parameter construction so the fixture cannot drift from the real request.

## 3. Frontend

### 3.1 State and navigation (`App.svelte`, `Tabs.svelte`, `HalfToggle.svelte`)

- Selection state stays one value: `tab` is a window id or `"plan"`. Default `"tonight"`.
- The tab strip lists one entry per distinct `day` (label `day_label`) plus Plan:
  **Tonight · Tomorrow · Fri · Sat · Plan**. Built by a pure helper
  `groupByDay(windows)` in `src/lib/days.js` → `[{day, label, am: Window|null, pm: Window|null}]`.
- Picking a day selects a window in that day: keep the current half (Sunrise/Sunset) if that
  day has it, otherwise the half it has. Pure helper `windowForDay(group, currentWindow)`.
- `HalfToggle` is a two-segment control (Sunrise | Sunset) rendered between the strip and
  the verdict banner whenever the selected day has both halves; hidden on Tonight and Plan.
- Map behaviour is unchanged: dots colour by the selected window, or by the best of all
  seven on Plan (`scoreForTab` already does this by taking the maximum non-null score).

### 3.2 Detail view (`WindowView.svelte`)

Unchanged, plus one line directly under the verdict banner when `win.outlook` is true:

> Outlook · 2+ days out, lower confidence

Muted text, no card. Everything else (elevation banner, bar, timing, conditions, notes,
why) renders exactly as today for all seven windows.

### 3.3 Plan tab (`PlanView.svelte`, `plan.js`)

- A grid with days across (Today, Tomorrow, Fri, Sat) and Sunrise / Sunset down. Column
  headers come from the day groups; "Tonight" is shown as "Today" in the header since the
  column also has a sunrise row.
- Each cell is a `<button>` showing score and verdict emoji + label. Today's sunrise cell is a
  disabled dash. Cells for `outlook` windows are muted and carry a small "outlook" tag.
- The best window's cell is outlined (`bestWindow` unchanged: highest score, earliest on ties,
  null counts as −1, so outlook windows can be the best).
- Tapping a cell sets `tab` to that window id, which shows its detail view.
- Below the grid: the drive line (if any), the summary sentence, and **one** conditions card
  for the best window. The seven per-window cards are dropped; detail is one tap away.
- `planSummary` copy: "No great windows in the next **three** days for …". "Best bet" copy
  uses the window's `title` in place of `tab`: "Best bet: Tomorrow Sunset at 7:31 PM — 78%
  likelihood." so the sentence still names the half.

### 3.4 Version

User-visible change: bump `frontend/package.json` (+ lockfile) and `backend/pyproject.toml`
to `0.4.0`.

## 4. Error handling

- Fewer than four usable sunrise/sunset entries from the provider: `parse_open_meteo` raises
  `ProviderError` → the poller records `last_error` and keeps the old snapshot, as any
  provider failure does. A test pins this at the parser and at the poller.
- Missing hourly row for any window: `null` result, "No data for this window." in the detail
  view, dash in the Plan grid, treated as −1 by `bestWindow`.
- Stale `tab` (e.g. a cached snapshot still naming `tomorrow_am`): `window_` resolves to
  null and the detail area renders nothing, exactly as today; the strip still works. The
  service-worker snapshot cache holds one entry and is network-first, so this lasts one
  refresh at most.

## 5. Testing

**Backend**
- `test_windows.py`: seven ids in order; `day`, `day_label`, `outlook`, `title` for each;
  weekday labels computed from the date; `IndexError` on short daily lists.
- `test_open_meteo.py`: `forecast_days == "4"`.
- `test_snapshot.py`: seven windows and seven result keys per viewpoint; new field set;
  `d3_pm` resolves to a non-null result against the new fixture.
- `test_app.py`/`test_poller.py`: unchanged unless they count windows.

**Frontend**
- `src/lib/days.test.js`: `groupByDay` and `windowForDay` (keep-half rule, Tonight has no AM).
- `src/lib/plan.test.js`: copy changes.
- `src/components/`: `Tabs` renders day labels + Plan; `HalfToggle` shows the active half and
  emits on click; `PlanView` grid shape (4×2), dash for today's sunrise, best cell outlined,
  outlook cells tagged, click selects the window, single conditions card for the best
  window; `WindowView` shows the outlook line only when `win.outlook`.

**Parity**: `test_score.py` is untouched. If it changes, the PR is wrong.

## 6. Documentation

- Base spec §4.2, §4.4, §5 gain a one-line pointer to this document.
- `CLAUDE.md`: the frontend layout line mentions the day strip + half toggle; the spec
  pointer list gains this file.
- `README.md`: the feature description mentions three days out.
