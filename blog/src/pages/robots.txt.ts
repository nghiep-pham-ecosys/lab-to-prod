import type { APIContext } from 'astro';
import { url } from '../lib';

export function GET(context: APIContext) {
  const sitemap = new URL(url('/sitemap-index.xml'), context.site).toString();
  return new Response(`User-agent: *\nAllow: /\n\nSitemap: ${sitemap}\n`);
}
