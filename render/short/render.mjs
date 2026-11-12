#!/usr/bin/env node
// Render short.mp4 (1080x1920) and short.srt for a post folder from its short.json.
//
//   node render/short/render.mjs content/2026-W47/2026-11-16-dsa-p2
//   node render/short/render.mjs <folder> --srt-only
//
// short.json: { title, kicker, theme?, scenes: [{ type: title|code|text|outro, say, seconds, ... }] }
// Every scene has a "say" line: it is burned in as a caption and written to the SRT file.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import YAML from 'yaml';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const args = process.argv.slice(2);
const folder = path.resolve(args.find((a) => !a.startsWith('--')) ?? '');
const srtOnly = args.includes('--srt-only');
const specPath = path.join(folder, 'short.json');
if (!fs.existsSync(specPath)) {
  console.error(`no short.json in ${folder}`);
  process.exit(2);
}
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));

const total = spec.scenes.reduce((sum, s) => sum + s.seconds, 0);
if (total < 30 || total > 60) {
  console.error(`the Short is ${total}s; it must be 30-60s`);
  process.exit(1);
}
for (const [i, s] of spec.scenes.entries()) {
  if (!s.say || !s.say.trim()) {
    console.error(`scene ${i + 1} has no "say" line; every scene needs a caption`);
    process.exit(1);
  }
}

const stamp = (sec) => {
  const ms = Math.round(sec * 1000);
  const p = (n, l = 2) => String(n).padStart(l, '0');
  return `${p(Math.floor(ms / 3600000))}:${p(Math.floor(ms / 60000) % 60)}:${p(Math.floor(ms / 1000) % 60)},${p(ms % 1000, 3)}`;
};
let at = 0;
const srt = spec.scenes
  .map((s, i) => {
    const block = `${i + 1}\n${stamp(at)} --> ${stamp(at + s.seconds - 0.05)}\n${s.say.trim()}\n`;
    at += s.seconds;
    return block;
  })
  .join('\n');
fs.writeFileSync(path.join(folder, 'short.srt'), srt);
console.log(`${path.relative(root, path.join(folder, 'short.srt'))} (${spec.scenes.length} captions, ${total}s)`);
if (srtOnly) process.exit(0);

const brand = YAML.parse(fs.readFileSync(path.join(root, 'brand/brand.yaml'), 'utf8'));
const option = brand.options[brand.selected];
const lum = (hex) => parseInt(hex.slice(1, 3), 16) + parseInt(hex.slice(3, 5), 16) + parseInt(hex.slice(5, 7), 16);
// Videos use the darker of the two main themes unless short.json names one.
const darkest = [option.primary, option.alt].sort((a, b) => lum(option.themes[a].bg) - lum(option.themes[b].bg))[0];
const theme = option.themes[spec.theme ?? darkest];
if (!theme) {
  console.error(`unknown theme ${spec.theme}`);
  process.exit(1);
}
const props = { title: spec.title, kicker: spec.kicker, scenes: spec.scenes, theme, fonts: option.fonts, brandKey: brand.selected, name: brand.name };
const outDir = path.join(here, 'out');
fs.mkdirSync(outDir, { recursive: true });
const propsFile = path.join(outDir, 'props.json');
fs.writeFileSync(propsFile, JSON.stringify(props));

const out = path.join(folder, 'short.mp4');
const res = spawnSync(
  'npx',
  ['remotion', 'render', 'src/index.ts', 'Short', out, `--props=${propsFile}`, `--public-dir=${path.join(root, 'blog/public')}`, '--codec=h264', '--crf=23', '--log=error'],
  { cwd: here, stdio: 'inherit' },
);
if (res.status !== 0) process.exit(res.status ?? 1);
console.log(`${path.relative(root, out)} (${(fs.statSync(out).size / 1e6).toFixed(1)} MB)`);
