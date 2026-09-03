import { describe, it, expect } from 'vitest';
import { bestWindow, planSummary } from './plan.js';

const windows = [
  { id: 'tonight', tab: '🌅 Tonight', sun_event: '2026-09-02T19:32' },
  { id: 'tomorrow_am', tab: '🌄 Tom. AM', sun_event: '2026-09-03T06:52' },
  { id: 'tomorrow_pm', tab: '🌇 Tom. PM', sun_event: '2026-09-03T19:31' },
];
const vp = { name: 'Hawk Hill', elev_ft: 923 };

describe('bestWindow', () => {
  it('picks the highest score, earliest on ties', () => {
    const results = { tonight: { score: 50 }, tomorrow_am: { score: 80 }, tomorrow_pm: { score: 80 } };
    expect(bestWindow(windows, results).id).toBe('tomorrow_am');
  });
  it('treats null results as -1', () => {
    const results = { tonight: null, tomorrow_am: null, tomorrow_pm: { score: 0 } };
    expect(bestWindow(windows, results).id).toBe('tomorrow_pm');
  });
  it('returns the first window when everything is null', () => {
    expect(bestWindow(windows, { tonight: null, tomorrow_am: null, tomorrow_pm: null }).id).toBe('tonight');
  });
});

describe('planSummary', () => {
  it('names the best bet when score >= 40', () => {
    const s = planSummary(windows[1], { score: 80, lcl_ft: 615 }, vp);
    expect(s).toBe('Best bet: 🌄 Tom. AM at 6:52 AM — 80% likelihood. Fog base ~615 ft vs Hawk Hill at 923 ft.');
  });
  it('omits the fog-base clause when lcl is null', () => {
    expect(planSummary(windows[0], { score: 45, lcl_ft: null }, vp)).toBe('Best bet: 🌅 Tonight at 7:32 PM — 45% likelihood.');
  });
  it('says no great windows below 40 or when null', () => {
    const msg = 'No great windows in the next two days for Hawk Hill. Check a higher viewpoint or wait for the next marine layer event.';
    expect(planSummary(windows[0], { score: 39, lcl_ft: 100 }, vp)).toBe(msg);
    expect(planSummary(windows[0], null, vp)).toBe(msg);
  });
});
