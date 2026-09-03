export const ORIGIN_KEY = 'goodfog.origin';

function isValid(o) {
  return (
    o != null && typeof o === 'object' &&
    typeof o.label === 'string' && o.label.length > 0 &&
    Number.isFinite(o.lat) && Number.isFinite(o.lon) &&
    Math.abs(o.lat) <= 90 && Math.abs(o.lon) <= 180
  );
}

/** Read {label, lat, lon} from storage; anything missing or malformed → null. Never throws. */
export function loadOrigin(storage) {
  try {
    const raw = storage?.getItem(ORIGIN_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw);
    return isValid(o) ? { label: o.label, lat: o.lat, lon: o.lon } : null;
  } catch {
    return null;
  }
}

/** Persist an origin, or remove it when null. Never throws. */
export function saveOrigin(storage, origin) {
  try {
    if (origin == null) storage?.removeItem(ORIGIN_KEY);
    else storage?.setItem(ORIGIN_KEY, JSON.stringify({ label: origin.label, lat: origin.lat, lon: origin.lon }));
  } catch {
    /* storage full or blocked: the origin just won't persist */
  }
}
