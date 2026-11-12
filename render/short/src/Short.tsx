import { useEffect, useMemo, useState } from 'react';
import { AbsoluteFill, Sequence, continueRender, delayRender, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Scene, ShortProps, Theme } from './types';

// Shorts overlay UI covers roughly the top 200px and the bottom 380px: keep content inside.
const SAFE = { top: 220, bottom: 400, side: 80 };
const FONT_FILES = ['Fraunces', 'Inter', 'SpaceGrotesk', 'JetBrainsMono'];

// JetBrains Mono draws `==` and friends as one glyph; code must read as typed (the Java post is about ==).
const NO_LIGATURES: React.CSSProperties = { fontVariantLigatures: 'none', fontFeatureSettings: '"liga" 0, "calt" 0' };

const useFonts = () => {
  const [handle] = useState(() => delayRender('fonts'));
  useEffect(() => {
    Promise.all(
      FONT_FILES.map((name) => {
        const face = new FontFace(name, `url(${staticFile(`fonts/${name}.woff2`)}) format('woff2')`, { weight: '100 900' });
        return face.load().then((f) => document.fonts.add(f));
      }),
    ).then(() => continueRender(handle));
  }, [handle]);
};

const useEnter = (delay = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 200 } });
  return { opacity: s, transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px)` };
};

const Lines = ({ text, style }: { text: string; style: React.CSSProperties }) => (
  <div style={style}>
    {text.split('\n').map((line, i) => (
      <div key={i} style={useEnter(i * 6)}>
        {line.split(/(==)/).map((part, j) => (part === '==' ? <span key={j} style={{ fontFamily: 'JetBrainsMono', fontWeight: 600, fontSize: '0.8em', ...NO_LIGATURES }}>==</span> : part))}
      </div>
    ))}
  </div>
);

const SceneView = ({ scene, p }: { scene: Scene; p: ShortProps }) => {
  const { theme: t, fonts } = p;
  const display: React.CSSProperties = { fontFamily: fonts.display, fontWeight: 650, color: t.fg, lineHeight: 1.08, letterSpacing: '-0.01em' };
  const enter = useEnter();
  const late = useEnter(14);
  if (scene.type === 'title') return <Lines text={scene.text} style={{ ...display, fontSize: 128 }} />;
  if (scene.type === 'text') {
    return (
      <div>
        <Lines text={scene.text} style={{ ...display, fontSize: 104 }} />
        {scene.note && <div style={{ ...late, marginTop: 48, fontFamily: fonts.body, fontSize: 52, color: t.accent }}>{scene.note}</div>}
      </div>
    );
  }
  if (scene.type === 'code') {
    const longest = Math.max(...scene.code.map((l) => l.replace(/^> /, '').length));
    const size = Math.min(54, Math.floor((1080 - 2 * SAFE.side - 96) / (longest * 0.6)));
    return (
      <div style={{ ...enter, background: t.panel, borderRadius: 28, padding: '56px 48px', border: `2px solid ${t.line}` }}>
        {scene.code.map((line, i) => {
          const hot = line.startsWith('> ');
          return <CodeLine key={i} text={hot ? line.slice(2) : line} color={hot ? t.panel_accent : t.panel_fg} size={size} font={fonts.mono} delay={8 + i * 10} />;
        })}
      </div>
    );
  }
  return (
    <div style={{ ...enter, textAlign: 'center' }}>
      <div style={{ ...display, fontSize: 96, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {p.style.lockup && p.style.mark === 'hexagon' && <Benzene t={t} size={96} />}
        {p.style.lockup && p.style.mark === 'badge' && <Badge size={96 * 0.7 * 1.8 / 0.8} id="outro" style={{ marginRight: 96 * 0.42 }} />}
        {p.style.wordmark === 'arrow' ? (
          <span>Lab <span style={{ color: t.accent }}>→</span> Prod</span>
        ) : p.style.wordmark === 'pill' ? (
          <Pill t={t} />
        ) : (
          <span style={{ fontFamily: fonts.mono, fontWeight: 700, display: 'flex', alignItems: 'center' }}>lab<span style={{ color: t.accent }}>-to-</span>prod<span style={{ display: 'inline-block', width: '0.4em', height: '0.84em', marginLeft: '0.1em', background: t.accent }} /></span>
        )}
      </div>
      <div style={{ marginTop: 40, fontFamily: fonts.body, fontSize: 48, color: t.muted }}>Full note on the blog</div>
    </div>
  );
};

// The brand mark: a benzene ring whose vertices are nodes, one lit (brand/build.py mark_hexagon,
// drawn with the lockup weight). Sized like the logo lockup: about 1.6x the wordmark's cap height.
const Benzene = ({ t, size }: { t: Theme; size: number }) => {
  const pt = (r: number, i: number) => [r * Math.cos(((30 + 60 * i) * Math.PI) / 180), r * Math.sin(((30 + 60 * i) * Math.PI) / 180)];
  const outer = [0, 1, 2, 3, 4, 5].map((i) => pt(36, i));
  const inner = [0, 1, 2, 3, 4, 5].map((i) => pt(36 * 0.6, i));
  const foil = t.foil ?? [t.accent, t.accent, t.accent];
  // Without foil, an accent equal to the ink (the amber theme) would hide the lit node: draw it
  // light with an ink outline instead, as brand/build.py does.
  const inkLit = !t.foil && t.accent.toLowerCase() === t.fg.toLowerCase();
  return (
    <svg viewBox="-50 -50 100 100" width={size * 1.45} height={size * 1.45} style={{ marginRight: size * 0.22, flex: 'none' }} aria-hidden="true">
      <defs>
        <linearGradient id="foil" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={foil[0]} />
          <stop offset="0.5" stopColor={foil[1]} />
          <stop offset="1" stopColor={foil[2]} />
        </linearGradient>
      </defs>
      <polygon points={outer.map((q) => q.join(',')).join(' ')} fill="none" stroke={t.fg} strokeWidth={6} strokeLinejoin="round" />
      {[0, 2, 4].map((i) => (
        <line key={i} x1={inner[i][0]} y1={inner[i][1]} x2={inner[(i + 1) % 6][0]} y2={inner[(i + 1) % 6][1]} stroke={t.fg} strokeWidth={5} />
      ))}
      {outer.slice(0, 5).map((q, i) => <circle key={i} cx={q[0]} cy={q[1]} r={6.2} fill={t.fg} />)}
      {inkLit ? (
        <circle cx={outer[5][0]} cy={outer[5][1]} r={9.6 - 2.5} fill={t.panel_fg} stroke={t.fg} strokeWidth={5} />
      ) : (
        <circle cx={outer[5][0]} cy={outer[5][1]} r={9.6} fill="url(#foil)" />
      )}
    </svg>
  );
};

// brand/build.py BADGE_GOLD: the badge is bright gold in every theme, so black L->P keeps its contrast.
const BADGE_GOLD = ['#E8A600', '#FFF2A6', '#FFCC14'];
const hex = (cx: number, cy: number, r: number) =>
  [0, 1, 2, 3, 4, 5].map((i) => [cx + r * Math.cos(((30 + 60 * i) * Math.PI) / 180), cy + r * Math.sin(((30 + 60 * i) * Math.PI) / 180)]);
const kekule = (cx: number, cy: number, r: number) => {
  const o = hex(cx, cy, r);
  const n = hex(cx, cy, r * 0.62);
  const ring = `M${o.map((q) => q.map((v) => v.toFixed(2)).join(' ')).join('L')}Z`;
  const bonds = [0, 2, 4].map((i) => `M${n[i].map((v) => v.toFixed(2)).join(' ')}L${n[(i + 1) % 6].map((v) => v.toFixed(2)).join(' ')}`).join('');
  return ring + bonds;
};

// The badge mark of brand/build.py (mark_badge): a glossy gold rounded square, a benzene ring pressed
// into it (a deep-gold groove with a pale lip, cut back around the letters), L -> P in black on top.
// `size` is the mark size; the square is 0.8 of it, as in build.py.
export const Badge = ({ size, id, style }: { size: number; id: string; style?: React.CSSProperties }) => {
  const letters = (stroke?: number) => (
    <g fill="#000" stroke={stroke ? '#000' : 'none'} strokeWidth={stroke} strokeLinejoin="round">
      <text x={38} y={50} textAnchor="end" dominantBaseline="central" fontFamily="SpaceGrotesk" fontWeight={700} fontSize={34}>L</text>
      <text x={62} y={50} textAnchor="start" dominantBaseline="central" fontFamily="SpaceGrotesk" fontWeight={700} fontSize={34}>P</text>
      <path d="M41.4 51.2H58.6M49 43.5l9.6 7.7-9.6 7.7" fill="none" stroke="#000" strokeWidth={3 + (stroke ?? 0)} strokeLinecap="round" strokeLinejoin="round" />
    </g>
  );
  return (
    <svg viewBox="0 0 100 100" width={size * 0.8} height={size * 0.8} style={{ overflow: 'visible', flex: 'none', ...style }} aria-hidden="true">
      <defs>
        <linearGradient id={`${id}-gold`} x1="1" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={BADGE_GOLD[0]} />
          <stop offset="0.46" stopColor={BADGE_GOLD[1]} />
          <stop offset="1" stopColor={BADGE_GOLD[2]} />
        </linearGradient>
        <linearGradient id={`${id}-sheen`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity={0.24} />
          <stop offset="0.5" stopColor="#fff" stopOpacity={0} />
        </linearGradient>
        <mask id={`${id}-knock`} maskUnits="userSpaceOnUse" x="0" y="0" width="100" height="100">
          <rect width="100" height="100" fill="#fff" />
          {letters(3.4)}
        </mask>
        <filter id={`${id}-shadow`} x="-30%" y="-30%" width="160%" height="170%">
          <feDropShadow dx="0" dy="2.2" stdDeviation="2.4" floodColor="#000" floodOpacity={0.4} />
        </filter>
      </defs>
      <g transform="translate(-12.5 -12.5) scale(1.25)">
        <rect x="10" y="10" width="80" height="80" rx="17" fill={`url(#${id}-gold)`} filter={`url(#${id}-shadow)`} />
        <rect x="10.35" y="10.35" width="79.3" height="79.3" rx="16.7" fill="none" stroke="rgb(122,82,0)" strokeOpacity={0.47} strokeWidth={0.7} />
        <g mask={`url(#${id}-knock)`} fill="none" strokeWidth={2.4} strokeLinejoin="round">
          <path d={kekule(50.8, 50.8, 30)} stroke="rgb(255,251,222)" strokeOpacity={0.65} />
          <path d={kekule(50, 50, 30)} stroke="rgb(139,92,0)" strokeOpacity={0.5} />
        </g>
        <rect x="10" y="10" width="80" height="80" rx="17" fill={`url(#${id}-sheen)`} />
        {letters()}
      </g>
    </svg>
  );
};

