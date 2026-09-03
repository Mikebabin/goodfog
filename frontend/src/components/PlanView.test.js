// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import PlanView from './PlanView.svelte';
import { eastPeak, windows, result } from './fixtures.js';

const vpWith = (results) => ({ ...eastPeak, results });

describe('PlanView', () => {
  it('outlines only the best-scoring window column', () => {
    const vp = vpWith({
      tonight: result({ score: 45 }),
      tomorrow_am: result({ score: 78 }),
      tomorrow_pm: result({ score: 60 }),
    });
    const { container } = render(PlanView, { vp, windows });
    const cols = [...container.querySelectorAll('.compare-col')];
    expect(cols).toHaveLength(3);
    const best = cols.filter((c) => c.classList.contains('best'));
    expect(best).toHaveLength(1);
    expect(best[0].querySelector('h4').textContent).toBe('Tomorrow AM');
    expect(best[0].querySelector('.compare-score').textContent).toBe('78%');
  });

  it('writes the best-bet summary with fog base and viewpoint elevation', () => {
    const vp = vpWith({
      tonight: result({ score: 72, lcl_ft: 1394 }),
      tomorrow_am: null,
      tomorrow_pm: result({ score: 40 }),
    });
    const { getByText } = render(PlanView, { vp, windows });
    expect(getByText('Best bet: Tonight at 7:32 PM — 72% likelihood. Fog base ~1,394 ft vs East Peak at 2,571 ft.')).toBeTruthy();
  });

  it('writes the no-great-windows summary when every score is under 40', () => {
    const vp = vpWith({
      tonight: result({ score: 12 }),
      tomorrow_am: result({ score: 25 }),
      tomorrow_pm: result({ score: 39 }),
    });
    const { getByText } = render(PlanView, { vp, windows });
    expect(getByText(/No great windows in the next two days for East Peak/)).toBeTruthy();
  });

  it('shows a dash for a window with no result and skips its conditions card', () => {
    const vp = vpWith({ tonight: result({ score: 72 }), tomorrow_am: null, tomorrow_pm: null });
    const { container } = render(PlanView, { vp, windows });
    const scores = [...container.querySelectorAll('.compare-score')].map((s) => s.textContent);
    expect(scores).toEqual(['72%', '—', '—']);
    expect(container.querySelectorAll('.card')).toHaveLength(2); // plan card + one conditions card
  });

  it('shows the drive line only when a drive is supplied', () => {
    const vp = vpWith({ tonight: result({ score: 72 }), tomorrow_am: null, tomorrow_pm: null });
    const without = render(PlanView, { vp, windows });
    expect(without.container.querySelector('.drive')).toBeNull();
    const withDrive = render(PlanView, { vp, windows, drive: { seconds: 2700 } });
    expect(withDrive.container.querySelector('.drive').textContent).toContain('drive · no traffic');
  });
});
