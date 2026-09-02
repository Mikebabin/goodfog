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
