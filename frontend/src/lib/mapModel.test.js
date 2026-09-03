import { describe, it, expect } from 'vitest';
import { DOT_R, FRAME, frameAspect, landPaths, makeProjection, nudgeApart, placeDots, scoreForTab } from './mapModel.js';

const W = 360;
const H = Math.round(W * frameAspect());
const proj = makeProjection(W, H);

const coast = {
  type: 'FeatureCollection',
  features: [{ type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[[-122.6, 37.9], [-122.5, 37.9], [-122.5, 37.8], [-122.6, 37.8], [-122.6, 37.9]]] } }],
};

const vp = (id, lon, lat, results) => ({ id, name: id, lon, lat, results });
const r = (score) => (score == null ? null : { score });

describe('projection', () => {
  it('fits the frame exactly', () => {
    const [x0, y0] = proj([FRAME.west, FRAME.north]);
    const [x1, y1] = proj([FRAME.east, FRAME.south]);
    expect(Math.abs(x0)).toBeLessThan(0.5);
    expect(Math.abs(y0)).toBeLessThan(0.5);
    expect(Math.abs(x1 - W)).toBeLessThan(0.5);
    expect(Math.abs(y1 - H)).toBeLessThan(0.5);
  });
  it('frameAspect is near square for this frame', () => {
    expect(frameAspect()).toBeGreaterThan(0.9);
    expect(frameAspect()).toBeLessThan(1.1);
  });
  it('landPaths returns one path string per feature', () => {
    const paths = landPaths(coast, proj);
    expect(paths).toHaveLength(1);
    expect(paths[0]).toMatch(/^M/);
  });
});

describe('scoreForTab', () => {
  const v = vp('a', -122.5, 37.85, { tonight: r(15), d1_am: r(35), d1_pm: null });
  it('reads the window score', () => {
    expect(scoreForTab(v, 'tonight')).toBe(15);
    expect(scoreForTab(v, 'd1_pm')).toBeNull();
  });
  it('plan uses the best window and ignores nulls', () => {
    expect(scoreForTab(v, 'plan')).toBe(35);
    expect(scoreForTab(vp('b', 0, 0, { tonight: null }), 'plan')).toBeNull();
  });
});

describe('nudgeApart', () => {
  it('separates overlapping dots symmetrically and keeps the midpoint', () => {
    const out = nudgeApart([{ id: 'a', x: 100, y: 100 }, { id: 'b', x: 104, y: 100 }]);
    const d = Math.hypot(out[1].x - out[0].x, out[1].y - out[0].y);
    expect(d).toBeGreaterThanOrEqual(2 * DOT_R + 2 - 1e-6);
    expect((out[0].x + out[1].x) / 2).toBeCloseTo(102, 6);
    expect(out[0].y).toBeCloseTo(100, 6);
  });
  it('leaves non-overlapping dots untouched and does not mutate input', () => {
    const input = [{ id: 'a', x: 0, y: 0 }, { id: 'b', x: 100, y: 0 }];
    const out = nudgeApart(input);
    expect(out).toEqual(input);
    expect(out).not.toBe(input);
  });
  it('handles coincident dots deterministically', () => {
    const out = nudgeApart([{ id: 'a', x: 50, y: 50 }, { id: 'b', x: 50, y: 50 }]);
    expect(Math.abs(out[1].x - out[0].x)).toBeGreaterThanOrEqual(2 * DOT_R + 2 - 1e-6);
  });
});

describe('placeDots', () => {
  const vps = [
    vp('hawk-hill', -122.4997, 37.8283, { tonight: r(80) }),
    vp('conzelman-pullouts', -122.49, 37.827, { tonight: r(55) }),
    vp('battery-spencer', -122.4818, 37.8278, { tonight: r(20) }),
    vp('twin-peaks-vantage', -122.4581, 37.7874, { tonight: null }),
  ];
  const dots = placeDots(vps, 'tonight', proj);
  it('returns one dot per viewpoint inside the viewBox with band colors', () => {
    expect(dots.map((d) => d.id)).toEqual(vps.map((v) => v.id));
    for (const d of dots) {
      expect(d.x).toBeGreaterThan(0); expect(d.x).toBeLessThan(W);
      expect(d.y).toBeGreaterThan(0); expect(d.y).toBeLessThan(H);
    }
    expect(dots[0].color).toBe('#3fb950');
    expect(dots[1].color).toBe('#d29922');
    expect(dots[2].color).toBe('#f85149');
    expect(dots[3]).toMatchObject({ score: null, color: '#8b949e' });
  });
  it('keeps the Headlands cluster from overlapping at 360px', () => {
    const min = 2 * DOT_R + 2;
    for (let i = 0; i < 3; i++) for (let j = i + 1; j < 3; j++) {
      expect(Math.hypot(dots[i].x - dots[j].x, dots[i].y - dots[j].y)).toBeGreaterThanOrEqual(min - 1e-6);
    }
  });
});
