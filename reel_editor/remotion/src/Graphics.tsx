import React from 'react';
import {AbsoluteFill, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {icons as LUCIDE} from 'lucide-react';
import type {RGraphic, RIcon} from './types';
import {useTheme} from './theme';
import {BESPOKE} from './bespoke';
import {NEWS_SERIF} from './fonts';
import {BACK_OUT, CanvasBackdrop, DrawLine, EXPO_IN, Kinetic, Mask, ease, useDrift, useInOut} from './motion';

type G<T extends RGraphic['type']> = Extract<RGraphic, {type: T}> & {dur: number};

const Region: React.FC<{pos?: RGraphic['pos']; children: React.ReactNode; style?: React.CSSProperties}> = ({pos = 'center', children, style}) => {
  const ad = useTheme().placement === 'meta-ad';
  return (
  <AbsoluteFill
    style={{
      justifyContent: pos === 'top' ? 'flex-start' : pos === 'bottom' ? 'flex-end' : 'center',
      alignItems: 'center',
      // 'canvas' = the free area above the docked speaker window
      ...(pos === 'canvas' ? {height: ad ? '38%' : '47%', bottom: 'auto'} : {}),
      paddingTop: pos === 'top' ? (ad ? '15%' : '12%') : pos === 'canvas' ? (ad ? '16.5%' : '7%') : 0,
      paddingBottom: pos === 'bottom' ? '34%' : pos === 'center' ? '6%' : 0,
      paddingLeft: 40,
      paddingRight: 150, // keep clear of Instagram's action rail
      ...style,
    }}
  >
    <div style={{transform: ad && pos === 'canvas' ? 'scale(0.9)' : undefined, transformOrigin: 'top center'}}>{children}</div>
  </AbsoluteFill>
  );
};

/** Card that unfolds from its left edge (clip-path) with a drawing accent spine, and folds away on exit. */
const Panel: React.FC<{start: number; end: number; children: React.ReactNode; style?: React.CSSProperties; accent?: boolean; paper?: boolean}> = ({start, end, children, style, accent, paper}) => {
  const t = useTheme();
  const isPaper = paper && !!t.colors.paper;
  const frame = useCurrentFrame();
  const open = ease(frame, [start, start + 16], [0, 1]);
  const close = ease(frame, [end - 10, end], [0, 1], EXPO_IN);
  const clip = `inset(0 ${(1 - open) * 100}% 0 ${close * 100}% round ${t.radius.card}px)`;
  return (
    <div style={{...t.cardStyle, position: 'relative', clipPath: clip, borderColor: accent && !isPaper ? t.colors.accent : t.colors.border,
      ...(isPaper ? {background: t.colors.paper, border: 'none', color: t.colors.onPaper} : {}), ...style}}>
      <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: isPaper ? 6 : 4, background: isPaper ? t.colors.onPaper : t.colors.accent, transform: `scaleY(${open})`, transformOrigin: 'top'}} />
      {children}
    </div>
  );
};

// Lucide icon; with `draw` (0..1) its strokes draw on like a pen.
export const LineIcon: React.FC<{name: string; size: number; color: string; stroke?: number; draw?: number}> = ({name, size, color, stroke = 1.5, draw}) => {
  const key = name.replace(/(^|-)(\w)/g, (_, __, c: string) => c.toUpperCase());
  const Icon = (LUCIDE as Record<string, React.FC<{size: number; color: string; strokeWidth: number}>>)[key];
  if (!Icon) return null;
  const id = `ic${key}${Math.round((draw ?? 1) * 100)}`;
  return (
    <span className={id} style={{display: 'inline-flex'}}>
      {draw !== undefined && <style>{`.${id} svg * { stroke-dasharray: 90; stroke-dashoffset: ${90 * (1 - draw)}; }`}</style>}
      <Icon size={size} color={color} strokeWidth={stroke} />
    </span>
  );
};

// ---------------------------------------------------------------- slam: kinetic type on the brand grid

const Slam: React.FC<{g: G<'slam'>}> = ({g}) => {
  const t = useTheme();
  const {frame} = useInOut(g.dur);
  const drift = useDrift(1.2);
  const last = g.words.length - 1;
  const wipe = ease(frame, [g.dur - 12, g.dur], [0, 1], EXPO_IN); // card lifts away bottom-up
  return (
    <AbsoluteFill style={{background: g.bg ?? t.colors.bg, clipPath: `inset(0 0 ${wipe * 100}% 0)`}}>
      <CanvasBackdrop start={0} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'flex-start', paddingLeft: 80, paddingRight: 170}}>
        <div style={{...drift, transformOrigin: 'left center'}}>
          {g.words.map((w, i) => (
            <div key={i} style={{fontFamily: t.display, fontWeight: t.weights.display, letterSpacing: '-0.055em', fontSize: w.text.length > 7 ? 132 : 172, lineHeight: 0.98, textTransform: 'uppercase', color: i === last ? g.color ?? t.colors.accent : t.colors.text}}>
              <Mask start={w.at - 3} len={14}>{w.text}</Mask>
            </div>
          ))}
          <DrawLine start={g.words[last].at + 6} width={260} height={10} style={{marginTop: 26}} />
        </div>
      </AbsoluteFill>
      {wipe > 0 && <div style={{position: 'absolute', left: 0, right: 0, bottom: `${wipe * 100}%`, height: 8, background: t.colors.accent}} />}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- flow: steps joined by drawing connectors

