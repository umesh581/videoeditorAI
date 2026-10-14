import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import type {ROverlay} from './types';
import {useTheme} from './theme';
import {BlurIn, Chars, DrawLine, EXPO_IN, Kinetic, Mask, ease} from './motion';

// Each overlay renders inside its own Sequence, so frame 0 = its entrance and `dur` = its exit.
const useLocal = (o: ROverlay) => ({s: useCurrentFrame(), dur: o.to - o.from});

/** Small caps label with an accent rule that draws — the brand "eyebrow". */
const Eyebrow: React.FC<{text?: string; start: number; end: number}> = ({text, start, end}) => {
  const t = useTheme();
  if (!text) return null;
  return (
    <div style={{marginBottom: 22}}>
      <div style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 26, letterSpacing: '0.2em', color: t.colors.accent, textTransform: 'uppercase'}}>
        <Kinetic text={text} start={start} end={end} stagger={2} len={12} />
      </div>
      <DrawLine start={start + 4} end={end} width={420} height={4} style={{marginTop: 14}} />
    </div>
  );
};

/** Gentle upward drift while on screen — keeps held type alive without being distracting. */
const Shift: React.FC<{s: number; children: React.ReactNode}> = ({s, children}) => (
  <div style={{transform: `translateY(${-Math.min(s, 120) * 0.12}px)`}}>{children}</div>
);

const Hook: React.FC<{o: ROverlay}> = ({o}) => {
  const t = useTheme();
  const {s, dur} = useLocal(o);
  return (
    <div style={{position: 'absolute', top: useTheme().placement === 'meta-ad' ? '15%' : '8%', left: 64, right: 150}}>
      <Shift s={s}>
        <Eyebrow text={t.eyebrow} start={0} end={dur} />
        <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: 104, lineHeight: 1.0, color: t.colors.text, letterSpacing: '-0.045em'}}>
          <Kinetic text={o.text} start={4} end={dur} stagger={3} len={16} />
        </div>
        {o.sub && (
          <BlurIn start={16} end={dur} style={{fontFamily: t.display, fontWeight: t.weights.sub, fontSize: 46, color: t.colors.muted, marginTop: 20, letterSpacing: '-0.015em'}}>
            {o.sub}
          </BlurIn>
        )}
      </Shift>
    </div>
  );
};

const Magazine: React.FC<{o: ROverlay}> = ({o}) => {
  const t = useTheme();
  const {s, dur} = useLocal(o);
  const track = ease(s, [0, 40], [-0.02, -0.065]); // tracking tightens as the letters land
  return (
    <div style={{position: 'absolute', top: t.placement === 'meta-ad' ? '15%' : '7%', left: 64, right: 150}}>
      <Eyebrow text={o.sub ?? t.eyebrow} start={0} end={dur} />
      <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: Math.min(210, Math.floor(1400 / Math.max(1, o.text.length))), lineHeight: 0.92, color: t.colors.text, letterSpacing: `${track}em`, textTransform: 'uppercase'}}>
        <Chars text={o.text} start={3} end={dur} stagger={1.6} />
      </div>
    </div>
  );
};

const Title: React.FC<{o: ROverlay}> = ({o}) => {
  const t = useTheme();
  const {s, dur} = useLocal(o);
  const open = ease(s, [0, 16], [0, 1]);
  const close = ease(s, [dur - 10, dur], [0, 1], EXPO_IN);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', paddingRight: 110}}>
      <div style={{...t.cardStyle, padding: '44px 56px', margin: 60, textAlign: 'left', clipPath: `inset(0 ${(1 - open) * 100}% 0 ${close * 100}% round ${t.radius.card}px)`}}>
        <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: 84, color: t.colors.text, lineHeight: 1.05, letterSpacing: '-0.04em'}}>
          <Kinetic text={o.text} start={6} end={dur} />
        </div>
        {o.sub && <BlurIn start={16} end={dur} style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 38, color: t.colors.muted, marginTop: 18}}>{o.sub}</BlurIn>}
      </div>
    </AbsoluteFill>
  );
};

