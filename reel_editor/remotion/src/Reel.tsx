import React from 'react';
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Sequence,
  interpolate,
  random,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {Grade, RBeat, ReelProps} from './types';
import {Captions} from './Captions';
import {Overlays} from './Overlays';
import {BrollLayer} from './Broll';
import {GraphicsLayer} from './Graphics';
import {ThemeContext, makeTheme, useTheme} from './theme';
import {CanvasBackdrop, EXPO_OUT, SNAP, dockAmount, dockRect, ease} from './motion';

const GRADES: Record<Grade, {filter: string; tint?: string; blend?: string}> = {
  natural: {filter: 'none'},
  warm: {
    filter: 'saturate(1.1) contrast(1.06) sepia(0.2) brightness(1.04)',
    tint: 'rgba(255,150,70,0.10)',
    blend: 'soft-light',
  },
  moody: {
    filter: 'contrast(1.18) saturate(0.65) brightness(0.8)',
    tint: 'rgba(15,35,70,0.32)',
    blend: 'multiply',
  },
  punchy: {filter: 'contrast(1.2) saturate(1.35) brightness(1.02)'},
  bw: {filter: 'grayscale(1) contrast(1.25) brightness(0.95)'},
  film: {
    filter: 'contrast(1.08) saturate(0.88) sepia(0.14)',
    tint: 'rgba(0,60,60,0.10)',
    blend: 'soft-light',
  },
};

const BeatClip: React.FC<{
  beat: RBeat;
  src: string;
  volume: number;
  push: boolean;
  fit: 'cover' | 'blur';
  docks?: [number, number][];
  punches?: number[];
}> = ({beat, src, volume, push, fit, docks, punches}) => {
  const frame = useCurrentFrame(); // local to the Sequence
  const {width, height} = useVideoConfig();
  const g = beat.from + frame; // global frame
  const d = dockAmount(docks, g);
  let scale = beat.zoom + (1 - beat.zoom) * Math.min(1, d); // docked window shows the plain framing
  if (push) scale *= interpolate(frame, [0, beat.duration], [1, 1.04]);
  // snap punch-in on emphasised words (held until the next cut)
  const hit = (punches ?? []).filter((p) => p >= beat.from && p <= g).pop();
  if (hit !== undefined) scale *= 1 + 0.1 * ease(g - hit, [0, 4], [0, 1]);
  let blur = 0;
  let shiftX = 0;
  if (beat.transition === 'zoom') {
    // punch-in with a short motion blur, like a fast camera move settling
    scale *= interpolate(frame, [0, 8], [1.15, 1], {easing: EXPO_OUT, extrapolateRight: 'clamp'});
    blur = interpolate(frame, [0, 5], [6, 0], {extrapolateRight: 'clamp'});
  }
  const whip = beat.transition === 'whip' ? ease(frame, [0, 8], [1, 0]) : 0;
  if (whip > 0) {
    shiftX = whip * 22; // content slides inside an overscanned frame, so no empty edge is ever exposed
    scale *= 1 + whip * 0.5;
  }
  const flash = beat.transition === 'flash' ? interpolate(frame, [0, 5], [0.9, 0], {extrapolateRight: 'clamp'}) : 0;
  const trim = {trimBefore: beat.trimBefore, trimAfter: beat.trimBefore + beat.duration};
  const th = useTheme();
  const R = dockRect(th.placement, th.dockStyle);
  const box: React.CSSProperties = {
    position: 'absolute',
    left: R.x * width * d,
    top: R.y * height * d,
    width: width * (1 - (1 - R.w) * d),
    height: height * (1 - (1 - R.h) * d),
    borderRadius: R.r * d,
    overflow: 'hidden',
    outline: d > 0.02 ? `2px solid rgba(255,255,255,${0.12 * d})` : undefined,
    filter: whip > 0.02 ? `url(#whip${beat.from})` : undefined,
  };
  return (
    <AbsoluteFill>
      {whip > 0.02 && (
        <svg width={0} height={0} style={{position: 'absolute'}}>
          <filter id={`whip${beat.from}`} x="-20%" width="140%"><feGaussianBlur stdDeviation={`${whip * 60} 0`} /></filter>
        </svg>
      )}
      <div style={box}>
        {fit === 'blur' && (
          // Landscape/screen footage: full frame in the middle over a blurred, darkened fill.
          <OffthreadVideo src={staticFile(src)} {...trim} muted
            style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(40px) brightness(0.55)', transform: 'scale(1.15)'}} />
        )}
        <OffthreadVideo
          src={staticFile(src)}
          {...trim}
          volume={volume}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: fit === 'blur' ? 'contain' : 'cover',
            objectPosition: `${beat.focusX * 100}% ${(beat.focusY * (1 - d) + 0.36 * d) * 100}%`,
            transform: `translateX(${shiftX}%) scale(${scale})`,
            transformOrigin: `${beat.focusX * 100}% ${beat.focusY * 100}%`,
            filter: [blur > 0.2 ? `blur(${blur}px)` : '', beat.mono ? 'grayscale(1) contrast(1.12)' : ''].join(' ').trim() || undefined,
          }}
        />
      </div>
      {flash > 0 && <AbsoluteFill style={{background: 'white', opacity: flash}} />}
    </AbsoluteFill>
  );
};

/** Canvas shown above the docked speaker: brand black with the 12-column grid. */
const DockCanvas: React.FC<{docks?: [number, number][]}> = ({docks}) => {
  const frame = useCurrentFrame();
  const d = Math.min(1, dockAmount(docks, frame));
  if (d <= 0) return null;
  return (
    <AbsoluteFill style={{opacity: d}}>
      <CanvasBackdrop />
    </AbsoluteFill>
  );
};

