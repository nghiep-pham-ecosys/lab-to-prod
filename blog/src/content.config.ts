import fs from 'node:fs';
import path from 'node:path';
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';
import YAML from 'yaml';

// Long articles: markdown files in this folder.
const posts = defineCollection({
  loader: glob({ pattern: '*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string().max(70),
    description: z.string().min(50).max(160),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    series: z.string(),
    part: z.number().int().optional(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

// Short notes: read straight from the post folders in ../content, so a social post and its
// blog note are one file. The note body is the "## linkedin" section.
const contentRoot = path.resolve(process.cwd(), '../content');

function readPostFolder(file: string) {
  const text = fs.readFileSync(file, 'utf8');
  const m = text.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!m) return null;
  const meta = YAML.parse(m[1]) ?? {};
  const sections: Record<string, string> = {};
  let current = '';
  for (const line of m[2].split('\n')) {
    const h = line.match(/^## +([a-z_]+)\s*$/);
    if (h) current = h[1];
    else if (current) sections[current] = `${sections[current] ?? ''}${line}\n`;
  }
  return { meta, sections };
}

const notes = defineCollection({
  loader: {
    name: 'post-folders',
    load: async ({ store, renderMarkdown, parseData, generateDigest }) => {
      store.clear();
      if (!fs.existsSync(contentRoot)) return;
      for (const week of fs.readdirSync(contentRoot).filter((d) => /^\d{4}-W\d{2}$/.test(d)).sort()) {
        for (const folder of fs.readdirSync(path.join(contentRoot, week)).sort()) {
          const file = path.join(contentRoot, week, folder, 'post.md');
          if (!fs.existsSync(file)) continue;
          const post = readPostFolder(file);
          if (!post || !['approved', 'published'].includes(post.meta.status)) continue;
          const lines = (post.sections.linkedin ?? '').trim().split('\n');
          let tags: string[] = [];
          const last = lines[lines.length - 1] ?? '';
          if (/^(#\w+\s*)+$/.test(last.trim())) {
            tags = last.trim().split(/\s+/).map((t) => t.slice(1));
            lines.pop();
          }
          const body = lines.join('\n').trim();
          const firstLine = (body.split(/\n\s*\n/)[0] ?? '').replace(/\s+/g, ' ').trim();
          const data = await parseData({
            id: folder,
            data: {
              title: post.meta.title,
              description: firstLine.length > 157 ? `${firstLine.slice(0, 157).trimEnd()}...` : firstLine,
              date: post.meta.date,
              series: post.meta.series,
              part: post.meta.part,
              sources: post.meta.sources ?? [],
              imageAlt: post.meta.image_alt ?? '',
              hasImage: fs.existsSync(path.join(contentRoot, week, folder, 'image.png')),
              tags,
            },
          });
          store.set({ id: folder, data, body, rendered: await renderMarkdown(body), digest: generateDigest(body + JSON.stringify(data)) });
        }
      }
    },
  },
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.coerce.date(),
    series: z.string(),
    part: z.number().int(),
    sources: z.array(z.string()).default([]),
    imageAlt: z.string().default(''),
    hasImage: z.boolean().default(false),
    tags: z.array(z.string()).default([]),
  }),
});

export const collections = { posts, notes };
