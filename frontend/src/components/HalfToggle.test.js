// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import HalfToggle from './HalfToggle.svelte';
import { groupByDay } from '../lib/days.js';
import { windows } from './fixtures.js';

const groups = groupByDay(windows);

describe('HalfToggle', () => {
  it('renders Sunrise and Sunset for a day with both, marking the active half', () => {
    const { container } = render(HalfToggle, { group: groups[1], active: 'd1_pm', onselect: () => {} });
    const buttons = [...container.querySelectorAll('button')];
    expect(buttons.map((b) => b.textContent.trim())).toEqual(['🌄 Sunrise', '🌇 Sunset']);
    expect(buttons.map((b) => b.getAttribute('aria-selected'))).toEqual(['false', 'true']);
  });

  it('reports the chosen window id', async () => {
    const onselect = vi.fn();
    const { getByText } = render(HalfToggle, { group: groups[2], active: 'd2_pm', onselect });
    await fireEvent.click(getByText('🌄 Sunrise'));
    expect(onselect).toHaveBeenCalledWith('d2_am');
  });

  it('renders nothing for Tonight, which has only a sunset', () => {
    const { container } = render(HalfToggle, { group: groups[0], active: 'tonight', onselect: () => {} });
    expect(container.querySelector('button')).toBeNull();
  });

  it('renders nothing when there is no group (Plan tab)', () => {
    const { container } = render(HalfToggle, { group: null, active: 'plan', onselect: () => {} });
    expect(container.querySelector('button')).toBeNull();
  });
});