/** Music bed that ducks under speech and lifts in the gaps (every reference reel does this). */
const useDucking = (chunks: ReelProps['chunks'], base: number) => (f: number) => {
  let near = 99;
  for (const c of chunks) {
    if (f >= c.from && f < c.to) return base;
    near = Math.min(near, Math.abs(f - c.from), Math.abs(f - c.to));
  }
  return base * (1 + 1.2 * Math.min(1, near / 8));
};

const Grain: React.FC = () => {
  const frame = useCurrentFrame();
  const seed = Math.floor(random(`grain-${frame}`) * 1000);
  return (
    <AbsoluteFill style={{opacity: 0.13, mixBlendMode: 'overlay', pointerEvents: 'none'}}>
      <svg width="100%" height="100%">
        <filter id={`g${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={seed} />
        </filter>
        <rect width="100%" height="100%" filter={`url(#g${seed})`} />
      </svg>
    </AbsoluteFill>
  );
};

/** Brand wipe: a Carbon panel with an accent leading edge sweeps across and hides the cut. */
const Wipe: React.FC = () => {
  const t = useTheme();
  const frame = useCurrentFrame(); // 0..16, cut at 8
  const x = interpolate(frame, [0, 8, 16], [-105, 0, 105], {easing: SNAP, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{transform: `translateX(${x}%) skewX(-8deg)`, background: t.colors.card}}>
      <div style={{position: 'absolute', top: 0, bottom: 0, right: 0, width: 14, background: t.colors.accent}} />
      <div style={{position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: t.colors.border}} />
    </AbsoluteFill>
  );
};

/** Film letterbox: bars ease in at the start (editorial treatment). */
const Letterbox: React.FC<{size: number}> = ({size}) => {
  const frame = useCurrentFrame();
  const p = ease(frame, [0, 16], [0, 1]);
  const bar: React.CSSProperties = {position: 'absolute', left: 0, right: 0, height: `${size * 100 * p}%`, background: '#000'};
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{...bar, top: 0}} />
      <div style={{...bar, bottom: 0}} />
    </AbsoluteFill>
  );
};

const ProgressBar: React.FC<{color: string}> = ({color}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return (
    <div style={{position: 'absolute', left: 0, top: 0, height: 10, width: `${(100 * (frame + 1)) / durationInFrames}%`, background: color, boxShadow: `0 0 12px ${color}`}} />
  );
};

export const Reel: React.FC<ReelProps> = (p) => {
  const grade = GRADES[p.look.grade] ?? GRADES.natural;
  const qaFrame = useCurrentFrame();
  const duck = useDucking(p.chunks, p.music?.volume ?? 0.1);
  const theme = React.useMemo(
    () => makeTheme({...(p.qa?.variant === 'overlay' ? {...p.theme, scrim: 0, noScrims: true} : p.theme), placement: p.placement ?? 'organic', dockStyle: p.look.dockStyle ?? 'bottom'}),
    [p.theme, p.qa?.variant, p.placement, p.look.dockStyle],
  );
  return (
    <ThemeContext.Provider value={theme}>
    <AbsoluteFill style={{background: theme.colors.bg}}>
      <DockCanvas docks={p.docks} />
      <AbsoluteFill style={{filter: grade.filter}}>
        {p.beats.map((b, i) => (
          <Sequence key={i} from={b.from} durationInFrames={b.duration}>
            <BeatClip
              beat={b}
              src={p.src}
              volume={p.sourceVolume}
              push={p.look.push}
              fit={p.look.fit ?? 'cover'}
              docks={p.docks}
              punches={p.punches}
            />
          </Sequence>
        ))}
        <BrollLayer broll={p.broll ?? []} speakerSrc={p.src} docks={p.docks} />
      </AbsoluteFill>
      {grade.tint && (
        <AbsoluteFill style={{background: grade.tint, mixBlendMode: grade.blend as never}} />
      )}
      {p.look.vignette > 0 && (
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,${p.look.vignette}) 100%)`,
          }}
        />
      )}
      {p.look.grain && <Grain />}
      {p.look.letterbox && p.qa?.variant !== 'footage' && <Letterbox size={typeof p.look.letterbox === 'number' ? p.look.letterbox : 0.085} />}
      {p.qa?.variant !== 'footage' &&
        p.beats
          .filter((b, i) => b.transition === 'wipe' && i > 0 && p.beats[i - 1].id !== b.id)
          .map((b) => (
            <Sequence key={`w${b.from}`} from={Math.max(0, b.from - 8)} durationInFrames={16}>
              <Wipe />
            </Sequence>
          ))}
      {p.qa?.variant !== 'footage' && (
        <>
          <Overlays overlays={p.overlays} />
          <GraphicsLayer graphics={p.graphics ?? []} />
          {p.captions.enabled && <Captions chunks={p.chunks} cfg={p.captions} docks={p.docks} />}
          {p.progressBar && <ProgressBar color={p.progressBar === 'accent' ? theme.colors.accent : p.progressBar} />}
        </>
      )}
      {(p.qa?.label || p.qa?.labelStep) && (
        <div style={{position: 'absolute', left: 0, top: 0, background: '#ff2d55', color: '#fff', fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 64, padding: '6px 18px'}}>
          {p.qa.label ?? Math.round(qaFrame / (p.qa.labelStep ?? 1))}
        </div>
      )}
      {(p.sfx ?? []).map((s, i) => (
        <Sequence key={`sfx${i}`} from={s.from} durationInFrames={Math.round(p.fps * 2)}>
          <Audio src={staticFile(s.src)} volume={s.volume} />
        </Sequence>
      ))}
      {p.music && <Audio src={staticFile(p.music.src)} volume={duck} loop />}
    </AbsoluteFill>
    </ThemeContext.Provider>
  );
};
