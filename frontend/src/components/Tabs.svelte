<script>
  let { tabs, active, onselect } = $props();
</script>

<div class="tabs">
  {#each tabs as t (t.id)}
    <button class="tab" class:active={t.id === active} onclick={() => onselect(t.id)}>{t.label}</button>
  {/each}
</div>

<style>
  .tabs { display: flex; gap: 4px; background: var(--panel); border-radius: 12px; padding: 4px; margin-bottom: 16px; border: 1px solid var(--border); }
  .tab { flex: 1; padding: 8px 2px; border-radius: 8px; border: none; background: transparent; color: var(--muted); font-size: 0.72rem; font-weight: 500; cursor: pointer; transition: all 0.15s; font-family: inherit; }
  .tab.active { background: var(--panel2); color: var(--text-strong); }
</style>