const Flow: React.FC<{g: G<'flow'>}> = ({g}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const drift = useDrift(0.6);
  return (
    <Region pos={g.pos ?? 'top'}>
      <div style={{width: 680, ...drift, transform: `${drift.transform} scale(${g.pos === 'canvas' ? 1.16 : 1})`, transformOrigin: 'top center'}}>
        {g.title && (
          <div style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 28, letterSpacing: '0.2em', textTransform: 'uppercase', color: t.colors.accent, marginBottom: 18}}>
            <Kinetic text={g.title} start={0} end={g.dur} stagger={2} />
          </div>
        )}
        {g.items.map((it, i) => {
          const on = frame >= it.at;
          const pop = spring({frame: frame - it.at, fps, config: {damping: 14, mass: 0.6}});
          const lineP = ease(frame, [it.at - 8, it.at + 2], [0, 1]);
          const isLast = i === g.items.length - 1;
          const out = ease(frame, [g.dur - 10, g.dur], [0, 1], EXPO_IN);
          return (
            <div key={i} style={{opacity: 1 - out}}>
              {i > 0 && (
                <div style={{marginLeft: 35, height: 34, width: 4, background: t.colors.border, position: 'relative', overflow: 'hidden', opacity: frame < it.at - 10 ? 0 : 1}}>
                  <div style={{position: 'absolute', inset: 0, background: t.colors.accent, transform: `scaleY(${lineP})`, transformOrigin: 'top'}} />
                </div>
              )}
              <div style={{display: 'flex', alignItems: 'center', gap: 22, opacity: frame < it.at - 10 ? 0 : 1}}>
                <div style={{width: 74, height: 74, borderRadius: 37, flex: 'none', background: on && isLast ? t.colors.accent : t.colors.card,
                  border: `3px solid ${on ? t.colors.accent : t.colors.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${0.6 + 0.4 * pop})`}}>
                  {it.icon ? (
                    <LineIcon name={it.icon} size={38} color={on && isLast ? t.colors.onAccent : on ? t.colors.accent : t.colors.muted} stroke={2} draw={ease(frame, [it.at, it.at + 18], [0, 1])} />
                  ) : (
                    <span style={{fontFamily: t.display, fontWeight: 800, fontSize: 30, color: on && isLast ? t.colors.onAccent : t.colors.text}}>{i + 1}</span>
                  )}
                </div>
                <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: 58, letterSpacing: '-0.035em', color: on ? t.colors.text : t.colors.muted}}>
                  <Mask start={it.at - 2} len={14}>{it.text}</Mask>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Region>
  );
};

// ---------------------------------------------------------------- checklist (unfolding card, drawn ticks)

const Check: React.FC<{done: number}> = ({done}) => {
  const t = useTheme();
  return (
    <svg width={56} height={56} viewBox="0 0 64 64" style={{flex: 'none'}}>
      <circle cx={32} cy={32} r={28} fill={t.colors.accent} fillOpacity={done} stroke={done > 0 ? t.colors.accent : t.colors.border} strokeWidth={4} />
      <path d="M20 33 l8 8 l16 -18" fill="none" stroke={t.colors.onAccent} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={40} strokeDashoffset={40 * (1 - done)} />
    </svg>
  );
};

const Checklist: React.FC<{g: G<'checklist'>}> = ({g}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  return (
    <Region pos={g.pos}>
      <Panel start={0} end={g.dur} style={{width: 840, padding: '40px 48px'}}>
        {g.title && (
          <div style={{fontFamily: t.display, fontWeight: t.weights.headline, fontSize: 50, letterSpacing: '-0.03em', color: t.colors.text, marginBottom: 18}}>
            <Kinetic text={g.title} start={6} />
          </div>
        )}
        {g.items.map((it, i) => {
          const done = ease(frame, [it.at + 4, it.at + 14], [0, 1]);
          return (
            <div key={i} style={{display: 'flex', alignItems: 'center', gap: 22, margin: '14px 0', opacity: frame >= it.at - 4 ? 1 : 0.25}}>
              <Check done={done} />
              <div style={{fontFamily: t.display, fontWeight: t.weights.sub, fontSize: 44, color: done > 0.5 ? t.colors.text : t.colors.muted}}>
                <Mask start={it.at - 4}>{it.text}</Mask>
              </div>
            </div>
          );
        })}
      </Panel>
    </Region>
  );
};

// ---------------------------------------------------------------- compare: panels unfold, lines strike through