// brand/build.py wordmark_pill: 'Lab' and 'Prod' around a glossy foil pill that carries the arrow.
const Pill = ({ t }: { t: Theme }) => {
  const foil = t.foil ?? [t.panel_accent, t.panel_accent, t.panel_accent];
  return (
    <span style={{ display: 'flex', alignItems: 'center' }}>
      Lab
      <svg viewBox="0 0 125 66" width="1.25em" height="0.66em" style={{ margin: '0.03em 0.22em 0' }} aria-hidden="true">
        <defs>
          <linearGradient id="pill-foil" x1="0.8" y1="0" x2="0.2" y2="1">
            <stop offset="0" stopColor={foil[0]} />
            <stop offset="0.46" stopColor={foil[1]} />
            <stop offset="1" stopColor={foil[2]} />
          </linearGradient>
          <linearGradient id="pill-sheen" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fff" stopOpacity={0.27} />
            <stop offset="0.5" stopColor="#fff" stopOpacity={0} />
          </linearGradient>
        </defs>
        <rect width="125" height="66" rx="33" fill="url(#pill-foil)" />
        <rect width="125" height="66" rx="33" fill="url(#pill-sheen)" />
        <path d="M27.5 33H97.5M73.5 13.8l24 19.2-24 19.2" fill="none" stroke="#0B0B0A" strokeWidth={7.5} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Prod
    </span>
  );
};

