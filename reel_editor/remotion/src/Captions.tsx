import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {CaptionStyle, RChunk, ReelProps, RWord} from './types';
import {useTheme, type Theme} from './theme';
import {Mask, dockAmount} from './motion';

const base = (t: Theme): Record<CaptionStyle, {font: string; px: number; upper: boolean; weight: number; stroke: boolean}> => ({
  premium: {font: t.display, px: 74, upper: false, weight: t.weights.display, stroke: false},
  editorial: {font: t.display, px: 60, upper: false, weight: t.weights.sub, stroke: false},
  kinetic: {font: t.display, px: 150, upper: true, weight: t.weights.display, stroke: false},
  'bold-pop': {font: t.display, px: 92, upper: true, weight: t.weights.display, stroke: true},
  'editorial-serif': {font: t.display, px: 80, upper: false, weight: t.weights.headline, stroke: false},
  minimal: {font: t.body, px: 58, upper: false, weight: 600, stroke: false},
  huge: {font: t.display, px: 170, upper: true, weight: t.weights.display, stroke: true},
});

// Instagram safe area: bottom ~20% = caption/username overlay, right ~14% = like/comment rail
/** Caption baseline (% from bottom): above Instagram's caption area organically, above Meta's CTA + primary
 *  text in ads; when docked, in the band between canvas and speaker window. */
const captionBottom = (placement: string | undefined, dock: number, style?: string) => {
  const d = Math.min(1, dock);
  if (style === 'top') return 24; // podcast: captions live in the lower canvas
  return placement === 'meta-ad' ? 37 + (58.5 - 37) * d : 25 + 22 * d;
};

const POS = {lower: {bottom: '25%'}, center: {top: '44%'}, upper: {top: '13%'}} as const;

const Word: React.FC<{w: RWord; active: boolean; spoken: boolean; cfg: ReelProps['captions']; chunkEnd: number}> = ({
  w,
  active,
  spoken,
  cfg,
  chunkEnd,
}) => {
  const t = useTheme();
  const style = base(t)[cfg.style];
  const pop = cfg.style === 'bold-pop' || cfg.style === 'huge';
  const css: React.CSSProperties = {
    display: 'inline-block',
    margin: '0 0.14em',
    color: cfg.color,
    transition: 'none',
  };
  if (pop && active) {
    css.color = cfg.highlightColor;
    css.transform = 'scale(1.08)';
  }
  if (cfg.style === 'premium' || cfg.style === 'editorial') {
    // karaoke-style: upcoming words in the muted colour, the word being spoken in the accent
    if (!spoken) css.color = t.colors.muted;
    if (active) css.color = cfg.highlightColor;
  }
  if (cfg.style === 'editorial-serif' || cfg.style === 'minimal') {
    css.opacity = spoken ? 1 : 0.55;
  }
  switch (w.emphasis) {
    case 'gold':
    case 'color':
      if (cfg.style === 'editorial' || cfg.style === 'kinetic') {
        css.color = t.colors.accent; // quieter treatments: accent colour, no box
      } else if (t.strictAccent) {
        // keyword highlight box: accent fill behind one word, text in the on-accent colour
        css.background = t.colors.accent;
        css.color = t.colors.onAccent;
        css.padding = '0 0.2em';
        css.borderRadius = t.radius.button;
      } else {
        css.color = cfg.highlightColor;
      }
      break;
    case 'big':
      css.fontSize = '1.3em';
      break;
    case 'strike':
      css.textDecoration = 'line-through';
      css.textDecorationColor = t.colors.negative;
      css.textDecorationThickness = '0.09em';
      css.opacity = 0.85;
      break;
  }
  const text = style.upper && w.emphasis !== 'gold' ? w.text.toUpperCase() : w.text;
  if (cfg.style === 'premium' || cfg.style === 'editorial' || cfg.style === 'kinetic') {
    // word-by-word: each word rises through its own mask as it's spoken; the line lifts out together
    if (!css.background) css.color = active ? cfg.highlightColor : (css.color === t.colors.muted ? cfg.color : css.color);
    return <Mask start={w.from - 3} end={chunkEnd} len={9} style={{margin: css.margin}}><span style={{...css, margin: 0}}>{text}</span></Mask>;
  }
  return <span style={css}>{text}</span>;
};

