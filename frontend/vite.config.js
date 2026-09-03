import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { VitePWA } from 'vite-plugin-pwa';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(fs.readFileSync(path.resolve(here, 'package.json'), 'utf8'));

export default defineConfig({
  // Footer build label; VITE_COMMIT is set by frontend/Dockerfile from Coolify's SOURCE_COMMIT.
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  plugins: [
    svelte(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'Good Fog',
        short_name: 'Good Fog',
        description: 'Will you be above the marine layer or inside it?',
        theme_color: '#0d1117',
        background_color: '#0d1117',
        display: 'standalone',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname === '/api/snapshot',
            handler: 'NetworkFirst',
            options: { cacheName: 'snapshot', networkTimeoutSeconds: 8, expiration: { maxEntries: 1 } },
          },
        ],
      },
    }),
  ],
  resolve: { alias: { '@data': path.resolve(here, '../data') } },
  server: {
    fs: { allow: [path.resolve(here, '..')] },
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: { environment: 'node', include: ['src/**/*.test.js'] },
});
