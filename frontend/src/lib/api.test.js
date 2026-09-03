import { describe, it, expect } from 'vitest';
import { fetchSnapshot, geocode, fetchDrive } from './api.js';

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

describe('geocode', () => {
  it('returns ok with the place and encodes the query', async () => {
    let url;
    const f = async (u) => { url = u; return { status: 200, ok: true, json: async () => ({ label: 'X', lat: 1, lon: 2 }) }; };
    expect(await geocode('24th & Noe', f)).toEqual({ status: 'ok', place: { label: 'X', lat: 1, lon: 2 } });
    expect(url).toBe('/api/geocode?q=24th%20%26%20Noe');
  });
  it('maps 404, 503, other errors and throws', async () => {
    expect(await geocode('x', mk(404, {}))).toEqual({ status: 'no_match' });
    expect(await geocode('x', mk(503, {}))).toEqual({ status: 'unavailable' });
    expect((await geocode('x', mk(500, {}))).status).toBe('error');
    expect((await geocode('x', async () => { throw new Error('offline'); })).status).toBe('error');
  });
});

describe('fetchDrive', () => {
  it('POSTs lat/lon as JSON and returns data', async () => {
    let call;
    const f = async (u, init) => { call = { u, init }; return { status: 200, ok: true, json: async () => ({ drives: {} }) }; };
    expect(await fetchDrive(37.7, -122.4, f)).toEqual({ status: 'ok', data: { drives: {} } });
    expect(call.u).toBe('/api/drive');
    expect(call.init.method).toBe('POST');
    expect(JSON.parse(call.init.body)).toEqual({ lat: 37.7, lon: -122.4 });
  });
  it('maps 503, other errors and throws', async () => {
    expect(await fetchDrive(0, 0, mk(503, {}))).toEqual({ status: 'unavailable' });
    expect((await fetchDrive(0, 0, mk(422, {}))).status).toBe('error');
    expect((await fetchDrive(0, 0, async () => { throw new Error('offline'); })).status).toBe('error');
  });
});
