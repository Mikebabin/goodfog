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
