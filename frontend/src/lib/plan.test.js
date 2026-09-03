import { describe, it, expect } from 'vitest';
import { bestWindow, planSummary } from './plan.js';

const windows = [
  { id: 'tonight', title: 'Tonight Sunset', tab: 'Tonight', sun_event: '2026-09-02T19:32' },
  { id: 'd1_am', title: 'Tomorrow Sunrise', tab: 'Tomorrow', sun_event: '2026-09-03T06:52' },
  { id: 'd1_pm', title: 'Tomorrow Sunset', tab: 'Tomorrow', sun_event: '2026-09-03T19:31' },
];
const vp = { name: 'Hawk Hill', elev_ft: 923 };

describe('bestWindow', () => {
  it('picks the highest score, earliest on ties', () => {
    const results = { tonight: { score: 50 }, d1_am: { score: 80 }, d1_pm: { score: 80 } };
    expect(bestWindow(windows, results).id).toBe('d1_am');
  });
  it('treats null results as -1', () => {
    const results = { tonight: null, d1_am: null, d1_pm: { score: 0 } };
    expect(bestWindow(windows, results).id).toBe('d1_pm');
  });
  it('returns the first window when everything is null', () => {
    expect(bestWindow(windows, { tonight: null, d1_am: null, d1_pm: null }).id).toBe('tonight');
  });
});

describe('planSummary', () => {
  it('names the best bet by window title when score >= 40', () => {
    const s = planSummary(windows[1], { score: 80, lcl_ft: 615 }, vp);
    expect(s).toBe('Best bet: Tomorrow Sunrise at 6:52 AM — 80% likelihood. Fog base ~615 ft vs Hawk Hill at 923 ft.');
  });
  it('omits the fog-base clause when lcl is null', () => {
    expect(planSummary(windows[0], { score: 45, lcl_ft: null }, vp)).toBe('Best bet: Tonight Sunset at 7:32 PM — 45% likelihood.');
  });
  it('says no great windows below 40 or when null', () => {
    const msg = 'No great windows in the next three days for Hawk Hill. Check a higher viewpoint or wait for the next marine layer event.';
    expect(planSummary(windows[0], { score: 39, lcl_ft: 100 }, vp)).toBe(msg);
    expect(planSummary(windows[0], null, vp)).toBe(msg);
  });
});
