// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import Tabs from './Tabs.svelte';

const tabs = [
  { id: 'day0', label: 'Tonight' }, { id: 'day1', label: 'Tomorrow' },
  { id: 'day2', label: 'Fri' }, { id: 'day3', label: 'Sat' }, { id: 'plan', label: '🔭 Plan' },
];

describe('Tabs', () => {
  it('renders one button per tab in order and marks the active one', () => {
    const { container } = render(Tabs, { tabs, active: 'day2', onselect: () => {} });
    const buttons = [...container.querySelectorAll('button.tab')];
    expect(buttons.map((b) => b.textContent)).toEqual(['Tonight', 'Tomorrow', 'Fri', 'Sat', '🔭 Plan']);
    expect(buttons.filter((b) => b.classList.contains('active')).map((b) => b.textContent)).toEqual(['Fri']);
  });

  it('reports the clicked tab id', async () => {
    const onselect = vi.fn();
    const { getByText } = render(Tabs, { tabs, active: 'day0', onselect });
    await fireEvent.click(getByText('Sat'));
    expect(onselect).toHaveBeenCalledWith('day3');
  });
});
