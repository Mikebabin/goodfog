import { geoMercator, geoPath } from 'd3-geo';
import { scoreColor } from './colors.js';

/** Fixed map frame around the eight viewpoints (lon/lat). The layout never shifts with data. */
export const FRAME = { west: -122.66, south: 37.76, east: -122.4, north: 37.96 };
export const DOT_R = 12; // px
const NO_DATA = '#8b949e';

// Clockwise ring (d3-geo spherical winding): a counter-clockwise ring means "everything but".
const framePolygon = {
  type: 'Polygon',
  coordinates: [[
    [FRAME.west, FRAME.north], [FRAME.east, FRAME.north], [FRAME.east, FRAME.south], [FRAME.west, FRAME.south], [FRAME.west, FRAME.north],
  ]],
};

/** height / width of the frame in Mercator space, so the SVG is never letterboxed. */
export function frameAspect() {
  const p = geoMercator();
  const [x0, y0] = p([FRAME.west, FRAME.north]);
  const [x1, y1] = p([FRAME.east, FRAME.south]);
  return (y1 - y0) / (x1 - x0);
}

export function makeProjection(width, height) {
  return geoMercator().fitExtent([[0, 0], [width, height]], framePolygon);
}

export function landPaths(coast, projection) {
  const path = geoPath(projection);
  return coast.features.map((f) => path(f));
}

/** Score to color a dot by: the tab's window, or on the Plan tab the best window (null if none). */
export function scoreForTab(vp, tab) {
  if (tab === 'plan') {
    const scores = Object.values(vp.results).filter((r) => r != null).map((r) => r.score);
    return scores.length ? Math.max(...scores) : null;
  }
  return vp.results[tab]?.score ?? null;
}

/** Push overlapping dots apart along their connecting axis. Pure, deterministic, symmetric. */
export function nudgeApart(dots, minDist = 2 * DOT_R + 2, iterations = 10) {
  const out = dots.map((d) => ({ ...d }));
  for (let it = 0; it < iterations; it++) {
    let moved = false;
    for (let i = 0; i < out.length; i++) {
      for (let j = i + 1; j < out.length; j++) {
        let dx = out[j].x - out[i].x;
        let dy = out[j].y - out[i].y;
        let d = Math.hypot(dx, dy);
        if (d >= minDist) continue;
        if (d === 0) { dx = 1; dy = 0; d = 1; }
        const push = (minDist - d) / 2;
        const ux = dx / d, uy = dy / d;
        out[i].x -= ux * push; out[i].y -= uy * push;
        out[j].x += ux * push; out[j].y += uy * push;
        moved = true;
      }
    }
    if (!moved) break;
  }
  return out;
}

export function placeDots(viewpoints, tab, projection) {
  const dots = viewpoints.map((vp) => {
    const [x, y] = projection([vp.lon, vp.lat]);
    const score = scoreForTab(vp, tab);
    return { id: vp.id, name: vp.name, x, y, score, color: score == null ? NO_DATA : scoreColor(score) };
  });
  return nudgeApart(dots);
}
