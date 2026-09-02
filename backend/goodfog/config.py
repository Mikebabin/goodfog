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
