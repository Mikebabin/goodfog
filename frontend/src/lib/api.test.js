import { describe, it, expect } from 'vitest';
import { fetchSnapshot } from './api.js';

const mk = (status, body) => async () => ({ status, ok: status >= 200 && status < 300, json: async () => body });

describe('fetchSnapshot', () => {
  it('returns ok with data', async () => {
    expect(await fetchSnapshot(mk(200, { a: 1 }))).toEqual({ status: 'ok', data: { a: 1 } });
  });
  it('maps 503 to warming_up', async () => {
    expect(await fetchSnapshot(mk(503, {}))).toEqual({ status: 'warming_up' });
  });
  it('maps other errors and thrown fetches to error', async () => {
    expect((await fetchSnapshot(mk(500, {}))).status).toBe('error');
    expect((await fetchSnapshot(async () => { throw new Error('offline'); })).status).toBe('error');
  });
});
