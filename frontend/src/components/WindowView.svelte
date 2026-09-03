<script>
  import VerdictBanner from './VerdictBanner.svelte';
  import ElevationBanner from './ElevationBanner.svelte';
  import ElevationBar from './ElevationBar.svelte';

  let { vp, win, result } = $props();
</script>

{#if !result}
  <div class="card"><p class="explanation">No data for this window.</p></div>
{:else}
  <VerdictBanner verdict={result.verdict} score={result.score} />
  <ElevationBanner elevation={result.elevation} />
  <ElevationBar {vp} lclFt={result.lcl_ft} />
{/if}
