import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {useTheme, type Theme} from '../theme';
import {BACK_OUT, EXPO_IN, EXPO_OUT, ease} from '../motion';

// Four one-off hero pieces for the VidIQ long-video clips (15 Oct 2026). Bright Ledger palette:
// green = right/gain, red = wrong/limit, gold = money, lime = highlighter only.

type Cues = Record<string, number>;
type P = {g: {scene?: string; cues: Cues; dur: number}};
const cue = (c: Cues, k: string, d = 0) => c[k] ?? d;
const INK = '#111111';
const SOFT = 'rgba(17,17,17,0.55)';
const RULE = 'rgba(17,17,17,0.12)';
const GREEN = (t: Theme) => t.colors.positive ?? '#16A34A';
const RED = (t: Theme) => (t.light ? t.colors.negative : '#DC2626');

/** Shell: a card that settles into the canvas and lifts away at the end. */
const Shell: React.FC<{dur: number; w?: number; top?: number; rot?: number; bg?: string; children: React.ReactNode; pad?: string}> = ({dur, w = 900, top = 250, rot = -1, bg = '#FFFFFF', children, pad = '40px 46px'}) => {
  const f = useCurrentFrame();
  const i = ease(f, [0, 14], [0, 1], BACK_OUT);
  const o = ease(f, [dur - 10, dur], [0, 1], EXPO_IN);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: (1080 - w) / 2, top, width: w, background: bg, borderRadius: 18, padding: pad,
        transform: `translateY(${(1 - i) * 90 - o * 50}px) rotate(${rot}deg) scale(${0.95 + 0.05 * i})`, opacity: Math.min(1, i * 1.5) * (1 - o),
        boxShadow: '0 30px 70px rgba(60,45,20,0.25), 0 0 0 1px rgba(17,17,17,0.06)'}}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

const Stamp: React.FC<{at: number; text: string; color: string; x: number; y: number; rot?: number; size?: number}> = ({at, text, color, x, y, rot = -9, size = 54}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  if (f < at) return null;
  const s = ease(f, [at, at + 7], [1.9, 1], EXPO_IN);
  const shake = f < at + 10 ? Math.sin((f - at) * 2.2) * (1 - (f - at) / 10) * 6 : 0;
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: `translate(${shake}px,${shake * 0.6}px) rotate(${rot}deg) scale(${s})`, opacity: ease(f, [at, at + 4], [0, 0.92]),
      border: `6px solid ${color}`, borderRadius: 10, padding: '6px 20px', color, fontFamily: t.display, fontWeight: 800, fontSize: size, letterSpacing: '0.06em', whiteSpace: 'nowrap', mixBlendMode: 'multiply'}}>
      {text}
    </div>
  );
};

const Label: React.FC<{children: React.ReactNode; color?: string}> = ({children, color = SOFT}) => {
  const t = useTheme();
  return <div style={{fontFamily: t.body, fontWeight: 600, fontSize: 22, letterSpacing: '0.16em', textTransform: 'uppercase', color}}>{children}</div>;
};

const Strike: React.FC<{at: number; color: string}> = ({at, color}) => {
  const f = useCurrentFrame();
  return <span style={{position: 'absolute', left: -6, right: -6, top: '52%', height: 5, background: color, transform: `scaleX(${ease(f, [at, at + 9], [0, 1])})`, transformOrigin: 'left'}} />;
};

// ---------------------------------------------------------------- 1. Timecard (education built for factories)

export const Timecard: React.FC<P> = ({g}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const c = g.cues;
  const rows: [string, string][] = [['Name', 'Graduate'], ['Trained to', 'Follow instructions'], ['Degree', 'B.Tech · B.Com · MBA'], ['Shift', '9:00 – 6:00']];
  const punch = (k: string) => ease(f, [cue(c, k, 1e9), cue(c, k, 1e9) + 5], [0, 1]);
  return (
    <Shell dur={g.dur} bg="#F3EAD3" rot={-1.5} pad="34px 42px 40px">
      <div style={{position: 'relative'}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderBottom: `3px solid ${INK}`, paddingBottom: 12}}>
          <span style={{fontFamily: t.display, fontWeight: 800, fontSize: 34, letterSpacing: '0.18em', color: INK}}>TIME CARD</span>
          <span style={{fontFamily: t.body, fontWeight: 700, fontSize: 30, color: RED(t), letterSpacing: '0.1em'}}>EST. 1947</span>
        </div>
        {rows.map(([k, v], i) => (
          <div key={k} style={{display: 'grid', gridTemplateColumns: '210px 1fr 40px', alignItems: 'center', padding: '15px 0', borderBottom: `1px dashed ${RULE}`,
            opacity: ease(f, [6 + i * 5, 14 + i * 5], [0, 1])}}>
            <Label>{k}</Label>
            <span style={{position: 'relative', fontFamily: t.display, fontWeight: 700, fontSize: 36, color: INK, justifySelf: 'start'}}>
              {v}{k === 'Degree' && <Strike at={cue(c, 'degree', 1e9)} color={RED(t)} />}
            </span>
            {/* punched hole */}
            <span style={{width: 26, height: 26, borderRadius: 13, background: '#2A2420', opacity: punch(`p${i}`), justifySelf: 'end'}} />
          </div>
        ))}
        <Stamp at={cue(c, 'obedient', 1e9)} text="OBEDIENT" color={RED(t)} x={430} y={70} rot={-8} />
        <Stamp at={cue(c, 'replaced', 1e9)} text="REPLACEABLE" color={RED(t)} x={250} y={250} rot={6} size={60} />
      </div>
    </Shell>
  );
};

