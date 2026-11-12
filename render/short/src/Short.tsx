import { useEffect, useState } from 'react';
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
        {p.style.wordmark === 'arrow' ? <span>Lab <span style={{ color: t.accent }}>→</span> Prod</span> : <span style={{ fontFamily: fonts.mono, fontWeight: 700, display: 'flex', alignItems: 'center' }}>lab<span style={{ color: t.accent }}>-to-</span>prod<span style={{ display: 'inline-block', width: '0.4em', height: '0.84em', marginLeft: '0.1em', background: t.accent }} /></span>}
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
  let from = 0;
  return (
    <AbsoluteFill style={{ background: t.bg2 ? `linear-gradient(180deg, ${t.bg} 0%, ${t.bg2} 100%)` : t.bg }}>
      <div style={{ position: 'absolute', top: SAFE.top, left: SAFE.side, right: SAFE.side, fontFamily: p.fonts.mono, fontSize: 34, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: t.accent, borderBottom: `2px solid ${t.line}`, paddingBottom: 28 }}>
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
