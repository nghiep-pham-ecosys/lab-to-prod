import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { SITE } from '../site';
import { url } from '../lib';
import { liveNotes, livePosts } from '../content';

export async function GET(context: APIContext) {
  const items = [
    ...(await livePosts()).map((p) => ({ e: p, link: url(`/posts/${p.id}/`) })),
    ...(await liveNotes()).map((n) => ({ e: n, link: url(`/notes/${n.id}/`) })),
  ].sort((a, b) => +b.e.data.date - +a.e.data.date);
  return rss({
    title: SITE.title,
    description: SITE.description,
    site: new URL(url('/'), context.site).toString(),
    items: items.map(({ e, link }) => ({
      title: e.data.title,
      description: e.data.description,
      pubDate: e.data.date,
      link,
      categories: [e.data.series, ...e.data.tags],
    })),
    customData: '<language>en</language>',
  });
}
