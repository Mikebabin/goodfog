<script>
  import VerdictBanner from './VerdictBanner.svelte';
  import ElevationBanner from './ElevationBanner.svelte';
  import ElevationBar from './ElevationBar.svelte';
  import TimingCard from './TimingCard.svelte';
  import ConditionsCard from './ConditionsCard.svelte';
  import ShotNotesCard from './ShotNotesCard.svelte';
  import WhyCard from './WhyCard.svelte';

  let { vp, win, result } = $props();
</script>

{#if !result}
  <div class="card"><p class="explanation">No data for this window.</p></div>
{:else}
  <VerdictBanner verdict={result.verdict} score={result.score} />
  <ElevationBanner elevation={result.elevation} />
  <ElevationBar {vp} lclFt={result.lcl_ft} />
  <TimingCard {vp} {win} />
  <ConditionsCard title={`Conditions at ${win.sun_label}`} {result} />
  <ShotNotesCard {vp} />
  <WhyCard explanation={result.explanation} />
{/if}
