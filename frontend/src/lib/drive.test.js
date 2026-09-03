import { describe, it, expect } from 'vitest';
import { driveMinutes, fmtDrive, leaveBy } from './drive.js';

describe('driveMinutes', () => {
  it('rounds up and rejects nonsense', () => {
    expect(driveMinutes(0)).toBe(0);
    expect(driveMinutes(59)).toBe(1);
    expect(driveMinutes(1540)).toBe(26);
    expect(driveMinutes(null)).toBeNull();
    expect(driveMinutes(undefined)).toBeNull();
    expect(driveMinutes(-5)).toBeNull();
    expect(driveMinutes(NaN)).toBeNull();
  });
});

describe('fmtDrive', () => {
  it('formats minutes and hours', () => {
    expect(fmtDrive(1540)).toBe('26 min');
    expect(fmtDrive(3600)).toBe('1 h 00 min');
    expect(fmtDrive(3900)).toBe('1 h 05 min');
    expect(fmtDrive(0)).toBe('0 min');
    expect(fmtDrive(null)).toBe('—');
  });
});

describe('leaveBy', () => {
  it('subtracts whole minutes from a local ISO string', () => {
    expect(leaveBy('2026-09-02T18:45', 1540)).toBe('2026-09-02T18:19');
    expect(leaveBy('2026-09-02T18:45', 0)).toBe('2026-09-02T18:45');
  });
  it('rolls over midnight and month boundaries', () => {
    expect(leaveBy('2026-09-03T06:20', 30 * 60)).toBe('2026-09-03T05:50');
    expect(leaveBy('2026-09-03T00:10', 20 * 60)).toBe('2026-09-02T23:50');
    expect(leaveBy('2026-10-01T00:05', 10 * 60)).toBe('2026-09-30T23:55');
  });
  it('returns null without a drive', () => {
    expect(leaveBy('2026-09-02T18:45', null)).toBeNull();
  });
});
