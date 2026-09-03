/** Resolve {lat, lon} from the Geolocation API, or reject. `geo` is injectable for tests. */
export function getPosition(geo = globalThis.navigator?.geolocation, timeoutMs = 10_000) {
  return new Promise((resolve, reject) => {
    if (!geo) return reject(new Error('unsupported'));
    geo.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      (err) => reject(err),
      { timeout: timeoutMs, maximumAge: 60_000 }
    );
  });
}
