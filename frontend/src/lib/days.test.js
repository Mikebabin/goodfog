import { describe, expect, it } from 'vitest';
import { groupByDay, windowForDay } from './days.js';

const w = (id, day, day_label, sun_label) => ({ id, day, day_label, sun_label, outlook: day >= 2 });
const windows = [
  w('tonight', 0, 'Tonight', 'Sunset'),
  w('d1_am', 1, 'Tomorrow', 'Sunrise'), w('d1_pm', 1, 'Tomorrow', 'Sunset'),
  w('d2_am', 2, 'Fri', 'Sunrise'), w('d2_pm', 2, 'Fri', 'Sunset'),
  w('d3_am', 3, 'Sat', 'Sunrise'), w('d3_pm', 3, 'Sat', 'Sunset'),
];

describe('groupByDay', () => {
  it('groups seven windows into four days in order', () => {
    const g = groupByDay(windows);
    expect(g.map((x) => [x.day, x.label])).toEqual([[0, 'Tonight'], [1, 'Tomorrow'], [2, 'Fri'], [3, 'Sat']]);
  });
  it('puts sunrise in am and sunset in pm; tonight has no am', () => {
    const g = groupByDay(windows);
    expect(g[0].am).toBeNull();
    expect(g[0].pm.id).toBe('tonight');
    expect(g[2].am.id).toBe('d2_am');
    expect(g[2].pm.id).toBe('d2_pm');
  });
  it('returns an empty list for no windows', () => {
    expect(groupByDay([])).toEqual([]);
  });
});

describe('windowForDay', () => {
  const g = groupByDay(windows);
  it('keeps the current half when the day has it', () => {
    expect(windowForDay(g[2], windows[1]).id).toBe('d2_am'); // current is a sunrise
    expect(windowForDay(g[2], windows[2]).id).toBe('d2_pm'); // current is a sunset
  });
  it('falls back to the half the day has', () => {
    expect(windowForDay(g[0], windows[1]).id).toBe('tonight'); // wanted sunrise, tonight only has sunset
  });
  it('prefers sunset when there is no current window', () => {
    expect(windowForDay(g[1], null).id).toBe('d1_pm');
  });
});
