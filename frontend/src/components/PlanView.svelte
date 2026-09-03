<script>
  import { fmtTime } from '../lib/time.js';
  import { scoreClass } from '../lib/colors.js';
  import { fmtDrive } from '../lib/drive.js';
  import { bestWindow, planSummary } from '../lib/plan.js';
  import { groupByDay } from '../lib/days.js';
  import ConditionsCard from './ConditionsCard.svelte';

  let { vp, windows, drive = null, onselect = () => {} } = $props();
  const groups = $derived(groupByDay(windows));
  const best = $derived(bestWindow(windows, vp.results));
  const bestResult = $derived(vp.results[best.id] ?? null);
  const halves = [['Sunrise', 'am'], ['Sunset', 'pm']];
  const header = (g) => (g.day === 0 ? 'Today' : g.label);
  const label = (w, r) => `${w.title}, ${r ? `${r.score}%` : 'no data'}`;
</script>

<div class="card">
  <h3>Best Window for {vp.name}</h3>
  {#if drive}
    <p class="drive">🚗 {fmtDrive(drive.seconds)} drive · no traffic</p>
  {/if}
  <div class="grid" style="grid-template-columns: auto repeat({groups.length}, 1fr)">
    <div class="corner"></div>
    {#each groups as g (g.day)}
      <div class="day-head">{header(g)}</div>
    {/each}
    {#each halves as [rowLabel, half] (half)}
      <div class="row-head">{rowLabel}</div>
      {#each groups as g (g.day)}
        {@const w = g[half]}
        {@const r = w ? vp.results[w.id] : null}
        {#if !w}
          <div class="cell empty" aria-hidden="true">—</div>
        {:else}
          <button class="cell" class:best={w.id === best.id} class:outlook={w.outlook} aria-label={label(w, r)} onclick={() => onselect(w.id)}>
            <div class="compare-score {scoreClass(r?.score)}">{r ? `${r.score}%` : '—'}</div>
            <div class="compare-verdict">{r ? `${r.verdict.emoji} ${r.verdict.label}` : ''}</div>
            <div class="when">{fmtTime(w.sun_event)}</div>
            {#if w.outlook}<div class="tag">outlook</div>{/if}
          </button>
        {/if}
      {/each}
    {/each}
  </div>
  <p class="explanation summary">{planSummary(best, bestResult, vp)}</p>
</div>

{#if bestResult}
  <ConditionsCard title={`${best.title} — ${fmtTime(best.sun_event)}`} result={bestResult} />
{/if}

<style>
  .grid { display: grid; gap: 6px; align-items: stretch; }
  .day-head, .row-head { font-size: 0.72rem; color: var(--muted); align-self: center; }
  .day-head { text-align: center; }
  .row-head { padding-right: 4px; }
  .cell { background: var(--bg); border-radius: 8px; padding: 8px 4px; border: 1px solid transparent; text-align: center; color: inherit; font-family: inherit; cursor: pointer; position: relative; min-height: 64px; }
  .cell.best { border-color: var(--green); }
  .cell.outlook { opacity: 0.8; padding-top: 14px; }
  .cell.empty { color: var(--muted); display: flex; align-items: center; justify-content: center; cursor: default; }
  .compare-score { font-size: 1.15rem; font-weight: 700; margin-bottom: 2px; }
  .compare-score.go { color: var(--score-go); }
  .compare-score.try { color: var(--score-try); }
  .compare-score.maybe { color: var(--score-maybe); }
  .compare-score.no { color: var(--score-no); }
  .compare-score.none { color: var(--score-none); }
  .compare-verdict { font-size: 0.66rem; line-height: 1.2; }
  .when { font-size: 0.66rem; color: var(--muted); margin-top: 3px; }
  .tag { position: absolute; top: 3px; right: 4px; font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
  .summary { margin-top: 12px; }
  .drive { font-size: 0.8rem; color: var(--muted); margin: -6px 0 10px; }
</style>
