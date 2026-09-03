<script>
  const verify = [
    { icon: '☁️', name: 'Windy — Clouds', desc: 'Cloud layer height over Mt. Tam', href: 'https://www.windy.com/?clouds,37.923,-122.597,11' },
    { icon: '🌫️', name: 'Windy — Fog (West Tam)', desc: 'Watch fog rolling in from the coast', href: 'https://www.windy.com/?fog,37.923,-122.597,11' },
    { icon: '💨', name: 'Windy — Wind', desc: 'Strong wind disperses the layer', href: 'https://www.windy.com/?wind,37.923,-122.597,11' },
    { icon: '🛰️', name: 'fog.today', desc: 'NOAA GOES-16 satellite fog tracker', href: 'https://fog.today' },
    { icon: '🇳🇴', name: 'yr.no — Mt. Tam', desc: 'Hourly Norwegian Met forecast — great fog detail', href: 'https://www.yr.no/en/forecast/daily-table/2-5381438/United%20States/California/Marin%20County/Mt.%20Tamalpais%20State%20Park' },
  ];
  const cams = [
    { name: 'West Peak — ALERTCalifornia', desc: 'Above clouds = white sea below. In clouds = grey/white everywhere.', href: 'https://cameras.alertcalifornia.org/?pos=37.9691_-122.5971_11&id=Axis-TamWest' },
    { name: 'East Peak — ALERTCalifornia', desc: 'Clear horizon above fog = inversion confirmed.', href: 'https://cameras.alertcalifornia.org/?pos=37.9691_-122.5971_11&id=Axis-TamEast' },
    { name: 'Muir Beach Overlook — ALERTCalifornia', desc: 'Fog rolling in from the Pacific — shows layer thickness.', href: 'https://cameras.alertcalifornia.org/?pos=37.9691_-122.5971_11&id=Axis-MuirBeach' },
  ];
</script>

{#snippet link(icon, name, desc, href)}
  <a class="resource-link" {href} target="_blank" rel="noopener">
    <span class="resource-icon">{icon}</span>
    <div class="resource-info">
      <div class="resource-name">{name}</div>
      <div class="resource-desc">{desc}</div>
    </div>
  </a>
{/snippet}

<div class="card top">
  <h3>Verify the Forecast</h3>
  <div class="resource-grid">
    {#each verify as r (r.href)}{@render link(r.icon, r.name, r.desc, r.href)}{/each}
  </div>
</div>

<div class="card">
  <h3>Live Cameras</h3>
  <div class="resource-grid">
    {#each cams as r (r.href)}{@render link('📷', r.name, r.desc, r.href)}{/each}
  </div>
  <p class="cam-hint">
    <strong>Reading the cams:</strong> If the summit cams show a flat white layer below with blue sky above = you'd be above the inversion.
    If it's all grey = you're in it. Muir Beach shows how thick and active the marine layer is coming off the ocean.
  </p>
</div>

<style>
  .top { margin-top: 8px; }
  .resource-grid { display: flex; flex-direction: column; gap: 8px; }
  .resource-link { display: flex; align-items: center; gap: 10px; background: var(--panel2); border-radius: 8px; padding: 10px 12px; text-decoration: none; color: var(--text); font-size: 0.86rem; transition: background 0.15s; }
  .resource-link:hover { background: #2d333b; }
  .resource-icon { font-size: 1.1rem; flex-shrink: 0; }
  .resource-info { flex: 1; }
  .resource-name { font-weight: 600; }
  .resource-desc { font-size: 0.76rem; color: var(--muted); margin-top: 1px; }
  .cam-hint { font-size: 0.79rem; color: var(--muted); margin-top: 10px; line-height: 1.5; }
</style>