const Compare: React.FC<{g: G<'compare'>}> = ({g}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const drift = useDrift(0.5);
  const vs = spring({frame: frame - 14, fps, config: {damping: 11, mass: 0.6}});
  const col = (good: boolean) => {
    const data = good ? g.right : g.left;
    const s0 = good ? 10 : 0;
    return (
      <Panel start={s0} end={g.dur} accent={good} paper={good && t.canvas === 'lit'} style={{flex: 1, padding: '30px 28px'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 10, fontFamily: t.display, fontWeight: t.weights.display, letterSpacing: '-0.035em', fontSize: 46, color: good ? (t.canvas === 'lit' ? t.colors.onPaper ?? '#0A0A0A' : t.colors.accent) : t.colors.muted, marginBottom: 14}}>
          <LineIcon name={good ? 'check' : 'x'} size={40} color={good ? (t.canvas === 'lit' ? t.colors.onPaper ?? '#0A0A0A' : t.colors.accent) : t.colors.muted} stroke={2.5} draw={ease(frame, [s0 + 8, s0 + 22], [0, 1])} />
          <Mask start={s0 + 6}>{data.title}</Mask>
        </div>
        {data.items.map((it, i) => {
          const at = s0 + 14 + i * 6;
          const strike = good ? 0 : ease(frame, [at + 10, at + 20], [0, 1]);
          return (
            <div key={i} style={{position: 'relative', fontFamily: t.body, fontWeight: 600, fontSize: 36, color: good ? (t.canvas === 'lit' ? t.colors.onPaper : t.colors.text) : t.colors.muted, margin: '12px 0'}}>
              <Mask start={at}>{it}</Mask>
              {!good && <div style={{position: 'absolute', left: 0, top: '54%', height: 3, width: '100%', background: t.colors.muted, transform: `scaleX(${strike})`, transformOrigin: 'left'}} />}
            </div>
          );
        })}
      </Panel>
    );
  };
  return (
    <Region pos={g.pos}>
      <div style={{position: 'relative', display: 'flex', gap: 18, width: 860, ...drift}}>
        {col(false)}
        {col(true)}
        <div style={{position: 'absolute', left: '50%', top: 30, transform: `translateX(-50%) scale(${vs * (1 - ease(frame, [g.dur - 10, g.dur], [0, 1], EXPO_IN))})`, width: 84, height: 84, borderRadius: 42, background: t.colors.bg, border: `2px solid ${t.colors.accent}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: t.display, fontWeight: 800, fontSize: 30, color: t.colors.text}}>
          VS
        </div>
      </div>
    </Region>
  );
};

// ---------------------------------------------------------------- counter: odometer digits

const Odometer: React.FC<{value: string; start: number; size: number; color: string; font: string}> = ({value, start, size, color, font}) => {
  const frame = useCurrentFrame();
  return (
    <span style={{display: 'inline-flex', fontFamily: font, fontWeight: 800, fontSize: size, letterSpacing: '-0.05em', color, lineHeight: 1}}>
      {[...value].map((ch, i) => {
        if (!/\d/.test(ch)) return <span key={i}>{ch}</span>;
        const target = Number(ch) + 10 * (2 + (i % 2)); // spin past a couple of full turns, columns out of phase
        const pos = ease(frame, [start + i * 3, start + i * 3 + 34], [0, 1]) * target;
        return (
          <span key={i} style={{display: 'inline-block', height: '1em', overflow: 'hidden'}}>
            <span style={{display: 'flex', flexDirection: 'column', transform: `translateY(${-(pos % 10)}em)`}}>
              {Array.from({length: 11}).map((_, d) => <span key={d} style={{height: '1em'}}>{d % 10}</span>)}
            </span>
          </span>
        );
      })}
    </span>
  );
};

const Counter: React.FC<{g: G<'counter'>}> = ({g}) => {
  const t = useTheme();
  const text = g.value.toLocaleString('en-US', {minimumFractionDigits: g.decimals ?? 0, maximumFractionDigits: g.decimals ?? 0});
  const frame = useCurrentFrame();
  const out = ease(frame, [g.dur - 10, g.dur], [0, 1], EXPO_IN);
  return (
    <Region pos={g.pos}>
      <div style={{opacity: 1 - out, transform: `translateY(${-out * 40}px)`}}>
        <div style={{fontFamily: t.display, fontWeight: 800, fontSize: 200, color: t.colors.accent, lineHeight: 1, letterSpacing: '-0.05em', display: 'flex', alignItems: 'baseline'}}>
          {g.prefix && <Mask start={0}>{g.prefix}</Mask>}
          <Odometer value={text} start={2} size={200} color={t.colors.accent} font={t.display} />
          {g.suffix && <Mask start={20}>{g.suffix}</Mask>}
        </div>
        <DrawLine start={18} width="100%" height={4} style={{margin: '18px 0 14px'}} />
        {g.label && (
          <div style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 36, color: t.colors.text, textTransform: 'uppercase', letterSpacing: '0.16em'}}>
            <Kinetic text={g.label} start={22} stagger={2} />
          </div>
        )}
      </div>
    </Region>
  );
};

// ---------------------------------------------------------------- cards: perspective rise, float, staggered exit

const Card: React.FC<{src: string; frame: 'plain' | 'browser' | 'phone'; width: number}> = ({src, frame, width}) => {
  const t = useTheme();
  const img = <Img src={staticFile(src)} style={{width: '100%', display: 'block'}} />;
  if (frame === 'phone') {
    return (
      <div style={{width, borderRadius: 54, padding: 14, background: t.colors.card, border: `2px solid ${t.colors.border}`}}>
        <div style={{borderRadius: 42, overflow: 'hidden'}}>{img}</div>
      </div>
    );
  }
  return (
    <div style={{width, borderRadius: t.radius.card, overflow: 'hidden', background: t.colors.card, border: `2px solid ${t.colors.border}`}}>
      {frame === 'browser' && (
        <div style={{height: 44, display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 18, borderBottom: `2px solid ${t.colors.border}`}}>
          {[0, 1, 2].map((c) => <div key={c} style={{width: 12, height: 12, borderRadius: 6, background: t.colors.border}} />)}
        </div>
      )}
      {img}
    </div>
  );
};

const Cards: React.FC<{g: G<'cards'>}> = ({g}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const n = Math.min(4, g.images.length);
  const width = n === 1 ? 700 : n === 2 ? 480 : 400;
  const layout = [[[0, 0, -2]], [[-170, -40, -6], [170, 60, 5]], [[-220, -80, -7], [220, -20, 6], [0, 160, -2]], [[-210, -170, -7], [210, -120, 5], [-190, 170, 4], [210, 210, -5]]][n - 1];
  return (
    <Region pos={g.pos}>
      <div style={{position: 'relative', width: 900, height: n === 1 ? 900 : 1000, perspective: 1600}}>
        {g.images.slice(0, 4).map((src, i) => {
          const [x, y, r] = layout[i];
          const p = ease(frame, [i * 5, i * 5 + 22], [0, 1]);
          const o = ease(frame, [g.dur - 10 - i * 2, g.dur - i * 2], [0, 1], EXPO_IN);
          const float = Math.sin((frame + i * 17) / 26) * 8;
          return (
            <div key={i} style={{position: 'absolute', left: '50%', top: '50%', opacity: 1 - o,
              transform: `translate(-50%, -50%) translate(${x}px, ${y + float + (1 - p) * 260 - o * 120}px) rotateX(${(1 - p) * 30}deg) rotate(${r * p}deg) scale(${0.9 + 0.1 * p})`}}>
              <Card src={src} frame={g.frame ?? 'plain'} width={width} />
            </div>
          );
        })}
      </div>
      {g.caption && (
        <div style={{fontFamily: t.display, fontWeight: t.weights.headline, fontSize: 48, letterSpacing: '-0.025em', color: t.colors.text}}>
          <Kinetic text={g.caption} start={12} end={g.dur} />
        </div>
      )}
    </Region>
  );
};

// ---------------------------------------------------------------- logos

const LogoTile: React.FC<{icon: RIcon; delay: number; size: number; dur: number}> = ({icon, delay, size, dur}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const p = ease(frame, [delay, delay + 16], [0, 1]);
  const o = ease(frame, [dur - 10, dur], [0, 1], EXPO_IN);
  const strike = icon.strike ? ease(frame, [delay + 14, delay + 24], [0, 1]) : 0;
  const len = Math.SQRT2 * size;
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, transform: `translateY(${(1 - p) * 40 - o * 30}px)`, opacity: p * (1 - o)}}>
      <div style={{position: 'relative', width: size, height: size, borderRadius: t.radius.card, background: t.colors.card, border: `2px solid ${t.colors.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: strike > 0.5 ? 0.6 : 1}}>
        {icon.image ? <Img src={staticFile(icon.image)} style={{width: size * 0.6, height: size * 0.6, objectFit: 'contain'}} />
          : icon.path ? <svg viewBox="0 0 24 24" width={size * 0.5} height={size * 0.5}><path d={icon.path} fill={t.colors.text} /></svg>
          : <span style={{fontFamily: t.display, fontWeight: 800, fontSize: size * 0.36, color: t.colors.text}}>{icon.name.slice(0, 2)}</span>}
        {strike > 0 && (
          <svg style={{position: 'absolute', inset: 0}} width={size} height={size}>
            <line x1={12} y1={12} x2={size - 12} y2={size - 12} stroke={t.colors.negative} strokeWidth={6} strokeLinecap="round" strokeDasharray={len} strokeDashoffset={len * (1 - strike)} />
          </svg>
        )}
      </div>
      <div style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 28, color: strike > 0.5 ? t.colors.muted : t.colors.text}}>{icon.name}</div>
    </div>
  );
};

