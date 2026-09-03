import { describe, it, expect } from 'vitest';
import { getPosition } from './geolocate.js';

describe('getPosition', () => {
  it('resolves lat/lon from the geolocation API with a timeout option', async () => {
    let opts;
    const geo = { getCurrentPosition: (ok, _err, o) => { opts = o; ok({ coords: { latitude: 37.7, longitude: -122.4 } }); } };
    expect(await getPosition(geo, 5000)).toEqual({ lat: 37.7, lon: -122.4 });
    expect(opts.timeout).toBe(5000);
  });
  it('rejects on error and when unsupported', async () => {
    const geo = { getCurrentPosition: (_ok, err) => err({ code: 1, message: 'denied' }) };
    await expect(getPosition(geo)).rejects.toBeTruthy();
    await expect(getPosition(undefined)).rejects.toThrow('unsupported');
  });
});
