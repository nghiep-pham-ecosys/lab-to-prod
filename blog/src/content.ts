import { getCollection } from 'astro:content';
import { isLive } from './lib';

const byDateDesc = (a: { data: { date: Date } }, b: { data: { date: Date } }) => +b.data.date - +a.data.date;

export const livePosts = async () =>
  (await getCollection('posts', (p) => !p.data.draft && isLive(p.data.date))).sort(byDateDesc);

export const liveNotes = async () => (await getCollection('notes', (n) => isLive(n.data.date))).sort(byDateDesc);
