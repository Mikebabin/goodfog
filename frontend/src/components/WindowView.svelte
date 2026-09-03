<script>
  import VerdictBanner from './VerdictBanner.svelte';
  import ElevationBanner from './ElevationBanner.svelte';
  import ElevationBar from './ElevationBar.svelte';
  import TimingCard from './TimingCard.svelte';
  import ConditionsCard from './ConditionsCard.svelte';
  import ShotNotesCard from './ShotNotesCard.svelte';
  import WhyCard from './WhyCard.svelte';

  let { vp, win, result, drive = null } = $props();
</script>

{#if !result}
  <div class="card"><p class="explanation">No data for this window.</p></div>
{:else}
  <VerdictBanner verdict={result.verdict} score={result.score} />
  {#if win.outlook}
    <p class="outlook">Outlook · 2+ days out, lower confidence</p>
  {/if}
  <ElevationBanner elevation={result.elevation} />
  <ElevationBar {vp} lclFt={result.lcl_ft} />
  <TimingCard {vp} {win} {drive} />
  <ConditionsCard title={`Conditions at ${win.sun_label}`} {result} />
  <ShotNotesCard {vp} />
  <WhyCard explanation={result.explanation} />
{/if}

<style>
  .outlook { text-align: center; font-size: 0.75rem; color: var(--muted); margin: -6px 0 12px; }
</style>
