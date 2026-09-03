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
