<script>
  import { fmtTime } from '../lib/time.js';
  import { scoreColor } from '../lib/colors.js';
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
    {#each groups as g, gi (g.day)}
      <div class="day-head" style="grid-column:{gi + 2}">{header(g)}</div>
    {/each}
    {#each halves as [rowLabel], ri (rowLabel)}
      <div class="row-head" style="grid-row:{ri + 2}">{rowLabel}</div>
    {/each}
    {#each groups as g, gi (g.day)}
      {#each halves as [, half], ri (half)}
        {@const w = g[half]}
        {@const r = w ? vp.results[w.id] : null}
        {#if !w}
          <div class="cell empty" style="grid-column:{gi + 2};grid-row:{ri + 2}" aria-hidden="true">—</div>
        {:else}
          <button
            class="cell"
            style="grid-column:{gi + 2};grid-row:{ri + 2}"
            class:best={w.id === best.id}
            class:outlook={w.outlook}
            aria-label={label(w, r)}
            onclick={() => onselect(w.id)}
          >
            <div class="compare-score" style="color:{scoreColor(r?.score)}">{r ? `${r.score}%` : '—'}</div>
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
  .cell.best { border-color: #238636; }
  .cell.outlook { opacity: 0.8; }
  .cell.empty { color: var(--muted); display: flex; align-items: center; justify-content: center; cursor: default; }
  .compare-score { font-size: 1.15rem; font-weight: 700; margin-bottom: 2px; }
  .compare-verdict { font-size: 0.66rem; line-height: 1.2; }
  .when { font-size: 0.66rem; color: var(--muted); margin-top: 3px; }
  .tag { position: absolute; top: 3px; right: 4px; font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
  .summary { margin-top: 12px; }
  .drive { font-size: 0.8rem; color: var(--muted); margin: -6px 0 10px; }
</style>
