<script>
  import { fmtTime } from '../lib/time.js';
  import { fmtDrive, leaveBy } from '../lib/drive.js';

  let { vp, win, drive = null } = $props();
  const isDawn = $derived(win.sun_label === 'Sunrise');
  const leave = $derived(drive ? leaveBy(win.arrive_by, drive.seconds) : null);
</script>

<div class="card">
  <h3>{win.title} Timing</h3>
  <div class="timing-row"><span class="timing-label">{win.sun_label}</span><span class="timing-value">{fmtTime(win.sun_event)}</span></div>
  <div class="timing-row"><span class="timing-label">Arrive by</span><span class="timing-value">{fmtTime(win.arrive_by)}</span></div>
  {#if drive && leave}
    <div class="timing-row"><span class="timing-label">Drive</span><span class="timing-value muted">{fmtDrive(drive.seconds)} · no traffic</span></div>
    <div class="timing-row"><span class="timing-label">Leave by</span><span class="timing-value">{fmtTime(leave)}</span></div>
  {/if}
  {#if isDawn && vp.dawn_gated}
    <div class="timing-row gate">
      <span class="timing-label warn">⚠ Gate</span>
      <span class="timing-value warn small">Summit road opens 7am — sunrise not viable</span>
    </div>
  {/if}
</div>

<style>
  .gate { border-top: 1px solid var(--panel2); }
  .warn { color: var(--warn); }
  .small { font-size: 0.8rem; text-align: right; }
  .muted { color: var(--muted); font-weight: 500; }
</style>