// The honeycomb texture of brand/build.py: a faint hexagonal lattice anchored on one foil benzene
// ring at the top right (on the kicker line). It fades out within CLEAR px of the ring and from the
// bottom-left corner, and a clear band runs along the kicker line left of the ring, so it never
// sits behind the kicker, the title, the code or the caption (build.py keeps a halo around text).
// r = 46: the ring's top vertex sits on SAFE.top, clear of the Shorts top bar.
const RING = { r: 46 };
const CLEAR = 420;
const ringAt = () => ({ cx: 1080 - SAFE.side - (Math.sqrt(3) / 2) * RING.r, cy: SAFE.top + RING.r });
const Honeycomb = ({ t }: { t: Theme }) => {
  const { cx, cy } = ringAt();
  const r = RING.r;
  const path = useMemo(() => {
    const dx = Math.sqrt(3) * r;
    const dy = 1.5 * r;
    let d = '';
    for (let row = Math.floor(-cy / dy) - 1; row <= Math.ceil((1920 - cy) / dy) + 1; row++) {
      const shift = row % 2 ? dx / 2 : 0;
      for (let col = Math.floor((-cx - shift) / dx) - 1; col <= Math.ceil((1080 - cx - shift) / dx) + 1; col++) {
        const pts = hex(cx + col * dx + shift, cy + row * dy, r);
        d += `M${pts.map((q) => q.map((v) => v.toFixed(1)).join(' ')).join('L')}Z`;
      }
    }
    return d;
  }, [cx, cy, r]);
  const lum = parseInt(t.bg.slice(1, 3), 16) + parseInt(t.bg.slice(3, 5), 16) + parseInt(t.bg.slice(5, 7), 16);
  const color = lum < 384 ? t.panel_accent : t.accent;
  const mask = `radial-gradient(circle at ${cx}px ${cy}px, #000 0, rgba(0,0,0,0.5) ${CLEAR * 0.45}px, transparent ${CLEAR}px), radial-gradient(circle at 0 1920px, rgba(0,0,0,0.6) 0, transparent 560px)`;
  // The kicker band (its text and the rule under it) stays clear up to just left of the ring. Mask
  // layers add up: everything outside the band, plus the column of the ring.
  const left = cx - (Math.sqrt(3) / 2) * r - 40;
  const band = `linear-gradient(180deg, #000 ${SAFE.top - 24}px, transparent ${SAFE.top - 12}px, transparent ${SAFE.top + 100}px, #000 ${SAFE.top + 112}px), linear-gradient(90deg, transparent ${left - 12}px, #000 ${left}px)`;
  const foil = t.foil ?? [t.accent, t.accent, t.accent];
  return (
    <>
      <div style={{ position: 'absolute', inset: 0, maskImage: band, WebkitMaskImage: band }}>
        <svg width={1080} height={1920} style={{ position: 'absolute', inset: 0, opacity: 0.09, maskImage: mask, WebkitMaskImage: mask }} aria-hidden="true">
          <path d={path} fill="none" stroke={color} strokeWidth={1.4} />
        </svg>
      </div>
      <svg width={1080} height={1920} style={{ position: 'absolute', inset: 0 }} aria-hidden="true">
        <defs>
          <linearGradient id="ring-foil" x1="1" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={foil[0]} />
            <stop offset="0.46" stopColor={foil[1]} />
            <stop offset="1" stopColor={foil[2]} />
          </linearGradient>
        </defs>
        <path d={kekule(cx, cy, r)} fill="none" stroke="url(#ring-foil)" strokeWidth={r * 0.085} strokeLinejoin="round" />
      </svg>
    </>
  );
};

