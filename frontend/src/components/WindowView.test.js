// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import WindowView from './WindowView.svelte';
import { eastPeak, windows, result } from './fixtures.js';

const OUTLOOK = 'Outlook · 2+ days out, lower confidence';

describe('WindowView', () => {
  it('shows the outlook line for a day-2 window, right after the verdict banner', () => {
    const win = windows.find((w) => w.id === 'd2_pm');
    const { container, getByText } = render(WindowView, { vp: eastPeak, win, result: result({ score: 72 }) });
    expect(getByText(OUTLOOK)).toBeTruthy();
    expect(container.querySelector('.verdict-banner + .outlook')).not.toBeNull();
  });

  it('shows no outlook line for tomorrow', () => {
    const win = windows.find((w) => w.id === 'd1_pm');
    const { queryByText } = render(WindowView, { vp: eastPeak, win, result: result({ score: 72 }) });
    expect(queryByText(OUTLOOK)).toBeNull();
  });

  it('shows the no-data card and no outlook line when the result is null', () => {
    const win = windows.find((w) => w.id === 'd3_am');
    const { getByText, queryByText } = render(WindowView, { vp: eastPeak, win, result: null });
    expect(getByText('No data for this window.')).toBeTruthy();
    expect(queryByText(OUTLOOK)).toBeNull();
  });
});
