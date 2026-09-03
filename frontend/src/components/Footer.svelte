<script>
  import { formatVersion } from '../lib/version.js';

  let { generatedAt = null } = $props();
  const build = formatVersion(__APP_VERSION__, import.meta.env.VITE_COMMIT);
  const updated = $derived(generatedAt ? new Date(generatedAt).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : null);
</script>

<footer>
  Forecast by <a href="https://open-meteo.com/">Open-Meteo</a> (CC BY 4.0). Fog base is an LCL estimate from
  temperature and dewpoint — a heuristic guide, not a measurement. Always confirm on the live cameras.
  <span class="build">{build}{updated ? ` · forecast ${updated}` : ''}</span>
</footer>

<style>
  footer { margin: 2rem 0 1rem; padding: 0 1rem; font-size: 0.75rem; color: var(--muted); line-height: 1.5; }
  a { color: inherit; }
  .build { display: block; margin-top: 0.5rem; font-size: 0.7rem; opacity: 0.8; font-variant-numeric: tabular-nums; }
</style>