/** Pill that grows from its left edge, then its text masks in. */
const Label: React.FC<{o: ROverlay}> = ({o}) => {
  const t = useTheme();
  const {s, dur} = useLocal(o);
  const grow = ease(s, [0, 14], [0, 1]);
  const close = ease(s, [dur - 10, dur], [0, 1], EXPO_IN);
  return (
    <div style={{position: 'absolute', top: '30%', left: 64}}>
      <div style={{display: 'inline-flex', alignItems: 'center', gap: 14, background: t.colors.card, border: `2px solid ${t.colors.border}`, borderRadius: t.radius.tag,
        padding: '12px 26px', clipPath: `inset(0 ${Math.min(1, 1 - grow + close) * 100}% 0 0 round ${t.radius.tag}px)`}}>
        <span style={{width: 12, height: 12, borderRadius: 6, background: t.colors.accent, transform: `scale(${0.6 + 0.4 * Math.abs(Math.sin(s / 9))})`}} />
        <span style={{fontFamily: t.body, fontWeight: 600, fontSize: 34, color: t.colors.text, letterSpacing: '0.12em', textTransform: 'uppercase'}}>
          <Mask start={6} end={dur}>{o.text}</Mask>
        </span>
      </div>
      {o.sub && (
        <div style={{fontFamily: t.display, fontWeight: t.weights.sub, fontSize: 42, color: t.colors.text, marginTop: 16, marginLeft: 6, letterSpacing: '-0.02em'}}>
          <Kinetic text={o.sub} start={12} end={dur} />
        </div>
      )}
    </div>
  );
};

/** CTA button: accent fills in from the left, text masks in, an arrow nudges, a shine sweeps across. */
const Cta: React.FC<{o: ROverlay}> = ({o}) => {
  const t = useTheme();
  const {s, dur} = useLocal(o);
  const fill = ease(s, [0, 16], [0, 1]);
  const close = ease(s, [dur - 10, dur], [0, 1], EXPO_IN);
  const shine = (((s - 24) % 60) + 60) % 60 / 60;
  return (
    <div style={{position: 'absolute', top: t.placement === 'meta-ad' ? '15.5%' : '11%', left: 64, right: 150}}>
      <div style={{position: 'relative', overflow: 'hidden', background: t.colors.card, border: `2px solid ${t.colors.accent}`, borderRadius: t.radius.button * 2,
        clipPath: `inset(0 0 0 ${close * 100}% round ${t.radius.button * 2}px)`}}>
        <div style={{position: 'absolute', inset: 0, background: t.colors.accent, transform: `scaleX(${fill})`, transformOrigin: 'left'}} />
        {s > 24 && <div style={{position: 'absolute', top: 0, bottom: 0, width: 120, left: `${-20 + shine * 140}%`, background: 'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.45), rgba(255,255,255,0))', transform: 'skewX(-18deg)'}} />}
        <div style={{position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, padding: '28px 36px'}}>
          <div>
            <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: 52, color: t.colors.onAccent, lineHeight: 1.1, letterSpacing: '-0.035em'}}>
              <Kinetic text={o.text} start={8} stagger={2} />
            </div>
            {o.sub && <div style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 30, color: t.colors.onAccent, opacity: 0.7, marginTop: 8}}><Mask start={14}>{o.sub}</Mask></div>}
          </div>
          <svg width={56} height={56} viewBox="0 0 24 24" style={{flex: 'none', transform: `translateX(${Math.sin(s / 6) * 5}px)`, opacity: fill}}>
            <path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke={t.colors.onAccent} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
    </div>
  );
};

/** Full-frame chapter card: paper slides in from the right, a big numeral + title mask in, then it slides away left. */
const Chapter: React.FC<{o: ROverlay}> = ({o}) => {
  const t = useTheme();
  const {s, dur} = useLocal(o);
  const inX = ease(s, [0, 12], [100, 0]);
  const outX = ease(s, [dur - 10, dur], [0, -100], EXPO_IN);
  const paper = t.colors.paper ?? t.colors.text;
  const ink = t.colors.onPaper ?? t.colors.bg;
  return (
    <AbsoluteFill style={{background: paper, transform: `translateX(${inX + outX}%)`, padding: '0 150px 0 80px', justifyContent: 'center'}}>
      <div style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 30, letterSpacing: '0.22em', textTransform: 'uppercase', color: ink, opacity: 0.55}}>
        <Mask start={8}>Chapter</Mask>
      </div>
      <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: 360, lineHeight: 0.9, letterSpacing: '-0.06em', color: ink, marginTop: 10}}>
        <Chars text={o.text} start={6} stagger={3} />
      </div>
      <DrawLine start={12} width={180} height={10} color={ink} style={{margin: '26px 0 30px'}} />
      {o.sub && (
        <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: 84, lineHeight: 1.02, letterSpacing: '-0.04em', color: ink}}>
          <Kinetic text={o.sub} start={12} stagger={3} />
        </div>
      )}
    </AbsoluteFill>
  );
};

