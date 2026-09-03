<script>
  import { onMount } from 'svelte';
  import coastRaw from '@data/coast.geojson?raw';
  import LikelihoodMap from './components/Map.svelte';
  import { fetchSnapshot, fetchDrive, geocode } from './lib/api.js';
  import Header from './components/Header.svelte';
  import LocationPicker from './components/LocationPicker.svelte';
  import Tabs from './components/Tabs.svelte';
  import WindowView from './components/WindowView.svelte';
  import PlanView from './components/PlanView.svelte';
  import VerifyLinks from './components/VerifyLinks.svelte';
  import Footer from './components/Footer.svelte';
  import OriginPicker from './components/OriginPicker.svelte';
  import { getPosition } from './lib/geolocate.js';
  import { loadOrigin, saveOrigin } from './lib/origin.js';

  const coast = JSON.parse(coastRaw); // Vite only auto-parses .json, so load .geojson as text

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

  let origin = $state(loadOrigin(globalThis.localStorage));
  let drives = $state(null);        // {[vpId]: {seconds, meters} | null} once fetched
  let driveBusy = $state(false);
  let driveError = $state(null);
  let drivesRequested = false;      // first snapshot triggers one fetch for a remembered origin
  let driveReq = 0;                 // generation counter; a superseded fetch must not write state

  const driveEnabled = $derived(snapshot?.features?.drive === true);
  const selectedDrive = $derived(driveEnabled && drives && vp ? (drives[vp.id] ?? null) : null);

  async function loadDrives(o) {
    const id = ++driveReq;
    if (!o) { drives = null; driveBusy = false; return; }
    driveBusy = true;
    const r = await fetchDrive(o.lat, o.lon);
    if (id !== driveReq) return;    // origin changed or was cleared while this was in flight
    driveBusy = false;
    if (r.status === 'ok') { drives = r.data.drives; driveError = null; }
    else { drives = null; driveError = 'Drive times unavailable right now'; }
  }

  function setOrigin(o) {
    origin = o;
    saveOrigin(globalThis.localStorage, o);
    driveError = null;
    drivesRequested = true;
    loadDrives(o);
  }

  async function submitAddress(text) {
    driveBusy = true;
    driveError = null;
    const r = await geocode(text);
    driveBusy = false;
    if (r.status === 'ok') setOrigin(r.place);
    else if (r.status === 'no_match') driveError = 'Address not found';
    else driveError = 'Drive times unavailable right now';
  }

  async function useMyLocation() {
    driveBusy = true;
    driveError = null;
    try {
      const { lat, lon } = await getPosition();
      setOrigin({ label: 'My location', lat, lon });
    } catch {
      driveBusy = false;
      driveError = 'Location blocked or unavailable';
    }
  }

  const viewpoints = $derived(snapshot?.viewpoints ?? []);
  const vp = $derived(
    viewpoints.find((v) => v.id === selectedId) ??
      viewpoints.find((v) => v.id === DEFAULT_ID) ??
      viewpoints[0] ??
      null
  );
  const tabs = $derived([...(snapshot?.windows ?? []).map((w) => ({ id: w.id, label: w.tab })), { id: 'plan', label: '🔭 Plan' }]);
  const window_ = $derived(vp?.windows.find((w) => w.id === tab) ?? null);

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
      if (!drivesRequested && r.data.features?.drive && origin) {
        drivesRequested = true;
        loadDrives(origin);
      }
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
    <LikelihoodMap {coast} {viewpoints} {selectedId} {tab} onselect={select} />
    {#if driveEnabled}
      <OriginPicker {origin} busy={driveBusy} error={driveError} onsubmit={submitAddress} onlocate={useMyLocation} onclear={() => setOrigin(null)} />
    {/if}
    <LocationPicker {viewpoints} {selectedId} onselect={select} drives={driveEnabled ? drives : null} />
    <Tabs {tabs} active={tab} onselect={(id) => (tab = id)} />

    {#if tab === 'plan'}
      <PlanView {vp} windows={vp.windows} drive={selectedDrive} />
    {:else if window_}
      <WindowView {vp} win={window_} result={vp.results[window_.id]} drive={selectedDrive} />
    {/if}
  {/if}

  <VerifyLinks />
  <Footer generatedAt={snapshot?.generated_at} />
</div>

<style>
  .spinner { text-align: center; padding: 24px; color: var(--muted); }
</style>
