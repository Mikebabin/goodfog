// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import ElevationBar from './ElevationBar.svelte';
import { barModel } from '../lib/barScale.js';
import { eastPeak } from './fixtures.js';

describe('ElevationBar', () => {
  it('places the fog-base marker and label when there is a marine layer', () => {
    const { container, queryByText } = render(ElevationBar, { vp: eastPeak, lclFt: 1394 });
    const marker = container.querySelector('.elev-marker.ceil');
    expect(marker).not.toBeNull();
    expect(marker.style.left).toBe(`${barModel(eastPeak, 1394).lclPct}%`);
    // The legend also says "fog base", so read the marker's own labels rather than the whole page.
    const labels = [...marker.querySelectorAll('.elev-marker-label.fog')].map((l) => l.textContent);
    expect(labels).toEqual(['🌫️ fog base', '1,394 ft']);
    expect(queryByText(/No marine layer this hour/)).toBeNull();
  });

  it('omits the fog-base marker and explains why when there is no marine layer', () => {
    const { container, getByText } = render(ElevationBar, { vp: eastPeak, lclFt: null });
    expect(container.querySelector('.elev-marker.ceil')).toBeNull();
    expect(container.querySelector('.elev-marker-label.fog')).toBeNull();
    expect(getByText(/No marine layer this hour/)).toBeTruthy();
  });

  it('labels the axis with the barModel maximum, thousands-separated', () => {
    const { maxFt } = barModel(eastPeak, 1394);
    const { container } = render(ElevationBar, { vp: eastPeak, lclFt: 1394 });
    const labels = [...container.querySelectorAll('.axis span')].map((s) => s.textContent);
    expect(labels).toEqual(['0 ft', `${maxFt.toLocaleString('en-US')} ft`]);
    expect(labels[1]).toMatch(/\d,\d{3} ft/);
  });

  it('positions the viewpoint marker and green band from barModel', () => {
    const m = barModel(eastPeak, null);
    const { container, getByText } = render(ElevationBar, { vp: eastPeak, lclFt: null });
    expect(container.querySelector('.elev-marker.loc').style.left).toBe(`${m.locPct}%`);
    const band = container.querySelector('.band');
    expect(band.style.left).toBe(`${m.bandL}%`);
    expect(band.style.width).toBe(`${m.bandW}%`);
    expect(getByText('East Peak')).toBeTruthy();
    expect(getByText('2,571 ft')).toBeTruthy();
  });
});
