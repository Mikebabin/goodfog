import { fmtTime } from './time.js';

const scoreOf = (r) => r?.score ?? -1;

/** Highest-scoring window; earliest wins ties (original reduce used strict >). */
export function bestWindow(windows, results) {
  return windows.reduce((a, b) => (scoreOf(results[b.id]) > scoreOf(results[a.id]) ? b : a));
}

export function planSummary(best, result, vp) {
  if (!result || result.score < 40) {
    return `No great windows in the next three days for ${vp.name}. Check a higher viewpoint or wait for the next marine layer event.`;
  }
  const fog = result.lcl_ft != null
    ? ` Fog base ~${result.lcl_ft.toLocaleString('en-US')} ft vs ${vp.name} at ${vp.elev_ft.toLocaleString('en-US')} ft.`
    : '';
  return `Best bet: ${best.title} at ${fmtTime(best.sun_event)} — ${result.score}% likelihood.${fog}`;
}
