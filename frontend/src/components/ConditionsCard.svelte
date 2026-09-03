<script>
  let { title, result } = $props();
  const ft = (n) => n.toLocaleString('en-US');
</script>

<div class="card">
  <h3>{title}</h3>
  <div class="wx-grid grid">
    <div><div class="wx-label">Low cloud</div><div class="wx-value">{result.wx.low_cloud}%</div></div>
    <div><div class="wx-label">Wind</div><div class="wx-value">{result.wx.wind_mph} mph</div></div>
    <div><div class="wx-label">Fog base (LCL)</div><div class="wx-value">{result.lcl_ft != null ? `${ft(result.lcl_ft)} ft` : 'None'}</div></div>
    <div><div class="wx-label">Rain</div><div class="wx-value">{result.wx.rain_pct}%</div></div>
  </div>
  <div class="factors">
    {#each result.factors as f}
      <span class="factor {f.rating}">{f.label}</span>
    {/each}
  </div>
</div>

<style>
  .grid { margin-bottom: 12px; }
</style>
