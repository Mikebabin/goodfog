/** Fetch /api/snapshot. Never throws; returns a tagged result. */
export async function fetchSnapshot(fetchImpl = fetch) {
  try {
    const r = await fetchImpl('/api/snapshot', { headers: { Accept: 'application/json' } });
    if (r.status === 503) return { status: 'warming_up' };
    if (!r.ok) return { status: 'error', error: `HTTP ${r.status}` };
    return { status: 'ok', data: await r.json() };
  } catch (e) {
    return { status: 'error', error: String(e) };
  }
}

/** GET /api/geocode?q=. Never throws; tagged result. */
export async function geocode(q, fetchImpl = fetch) {
  try {
    const r = await fetchImpl(`/api/geocode?q=${encodeURIComponent(q)}`, { headers: { Accept: 'application/json' } });
    if (r.status === 404) return { status: 'no_match' };
    if (r.status === 503) return { status: 'unavailable' };
    if (!r.ok) return { status: 'error', error: `HTTP ${r.status}` };
    return { status: 'ok', place: await r.json() };
  } catch (e) {
    return { status: 'error', error: String(e) };
  }
}

/** POST /api/drive with an origin. Never throws; tagged result. */
export async function fetchDrive(lat, lon, fetchImpl = fetch) {
  try {
    const r = await fetchImpl('/api/drive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ lat, lon }),
    });
    if (r.status === 503) return { status: 'unavailable' };
    if (!r.ok) return { status: 'error', error: `HTTP ${r.status}` };
    return { status: 'ok', data: await r.json() };
  } catch (e) {
    return { status: 'error', error: String(e) };
  }
}