const Logos: React.FC<{g: G<'logos'>}> = ({g}) => {
  const t = useTheme();
  const size = g.items.length <= 2 ? 220 : g.items.length <= 4 ? 176 : 140;
  return (
    <Region pos={g.pos}>
      {g.title && (
        <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: 70, letterSpacing: '-0.04em', color: t.colors.text, marginBottom: 36}}>
          <Kinetic text={g.title} start={0} end={g.dur} />
        </div>
      )}
      <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 36, maxWidth: 860}}>
        {g.items.map((icon, i) => <LogoTile key={i} icon={icon} delay={6 + i * 4} size={size} dur={g.dur} />)}
      </div>
    </Region>
  );
};

// ---------------------------------------------------------------- highlight

const Highlight: React.FC<{g: G<'highlight'>}> = ({g}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const [x, y, w, h] = g.box;
  const L = x * width, T = y * height, W = w * width, H = h * height;
  const per = 2 * (W + H);
  const out = ease(frame, [g.dur - 8, g.dur], [0, 1]);
  const draw = ease(frame, [2, 20], [0, 1]) * (1 - out);
  const dim = ease(frame, [0, 10], [0, 1]) * (1 - out);
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: L, top: T, width: W, height: H, borderRadius: t.radius.button, boxShadow: t.noScrims ? undefined : `0 0 0 3000px rgba(0,0,0,${0.55 * dim})`}} />
      <svg style={{position: 'absolute', left: L - 6, top: T - 6}} width={W + 12} height={H + 12}>
        <rect x={6} y={6} width={W} height={H} rx={t.radius.button} fill="none" stroke={t.colors.accent} strokeWidth={4} strokeDasharray={per} strokeDashoffset={per * (1 - draw)} />
      </svg>
      {g.label && (
        <div style={{position: 'absolute', left: Math.max(40, L), top: T > 200 ? T - 96 : T + H + 24}}>
          <Mask start={10} end={g.dur}>
            <span style={{display: 'inline-block', background: t.colors.accent, color: t.colors.onAccent, fontFamily: t.body, fontWeight: 600, fontSize: 38, padding: '10px 24px', borderRadius: t.radius.tag}}>{g.label}</span>
          </Mask>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- prompt (message card typing)

const Prompt: React.FC<{g: G<'prompt'>}> = ({g}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const typeEnd = Math.min(g.dur * 0.6, 40);
  const chars = Math.round(interpolate(frame, [12, typeEnd], [0, g.text.length], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  return (
    <Region pos={g.pos ?? 'top'}>
      <Panel start={0} end={g.dur} paper={t.canvas === 'lit'} style={{width: 840, padding: '32px 40px', transform: g.pos === 'canvas' ? 'scale(1.12)' : undefined}}>
        <div style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 24, letterSpacing: '0.2em', color: t.canvas === 'lit' ? '#6b6b6b' : t.colors.muted, marginBottom: 12}}>
          <Kinetic text={(g.who ?? 'TO CLAUDE').toUpperCase()} start={6} stagger={2} />
        </div>
        <div style={{fontFamily: t.display, fontWeight: t.weights.headline, fontSize: 50, color: t.canvas === 'lit' ? t.colors.onPaper : t.colors.text, lineHeight: 1.25, minHeight: 60, letterSpacing: '-0.02em'}}>
          {g.text.slice(0, chars)}
          {chars < g.text.length && <span style={{color: t.canvas === 'lit' ? t.colors.onPaper : t.colors.accent, opacity: Math.floor(frame / 8) % 2 ? 0 : 1}}>▍</span>}
        </div>
        {g.status && (
          <div style={{marginTop: 18}}>
            <Mask start={typeEnd + 4}>
              <span style={{display: 'inline-block', background: t.colors.accent, color: t.colors.onAccent, fontFamily: t.body, fontWeight: 600, fontSize: 26, padding: '6px 18px', borderRadius: t.radius.tag, letterSpacing: '0.08em'}}>{g.status.toUpperCase()}</span>
            </Mask>
          </div>
        )}
      </Panel>
    </Region>
  );
};

// ---------------------------------------------------------------- sticker / icon chip (ring + strokes draw on)

const Sticker: React.FC<{g: G<'sticker'>}> = ({g}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const size = g.size ?? 160;
  const pop = spring({frame, fps, config: {damping: 13, mass: 0.6}});
  const o = ease(frame, [g.dur - 10, g.dur], [0, 1], EXPO_IN);
  const ring = ease(frame, [0, 20], [0, 1]);
  const box: React.CSSProperties = {position: 'absolute', left: g.x * width - size / 2, top: g.y * height - size / 2, width: size, height: size};
  if (g.icon) {
    const c = 2 * Math.PI * (size / 2 - 3);
    return (
      <div style={{...box, transform: `scale(${(0.7 + 0.3 * pop) * (1 - 0.3 * o)})`, opacity: 1 - o}}>
        <div style={{position: 'absolute', inset: 0, borderRadius: size / 2, background: t.colors.card}} />
        <svg style={{position: 'absolute', inset: 0}} width={size} height={size}>
          <circle cx={size / 2} cy={size / 2} r={size / 2 - 3} fill="none" stroke={g.accent ? t.colors.accent : t.colors.border} strokeWidth={3}
            strokeDasharray={c} strokeDashoffset={c * (1 - ring)} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
        </svg>
        <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <LineIcon name={g.icon} size={size * 0.5} color={g.accent ? t.colors.accent : t.colors.text} draw={ease(frame, [4, 26], [0, 1])} />
        </div>
      </div>
    );
  }
  return (
    <div style={{...box, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${pop})`, opacity: 1 - o}}>
      {g.image ? <Img src={staticFile(g.image)} style={{width: '100%', height: '100%', objectFit: 'contain'}} /> : <span style={{fontSize: size * 0.85, lineHeight: 1}}>{g.emoji}</span>}
    </div>
  );
};

// ---------------------------------------------------------------- notify: phone notifications that drop in and stack
// (bank SMS, email, app alerts) — the everyday UI the audience recognises from their own phone.

const Notify: React.FC<{g: G<'notify'>}> = ({g}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const out = ease(frame, [g.dur - 10, g.dur], [0, 1], EXPO_IN);
  const shown = g.items.filter((it) => frame >= it.at - 2);
  return (
    <Region pos={g.pos ?? 'top'}>
      <div style={{width: 860, display: 'flex', flexDirection: 'column-reverse', gap: 16, transform: `translateY(${-out * 60}px)`, opacity: 1 - out}}>
        {shown.map((it, i) => {
          const drop = spring({frame: frame - it.at, fps, config: {damping: 16, mass: 0.7}});
          const newest = i === shown.length - 1;
          return (
            <div key={i} style={{display: 'flex', gap: 22, alignItems: 'flex-start', padding: '24px 28px', borderRadius: 30,
              background: 'rgba(28,28,30,0.86)', backdropFilter: 'blur(24px)', border: '1px solid rgba(255,255,255,0.08)',
              boxShadow: '0 20px 50px rgba(0,0,0,0.45)', transform: `translateY(${(1 - drop) * -120}px) scale(${newest ? 1 : 0.96})`,
              opacity: Math.min(1, drop * 1.5) * (newest ? 1 : 0.75), transformOrigin: 'top center'}}>
              <div style={{width: 76, height: 76, borderRadius: 18, background: t.colors.accent, flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                <LineIcon name={it.icon ?? 'bell'} size={42} color={t.colors.onAccent} stroke={2} />
              </div>
              <div style={{flex: 1, minWidth: 0}}>
                <div style={{display: 'flex', justifyContent: 'space-between', fontFamily: t.body, fontWeight: 500, fontSize: 26, color: 'rgba(255,255,255,0.55)', letterSpacing: '0.04em', textTransform: 'uppercase'}}>
                  <span>{it.app}</span><span>{it.time ?? 'now'}</span>
                </div>
                <div style={{fontFamily: t.display, fontWeight: 700, fontSize: 40, color: '#fff', marginTop: 6, letterSpacing: '-0.02em'}}>{it.title}</div>
                <div style={{fontFamily: t.body, fontWeight: 400, fontSize: 32, color: 'rgba(255,255,255,0.82)', marginTop: 4, lineHeight: 1.3}}>{it.body}</div>
              </div>
            </div>
          );
        })}
      </div>
    </Region>
  );
};

// ---------------------------------------------------------------- event: a calendar-invite style card for dates

const EventCard: React.FC<{g: G<'event'>}> = ({g}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 14, mass: 0.7}});
  const out = ease(frame, [g.dur - 10, g.dur], [0, 1], EXPO_IN);
  const paper = t.colors.paper ?? '#F6F5F0';
  const ink = t.colors.onPaper ?? '#0A0A0A';
  return (
    <Region pos={g.pos ?? 'top'}>
      <div style={{width: 820, display: 'flex', borderRadius: 28, overflow: 'hidden', background: paper, boxShadow: '0 30px 80px rgba(0,0,0,0.55)',
        transform: `translateY(${(1 - pop) * 80 - out * 50}px) rotate(${(1 - pop) * -3}deg)`, opacity: Math.min(1, pop * 1.4) * (1 - out)}}>
        <div style={{width: 230, background: t.colors.accent, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '28px 0'}}>
          <div style={{fontFamily: t.body, fontWeight: 600, fontSize: 30, letterSpacing: '0.2em', color: t.colors.onAccent, textTransform: 'uppercase'}}><Mask start={6}>{g.day}</Mask></div>
          {g.date && <div style={{fontFamily: t.display, fontWeight: 800, fontSize: 96, lineHeight: 1, color: t.colors.onAccent, letterSpacing: '-0.04em'}}><Mask start={9}>{g.date}</Mask></div>}
        </div>
        <div style={{flex: 1, padding: '30px 34px'}}>
          {g.tag && <div style={{display: 'inline-block', fontFamily: t.body, fontWeight: 600, fontSize: 24, letterSpacing: '0.14em', textTransform: 'uppercase', color: ink, border: `2px solid ${ink}`, borderRadius: 999, padding: '4px 14px', marginBottom: 14}}><Mask start={8}>{g.tag}</Mask></div>}
          <div style={{fontFamily: t.display, fontWeight: 800, fontSize: 56, lineHeight: 1.02, color: ink, letterSpacing: '-0.035em'}}><Kinetic text={g.title} start={10} stagger={3} /></div>
          {(g.details ?? []).map((d, i) => (
            <div key={i} style={{fontFamily: t.body, fontWeight: 500, fontSize: 30, color: ink, opacity: 0.7, marginTop: i ? 4 : 14}}><Mask start={16 + i * 4}>{d}</Mask></div>
          ))}
        </div>
      </div>
    </Region>
  );
};


// ---------------------------------------------------------------- newspaper clipping

const PAPER_NEWS = '#F1ECDF';
const NEWS_INK = '#161514';

/** Jagged torn-paper outline, deterministic per clipping. */
const torn = (seed: number) => {
  const r = (i: number) => (Math.sin(seed * 97.13 + i * 12.9898) * 43758.5453) % 1;
  const j = (i: number, a: number) => Math.abs(r(i)) * a;
  const pts: string[] = [];
  const n = 26;
  for (let i = 0; i <= n; i++) pts.push(`${(i / n) * 100}% ${j(i, 1.6)}%`);
  for (let i = 0; i <= n; i++) pts.push(`${100 - j(i + 40, 1.4)}% ${(i / n) * 100}%`);
  for (let i = n; i >= 0; i--) pts.push(`${(i / n) * 100}% ${100 - j(i + 80, 1.8)}%`);
  for (let i = n; i >= 0; i--) pts.push(`${j(i + 120, 1.4)}% ${(i / n) * 100}%`);
  return `polygon(${pts.join(',')})`;
};

const HeadlineText: React.FC<{text: string; hl?: string | null; at: number}> = ({text, hl, at}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  if (!hl) return <>{text}</>;
  const i = text.toLowerCase().indexOf(hl.toLowerCase());
  const sweep = ease(frame, [at, at + 12], [0, 1]);
  return (
    <>
      {text.slice(0, i)}
      {/* per-line highlighter: a background that follows every wrapped line of the phrase */}
      <span style={{backgroundImage: `linear-gradient(${t.colors.accent}, ${t.colors.accent})`, backgroundRepeat: 'no-repeat',
        backgroundSize: `${sweep * 100}% 72%`, backgroundPosition: '0 85%', WebkitBoxDecorationBreak: 'clone', boxDecorationBreak: 'clone',
        padding: '0 4px', margin: '0 -4px'}}>{text.slice(i, i + hl.length)}</span>
      {text.slice(i + hl.length)}
    </>
  );
};

const ClippingCard: React.FC<{it: {headline: string; source: string; date: string; highlight?: string | null}; at: number; k: number; dur: number; article?: boolean}> = ({it, at, k, dur, article}) => {
  const frame = useCurrentFrame();
  const t = useTheme();
  const f = frame - at;
  if (f < 0) return null;
  const slap = ease(f, [0, 12], [0, 1], BACK_OUT);
  const out = ease(frame, [dur - 10, dur], [0, 1], EXPO_IN);
  const rot = article ? 0 : [-2.5, 2.2, -1.2][k % 3];
  const dx = [0, 26, -20][k % 3], dy = k * 70;
  const words = it.headline.split(' ').length;
  const size = words > 14 ? 50 : words > 9 ? 58 : 66;
  return (
    <div style={{position: k ? 'absolute' : 'relative', top: k ? dy : undefined, left: k ? dx : undefined, width: 860,
      transform: article ? `translateY(${(1 - slap) * 70 - out * 40}px) scale(${0.96 + 0.04 * slap})` : `translate(${(1 - slap) * 120 - out * 60}px, ${(1 - slap) * -160 + out * 80}px) rotate(${rot + (1 - slap) * 9}deg) scale(${1 + (1 - slap) * 0.18})`,
      opacity: Math.min(1, slap * 2) * (1 - out), filter: `drop-shadow(0 ${18 + 10 * (1 - slap)}px 30px rgba(0,0,0,0.45))`}}>
      <div style={{clipPath: article ? undefined : torn(k + it.headline.length), background: article ? '#FFFFFF' : PAPER_NEWS, borderRadius: article ? 18 : 0, padding: '46px 54px 50px', position: 'relative'}}>
        {/* newsprint: warm fibre grain + faint yellowing at the edges */}
        <svg style={{position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: article ? 0 : 0.18, mixBlendMode: 'multiply'}}>
          <filter id={`fib${k}`}><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed={k + 3} /><feColorMatrix values="0 0 0 0 0.4  0 0 0 0 0.33  0 0 0 0 0.2  0 0 0 1 0" /></filter>
          <rect width="100%" height="100%" filter={`url(#fib${k})`} />
        </svg>
        {!article && <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(120,90,40,0.16) 100%)'}} />}
        <div style={{position: 'relative'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontFamily: t.body, fontWeight: 700, fontSize: 22,
            letterSpacing: '0.16em', textTransform: 'uppercase', color: NEWS_INK, opacity: 0.8}}>
            <span>{it.source}</span><span style={{fontWeight: 500}}>{it.date}</span>
          </div>
          <div style={{borderTop: `3px solid ${NEWS_INK}`, borderBottom: `1px solid ${NEWS_INK}`, height: 4, margin: '14px 0 22px', opacity: 0.85}} />
          <div style={{fontFamily: NEWS_SERIF, fontWeight: 800, fontSize: size, lineHeight: 1.06, letterSpacing: '-0.012em', color: NEWS_INK}}>
            <HeadlineText text={it.headline} hl={it.highlight} at={at + 14} />
          </div>
          {/* body columns, abstract: newsprint texture only, no invented article text */}
          <div style={{display: 'flex', gap: 22, marginTop: 26, opacity: 0.22}}>
            {[0, 1, 2].map((c) => (
              <div key={c} style={{flex: 1, display: 'flex', flexDirection: 'column', gap: 9}}>
                {[0, 1, 2, 3].map((l) => <div key={l} style={{height: 7, background: NEWS_INK, width: `${l === 3 ? 55 + c * 10 : 100}%`}} />)}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const Clipping: React.FC<{g: G<'clipping'>}> = ({g}) => {
  const step = Math.min(24, Math.max(10, Math.floor(g.dur / (g.items.length + 1))));
  return (
    <Region pos={g.pos ?? 'top'}>
      <div style={{position: 'relative', width: 860}}>
        {g.items.slice(0, 3).map((it, k) => <ClippingCard key={k} it={it} at={k * step} k={k} dur={g.dur} article={g.look === 'article'} />)}
      </div>
    </Region>
  );
};

// ---------------------------------------------------------------- layer

const render = (g: RGraphic, dur: number) => {
  const p = {...g, dur} as never;
  switch (g.type) {
    case 'bespoke': {
      const Scene = BESPOKE[g.name];
      return Scene ? <Scene g={p} /> : null;
    }
    case 'clipping': return <Clipping g={p} />;
    case 'cards': return <Cards g={p} />;
    case 'logos': return <Logos g={p} />;
    case 'counter': return <Counter g={p} />;
    case 'checklist': return <Checklist g={p} />;
    case 'flow': return <Flow g={p} />;
    case 'highlight': return <Highlight g={p} />;
    case 'compare': return <Compare g={p} />;
    case 'prompt': return <Prompt g={p} />;
    case 'slam': return <Slam g={p} />;
    case 'sticker': return <Sticker g={p} />;
    case 'notify': return <Notify g={p} />;
    case 'event': return <EventCard g={p} />;
  }
};

// Item times (checklist/flow/slam `at`) arrive in output frames; shift them to Sequence-local.
const localize = (g: RGraphic): RGraphic => {
  if (g.type === 'bespoke') return {...g, cues: Object.fromEntries(Object.entries(g.cues).map(([k, v]) => [k, v - g.from]))};
  if (g.type === 'checklist' || g.type === 'flow' || g.type === 'notify') return {...g, items: g.items.map((i) => ({...i, at: i.at - g.from}))} as RGraphic;
  if (g.type === 'slam') return {...g, words: g.words.map((w) => ({...w, at: w.at - g.from}))};
  return g;
};

// Big graphics get a dark scrim so they read over any footage (opt out with dim: false).
const DIM_DEFAULT: Partial<Record<RGraphic['type'], boolean>> = {logos: true, counter: true, cards: true, compare: true, flow: true};

const Dim: React.FC<{dur: number; pos?: RGraphic['pos']}> = ({dur, pos}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  if (t.noScrims) return null;
  const o = interpolate(frame, [0, 8, dur - 8, dur], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const a = Math.max(0.5, t.scrim);
  const bg = pos === 'top'
    ? `linear-gradient(180deg, rgba(0,0,0,${a}) 0%, rgba(0,0,0,${a * 0.7}) 40%, rgba(0,0,0,0) 62%)`
    : `radial-gradient(ellipse at center, rgba(0,0,0,${a}) 0%, rgba(0,0,0,${a * 0.6}) 75%)`;
  return <AbsoluteFill style={{background: bg, opacity: o}} />;
};

export const GraphicsLayer: React.FC<{graphics: RGraphic[]}> = ({graphics}) => (
  <AbsoluteFill>
    {graphics.map((g, i) => {
      const dur = Math.max(1, g.to - g.from);
      // canvas graphics sit on the black dock canvas — a scrim would only darken the speaker window
      const dim = g.pos === 'canvas' ? false : (g as {dim?: boolean}).dim ?? DIM_DEFAULT[g.type] ?? false;
      return (
        <Sequence key={i} from={g.from} durationInFrames={dur}>
          {dim && <Dim dur={dur} pos={g.pos} />}
          {render(localize(g), dur)}
        </Sequence>
      );
    })}
  </AbsoluteFill>
);
