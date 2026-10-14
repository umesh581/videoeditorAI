// Motion primitives shared by every on-screen element. The rules that separate designed motion
// from "AI slop": expo-out easing (never linear), masked reveals instead of fades, staggered
// word/char timing, designed exits, lines that draw, and nothing entering all at once.
import React from 'react';
import {Easing, interpolate, useCurrentFrame} from 'remotion';
import {useTheme} from './theme';

export const EXPO_OUT = Easing.bezier(0.16, 1, 0.3, 1);
export const EXPO_IN = Easing.bezier(0.7, 0, 0.84, 0);
export const SNAP = Easing.bezier(0.85, 0, 0.15, 1); // in-out, for wipes
export const BACK_OUT = Easing.bezier(0.34, 1.4, 0.64, 1); // settles with a small overshoot, for layout moves

export const ease = (frame: number, range: [number, number], out: [number, number], easing = EXPO_OUT) =>
  interpolate(frame, range, out, {easing, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

/** 0 → 1 entrance progress and 0 → 1 exit progress for an element living [0, dur). */
export const useInOut = (dur: number, delay = 0, inLen = 14, outLen = 10) => {
  const frame = useCurrentFrame();
  return {
    frame,
    inP: ease(frame, [delay, delay + inLen], [0, 1]),
    outP: ease(frame, [dur - outLen, dur], [0, 1], EXPO_IN),
  };
};

/** Content slides up out of an invisible mask; on exit it continues up and out. */
export const Mask: React.FC<{
  start: number;
  end?: number;
  len?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
  dir?: 'up' | 'down';
}> = ({start, end, len = 16, children, style, dir = 'up'}) => {
  const frame = useCurrentFrame();
  const inY = ease(frame, [start, start + len], [1, 0]);
  const outY = end === undefined ? 0 : ease(frame, [end - len * 0.7, end], [0, 1], EXPO_IN);
  const s = dir === 'up' ? 1 : -1;
  const y = (inY * 135 - outY * 135) * s; // fully clear of the mask (incl. its padding) when hidden
  return (
    <span style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'top', padding: '0.14em 0.04em 0.12em', margin: '-0.14em -0.04em -0.12em', ...style}}>
      <span style={{display: 'inline-block', transform: `translateY(${y}%)`, willChange: 'transform'}}>{children}</span>
    </span>
  );
};

/** Text split into words, each revealed through its own mask with a stagger. */
export const Kinetic: React.FC<{
  text: string;
  start: number;
  end?: number;
  stagger?: number;
  len?: number;
  style?: React.CSSProperties;
  wordStyle?: (i: number, word: string) => React.CSSProperties | undefined;
  gap?: string;
}> = ({text, start, end, stagger = 3, len = 16, style, wordStyle, gap = '0.24em'}) => {
  const words = text.split(/\s+/).filter(Boolean);
  return (
    <span style={{display: 'inline', ...style}}>
      {words.map((w, i) => (
        <React.Fragment key={i}>
          <Mask start={start + i * stagger} end={end === undefined ? undefined : end - (words.length - 1 - i) * 1} len={len} style={wordStyle?.(i, w)}>
            {w}
          </Mask>
          {i < words.length - 1 && <span style={{display: 'inline-block', width: gap}} />}
        </React.Fragment>
      ))}
    </span>
  );
};

/** Per-character rise with tight stagger — for mastheads and single power words. */
export const Chars: React.FC<{text: string; start: number; end?: number; stagger?: number; style?: React.CSSProperties}> = ({
  text,
  start,
  end,
  stagger = 1.5,
  style,
}) => (
  <span style={{display: 'inline-block', whiteSpace: 'pre', ...style}}>
    {[...text].map((c, i) => (
      <Mask key={i} start={start + i * stagger} end={end} len={18}>
        {c === ' ' ? ' ' : c}
      </Mask>
    ))}
  </span>
);

/** Blur + rise + fade, for secondary text that should feel softer than masked headlines. */
export const BlurIn: React.FC<{start: number; end?: number; children: React.ReactNode; style?: React.CSSProperties}> = ({start, end, children, style}) => {
  const frame = useCurrentFrame();
  const p = ease(frame, [start, start + 18], [0, 1]);
  const o = end === undefined ? 0 : ease(frame, [end - 8, end], [0, 1], EXPO_IN);
  return (
    <div style={{opacity: p * (1 - o), filter: `blur(${(1 - p) * 14 + o * 8}px)`, transform: `translateY(${(1 - p) * 24 - o * 16}px)`, ...style}}>
      {children}
    </div>
  );
};

/** A line that draws itself (horizontal by default). */
export const DrawLine: React.FC<{start: number; len?: number; end?: number; width: number | string; height?: number; color?: string; style?: React.CSSProperties; origin?: 'left' | 'right'}> = ({
  start,
  len = 18,
  end,
  width,
  height = 4,
  color,
  style,
  origin = 'left',
}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const p = ease(frame, [start, start + len], [0, 1]);
  const o = end === undefined ? 0 : ease(frame, [end - 10, end], [0, 1], EXPO_IN);
  return (
    <div
      style={{
        width,
        height,
        background: color ?? t.colors.accent,
        transform: `scaleX(${p * (1 - o)})`,
        transformOrigin: o > 0 ? (origin === 'left' ? 'right' : 'left') : origin,
        ...style,
      }}
    />
  );
};

