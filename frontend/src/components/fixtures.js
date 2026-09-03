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
