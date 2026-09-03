export function scoreColor(score) {
  if (score == null) return '#8b949e';
  if (score >= 70) return '#3fb950';
  if (score >= 50) return '#d29922';
  if (score >= 30) return '#e3812c';
  return '#f85149';
}
