import { it, expect } from 'vitest';
import { fmtTime } from './time.js';

it('formats local ISO strings as 12-hour times', () => {
  expect(fmtTime('2026-09-02T19:32')).toBe('7:32 PM');
  expect(fmtTime('2026-09-03T06:05')).toBe('6:05 AM');
  expect(fmtTime('2026-09-03T00:00')).toBe('12:00 AM');
});
