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
  .go    { background: #0d4429; border: 1px solid #238636; }
  .try   { background: #3d2400; border: 1px solid #9e6a03; }
  .maybe { background: #2d1b00; border: 1px solid #7d4e00; }
  .no    { background: #3d0d12; border: 1px solid #8b2020; }
  .verdict-emoji { font-size: 2.2rem; margin-bottom: 6px; }
  .verdict-label { font-size: 1.3rem; font-weight: 700; }
  .verdict-score { font-size: 0.88rem; color: var(--muted); margin-top: 4px; }
</style>
