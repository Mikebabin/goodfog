<script>
  let { vp } = $props();
</script>

<div class="card">
  <h3>Shot Notes</h3>
  <div class="timing-row"><span class="timing-label">Composition</span></div>
  <p class="explanation gap">{vp.composition}</p>
  <div class="timing-row"><span class="timing-label">Access</span></div>
  <p class="explanation">{vp.access}</p>
</div>

<style>
  .gap { margin: 2px 0 12px; }
</style>
