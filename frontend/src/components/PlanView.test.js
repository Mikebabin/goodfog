// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import PlanView from './PlanView.svelte';
import { eastPeak, windows, result, resultsFor } from './fixtures.js';

const vpWith = (spec) => ({ ...eastPeak, results: resultsFor(spec) });
const cells = (container) => [...container.querySelectorAll('.cell')];

describe('PlanView grid', () => {
  it('lays out four day columns by two half rows, with a dash for today\'s sunrise', () => {
    const vp = vpWith({ tonight: result({ score: 72 }) });
    const { container } = render(PlanView, { vp, windows });
    const heads = [...container.querySelectorAll('.day-head')].map((h) => h.textContent);
    expect(heads).toEqual(['Today', 'Tomorrow', 'Fri', 'Sat']);
    const rows = [...container.querySelectorAll('.row-head')].map((h) => h.textContent);
    expect(rows).toEqual(['Sunrise', 'Sunset']);
    const all = cells(container);
    expect(all).toHaveLength(8);
    expect(all[0].classList.contains('empty')).toBe(true); // today's sunrise
    expect(all[0].textContent.trim()).toBe('—');
    expect(container.querySelectorAll('button.cell')).toHaveLength(7);
  });

  it('outlines only the best-scoring window cell', () => {
    const vp = vpWith({
      tonight: result({ score: 45 }), d1_am: result({ score: 61 }), d1_pm: result({ score: 78 }),
      d2_am: result({ score: 44 }), d2_pm: result({ score: 55 }), d3_am: result({ score: 30 }), d3_pm: result({ score: 25 }),
    });
    const { container } = render(PlanView, { vp, windows });
    const best = cells(container).filter((c) => c.classList.contains('best'));
    expect(best).toHaveLength(1);
    expect(best[0].getAttribute('aria-label')).toBe('Tomorrow Sunset, 78%');
    expect(best[0].querySelector('.compare-score').textContent).toBe('78%');
  });

  it('marks day 2 and 3 cells as outlook and leaves day 0 and 1 unmarked', () => {
    const vp = vpWith({});
    const { container } = render(PlanView, { vp, windows });
    const buttons = [...container.querySelectorAll('button.cell')];
    expect(buttons.map((b) => b.classList.contains('outlook'))).toEqual([false, false, false, true, true, true, true]);
    expect(container.querySelectorAll('.cell .tag')).toHaveLength(4);
  });

  it('shows a dash and no-data label for a window with no result', () => {
    const vp = vpWith({ tonight: result({ score: 72 }) });
    const { container } = render(PlanView, { vp, windows });
    const d1am = container.querySelector('button.cell[aria-label="Tomorrow Sunrise, no data"]');
    expect(d1am).not.toBeNull();
    expect(d1am.querySelector('.compare-score').textContent).toBe('—');
  });

  it('reports the tapped window id', async () => {
    const onselect = vi.fn();
    const vp = vpWith({ d2_am: result({ score: 50 }) });
    const { container } = render(PlanView, { vp, windows, onselect });
    await fireEvent.click(container.querySelector('button.cell[aria-label="Friday Sunrise, 50%"]'));
    expect(onselect).toHaveBeenCalledWith('d2_am');
  });
});

describe('PlanView summary and cards', () => {
  it('writes the best-bet summary with fog base and viewpoint elevation', () => {
    const vp = vpWith({ tonight: result({ score: 72, lcl_ft: 1394 }), d1_pm: result({ score: 40 }) });
    const { getByText } = render(PlanView, { vp, windows });
    expect(getByText('Best bet: Tonight Sunset at 7:32 PM — 72% likelihood. Fog base ~1,394 ft vs East Peak at 2,571 ft.')).toBeTruthy();
  });

  it('drops the fog-base clause when the best window has no marine layer', () => {
    const vp = vpWith({ tonight: result({ score: 30 }), d1_am: result({ score: 55, lcl_ft: null }) });
    const { getByText } = render(PlanView, { vp, windows });
    expect(getByText('Best bet: Tomorrow Sunrise at 6:48 AM — 55% likelihood.')).toBeTruthy();
  });

  it('writes the no-great-windows summary when every score is under 40', () => {
    const vp = vpWith({ tonight: result({ score: 12 }), d1_am: result({ score: 25 }), d3_pm: result({ score: 39 }) });
    const { getByText } = render(PlanView, { vp, windows });
    expect(getByText(/No great windows in the next three days for East Peak/)).toBeTruthy();
  });

  it('writes the no-great-windows summary when every result is null and still outlines one cell', () => {
    const vp = vpWith({});
    const { container, getByText } = render(PlanView, { vp, windows });
    expect(getByText(/No great windows in the next three days for East Peak/)).toBeTruthy();
    expect(container.querySelectorAll('.cell.best')).toHaveLength(1);
  });

  it('renders exactly one conditions card, for the best window', () => {
    const vp = vpWith({ tonight: result({ score: 72 }), d1_pm: result({ score: 78 }), d2_pm: result({ score: 60 }) });
    const { container, getByText } = render(PlanView, { vp, windows });
    expect(container.querySelectorAll('.card')).toHaveLength(2); // plan card + one conditions card
    expect(getByText('Tomorrow Sunset — 7:30 PM')).toBeTruthy();
  });

  it('renders no conditions card when every result is null', () => {
    const { container } = render(PlanView, { vp: vpWith({}), windows });
    expect(container.querySelectorAll('.card')).toHaveLength(1);
  });

  it('shows the drive line only when a drive is supplied', () => {
    const vp = vpWith({ tonight: result({ score: 72 }) });
    const without = render(PlanView, { vp, windows });
    expect(without.container.querySelector('.drive')).toBeNull();
    const withDrive = render(PlanView, { vp, windows, drive: { seconds: 2700 } });
    expect(withDrive.container.querySelector('.drive').textContent).toContain('drive · no traffic');
  });
});
