<script>
  import { fmtTime } from '../lib/time.js';
  import { scoreColor } from '../lib/colors.js';
  import { fmtDrive } from '../lib/drive.js';
  import { bestWindow, planSummary } from '../lib/plan.js';
  import ConditionsCard from './ConditionsCard.svelte';

  let { vp, windows, drive = null } = $props();
  const best = $derived(bestWindow(windows, vp.results));
</script>

<div class="card">
  <h3>Best Window for {vp.name}</h3>
  {#if drive}
    <p class="drive">🚗 {fmtDrive(drive.seconds)} drive · no traffic</p>
  {/if}
  <div class="compare-grid">
    {#each windows as w (w.id)}
      {@const r = vp.results[w.id]}
      <div class="compare-col" class:best={w.id === best.id}>
        <h4>{w.tab}</h4>
        <div class="compare-score" style="color:{scoreColor(r?.score)}">{r ? `${r.score}%` : '—'}</div>
        <div class="compare-verdict">{r ? `${r.verdict.emoji} ${r.verdict.label}` : ''}</div>
        <div class="when">{fmtTime(w.sun_event)}</div>
      </div>
    {/each}
  </div>
  <p class="explanation summary">{planSummary(best, vp.results[best.id], vp)}</p>
</div>

{#each windows as w (w.id)}
  {#if vp.results[w.id]}
    <ConditionsCard title={`${w.tab} — ${fmtTime(w.sun_event)}`} result={vp.results[w.id]} />
  {/if}
{/each}

<style>
  .compare-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .compare-col { background: var(--bg); border-radius: 8px; padding: 12px; border: 1px solid transparent; }
  .compare-col.best { border-color: #238636; }
  .compare-col h4 { font-size: 0.78rem; color: var(--muted); margin-bottom: 8px; }
  .compare-score { font-size: 1.7rem; font-weight: 700; margin-bottom: 4px; }
  .compare-verdict { font-size: 0.75rem; }
  .when { font-size: 0.7rem; color: var(--muted); margin-top: 4px; }
  .summary { margin-top: 12px; }
  .drive { font-size: 0.8rem; color: var(--muted); margin: -6px 0 10px; }
</style>
