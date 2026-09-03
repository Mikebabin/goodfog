<script>
  import { barModel } from '../lib/barScale.js';

  let { vp, lclFt } = $props();
  const m = $derived(barModel(vp, lclFt));
  const ft = (n) => n.toLocaleString('en-US');
</script>

<div class="card">
  <h3>Fog Base (LCL) vs Your Elevation</h3>
  <div class="axis"><span>0 ft</span><span>{ft(m.maxFt)} ft</span></div>
  <div class="elev-bar-wrap">
    <div class="elev-bar-track">
      <div class="band" style="left:{m.bandL}%; width:{m.bandW}%"></div>
    </div>
    <div class="elev-marker-label sweet" style="left:{m.bandCenter}%">✓ sweet spot</div>
    <div class="elev-marker loc" style="left:{m.locPct}%">
      <div class="elev-marker-label" style="top:-18px; left:-10px;">{vp.name}</div>
      <div class="elev-marker-label" style="bottom:-18px; left:-10px;">{ft(vp.elev_ft)} ft</div>
    </div>
    {#if m.lclPct !== null}
      <div class="elev-marker ceil" style="left:{m.lclPct}%">
        <div class="elev-marker-label fog" style="top:-18px; left:6px;">🌫️ fog base</div>
        <div class="elev-marker-label fog" style="bottom:-18px; left:6px;">{ft(lclFt)} ft</div>
      </div>
    {/if}
  </div>
  {#if m.lclPct === null}
    <p class="none">🔭 No marine layer this hour — no fog base to place on the bar yet.</p>
  {/if}
  <p class="legend">
    The <span class="g">green band</span> is where the fog base needs to sit for a good {vp.name} shot
    ({ft(vp.green_ft[0])}–{ft(vp.green_ft[1])} ft). When there's a marine layer, the
    <span class="f">🌫️ fog base</span> marker appears — if it lands in the green, you're above the layer.
    LCL is derived from temperature and dewpoint — a guide, not a precise ceiling. Verify with the live cameras and Windy.
  </p>
</div>

<style>
  .axis { display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--muted); margin-bottom: 4px; }
  .elev-bar-wrap { margin: 12px 0 4px; position: relative; height: 48px; }
  .elev-bar-track { position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%); height: 6px; background: var(--panel2); border-radius: 3px; }
  .band { position: absolute; top: 0; bottom: 0; background: var(--band); border-radius: 3px; }
  .elev-marker { position: absolute; top: 50%; transform: translate(-50%, -50%); width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--bg); }
  .elev-marker.loc { background: var(--text-strong); }
  .elev-marker.ceil { background: var(--fog); }
  .elev-marker-label { position: absolute; font-size: 0.68rem; white-space: nowrap; color: var(--muted); }
  .elev-marker-label.sweet { top: -16px; transform: translateX(-50%); color: var(--green-text); font-weight: 600; }
  .elev-marker-label.fog { color: var(--fog); }
  .none { text-align: center; font-size: 0.79rem; color: var(--muted); margin-top: 12px; }
  .legend { font-size: 0.75rem; color: var(--muted); margin-top: 8px; }
  .g { color: var(--green-text); }
  .f { color: var(--fog); }
</style>
