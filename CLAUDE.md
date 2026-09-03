# Good Fog — project rules for Claude Code

Marin marine-layer inversion checker for photographers. Design spec: `docs/superpowers/specs/2026-09-02-goodfog-design.md`.
New contributor? Read `docs/GETTING-STARTED.md`.

## Layout
- `backend/` — Python 3.12 + FastAPI. `viewpoints.py` (data), `fog.py` (pure math), `windows.py`, `providers/open_meteo.py`, `snapshot.py`, `poller.py`, `app.py`, `config.py` (settings).
- `frontend/` — Svelte 5 + Vite PWA. Pure helpers in `src/lib/` (tested), components in `src/components/`.
- `data/` — generated coastline GeoJSON for the map; regenerate with `uv run --project backend python scripts/build_geo.py`, never hand-edit (a test guards winding and the frame).

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
