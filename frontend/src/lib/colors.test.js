import { it, expect } from 'vitest';
import { scoreColor } from './colors.js';

it('maps score bands to colors', () => {
  expect(scoreColor(70)).toBe('#3fb950');
  expect(scoreColor(50)).toBe('#d29922');
  expect(scoreColor(30)).toBe('#e3812c');
  expect(scoreColor(29)).toBe('#f85149');
  expect(scoreColor(null)).toBe('#8b949e');
});
