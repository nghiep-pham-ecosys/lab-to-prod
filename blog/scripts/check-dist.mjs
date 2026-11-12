// Smoke test of the built site: run after `astro build`.
import fs from 'node:fs';
import path from 'node:path';

const dist = path.resolve('dist');
const base = '/lab-to-prod';
const fail = [];
const need = (cond, msg) => { if (!cond) fail.push(msg); };
const read = (p) => fs.readFileSync(path.join(dist, p), 'utf8');

for (const p of ['index.html', 'notes/index.html', 'posts/index.html', 'series/index.html', 'about/index.html',
  '404.html', 'rss.xml', 'sitemap-index.xml', 'robots.txt', 'og/default.png', 'favicon.png']) {
  need(fs.existsSync(path.join(dist, p)), `missing ${p}`);
}

const pages = [];
(function walk(dir) {
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, f.name);
    if (f.isDirectory()) walk(p);
    else if (f.name.endsWith('.html')) pages.push(p);
  }
})(dist);

for (const page of pages) {
  const html = fs.readFileSync(page, 'utf8');
  const rel = path.relative(dist, page);
  need(/<title>[^<]{10,}<\/title>/.test(html), `${rel}: no title`);
  need(/<meta name="description" content="[^"]{50,}"/.test(html), `${rel}: description missing or too short`);
  need(html.includes('rel="canonical"'), `${rel}: no canonical link`);
  need(html.includes('property="og:image"'), `${rel}: no og:image`);
  for (const [, href] of html.matchAll(/(?:href|src)="(\/[^"#?]*)/g)) {
    if (!href.startsWith(`${base}/`)) { fail.push(`${rel}: link ${href} is outside the base path`); continue; }
    const target = path.join(dist, href.slice(base.length));
    const ok = fs.existsSync(target) && (fs.statSync(target).isFile() || fs.existsSync(path.join(target, 'index.html')));
    need(ok, `${rel}: broken link ${href}`);
  }
  for (const [, img] of html.matchAll(/property="og:image" content="https?:\/\/[^/]+([^"]+)"/g)) {
    need(fs.existsSync(path.join(dist, img.slice(base.length))), `${rel}: og:image ${img} does not exist`);
  }
}

const articles = pages.filter((p) => /dist\/posts\/[^/]+\/index\.html$/.test(p));
need(articles.length >= 1, 'no article page was built');
for (const a of articles) {
  const html = fs.readFileSync(a, 'utf8');
  need(html.includes('"@type":"Article"'), `${path.relative(dist, a)}: no Article structured data`);
}
need(read('rss.xml').includes('<item>'), 'rss.xml has no items');
need(read('robots.txt').includes('sitemap-index.xml'), 'robots.txt does not point to the sitemap');

if (fail.length) {
  console.error(fail.map((f) => `FAIL ${f}`).join('\n'));
  process.exit(1);
}
console.log(`dist ok: ${pages.length} pages, ${articles.length} article(s)`);
