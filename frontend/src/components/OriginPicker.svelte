<script>
  let { origin, busy = false, error = null, onsubmit, onlocate, onclear } = $props();
  let text = $state('');

  function submit(e) {
    e.preventDefault();
    const q = text.trim();
    if (q && !busy) onsubmit(q);
  }
</script>

<div class="origin">
  {#if origin}
    <div class="resolved">
      <span>From <strong>{origin.label}</strong> · drive times, no traffic</span>
      <button type="button" class="clear" onclick={onclear} aria-label="Clear origin" title="Clear origin">✕</button>
    </div>
  {:else}
    <form class="row" onsubmit={submit}>
      <input
        type="text"
        bind:value={text}
        placeholder="Your address or neighborhood"
        aria-label="Your starting address"
        autocomplete="street-address"
        maxlength="200"
        disabled={busy}
      />
      <button type="submit" disabled={busy || !text.trim()}>Go</button>
      <button type="button" class="locate" onclick={onlocate} disabled={busy} aria-label="Use my location" title="Use my location">📍</button>
    </form>
  {/if}
  {#if busy}<p class="hint">Finding drive times…</p>{/if}
  {#if error}<p class="err" role="alert">{error}</p>{/if}
</div>

<style>
  .origin { margin-bottom: 16px; }
  .row { display: flex; gap: 8px; }
  input { flex: 1; min-width: 0; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; color: var(--text); font: inherit; }
  input:focus { outline: none; border-color: var(--blue); }
  button { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; color: var(--text); font: inherit; cursor: pointer; }
  button:hover:not(:disabled) { border-color: var(--blue); }
  button:disabled { opacity: 0.5; cursor: default; }
  .locate { padding: 10px 12px; }
  .resolved { display: flex; align-items: center; justify-content: space-between; gap: 8px; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; font-size: 0.85rem; }
  .clear { padding: 4px 8px; font-size: 0.8rem; }
  .hint { font-size: 0.78rem; color: var(--muted); margin-top: 6px; }
  .err { font-size: 0.78rem; color: #f85149; margin-top: 6px; }
</style>
