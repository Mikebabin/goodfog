<script>
  let { group, active, onselect } = $props();
  const both = $derived(Boolean(group?.am && group?.pm));
</script>

{#if both}
  <div class="half" role="tablist" aria-label="Sunrise or sunset">
    <button role="tab" class:active={active === group.am.id} aria-selected={active === group.am.id} onclick={() => onselect(group.am.id)}>🌄 Sunrise</button>
    <button role="tab" class:active={active === group.pm.id} aria-selected={active === group.pm.id} onclick={() => onselect(group.pm.id)}>🌇 Sunset</button>
  </div>
{/if}

<style>
  .half { display: flex; justify-content: center; gap: 4px; margin: -8px 0 12px; }
  button { padding: 5px 14px; border-radius: 999px; border: 1px solid var(--border); background: transparent; color: var(--muted); font-size: 0.74rem; font-weight: 500; cursor: pointer; font-family: inherit; transition: all 0.15s; }
  button.active { background: var(--panel2); color: var(--text-strong); border-color: var(--panel2); }
</style>
