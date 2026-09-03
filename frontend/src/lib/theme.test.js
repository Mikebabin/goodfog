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
const stripComments = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '');
const css = stripComments(readFileSync(path.resolve(here, '../app.css'), 'utf8'));
const componentsDir = path.resolve(here, '../components');

/** Token names declared inside the first `:root { ... }` block at or after `from`. */
function tokensIn(source, from = 0) {
  const m = /:root\s*{/.exec(source.slice(from));
  if (!m) return null;
  const open = from + m.index + m[0].length - 1;
  const close = source.indexOf('}', open);
  return new Set([...source.slice(open, close).matchAll(/--([\w-]+)\s*:/g)].map((m) => m[1]));
}

/**
 * Raw colours in a style body: hex, rgb()/hsl(), or a CSS colour keyword used as a value.
 * Known limit: an `#id` selector made of hex digits would be flagged too; there are none.
 */
// Hyphen-aware boundaries so `white-space` and `--green-text` never match.
const KEYWORDS = /(?<![\w-])(white|black|red|green|blue|yellow|orange|gray|grey|silver|purple|pink|brown|navy|teal|aqua|lime|maroon|olive|gold|crimson|ivory|beige|tan|salmon|coral|khaki|magenta|cyan|violet|indigo)(?![\w-])/g;
function rawColours(style) {
  const body = stripComments(style).replace(/var\(--[\w-]+\)/g, 'var()');
  return [...(body.match(/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/g) ?? []), ...(body.match(KEYWORDS) ?? [])];
}

describe('app.css palettes', () => {
  const dark = tokensIn(css);
  const lightBlock = css.slice(css.indexOf('@media (prefers-color-scheme: light)'));
  const light = tokensIn(lightBlock);

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
    expect(rawColours(style)).toEqual([]);
  });

  it('app.css has no raw colours outside the two palette blocks', () => {
    const outside = css.replace(/:root\s*{[^}]*}/g, ''); // strip both palette blocks
    expect(rawColours(outside)).toEqual([]);
  });
});
