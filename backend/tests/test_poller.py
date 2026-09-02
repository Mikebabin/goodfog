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
