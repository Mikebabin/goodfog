import { it, expect } from 'vitest';
import { makeLatest } from './latest.js';

it('only the most recent begin() is current', () => {
  const l = makeLatest();
  const a = l.begin();
  expect(l.isCurrent(a)).toBe(true);
  const b = l.begin();
  expect(l.isCurrent(a)).toBe(false);
  expect(l.isCurrent(b)).toBe(true);
});