// ---------------------------------------------------------------- 2. Handover (my business runs on AI)

export const Handover: React.FC<P> = ({g}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const c = g.cues;
  if (g.scene === 'security') {
    const a = cue(c, 'job', 6), b = cue(c, 'skills', 40);
    return (
      <Shell dur={g.dur}>
        <Label>What actually protects you</Label>
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 22, marginTop: 22}}>
          {[{k: 'A job', sub: 'even a good one', at: a, good: false}, {k: 'Skills', sub: '+ market demand', at: b, good: true}].map((x) => {
            const o = ease(f, [x.at, x.at + 10], [0, 1], BACK_OUT);
            const col = x.good ? GREEN(t) : RED(t);
            return (
              <div key={x.k} style={{border: `3px solid ${col}`, borderRadius: 16, padding: '26px 24px', opacity: o, transform: `scale(${0.9 + 0.1 * o})`, background: x.good ? 'rgba(22,163,74,0.06)' : 'rgba(220,38,38,0.05)'}}>
                <div style={{fontFamily: t.display, fontWeight: 800, fontSize: 52, color: INK, position: 'relative', display: 'inline-block'}}>
                  {x.k}{!x.good && <Strike at={x.at + 12} color={RED(t)} />}
                </div>
                <div style={{fontFamily: t.body, fontWeight: 500, fontSize: 28, color: SOFT, marginTop: 6}}>{x.sub}</div>
                <div style={{marginTop: 16, fontFamily: t.body, fontWeight: 700, fontSize: 26, color: col}}>{x.good ? '✓ Security' : '✕ Not security'}</div>
              </div>
            );
          })}
        </div>
      </Shell>
    );
  }
  const tasks = [['Content creation', 'content'], ['Data analysis', 'data'], ['Automation', 'automation'], ['Customer service', 'customer']];
  const out = cue(c, 'output', 1e9), team = cue(c, 'people', 1e9), cl = cue(c, 'clients', 1e9), rev = cue(c, 'revenue', 1e9);
  const pts = Array.from({length: 9}, (_, i) => 70 - i * i * 0.8);
  const draw = ease(f, [out, out + 24], [0, 1]);
  return (
    <Shell dur={g.dur} pad="28px 40px 28px">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
        <Label color={INK}>My business · this month</Label>
        <Label>who does it</Label>
      </div>
      <div style={{marginTop: 10}}>
        {tasks.map(([name, k]) => {
          const on = ease(f, [cue(c, k, 1e9), cue(c, k, 1e9) + 8], [0, 1]);
          return (
            <div key={k} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: `1px solid ${RULE}`}}>
              <span style={{fontFamily: t.display, fontWeight: 700, fontSize: 34, color: INK}}>{name}</span>
              <span style={{display: 'flex', alignItems: 'center', gap: 12, fontFamily: t.body, fontWeight: 700, fontSize: 24, color: on > 0.5 ? GREEN(t) : SOFT}}>
                {on > 0.5 ? 'AI' : 'Me'}
                <span style={{width: 66, height: 36, borderRadius: 18, background: on > 0.5 ? GREEN(t) : 'rgba(17,17,17,0.15)', position: 'relative'}}>
                  <span style={{position: 'absolute', top: 4, left: 4 + 30 * on, width: 28, height: 28, borderRadius: 14, background: '#fff'}} />
                </span>
              </span>
            </div>
          );
        })}
      </div>
      <div style={{display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 24, marginTop: 12, alignItems: 'end'}}>
        <div style={{opacity: f >= out ? 1 : 0}}>
          <Label>Output</Label>
          <svg width={440} height={76} viewBox="0 0 440 90" style={{marginTop: 4}}>
            <polyline points={pts.map((y, i) => `${i * 55},${y + 12}`).join(' ')} fill="none" stroke={GREEN(t)} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round"
              strokeDasharray={600} strokeDashoffset={600 * (1 - draw)} />
          </svg>
        </div>
        <div style={{display: 'flex', flexDirection: 'column', gap: 10}}>
          {[['People added', '0', team, INK], ['Clients', '↑', cl, GREEN(t)], ['Revenue', '↑', rev, GREEN(t)]].map(([k, v, at, col]) => (
            <div key={k as string} style={{display: 'flex', justifyContent: 'space-between', opacity: ease(f, [at as number, (at as number) + 8], [0, 1])}}>
              <span style={{fontFamily: t.body, fontWeight: 500, fontSize: 26, color: SOFT}}>{k}</span>
              <span style={{fontFamily: t.display, fontWeight: 800, fontSize: 34, color: col as string}}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
};

// ---------------------------------------------------------------- 3. Week (three moves, mapped onto your week)

export const Week: React.FC<P> = ({g}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const c = g.cues;
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const ai = cue(c, 'ai', 1e9), hand = cue(c, 'hand', 1e9), first = cue(c, 'first', 1e9), skills = cue(c, 'skills', 1e9), side = cue(c, 'side', 1e9), weekend = cue(c, 'weekend', 1e9);
  const chips = [['marketing', 'Marketing'], ['sales', 'Sales'], ['consulting', 'Consulting'], ['copywriting', 'Copywriting']];
  return (
    <Shell dur={g.dur} pad="30px 34px 34px">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14}}>
        <Label color={INK}>Your week, rebuilt</Label>
        <span style={{fontFamily: t.body, fontWeight: 700, fontSize: 22, color: GREEN(t), opacity: ease(f, [first, first + 8], [0, 1])}}>1st-mover advantage</span>
      </div>
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8}}>
        {days.map((d, i) => {
          const wk = i >= 5;
          const fill = wk ? ease(f, [Math.min(side, weekend) + (i - 5) * 4, Math.min(side, weekend) + (i - 5) * 4 + 10], [0, 1]) : 1;
          return (
            <div key={d} style={{display: 'flex', flexDirection: 'column', gap: 6}}>
              <div style={{textAlign: 'center', fontFamily: t.body, fontWeight: 700, fontSize: 22, color: wk ? INK : SOFT}}>{d}</div>
              {/* day: job block */}
              <div style={{height: 150, borderRadius: 10, background: wk ? `rgba(22,163,74,${0.12 + 0.75 * fill})` : 'rgba(17,17,17,0.07)', position: 'relative', overflow: 'hidden',
                display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 4}}>
                {!wk && <span style={{fontFamily: t.body, fontWeight: 600, fontSize: 18, color: SOFT, writingMode: 'vertical-rl', transform: 'rotate(180deg)'}}>Office job</span>}
                {!wk && <span style={{position: 'absolute', left: 4, right: 4, bottom: 4, height: 30, borderRadius: 6, background: t.colors.accent, transform: `scaleY(${ease(f, [ai + i * 2, ai + i * 2 + 8], [0, 1])})`, transformOrigin: 'bottom',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: t.body, fontWeight: 800, fontSize: 18, color: t.colors.onAccent}}>+AI</span>}
                {wk && <span style={{fontFamily: t.body, fontWeight: 800, fontSize: 20, color: '#fff', opacity: fill, writingMode: 'vertical-rl', transform: 'rotate(180deg)'}}>Side income</span>}
              </div>
              {/* evening: skill block */}
              <div style={{height: 60, borderRadius: 10, background: !wk && f >= skills ? 'rgba(245,184,0,0.25)' : 'rgba(17,17,17,0.04)', border: !wk && f >= skills ? `2px solid ${t.colors.money ?? '#F5B800'}` : '2px solid transparent'}} />
            </div>
          );
        })}
      </div>
      <div style={{display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 18, minHeight: 50}}>
        {f >= skills && <span style={{fontFamily: t.body, fontWeight: 600, fontSize: 22, color: SOFT, alignSelf: 'center'}}>Evenings:</span>}
        {chips.map(([k, label]) => {
          const o = ease(f, [cue(c, k, 1e9), cue(c, k, 1e9) + 8], [0, 1], BACK_OUT);
          return o > 0 ? <span key={k} style={{transform: `scale(${o})`, background: '#FFF4CC', border: `2px solid ${t.colors.money ?? '#F5B800'}`, borderRadius: 999, padding: '6px 16px',
            fontFamily: t.display, fontWeight: 700, fontSize: 26, color: INK}}>{label}</span> : null;
        })}
      </div>
      {/* the ask from work: someone to hand-hold them */}
      <div style={{position: 'absolute', right: -20, top: 120, width: 400, background: INK, color: '#fff', borderRadius: 18, borderBottomRightRadius: 4, padding: '16px 20px',
        opacity: ease(f, [hand, hand + 8], [0, 1]) * (1 - ease(f, [skills - 6, skills], [0, 1])), transform: `translateY(${(1 - ease(f, [hand, hand + 10], [0, 1], BACK_OUT)) * 30}px)`,
        boxShadow: '0 20px 40px rgba(0,0,0,0.25)'}}>
        <div style={{fontFamily: t.body, fontWeight: 600, fontSize: 18, opacity: 0.6}}>Your manager</div>
        <div style={{fontFamily: t.display, fontWeight: 700, fontSize: 28, marginTop: 4, lineHeight: 1.2}}>Can you show the team how you did this?</div>
      </div>
    </Shell>
  );
};

