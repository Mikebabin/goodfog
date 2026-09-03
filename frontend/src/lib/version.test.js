import { it, expect } from 'vitest';
import { formatVersion } from './version.js';

it('formats version and short sha', () => {
  expect(formatVersion('0.1.0', 'a1b2c3d4e5f6')).toBe('v0.1.0 · a1b2c3d');
  expect(formatVersion('0.1.0', '')).toBe('v0.1.0 · dev');
  expect(formatVersion('0.1.0', undefined)).toBe('v0.1.0 · dev');
});
