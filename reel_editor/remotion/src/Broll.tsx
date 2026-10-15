import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {RBroll} from './types';
import {useTheme} from './theme';
import {EXPO_IN, Mask, dockAmount, dockRect, ease} from './motion';

// Fills its box with the b-roll clip or a Ken-Burns'd still.
const Media: React.FC<{b: RBroll; dur: number}> = ({b, dur}) => {
  const frame = useCurrentFrame();
  const pos = `${b.focusX * 100}% ${b.focusY * 100}%`;
  const style: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover', objectPosition: pos};
  if (b.kind === 'image') {
    const s = interpolate(frame, [0, dur], [1.04, 1.16]);
    const x = interpolate(frame, [0, dur], [-1.5, 1.5]);
    return (
      <Img
        src={staticFile(b.src)}
        style={{...style, transform: `scale(${s}) translateX(${x}%)`, transformOrigin: pos}}
      />
    );
  }
  const s = interpolate(frame, [0, dur], [1.0, 1.06]);
  return (
    <OffthreadVideo
      src={staticFile(b.src)}
      trimBefore={b.clipStart}
      muted
      style={{...style, transform: `scale(${s})`, transformOrigin: pos}}
    />
  );
};

// The speaker, re-rendered from the source at the right moment (for pip/split).
const Speaker: React.FC<{src: string; trim: number; dur: number; style?: React.CSSProperties}> = ({
  src,
  trim,
  dur,
  style,
}) => (
  <OffthreadVideo
    src={staticFile(src)}
    trimBefore={trim}
    trimAfter={trim + dur}
    muted
    style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: '50% 42%', ...style}}
  />
);

const Clip: React.FC<{b: RBroll; speakerSrc: string; docks?: [number, number][]}> = ({b, speakerSrc, docks}) => {
  const t = useTheme();
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const d = dockAmount(docks, b.from + frame);
  const dur = b.to - b.from;
  // masked in/out — no cross-fades (they leave ghosted double images)
  const open = ease(frame, [0, 12], [0, 1]);
  const close = ease(frame, [dur - 10, dur], [0, 1], EXPO_IN);

  const label = b.label ? (
    <div style={{position: 'absolute', top: b.mode === 'split' ? 'calc(50% - 90px)' : '12%', left: 50}}>
      <Mask start={8} end={dur}>
        <span style={{display: 'inline-block', background: t.colors.card, border: `2px solid ${t.colors.border}`, color: t.colors.text, fontFamily: t.body,
          fontWeight: t.weights.label, fontSize: 36, letterSpacing: '0.12em', textTransform: 'uppercase', padding: '10px 20px', borderRadius: t.radius.tag}}>
          {b.label}
        </span>
      </Mask>
    </div>
  ) : null;

  if (b.mode === 'card') {
    // Framed clip on the brand canvas above the docked speaker (e.g. AI-generated / Flow clips):
    // the clip keeps its own frame — watermark included — and reads as a designed element.
    const float = Math.sin(frame / 30) * 6;
    const lift = ease(frame, [0, 18], [0, 1]);
    return (
      <AbsoluteFill style={{height: '50%', bottom: 'auto', justifyContent: 'center', alignItems: 'center', paddingTop: '7%', paddingLeft: 40, paddingRight: 150, perspective: 1600}}>
        <div style={{width: 820, transform: `translateY(${(1 - lift) * 80 + float - close * 60}px) rotateX(${(1 - lift) * 18}deg)`, opacity: 1 - close}}>
          {b.label && (
            <div style={{marginBottom: 14}}>
              <Mask start={10} end={dur}>
                <span style={{display: 'inline-flex', alignItems: 'center', gap: 10, fontFamily: t.body, fontWeight: t.weights.label, fontSize: 26, letterSpacing: '0.18em', textTransform: 'uppercase', color: t.light ? t.colors.text : t.colors.accent}}>
                  <span style={{width: 10, height: 10, borderRadius: 5, background: t.light ? t.colors.negative : t.colors.accent}} />
                  {b.label}
                </span>
              </Mask>
            </div>
          )}
          <div style={{position: 'relative', aspectRatio: '16 / 9', borderRadius: t.radius.card, overflow: 'hidden', border: `2px solid ${t.colors.border}`,
            background: t.colors.card, clipPath: `inset(${(1 - open) * 50}% 0 ${(1 - open) * 50}% 0 round ${t.radius.card}px)`}}>
            <Media b={b} dur={dur} />
          </div>
          {/* licence credit (CC BY requires attribution) */}
          {(b as {credit?: string}).credit && <div style={{marginTop: 8, fontFamily: t.body, fontWeight: 500, fontSize: 17, color: t.light ? 'rgba(17,17,17,0.55)' : 'rgba(255,255,255,0.55)'}}>{(b as {credit?: string}).credit}</div>}
        </div>
      </AbsoluteFill>
    );
  }

  if (b.mode === 'split') {
    // speaker fills the bottom half at once; the b-roll unrolls down from the top, the divider draws across
    return (
      <AbsoluteFill style={{clipPath: `inset(0 0 ${close * 100}% 0)`}}>
        <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: '50%', overflow: 'hidden', background: 'black'}}>
          <Speaker src={speakerSrc} trim={b.speakerTrim} dur={dur} />
        </div>
        <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: '50%', overflow: 'hidden', clipPath: `inset(0 0 ${(1 - open) * 100}% 0)`}}>
          <Media b={b} dur={dur} />
        </div>
        <div style={{position: 'absolute', left: 0, right: 0, top: 'calc(50% - 3px)', height: 6, background: t.colors.accent, transform: `scaleX(${ease(frame, [4, 18], [0, 1])})`, transformOrigin: 'left'}} />
        {label}
      </AbsoluteFill>
    );
  }

  // full / pip: the b-roll opens as a band from the centre and closes upward on exit
  const half = (1 - open) * 50;
  const R = dockRect(t.placement, t.dockStyle, t.dockRect); // while the speaker is docked, b-roll plays inside the same window
  const dockBox: React.CSSProperties = d > 0.01 ? {left: R.x * width * d, top: R.y * height * d, width: width * (1 - (1 - R.w) * d),
    height: height * (1 - (1 - R.h) * d), right: 'auto', bottom: 'auto', borderRadius: R.r * d, overflow: 'hidden'} : {};
  return (
    <AbsoluteFill style={{clipPath: `inset(${half}% 0 ${Math.max(half, close * 100)}% 0)`, ...dockBox}}>
      <AbsoluteFill style={{transform: `scale(${1.06 - 0.06 * open})`, overflow: 'hidden'}}>
        <Media b={b} dur={dur} />
      </AbsoluteFill>
      {b.mode === 'pip' && (
        <div style={{position: 'absolute', left: 56, bottom: '30%', width: 330, height: 330, borderRadius: '50%', overflow: 'hidden', border: `4px solid ${t.colors.accent}`, transform: `scale(${open})`}}>
          <Speaker src={speakerSrc} trim={b.speakerTrim} dur={dur} />
        </div>
      )}
      {label}
    </AbsoluteFill>
  );
};

export const BrollLayer: React.FC<{broll: RBroll[]; speakerSrc: string; docks?: [number, number][]}> = ({broll, speakerSrc, docks}) => (
  <AbsoluteFill>
    {broll.map((b, i) => (
      <Sequence key={i} from={b.from} durationInFrames={Math.max(1, b.to - b.from)}>
        <Clip b={b} speakerSrc={speakerSrc} docks={docks} />
      </Sequence>
    ))}
  </AbsoluteFill>
);