// ---------------------------------------------------------------- 4. Seminar (positive thinking keeps you broke)

export const Seminar: React.FC<P> = ({g}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const c = g.cues;
  if (g.scene === 'salary') {
    const a = cue(c, 'later', 10), s = cue(c, 'same', 40), b = cue(c, 'broke', 70);
    const years = ['Year 1', 'Year 2', 'Year 3'];
    return (
      <Shell dur={g.dur}>
        <Label>Salary after the seminar</Label>
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18, marginTop: 20}}>
          {years.map((y, i) => {
            const o = ease(f, [a + i * 8, a + i * 8 + 10], [0, 1], BACK_OUT);
            return (
              <div key={y} style={{opacity: o, transform: `translateY(${(1 - o) * 20}px)`, borderRadius: 14, border: `2px solid ${RULE}`, padding: '18px 16px'}}>
                <Label>{y}</Label>
                <div style={{fontFamily: t.display, fontWeight: 800, fontSize: 50, color: f >= s ? RED(t) : INK, marginTop: 6, fontVariantNumeric: 'tabular-nums'}}>₹30,000</div>
              </div>
            );
          })}
        </div>
        <div style={{height: 6, marginTop: 26, background: RED(t), borderRadius: 3, transform: `scaleX(${ease(f, [s, s + 14], [0, 1])})`, transformOrigin: 'left'}} />
        <div style={{display: 'flex', justifyContent: 'space-between', marginTop: 12, fontFamily: t.body, fontWeight: 700, fontSize: 28}}>
          <span style={{color: RED(t), opacity: ease(f, [s, s + 10], [0, 1])}}>Same salary</span>
          <span style={{color: RED(t), opacity: ease(f, [b, b + 10], [0, 1])}}>Still broke</span>
        </div>
      </Shell>
    );
  }
  const scam = cue(c, 'scam', 1e9), trap = cue(c, 'trap', 1e9), aff = cue(c, 'rich', 1e9);
  const tear = ease(f, [trap, trap + 14], [0, 1], BACK_OUT);
  const lines = ['Visualise it.', 'Affirm it.', 'Attract it.'];
  return (
    <Shell dur={g.dur} bg="#FFFFFF" rot={-2} pad="0">
      <div style={{display: 'flex', position: 'relative'}}>
        <div style={{flex: 1, padding: '38px 40px', background: 'linear-gradient(135deg,#FFF7DB,#FFE7A3)', borderRadius: '18px 0 0 18px',
          transform: `translate(${-tear * 30}px, ${tear * 18}px) rotate(${-tear * 5}deg)`}}>
          <Label color="#8A6400">Live seminar · this weekend</Label>
          <div style={{fontFamily: t.display, fontWeight: 800, fontSize: 64, lineHeight: 1.0, color: INK, marginTop: 12, letterSpacing: '-0.02em'}}>Millionaire<br />Mindset</div>
          <div style={{marginTop: 16, display: 'flex', gap: 14, flexWrap: 'wrap'}}>
            {lines.map((l, i) => <span key={l} style={{fontFamily: t.body, fontWeight: 600, fontSize: 26, color: '#5A4300', opacity: ease(f, [aff + i * 6, aff + i * 6 + 8], [0, 1])}}>{l}</span>)}
          </div>
        </div>
        <div style={{width: 210, padding: '38px 24px', borderLeft: '4px dashed rgba(17,17,17,0.25)', background: '#FFF7DB', borderRadius: '0 18px 18px 0',
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between', transform: `translate(${tear * 30}px, ${-tear * 10}px) rotate(${tear * 6}deg)`}}>
          <Label color="#8A6400">Admit one</Label>
          <div style={{fontFamily: t.display, fontWeight: 800, fontSize: 46, color: INK}}>₹4,999</div>
        </div>
        <Stamp at={scam} text="SCAM" color={RED(t)} x={250} y={110} rot={-12} size={96} />
      </div>
    </Shell>
  );
};
