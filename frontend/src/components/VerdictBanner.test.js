// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import VerdictBanner from './VerdictBanner.svelte';
import { verdicts } from './fixtures.js';

describe('VerdictBanner', () => {
  it.each(Object.entries(verdicts))('renders the %s verdict with its class, emoji, label, and score', (cls, verdict) => {
    const { container, getByText } = render(VerdictBanner, { verdict, score: 72 });
    const banner = container.querySelector('.verdict-banner');
    expect(banner.classList.contains(cls)).toBe(true);
    expect(getByText(verdict.emoji)).toBeTruthy();
    expect(getByText(verdict.label)).toBeTruthy();
    expect(getByText('72% inversion likelihood')).toBeTruthy();
  });

  it('applies exactly one verdict class', () => {
    const { container } = render(VerdictBanner, { verdict: verdicts.no, score: 12 });
    const banner = container.querySelector('.verdict-banner');
    const applied = ['go', 'try', 'maybe', 'no'].filter((c) => banner.classList.contains(c));
    expect(applied).toEqual(['no']);
  });
});
