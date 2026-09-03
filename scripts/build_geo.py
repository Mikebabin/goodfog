"""Build data/coast.geojson: land polygons for the Good Fog map frame.

Land = (Marin + San Francisco county polygons) − (Census areal hydrography), clipped to
FRAME, simplified, exterior rings clockwise (d3-geo winding). County legal boundaries
include water (SF covers the Golden Gate channel), hence the subtraction.

Run from repo root:  uv run --project backend python scripts/build_geo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
from shapely.geometry import box, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

FRAME = (-122.66, 37.76, -122.40, 37.96)  # west, south, east, north
TOLERANCE_DEG = 0.0005
MIN_AREA_DEG2 = 1e-7
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"
COUNTIES_URL = f"{TIGER}/State_County/MapServer/1/query"
WATER_URL = f"{TIGER}/Hydro/MapServer/1/query"
OUT = Path(__file__).resolve().parent.parent / "data" / "coast.geojson"


def _geo_params(where: str, out_fields: str) -> dict:
    west, south, east, north = FRAME
    return {
        "where": where,
        "outFields": out_fields,
        "geometry": f"{west},{south},{east},{north}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outSR": "4326",
        "resultRecordCount": "2000",
        "f": "geojson",
    }


def fetch(url: str, params: dict) -> list[dict]:
    r = httpx.get(url, params=params, timeout=120)
    r.raise_for_status()
    data = r.json()
    if "features" not in data:
        raise SystemExit(f"{url}: unexpected response: {str(data)[:200]}")
    if data.get("exceededTransferLimit") or data.get("properties", {}).get("exceededTransferLimit"):
        raise SystemExit(f"{url}: exceededTransferLimit; narrow the query")
    return data["features"]


def round_coords(obj):
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: round_coords(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [round_coords(x) for x in obj]
    return obj


def build() -> dict:
    counties = fetch(COUNTIES_URL, _geo_params("STATE='06' AND COUNTY IN ('041','075')", "NAME,GEOID"))
    if len(counties) != 2:
        raise SystemExit(f"expected 2 counties, got {len(counties)}")
    water = fetch(WATER_URL, _geo_params("1=1", "NAME,MTFCC"))
    if not water:
        raise SystemExit("no water features returned")

    frame = box(*FRAME)
    land = unary_union([shape(f["geometry"]) for f in counties]).intersection(frame)
    land = land.difference(unary_union([shape(f["geometry"]) for f in water]).intersection(frame))
    land = land.simplify(TOLERANCE_DEG, preserve_topology=True)

    parts = [p for p in getattr(land, "geoms", [land]) if p.geom_type == "Polygon" and p.area > MIN_AREA_DEG2]
    features = [
        {"type": "Feature", "properties": {}, "geometry": round_coords(mapping(orient(p, sign=-1.0)))}
        for p in parts
    ]
    return {"type": "FeatureCollection", "bbox": list(FRAME), "features": features}


def main() -> int:
    fc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fc, separators=(",", ":")) + "\n")
    n = sum(len(r) for f in fc["features"] for r in f["geometry"]["coordinates"])
    print(f"wrote {OUT} ({len(fc['features'])} parts, {n} vertices, {OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
