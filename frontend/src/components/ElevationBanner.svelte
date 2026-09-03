<script>
  let { elevation } = $props();
</script>

<div class="elevation-banner {elevation.cls}">
  <div class="elev-icon">{elevation.icon}</div>
  <div class="elev-body">
    <div class="elev-title">{elevation.title}</div>
    <div class="elev-detail">{elevation.detail}</div>
  </div>
</div>

<style>
  .elevation-banner { border-radius: 10px; padding: 14px 16px; margin-bottom: 12px; display: flex; align-items: flex-start; gap: 12px; }
  .above { background: var(--above-bg); border: 1px solid var(--above-border); }
  .edge  { background: var(--edge-bg); border: 1px solid var(--edge-border); }
  .below { background: var(--below-bg); border: 1px solid var(--below-border); }
  .clear { background: var(--panel); border: 1px solid var(--border); }
  .elev-icon { font-size: 1.6rem; flex-shrink: 0; }
  .elev-body { flex: 1; }
  .elev-title { font-size: 0.9rem; font-weight: 700; margin-bottom: 4px; }
  .elev-detail { font-size: 0.8rem; color: var(--muted); line-height: 1.5; }
</style>
