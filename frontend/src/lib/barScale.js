/** Round up to a clean axis maximum with headroom, so low spots aren't crushed against the left edge. */
export function niceMax(v) {
  if (v <= 500) return Math.ceil(v / 100) * 100;
  if (v <= 1500) return Math.ceil(v / 250) * 250;
  return Math.ceil(v / 500) * 500;
}

/**
 * Geometry for the fog-base-vs-elevation bar. `lclFt` is null when there is no marine layer.
 * Percentages are 0..100 along the bar.
 */
export function barModel(vp, lclFt) {
  const topFt = Math.max(vp.elev_ft, vp.yellow_ft[1], lclFt != null ? lclFt : 0);
  const maxFt = niceMax(topFt * 1.2);
  const pct = (ft) => Math.min(100, Math.max(0, (ft / maxFt) * 100));
  const [g0, g1] = vp.green_ft;
  return {
    maxFt,
    locPct: pct(vp.elev_ft),
    lclPct: lclFt != null ? pct(lclFt) : null,
    bandL: pct(g0),
    bandW: pct(g1) - pct(g0),
    bandCenter: pct((g0 + g1) / 2),
  };
}