const CodeLine = ({ text, color, size, font, delay }: { text: string; color: string; size: number; font: string; delay: number }) => (
  <div style={{ ...useEnter(delay), fontFamily: font, fontSize: size, fontWeight: 500, color, whiteSpace: 'pre', lineHeight: 1.7, ...NO_LIGATURES }}>{text}</div>
);

const Caption = ({ text, t, font }: { text: string; t: Theme; font: string }) => (
  <div style={{ ...useEnter(4), position: 'absolute', left: SAFE.side, right: SAFE.side, bottom: SAFE.bottom, textAlign: 'center' }}>
    <span style={{ fontFamily: font, fontSize: 44, lineHeight: 1.4, color: t.fg, background: t.panel, padding: '10px 22px', borderRadius: 14, boxDecorationBreak: 'clone', WebkitBoxDecorationBreak: 'clone' }}>{text}</span>
  </div>
);

export const Short = (p: ShortProps) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = p.theme;
  const honey = p.style.texture === 'honeycomb';
  let from = 0;
  return (
    <AbsoluteFill style={{ background: t.bg2 ? `linear-gradient(180deg, ${t.bg} 0%, ${t.bg2} 100%)` : t.bg }}>
      {honey && <Honeycomb t={t} />}
      <div style={{ position: 'absolute', top: SAFE.top, left: SAFE.side, right: honey ? SAFE.side + Math.sqrt(3) * RING.r + 24 : SAFE.side, fontFamily: p.fonts.mono, fontSize: 34, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: t.accent, borderBottom: `2px solid ${t.line}`, paddingBottom: 28 }}>
        {p.kicker}
      </div>
      {p.scenes.map((scene, i) => {
        const frames = Math.round(scene.seconds * fps);
        const seq = (
          <Sequence key={i} from={from} durationInFrames={frames}>
            <AbsoluteFill style={{ justifyContent: 'center', padding: `${SAFE.top + 120}px ${SAFE.side}px ${SAFE.bottom + 260}px` }}>
              <SceneView scene={scene} p={p} />
            </AbsoluteFill>
            <Caption text={scene.say} t={t} font={p.fonts.body} />
          </Sequence>
        );
        from += frames;
        return seq;
      })}
      <div style={{ position: 'absolute', left: SAFE.side, right: SAFE.side, bottom: SAFE.bottom - 70, fontFamily: p.fonts.body, fontSize: 30, color: t.muted, textAlign: 'center' }}>{p.name}</div>
      <div style={{ position: 'absolute', left: 0, bottom: 0, height: 10, width: `${(frame / durationInFrames) * 100}%`, background: t.accent }} />
    </AbsoluteFill>
  );
};
