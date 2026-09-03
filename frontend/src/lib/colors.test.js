import { it, expect } from 'vitest';
import { scoreClass, scoreColor } from './colors.js';

it('maps score bands to verdict classes for themed text', () => {
  expect(scoreClass(70)).toBe('go');
  expect(scoreClass(50)).toBe('try');
  expect(scoreClass(30)).toBe('maybe');
  expect(scoreClass(29)).toBe('no');
  expect(scoreClass(null)).toBe('none');
});

it('maps score bands to colors', () => {
  expect(scoreColor(70)).toBe('#3fb950');
  expect(scoreColor(50)).toBe('#d29922');
  expect(scoreColor(30)).toBe('#e3812c');
  expect(scoreColor(29)).toBe('#f85149');
  expect(scoreColor(null)).toBe('#8b949e');
});

import { textColorFor } from './colors.js';

it('picks dark text only on the bright amber band', () => {
  expect(textColorFor('#d29922')).toBe('#0d1117'); // amber
  expect(textColorFor('#3fb950')).toBe('#ffffff'); // green
  expect(textColorFor('#e3812c')).toBe('#ffffff'); // orange
  expect(textColorFor('#f85149')).toBe('#ffffff'); // red
  expect(textColorFor('#8b949e')).toBe('#ffffff'); // grey (no data)
});