/** Brand 12-column grid that draws in behind full-screen cards (Layout & Grid page of the guidelines). */
export const GridBackdrop: React.FC<{start?: number; opacity?: number; cols?: number}> = ({start = 0, opacity = 0.5, cols = 12}) => {
  const line = 'rgba(255,255,255,0.09)';
  const frame = useCurrentFrame();
  return (
    <div style={{position: 'absolute', inset: 0, opacity}}>
      {Array.from({length: cols + 1}).map((_, i) => {
        const p = ease(frame, [start + i * 1.2, start + i * 1.2 + 22], [0, 1]);
        return <div key={i} style={{position: 'absolute', top: 0, bottom: 0, left: `${(i * 100) / cols}%`, width: 1, background: line, transform: `scaleY(${p})`, transformOrigin: i % 2 ? 'top' : 'bottom'}} />;
      })}
      {[0.25, 0.5, 0.75].map((y, i) => {
        const p = ease(frame, [start + 6 + i * 3, start + 30 + i * 3], [0, 1]);
        return <div key={`h${i}`} style={{position: 'absolute', left: 0, right: 0, top: `${y * 100}%`, height: 1, background: line, transform: `scaleX(${p})`, transformOrigin: 'left'}} />;
      })}
    </div>
  );
};

/** Slow camera drift for graphics so nothing is ever perfectly static. */
export const useDrift = (amp = 1) => {
  const frame = useCurrentFrame();
  return {
    transform: `translate(${Math.sin(frame / 60) * 6 * amp}px, ${Math.cos(frame / 75) * 5 * amp}px) scale(${1 + frame * 0.00035 * amp})`,
  };
};

// Dock: the speaker shrinks into a rounded window at the bottom and the top becomes a canvas for
// graphics (the layout every premium explainer reel uses). Amount 0 = full screen, 1 = docked.
export const DOCK_RECT = {x: 0.04, y: 0.555, w: 0.92, h: 0.37, r: 28};
// Meta ads: the window runs down under the ad's CTA/primary-text area (footage is fine there, text isn't)
export const DOCK_RECT_AD = {x: 0.04, y: 0.425, w: 0.92, h: 0.545, r: 28}; // footage may sit under Meta's overlay; text may not
export const DOCK_RECT_TOP = {x: 0, y: 0, w: 1, h: 0.56, r: 0}; // podcast clip layout
export const dockRect = (placement?: string, style?: string) =>
  style === 'top' ? DOCK_RECT_TOP : placement === 'meta-ad' ? DOCK_RECT_AD : DOCK_RECT;
export const dockAmount = (docks: [number, number][] | undefined, f: number) => {
  let d = 0;
  for (const [a, z] of docks ?? []) {
    if (f < a || f >= z) continue;
    d = Math.max(d, ease(f, [a, a + 14], [0, 1], BACK_OUT) * (1 - ease(f, [z - 12, z], [0, 1], EXPO_IN)));
  }
  return d;
};


/** Background for the dock canvas and full-screen cards. Video mode: a soft pool of light from the top
 *  (a hint of the accent), falling off to black, with film grain and a whisper of the brand grid. */
export const CanvasBackdrop: React.FC<{start?: number}> = ({start = -60}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  if (t.canvas !== 'lit') return <GridBackdrop start={start} opacity={0.9} />;
  const a = t.colors.accent;
  const hex = (x: string) => [1, 3, 5].map((i) => parseInt(x.slice(i, i + 2), 16)).join(',');
  const drift = Math.sin(frame / 90) * 4;
  return (
    <div style={{position: 'absolute', inset: 0, background: '#050505', overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(ellipse 90% 55% at ${50 + drift}% 12%, rgba(${hex(a)},0.16) 0%, rgba(40,40,40,0.55) 38%, rgba(5,5,5,0) 75%)`}} />
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 70% 40% at 50% 45%, rgba(255,255,255,0.045) 0%, rgba(0,0,0,0) 70%)'}} />
      <GridBackdrop start={start} opacity={0.35} />
      <Grain amount={t.grain ?? 0.05} />
    </div>
  );
};

/** Animated film grain (deterministic per frame). */
export const Grain: React.FC<{amount: number}> = ({amount}) => {
  const frame = useCurrentFrame();
  const seed = frame % 8;
  return (
    <svg style={{position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: amount, mixBlendMode: 'overlay', pointerEvents: 'none'}}>
      <filter id={`grain${seed}`}><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={seed} stitchTiles="stitch" /></filter>
      <rect width="100%" height="100%" filter={`url(#grain${seed})`} />
    </svg>
  );
};
