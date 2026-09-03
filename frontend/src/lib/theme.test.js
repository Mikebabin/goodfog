/**
 * Theme hygiene. The dark palette lives on bare `:root`; light mode overrides the same
 * tokens under `prefers-color-scheme: light`. These tests keep the two blocks in lockstep
 * and keep raw colours out of component styles so every colour has a light-mode answer.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const css = readFileSync(path.resolve(here, '../app.css'), 'utf8');
const componentsDir = path.resolve(here, '../components');

/** Token names declared inside the first `{...}` that follows `selector`. */
function tokensIn(source, selector) {
  const start = source.indexOf(selector);
  if (start < 0) return null;
  const open = source.indexOf('{', start);
  const close = source.indexOf('}', open);
  return new Set([...source.slice(open, close).matchAll(/--([\w-]+)\s*:/g)].map((m) => m[1]));
}

describe('app.css palettes', () => {
  const dark = tokensIn(css, ':root {');
  const lightBlock = css.slice(css.indexOf('@media (prefers-color-scheme: light)'));
  const light = tokensIn(lightBlock, ':root {');

  it('declares the dark palette on bare :root and a light override block', () => {
    expect(dark?.size).toBeGreaterThan(10);
    expect(light).not.toBeNull();
  });

  it('defines exactly the same tokens in both palettes', () => {
    expect([...light].sort()).toEqual([...dark].sort());
  });

  it('sets color-scheme in both palettes so native controls follow', () => {
    expect(css).toMatch(/:root\s*{[^}]*color-scheme:\s*dark/);
    expect(lightBlock).toMatch(/:root\s*{[^}]*color-scheme:\s*light/);
  });
});

describe('component styles', () => {
  const files = readdirSync(componentsDir).filter((f) => f.endsWith('.svelte'));

  it.each(files)('%s uses tokens, not raw colours, in its <style> block', (file) => {
    const source = readFileSync(path.join(componentsDir, file), 'utf8');
    const style = source.match(/<style>([\s\S]*?)<\/style>/)?.[1] ?? '';
    const raw = style.match(/#[0-9a-fA-F]{3,8}\b|rgba?\(/g) ?? [];
    expect(raw).toEqual([]);
  });

  it('app.css has no raw colours outside the two palette blocks', () => {
    const outside = css
      .replace(/:root\s*{[^}]*}/g, '') // strip both palette blocks
      .match(/#[0-9a-fA-F]{3,8}\b|rgba?\(/g) ?? [];
    expect(outside).toEqual([]);
  });
});
