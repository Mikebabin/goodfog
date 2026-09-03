<script>
  import { onMount } from 'svelte';
  import { fetchSnapshot } from './lib/api.js';
  import Header from './components/Header.svelte';
  import LocationPicker from './components/LocationPicker.svelte';
  import Tabs from './components/Tabs.svelte';
  import WindowView from './components/WindowView.svelte';

  const STORAGE_KEY = 'goodfog.viewpoint';
  const DEFAULT_ID = 'east-peak';
  const REFRESH_MS = 5 * 60 * 1000;

  function loadSelected() {
    try { return globalThis.localStorage?.getItem(STORAGE_KEY) || DEFAULT_ID; } catch { return DEFAULT_ID; }
  }

  let snapshot = $state(null);
  let status = $state('loading'); // loading | ok | warming_up | error
  let error = $state(null);
  let selectedId = $state(loadSelected());
  let tab = $state('tonight'); // tonight | tomorrow_am | tomorrow_pm | plan

  const viewpoints = $derived(snapshot?.viewpoints ?? []);
  const vp = $derived(viewpoints.find((v) => v.id === selectedId) ?? viewpoints[0] ?? null);
  const tabs = $derived([...(snapshot?.windows ?? []).map((w) => ({ id: w.id, label: w.tab })), { id: 'plan', label: '🔭 Plan' }]);
  const window_ = $derived(snapshot?.windows.find((w) => w.id === tab) ?? null);

  function select(id) {
    selectedId = id;
    try { globalThis.localStorage?.setItem(STORAGE_KEY, id); } catch {}
  }

  async function load() {
    const r = await fetchSnapshot();
    if (r.status === 'ok') {
      snapshot = r.data;
      status = 'ok';
      error = null;
    } else if (!snapshot) {
      status = r.status;
      error = r.error ?? null;
    }
  }

  onMount(() => {
    load();
    const timer = setInterval(() => { if (document.visibilityState === 'visible') load(); }, REFRESH_MS);
    const onVisible = () => { if (document.visibilityState === 'visible') load(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', onVisible); };
  });
</script>

<div class="container">
  <Header />

  {#if status === 'loading'}
    <p class="spinner">Fetching weather data…</p>
  {:else if status === 'warming_up'}
    <p class="spinner">Warming up — first forecast arriving shortly…</p>
  {:else if status === 'error'}
    <div class="error-box">Error fetching weather: {error}. Check your connection and try again.</div>
  {/if}

  {#if snapshot && vp}
    <LocationPicker {viewpoints} {selectedId} onselect={select} />
    <Tabs {tabs} active={tab} onselect={(id) => (tab = id)} />

    {#if tab === 'plan'}
      <div class="card"><p class="explanation">Plan view coming in the next task.</p></div>
    {:else if window_}
      <WindowView {vp} win={window_} result={vp.results[window_.id]} />
    {/if}
  {/if}
</div>

<style>
  .spinner { text-align: center; padding: 24px; color: var(--muted); }
</style>
