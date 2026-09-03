import { describe, it, expect } from 'vitest';
import { ORIGIN_KEY, loadOrigin, saveOrigin } from './origin.js';

function fakeStorage(initial = {}) {
  const m = new Map(Object.entries(initial));
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), m };
}

describe('loadOrigin', () => {
  it('round-trips a valid origin', () => {
    const s = fakeStorage();
    saveOrigin(s, { label: 'Home', lat: 37.7, lon: -122.4, extra: 'dropped' });
    expect(loadOrigin(s)).toEqual({ label: 'Home', lat: 37.7, lon: -122.4 });
    expect(JSON.parse(s.m.get(ORIGIN_KEY))).toEqual({ label: 'Home', lat: 37.7, lon: -122.4 });
  });
  it('returns null for missing, malformed or out-of-range values', () => {
    expect(loadOrigin(fakeStorage())).toBeNull();
    expect(loadOrigin(fakeStorage({ [ORIGIN_KEY]: 'not json' }))).toBeNull();
    expect(loadOrigin(fakeStorage({ [ORIGIN_KEY]: JSON.stringify({ label: '', lat: 1, lon: 2 }) }))).toBeNull();
    expect(loadOrigin(fakeStorage({ [ORIGIN_KEY]: JSON.stringify({ label: 'x', lat: 91, lon: 2 }) }))).toBeNull();
    expect(loadOrigin(fakeStorage({ [ORIGIN_KEY]: JSON.stringify({ label: 'x', lat: '1', lon: 2 }) }))).toBeNull();
    expect(loadOrigin(undefined)).toBeNull();
  });
});

describe('saveOrigin', () => {
  it('removes the key when origin is null and never throws', () => {
    const s = fakeStorage({ [ORIGIN_KEY]: '{}' });
    saveOrigin(s, null);
    expect(s.m.has(ORIGIN_KEY)).toBe(false);
    expect(() => saveOrigin({ setItem() { throw new Error('quota'); } }, { label: 'x', lat: 1, lon: 2 })).not.toThrow();
    expect(() => saveOrigin(undefined, null)).not.toThrow();
  });
});
