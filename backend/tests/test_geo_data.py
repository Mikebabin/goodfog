"""Guards for the generated data/coast.geojson (see scripts/build_geo.py)."""
import json
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.geometry.polygon import LinearRing
from shapely.ops import unary_union

from goodfog.viewpoints import VIEWPOINTS

ROOT = Path(__file__).resolve().parents[2]
COAST = ROOT / "data" / "coast.geojson"
FRAME = (-122.66, 37.76, -122.40, 37.96)


def _fc():
    return json.loads(COAST.read_text())


def test_file_shape_and_bbox():
    fc = _fc()
    assert fc["type"] == "FeatureCollection"
    assert fc["bbox"] == [-122.66, 37.76, -122.4, 37.96]
    assert 1 <= len(fc["features"]) <= 20
    for f in fc["features"]:
        assert f["geometry"]["type"] == "Polygon"
        assert f["properties"] == {}


def test_rings_are_within_frame_and_rounded():
    west, south, east, north = FRAME
    for f in _fc()["features"]:
        for ring in f["geometry"]["coordinates"]:
            for lon, lat in ring:
                assert west - 1e-9 <= lon <= east + 1e-9 and south - 1e-9 <= lat <= north + 1e-9
                assert round(lon, 4) == lon and round(lat, 4) == lat


def test_exterior_clockwise_holes_counterclockwise():
    # d3-geo uses spherical winding: a counter-clockwise exterior is read as the whole
    # sphere minus the polygon and paints the entire map.
    for f in _fc()["features"]:
        exterior, *holes = f["geometry"]["coordinates"]
        assert not LinearRing(exterior).is_ccw
        for h in holes:
            assert LinearRing(h).is_ccw


def test_viewpoints_on_land_and_golden_gate_is_water():
    land = unary_union([shape(f["geometry"]) for f in _fc()["features"]])
    for vp in VIEWPOINTS:
        assert land.contains(Point(vp.lon, vp.lat)), vp.id
    assert not land.contains(Point(-122.478, 37.818))  # mid Golden Gate channel
    assert not land.contains(Point(-122.47, 37.85))    # Richardson Bay
    assert not land.contains(Point(-122.535, 37.831))  # Rodeo Lagoon
