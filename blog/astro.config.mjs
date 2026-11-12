import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// A custom domain later: set site to it and base to '/'.
export default defineConfig({
  site: 'https://pqnghiep1354.github.io',
  base: '/lab-to-prod',
  trailingSlash: 'always',
  integrations: [sitemap()],
  markdown: { shikiConfig: { theme: 'github-dark-dimmed' } },
});
