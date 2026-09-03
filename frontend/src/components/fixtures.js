/**
 * Hand-written snapshot fragments matching design spec §4.4. Copy and thresholds mirror
 * backend/goodfog/fog.py (verdict, elevation_verdict); these are shapes, not parity tests.
 */

export const eastPeak = {
  id: 'east-peak',
  name: 'East Peak',
  elev_ft: 2571,
  green_ft: [200, 2400],
  yellow_ft: [2400, 2571],
};

export const windows = [
  { id: 'tonight', title: 'Tonight Sunset', tab: 'Tonight', sun_label: 'Sunset', sun_event: '2026-09-02T19:32', arrive_by: '2026-09-02T18:47', hour: '2026-09-02T19:00' },
  { id: 'tomorrow_am', title: 'Tomorrow Sunrise', tab: 'Tomorrow AM', sun_label: 'Sunrise', sun_event: '2026-09-03T06:48', arrive_by: '2026-09-03T06:03', hour: '2026-09-03T07:00' },
  { id: 'tomorrow_pm', title: 'Tomorrow Sunset', tab: 'Tomorrow PM', sun_label: 'Sunset', sun_event: '2026-09-03T19:30', arrive_by: '2026-09-03T18:45', hour: '2026-09-03T19:00' },
];

export const verdicts = {
  go: { label: 'Go for it!', emoji: '🚀', cls: 'go' },
  try: { label: 'Worth a try', emoji: '🤔', cls: 'try' },
  maybe: { label: 'Maybe next time', emoji: '😶‍🌫️', cls: 'maybe' },
  no: { label: 'Stay home', emoji: '🛑', cls: 'no' },
};

export const elevations = {
  clear: { cls: 'clear', icon: '🔭', title: 'No marine layer', detail: 'East Peak at 2,571 ft. Low cloud is thin — no significant marine layer expected.' },
  above: { cls: 'above', icon: '🏔️', title: 'Above the fog layer', detail: 'Fog base sits around 1,394 ft — comfortably below East Peak (2,571 ft).' },
  edge: { cls: 'edge', icon: '⚡', title: 'Right at the edge', detail: 'Fog base near 2,450 ft — close to East Peak (2,571 ft).' },
  below: { cls: 'below', icon: '🌫️', title: 'Socked in', detail: 'Fog base ~150 ft. Consider a higher viewpoint.' },
};

const wx = (over = {}) => ({
  low_cloud: 80, mid_cloud: 5, high_cloud: 0, wind_mph: 4, rain_pct: 0,
  temp_f: 61, dewpoint_f: 55, lcl_ft: 1394, ...over,
});

/** A full window result. `score` picks the verdict; `lcl_ft` null means no marine layer. */
export function result({ score, lcl_ft = 1394, elevation = elevations.above } = {}) {
  const verdict = score >= 70 ? verdicts.go : score >= 50 ? verdicts.try : score >= 30 ? verdicts.maybe : verdicts.no;
  return {
    score,
    verdict,
    status: { kind: lcl_ft == null ? 'none' : 'green', reason: null },
    factors: [
      { label: 'Low cloud 80%', rating: 'good' },
      { label: 'Wind 4 mph', rating: 'good' },
    ],
    explanation: 'Strong marine layer signal.',
    lcl_ft,
    elevation,
    wx: wx({ lcl_ft }),
  };
}
