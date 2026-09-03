<script>
  import { DOT_R, frameAspect, landPaths, makeProjection, placeDots } from '../lib/mapModel.js';
  import { textColorFor } from '../lib/colors.js';

  let { coast, viewpoints, selectedId, tab, onselect } = $props();

  let width = $state(360);
  const height = $derived(Math.round(width * frameAspect()));
  const projection = $derived(makeProjection(width, height));
  const land = $derived(landPaths(coast, projection));
  const dots = $derived(placeDots(viewpoints, tab, projection));
  const selected = $derived(dots.find((d) => d.id === selectedId) ?? null);
  const labelX = $derived(selected ? Math.min(Math.max(selected.x, 60), width - 60) : 0);

  function keyselect(e, id) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onselect(id); }
  }
</script>

<div class="wrap" bind:clientWidth={width}>
  <svg viewBox="0 0 {width} {height}" {width} {height} role="img" aria-label="Map of viewpoints colored by inversion likelihood">
    <rect x="0" y="0" {width} {height} class="water" />
    {#each land as d, i (i)}
      <path {d} class="land" />
    {/each}
    {#each dots as dot (dot.id)}
      <g
        class="dot"
        role="button"
        tabindex="0"
        aria-label="{dot.name}, {dot.score == null ? 'no data' : `${dot.score}% likelihood`}"
        onclick={() => onselect(dot.id)}
        onkeydown={(e) => keyselect(e, dot.id)}
      >
        {#if dot.id === selectedId}
          <circle cx={dot.x} cy={dot.y} r={DOT_R + 4} class="ring" />
        {/if}
        <circle cx={dot.x} cy={dot.y} r={DOT_R} fill={dot.color} class="disc" />
        <text x={dot.x} y={dot.y} dy="0.35em" text-anchor="middle" fill={textColorFor(dot.color)} class="score">{dot.score ?? '–'}</text>
      </g>
    {/each}
    {#if selected}
      <text x={labelX} y={selected.y + DOT_R + 14} text-anchor="middle" class="name">{selected.name}</text>
    {/if}
  </svg>
</div>

<style>
  .wrap { margin-bottom: 16px; border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }
  svg { display: block; width: 100%; height: auto; }
  .water { fill: #0b1a2b; }
  .land { fill: var(--panel); stroke: var(--border); stroke-width: 1; }
  .dot { cursor: pointer; outline: none; }
  .dot:focus-visible .disc { stroke: var(--blue); stroke-width: 3; }
  .disc { stroke: var(--bg); stroke-width: 2; }
  .ring { fill: none; stroke: var(--blue); stroke-width: 2; }
  .score { font-size: 0.7rem; font-weight: 700; pointer-events: none; user-select: none; }
  .name { font-size: 0.7rem; font-weight: 600; fill: var(--text-strong); paint-order: stroke; stroke: var(--bg); stroke-width: 3px; pointer-events: none; }
</style>
