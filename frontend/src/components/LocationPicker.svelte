<script>
  import { fmtDrive } from '../lib/drive.js';

  let { viewpoints, selectedId, onselect, drives = null } = $props();
</script>

<p class="loc-label">Choose your viewpoint</p>
<div class="loc-grid">
  {#each viewpoints as vp (vp.id)}
    <button class="loc-btn" class:active={vp.id === selectedId} onclick={() => onselect(vp.id)}>
      <div class="loc-name">{vp.name}</div>
      <div class="loc-elev">{vp.desc}</div>
      {#if drives}
        <div class="loc-drive">{drives[vp.id] ? `~${fmtDrive(drives[vp.id].seconds)} drive` : '—'}</div>
      {/if}
    </button>
  {/each}
</div>

<style>
  .loc-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-bottom: 8px; }
  .loc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
  .loc-btn { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; cursor: pointer; text-align: left; transition: all 0.15s; color: var(--text); font: inherit; }
  .loc-btn:hover { border-color: var(--blue); }
  .loc-btn.active { border-color: var(--blue); background: var(--loc-active-bg); }
  .loc-name { font-size: 0.88rem; font-weight: 600; }
  .loc-elev { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }
  .loc-drive { font-size: 0.75rem; color: var(--blue); margin-top: 4px; }
</style>
