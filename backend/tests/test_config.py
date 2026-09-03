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


def test_frontend_and_backend_versions_match():
    # Footer shows package.json's version; /api/health shows pyproject's. Bump both together.
    import json

    pkg = json.loads((ROOT / "frontend" / "package.json").read_text())
    assert pkg["version"] == _pyproject_version()
