<script>
  let { verdict, score } = $props();
</script>

<div class="verdict-banner {verdict.cls}">
  <div class="verdict-emoji">{verdict.emoji}</div>
  <div class="verdict-label">{verdict.label}</div>
  <div class="verdict-score">{score}% inversion likelihood</div>
</div>

<style>
  .verdict-banner { border-radius: 12px; padding: 20px; margin-bottom: 12px; text-align: center; }
  .go    { background: var(--go-bg); border: 1px solid var(--go-border); }
  .try   { background: var(--try-bg); border: 1px solid var(--try-border); }
  .maybe { background: var(--maybe-bg); border: 1px solid var(--maybe-border); }
  .no    { background: var(--no-bg); border: 1px solid var(--no-border); }
  .verdict-emoji { font-size: 2.2rem; margin-bottom: 6px; }
  .verdict-label { font-size: 1.3rem; font-weight: 700; }
  .verdict-score { font-size: 0.88rem; color: var(--muted); margin-top: 4px; }
</style>
