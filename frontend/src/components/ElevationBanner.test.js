// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import ElevationBanner from './ElevationBanner.svelte';
import { elevations } from './fixtures.js';

describe('ElevationBanner', () => {
  it.each(Object.entries(elevations))('renders the %s elevation with its class, icon, title, and detail', (cls, elevation) => {
    const { container, getByText } = render(ElevationBanner, { elevation });
    const banner = container.querySelector('.elevation-banner');
    expect(banner.classList.contains(cls)).toBe(true);
    expect(getByText(elevation.icon)).toBeTruthy();
    expect(getByText(elevation.title)).toBeTruthy();
    expect(getByText(elevation.detail)).toBeTruthy();
  });

  it('applies exactly one elevation class', () => {
    const { container } = render(ElevationBanner, { elevation: elevations.edge });
    const banner = container.querySelector('.elevation-banner');
    const applied = ['clear', 'above', 'edge', 'below'].filter((c) => banner.classList.contains(c));
    expect(applied).toEqual(['edge']);
  });
});
