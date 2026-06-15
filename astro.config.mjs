import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

import cloudflare from "@astrojs/cloudflare";

// Pure static output for Cloudflare Pages.
// /functions directory is auto-detected by Pages and runs independently.
export default defineConfig({
  site: 'https://cl-analysis.com',
  output: 'static',
  integrations: [sitemap()],
  adapter: cloudflare()
});