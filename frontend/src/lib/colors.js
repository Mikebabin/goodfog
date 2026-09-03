export function scoreColor(score) {
  if (score == null) return '#8b949e';
  if (score >= 70) return '#3fb950';
  if (score >= 50) return '#d29922';
  if (score >= 30) return '#e3812c';
  return '#f85149';
}

/** Text color that reads on a dot of the given fill: dark only on the bright amber band. */
export function textColorFor(hex) {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  const brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return brightness >= 0.6 ? '#0d1117' : '#ffffff';
}
