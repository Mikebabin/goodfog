import { describe, it, expect } from 'vitest';
import { barModel, niceMax } from './barScale.js';

const hawk = { elev_ft: 923, green_ft: [200, 850], yellow_ft: [850, 950] };
const bonita = { elev_ft: 100, green_ft: [50, 200], yellow_ft: [200, 300] };

describe('niceMax', () => {
  it('rounds up to a clean maximum by band', () => {
    expect(niceMax(360)).toBe(400);
    expect(niceMax(500)).toBe(500);
    expect(niceMax(1140)).toBe(1250);
    expect(niceMax(1500)).toBe(1500);
    expect(niceMax(3085)).toBe(3500);
  });
});

describe('barModel', () => {
  it('scales the axis to the viewpoint and fog base', () => {
    const m = barModel(hawk, 1271);
    expect(m.maxFt).toBe(2000); // max(923, 950, 1271) * 1.2 = 1525.2 -> ceil to 500s -> 2000
    expect(m.locPct).toBeCloseTo((923 / 2000) * 100, 5);
    expect(m.lclPct).toBeCloseTo((1271 / 2000) * 100, 5);
    expect(m.bandL).toBeCloseTo((200 / 2000) * 100, 5);
    expect(m.bandW).toBeCloseTo(((850 - 200) / 2000) * 100, 5);
    expect(m.bandCenter).toBeCloseTo((525 / 2000) * 100, 5);
  });
  it('omits the fog marker when there is no layer', () => {
    const m = barModel(bonita, null);
    expect(m.maxFt).toBe(400); // max(100, 300, 0) * 1.2 = 360 -> 400
    expect(m.lclPct).toBeNull();
  });
  it('clamps percentages to 0..100', () => {
    expect(barModel(hawk, 100000).lclPct).toBe(100);
  });
});
