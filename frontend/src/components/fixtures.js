/**
 * Hand-written snapshot fragments matching design spec §4.4, with copy taken verbatim from
 * backend/goodfog/fog.py (verdict, elevation_verdict) and viewpoints.py (East Peak). Shapes for
 * component rendering only; score/copy parity lives in backend/tests/test_score.py.
 */

export const eastPeak = {
  id: 'east-peak',
  name: 'East Peak',
  elev_ft: 2571,
  green_ft: [200, 2400],
  yellow_ft: [2400, 2571],
};

const win = (id, day, day_label, long, sun_label, sun_event, arrive_by) => ({
  id, day, day_label, outlook: day >= 2, title: `${long} ${sun_label}`, tab: day_label,
  sun_label, sun_event, arrive_by, hour: `${sun_event.slice(0, 13)}:00`,
});

/** Seven windows as the backend emits them for a Wednesday (2026-09-02). */
export const windows = [
  win('tonight', 0, 'Tonight', 'Tonight', 'Sunset', '2026-09-02T19:32', '2026-09-02T18:47'),
  win('d1_am', 1, 'Tomorrow', 'Tomorrow', 'Sunrise', '2026-09-03T06:48', '2026-09-03T06:18'),
  win('d1_pm', 1, 'Tomorrow', 'Tomorrow', 'Sunset', '2026-09-03T19:30', '2026-09-03T18:45'),
  win('d2_am', 2, 'Fri', 'Friday', 'Sunrise', '2026-09-04T06:49', '2026-09-04T06:19'),
  win('d2_pm', 2, 'Fri', 'Friday', 'Sunset', '2026-09-04T19:29', '2026-09-04T18:44'),
  win('d3_am', 3, 'Sat', 'Saturday', 'Sunrise', '2026-09-05T06:50', '2026-09-05T06:20'),
  win('d3_pm', 3, 'Sat', 'Saturday', 'Sunset', '2026-09-05T19:27', '2026-09-05T18:42'),
];

/** Results keyed by window id; unspecified windows are null. */
export function resultsFor(spec) {
  return Object.fromEntries(windows.map((w) => [w.id, spec[w.id] ?? null]));
}

export const verdicts = {
  go: { label: 'Go for it!', emoji: '🚀', cls: 'go' },
  try: { label: 'Worth a try', emoji: '🤔', cls: 'try' },
  maybe: { label: 'Maybe next time', emoji: '😶‍🌫️', cls: 'maybe' },
  no: { label: 'Stay home', emoji: '🛑', cls: 'no' },
};

export const elevations = {
  clear: { cls: 'clear', icon: '🔭', title: 'No marine layer', detail: 'East Peak at 2,571 ft. Low cloud is thin — no significant marine layer expected. Clear views, but no inversion to shoot.' },
  above: { cls: 'above', icon: '🏔️', title: 'Above the fog layer', detail: 'Fog base sits around 1,394 ft — comfortably below East Peak (2,571 ft). You should be looking down onto the layer. Highest vantage — 360° sea of cloud over all of Marin and SF. Trees/ridgeline as foreground.' },
  edge: { cls: 'edge', icon: '⚡', title: 'Right at the edge', detail: 'Fog base near 2,450 ft — close to East Peak (2,571 ft). The layer may swirl around you: dramatic but unpredictable. Check the live cameras before committing.' },
  below: { cls: 'below', icon: '🌫️', title: 'Socked in', detail: 'Fog base ~150 ft. Fog base extremely low — a very deep layer could still reach you. Consider a higher viewpoint.' },
};

const wx = (over = {}) => ({
  low_cloud: 80, mid_cloud: 5, high_cloud: 0, wind_mph: 4, rain_pct: 0,
  temp_f: 61, dewpoint_f: 55, lcl_ft: 1394, ...over,
});

/**
 * A full window result. `score` picks the verdict; `lcl_ft` null means no marine layer, which
 * also flips status, elevation, and the low-cloud factor to what the backend would emit.
 */
export function result({ score, lcl_ft = 1394, elevation } = {}) {
  const verdict = score >= 70 ? verdicts.go : score >= 50 ? verdicts.try : score >= 30 ? verdicts.maybe : verdicts.no;
  const layer = lcl_ft != null;
  return {
    score,
    verdict,
    status: { kind: layer ? 'green' : 'none', reason: null },
    factors: [
      layer ? { label: 'Low cloud 80%', rating: 'good' } : { label: 'Low cloud 10%', rating: 'bad' },
      { label: 'Wind 4 mph', rating: 'good' },
    ],
    explanation: 'Strong marine layer signal.',
    lcl_ft,
    elevation: elevation ?? (layer ? elevations.above : elevations.clear),
    wx: wx({ lcl_ft, low_cloud: layer ? 80 : 10 }),
  };
}
