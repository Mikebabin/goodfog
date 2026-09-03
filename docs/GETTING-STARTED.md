# Getting started with Good Fog (Claude Code desktop app)

You don't need to touch a terminal. Claude Code handles the command-line parts; you
handle the decisions. Follow these steps in order — about 20 minutes.

## 1. Accept the invite

Open the GitHub invitation email and click **Accept invitation**. You should then be
able to open https://github.com/Mikebabin/goodfog in your browser.

## 2. Get the code onto your computer (GitHub Desktop)

1. Install **GitHub Desktop** from https://desktop.github.com and sign in with your
   GitHub account (skip if you already use it).
2. In GitHub Desktop: **File → Clone repository… → GitHub.com tab**, pick
   `Mikebabin/goodfog`, choose a folder (the default is fine), click **Clone**.

You now have a `goodfog` folder on your machine. (If the Claude Code app offers
"Clone repository" when you create a session, that works too.)

## 3. Fresh-Mac prep (MacBook, one time)

Two installs that are easier done by hand than by Claude, because they need an
admin password or a click in a system dialog:

1. **Node.js** — go to https://nodejs.org, download the **macOS Installer (.pkg)** for
   the LTS version, open it, and click through. This gives you `node` and `npm`.
2. **Command line developer tools** — the first time git runs, macOS shows a dialog
   "The git command requires the command line developer tools." Click **Install** and
   wait (a few minutes). If you don't see it, Claude will trigger it in the next step —
   click **Install** when it appears.

Nothing else is needed: Claude installs `uv` (the Python tool) itself without a
password.

## 4. Open the project in Claude Code

1. Install the **Claude Code desktop app** from https://claude.com/claude-code and
   sign in (skip if installed).
2. **Open folder** → choose the `goodfog` folder you just cloned.
3. Paste this as your first message:

> Read README.md and CLAUDE.md. Then set the project up: install uv if it's missing
> (use the official installer script, no Homebrew, no sudo), install the backend and
> frontend dependencies, run both test suites, and tell me what passed.

Claude will ask permission before installing things — click **Allow**. When it
reports all tests pass (currently 60 backend, 16 frontend), you're set up.

## 5. See it running

Paste:

> Start the backend and the frontend dev server, then give me the local URL.

Open the URL it gives you (normally http://localhost:5173). You should see the viewpoint
picker, the Tonight / Tom. AM / Tom. PM / Plan tabs, and the verdict card for East Peak.
The live site is https://goodfog.babins.net — your local copy is the same app.

## 6. Pick something to work on

Open https://github.com/Mikebabin/goodfog/issues and pick an issue. Then tell
Claude, for example:

> Work on issue #6 (Celsius toggle). Create a branch for it, follow CLAUDE.md, write
> tests, and open a pull request when it's done.

Claude will create the branch, make the changes, run the tests, and open a PR. You
can watch the changed files in GitHub Desktop as it goes.

## 7. The rules that matter

- **Never push to `main` directly.** Every change goes through a pull request. Merging
  to `main` deploys to the live site automatically within a few minutes.
- **Never commit secrets.** If Claude needs a value locally, it goes in a `.env` file,
  which is ignored by git.
- **Tests must pass** before a PR is opened. Ask Claude to run them if unsure.
- Ask Claude to explain anything — "explain how the fog-base (LCL) status and the
  likelihood score are computed in backend/goodfog/fog.py" or "what does this PR
  change?" are good questions.

## 8. Day-to-day loop

1. In GitHub Desktop: **Fetch origin** so you have the latest `main`.
2. In Claude Code: describe the task and reference the issue number.
3. Review the PR on GitHub; Mike merges.

## If something goes wrong

- Claude says a command failed → ask it "diagnose the root cause before fixing".
- Site looks broken locally but tests pass → ask it to "restart both servers".
- Git got confusing → in GitHub Desktop, **Branch → Discard all changes** brings you
  back to a clean state (this deletes uncommitted work).

## Where things live

| What | Where |
|---|---|
| Design decisions | `docs/superpowers/specs/2026-09-02-goodfog-design.md` |
| Backend (Python/FastAPI) | `backend/` |
| Viewpoint data & thresholds | `backend/goodfog/viewpoints.py` |
| Fog-base & scoring math | `backend/goodfog/fog.py` |
| Frontend (Svelte) | `frontend/` |
| UI cards | `frontend/src/components/` |
| Live site | https://goodfog.babins.net |
| Hosting | Coolify at coolify.babins.net (Mike manages) |
