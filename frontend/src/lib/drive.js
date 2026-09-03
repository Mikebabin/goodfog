/** Whole minutes for a drive, rounded UP so "leave by" is never too late. Invalid → null. */
export function driveMinutes(seconds) {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return null;
  return Math.ceil(seconds / 60);
}

/** '26 min' / '1 h 05 min' / '—' for no drive. */
export function fmtDrive(seconds) {
  const m = driveMinutes(seconds);
  if (m == null) return '—';
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')} min`;
}

/**
 * Subtract a drive from a local ISO string ('YYYY-MM-DDTHH:MM') and return the same shape.
 * Components go through Date.UTC so neither DST nor the viewer's zone can leak in.
 */
export function leaveBy(arriveByIso, seconds) {
  const m = driveMinutes(seconds);
  if (m == null) return null;
  const [date, time] = arriveByIso.slice(0, 16).split('T');
  const [Y, M, D] = date.split('-').map(Number);
  const [h, mi] = time.split(':').map(Number);
  const t = new Date(Date.UTC(Y, M - 1, D, h, mi) - m * 60_000);
  const p = (n) => String(n).padStart(2, '0');
  return `${t.getUTCFullYear()}-${p(t.getUTCMonth() + 1)}-${p(t.getUTCDate())}T${p(t.getUTCHours())}:${p(t.getUTCMinutes())}`;
}
