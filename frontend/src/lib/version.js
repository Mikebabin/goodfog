/** Footer build label: 'v0.1.0 · a1b2c3d', or 'v0.1.0 · dev' when no commit sha is known. */
export function formatVersion(version, sha) {
  const short = (sha ?? '').trim().slice(0, 7) || 'dev';
  return `v${version} · ${short}`;
}
