/** Format a local ISO string (no offset, as Open-Meteo returns) as '7:32 PM'. Pure string math, no Date. */
export function fmtTime(iso) {
  const [h, m] = iso.slice(11, 16).split(':').map(Number);
  const suffix = h >= 12 ? 'PM' : 'AM';
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return `${hour12}:${String(m).padStart(2, '0')} ${suffix}`;
}