const Chunk: React.FC<{chunk: RChunk; cfg: ReelProps['captions']; dock: number}> = ({chunk, cfg, dock}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = useTheme();
  const style = base(t)[cfg.style];
  const enter = spring({frame: frame - chunk.from, fps, config: {damping: 14, mass: 0.6}});
  const pop = cfg.style === 'bold-pop' || cfg.style === 'huge';
  return (
    <div
      style={{
        position: 'absolute',
        left: cfg.style === 'editorial' ? 72 : 70,
        right: cfg.style === 'editorial' ? 260 : 150,
        ...(cfg.style === 'kinetic' ? {top: t.dockStyle === 'top' ? '64%' : '40%'} : cfg.position === 'lower' ? {bottom: `${captionBottom(t.placement, dock, t.dockStyle)}%`} : POS[cfg.position]),
        textAlign: cfg.style === 'editorial' ? 'left' : 'center',
        fontFamily: style.font,
        fontWeight: style.weight,
        fontSize: style.px * cfg.size,
        lineHeight: cfg.style === 'kinetic' ? 0.95 : 1.08,
        letterSpacing: pop ? '-0.01em' : '-0.025em',
        transform: pop ? `scale(${0.75 + 0.25 * enter})` : cfg.style === 'kinetic' ? `scale(${0.86 + 0.14 * enter})` : cfg.style === 'premium' || cfg.style === 'editorial' ? undefined : `translateY(${(1 - enter) * 24}px)`,
        opacity: ['premium', 'editorial', 'kinetic'].includes(cfg.style) ? 1 : Math.min(1, enter * 1.4),
        WebkitTextStroke: style.stroke ? `${Math.round(8 * cfg.size)}px black` : undefined,
        paintOrder: 'stroke fill',
        textShadow: style.stroke
          ? '0 6px 18px rgba(0,0,0,0.55)'
          : '0 2px 20px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.45)',
      }}
    >
      {chunk.words.map((w, i) => (
        <Word key={i} w={w} cfg={cfg} chunkEnd={chunk.to} active={frame >= w.from && frame < w.to} spoken={frame >= w.from} />
      ))}
    </div>
  );
};

export const Captions: React.FC<{chunks: RChunk[]; cfg: ReelProps['captions']; docks?: [number, number][]}> = ({chunks, cfg, docks}) => {
  const frame = useCurrentFrame();
  const t = useTheme();
  const current = chunks.find((c) => frame >= c.from && frame < c.to);
  // brand scrim behind the caption zone so text never fights the footage
  // Localised scrim: a soft dark ellipse only behind the caption line (a full-width gradient darkened
  // the speaker's face whenever it sat in the lower half — docked window, split screen).
  const d = dockAmount(docks, frame);
  const bottomPct = cfg.position === 'lower' ? captionBottom(t.placement, d, t.dockStyle) : cfg.position === 'upper' ? null : 50;
  const cy = bottomPct === null ? 16 : 100 - bottomPct - 3;
  const scrim = current ? `radial-gradient(ellipse 62% 7% at 45% ${cy}%, rgba(0,0,0,${t.scrim}) 0%, rgba(0,0,0,${t.scrim * 0.5}) 55%, rgba(0,0,0,0) 100%)` : undefined;
  return (
    <AbsoluteFill>
      {scrim && !t.noScrims && <AbsoluteFill style={{background: scrim}} />}
      {current && <Chunk chunk={current} cfg={cfg} dock={dockAmount(docks, frame)} />}
    </AbsoluteFill>
  );
};
