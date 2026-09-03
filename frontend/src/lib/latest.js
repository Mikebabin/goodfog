/** Tracks the newest of a series of async requests so superseded responses can be ignored. */
export function makeLatest() {
  let current = 0;
  return {
    begin() { return ++current; },
    isCurrent(id) { return id === current; },
  };
}
