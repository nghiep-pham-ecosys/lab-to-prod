import fs from 'node:fs';
import path from 'node:path';
import YAML from 'yaml';

const repoRoot = path.resolve(process.cwd(), '..');
const base = import.meta.env.BASE_URL.replace(/\/$/, '');

/** Prefix an internal path with the site base. */
export const url = (p: string) => `${base}${p.startsWith('/') ? p : `/${p}`}`;

/** Absolute URL for canonical links, feeds and Open Graph. */
export const abs = (p: string, site: URL | undefined) => new URL(url(p), site).toString();

const today = () =>
  new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date());

/** Dated content only appears on or after its day (the site is rebuilt daily). */
export const isLive = (date: Date) =>
  process.env.SHOW_FUTURE === '1' || date.toISOString().slice(0, 10) <= today();

export const fmtDate = (d: Date) =>
  d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

type SeriesInfo = { name: string; pillar: string; kind: 'post' | 'blog' };
const calendar = YAML.parse(fs.readFileSync(path.join(repoRoot, 'content/calendar.yaml'), 'utf8'));
export const SERIES: Record<string, SeriesInfo> = calendar.series;
export const seriesName = (id: string) => SERIES[id]?.name ?? id;

type Theme = Record<'bg' | 'fg' | 'muted' | 'accent' | 'line' | 'panel' | 'panel_fg' | 'panel_accent', string>;
const brand = YAML.parse(fs.readFileSync(path.join(repoRoot, 'brand/brand.yaml'), 'utf8'));
const option = brand.options[brand.selected];
const lum = (hex: string) => parseInt(hex.slice(1, 3), 16) + parseInt(hex.slice(3, 5), 16) + parseInt(hex.slice(5, 7), 16);
const pair: Theme[] = [option.themes[option.primary], option.themes[option.alt]].sort((a, b) => lum(b.bg) - lum(a.bg));
export const BRAND = {
  key: brand.selected as 'a' | 'b',
  fonts: option.fonts as { display: string; body: string; mono: string },
  light: pair[0],
  dark: pair[1],
};
const vars = (t: Theme) => Object.entries(t).map(([k, v]) => `--${k.replaceAll('_', '-')}:${v}`).join(';');
export const themeCss = `:root{${vars(BRAND.light)}}@media (prefers-color-scheme: dark){:root{${vars(BRAND.dark)}}}`;