/** Full-screen statement on paper: big black type word by word, accent bar under the last line. */
const Statement: React.FC<{o: ROverlay}> = ({o}) => {
  const t = useTheme();
  const {s, dur} = useLocal(o);
  const open = ease(s, [0, 10], [0, 1]);
  const close = ease(s, [dur - 10, dur], [0, 1], EXPO_IN);
  const ink = t.colors.onPaper ?? t.colors.bg;
  return (
    <AbsoluteFill style={{background: t.colors.paper ?? t.colors.text, clipPath: `inset(${(1 - open) * 50}% 0 ${Math.max((1 - open) * 50, close * 100)}% 0)`,
      padding: '0 160px 0 80px', justifyContent: 'center'}}>
      <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: o.text.length > 40 ? 104 : 128, lineHeight: 1.0, letterSpacing: '-0.05em', color: ink}}>
        <Kinetic text={o.text} start={4} stagger={3} len={14} />
      </div>
      {o.sub && <div style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 36, color: ink, opacity: 0.6, marginTop: 30}}><Mask start={18}>{o.sub}</Mask></div>}
      <DrawLine start={16} width={240} height={14} style={{marginTop: 36}} />
    </AbsoluteFill>
  );
};

/** Documentary name tag: accent bar draws, name and role mask in, bottom-left above the captions. */
const LowerThird: React.FC<{o: ROverlay}> = ({o}) => {
  const t = useTheme();
  const {dur} = useLocal(o);
  const ad = t.placement === 'meta-ad';
  return (
    <div style={{position: 'absolute', left: 72, bottom: ad ? '44%' : '36%', display: 'flex', gap: 22, alignItems: 'stretch'}}>
      <DrawLine start={0} end={dur} width={8} height={120} style={{transformOrigin: 'top', transform: undefined}} />
      <div>
        <div style={{fontFamily: t.display, fontWeight: t.weights.display, fontSize: 54, color: t.colors.text, letterSpacing: '-0.03em'}}><Mask start={4} end={dur}>{o.text}</Mask></div>
        {o.sub && <div style={{fontFamily: t.body, fontWeight: t.weights.label, fontSize: 30, letterSpacing: '0.12em', textTransform: 'uppercase', color: t.colors.accent, marginTop: 6}}><Mask start={9} end={dur}>{o.sub}</Mask></div>}
      </div>
    </div>
  );
};

const BY_STYLE = {hook: Hook, magazine: Magazine, title: Title, label: Label, cta: Cta, chapter: Chapter, statement: Statement, lowerthird: LowerThird};

// Brand scrim: black gradient behind text that sits over footage (top-anchored overlays).
const TopScrim: React.FC<{o: ROverlay}> = ({o}) => {
  const t = useTheme();
  const {s, dur} = useLocal(o);
  const op = ease(s, [0, 10], [0, 1]) * (1 - ease(s, [dur - 10, dur], [0, 1]));
  return <AbsoluteFill style={{opacity: op, background: `linear-gradient(180deg, rgba(0,0,0,${t.scrim}) 0%, rgba(0,0,0,${t.scrim * 0.55}) 26%, rgba(0,0,0,0) 44%)`}} />;
};

export const Overlays: React.FC<{overlays: ROverlay[]}> = ({overlays}) => {
  const t = useTheme();
  return (
    <AbsoluteFill>
      {overlays.map((o, i) => {
        const C = BY_STYLE[o.style] ?? Title;
        const top = o.style === 'hook' || o.style === 'magazine' || o.style === 'cta';
        return (
          <Sequence key={i} from={o.from} durationInFrames={Math.max(1, o.to - o.from)}>
            {top && !t.noScrims && <TopScrim o={o} />}
            <C o={o} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
