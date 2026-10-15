import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {useTheme} from '../theme';
import {BACK_OUT, EXPO_IN, EXPO_OUT, ease} from '../motion';

// "The middle-class math" (vq-d1): the speaker's OWN numbers, nothing invented. ₹7.2 L a year → tax, EMI, rent
// come out → 10–15 % is left to save (₹72,000–1,08,000, plain arithmetic on his figures).

type P = {g: {cues: Record<string, number>; dur: number; income?: number; saveLo?: number; saveHi?: number}};
const INK = '#111111', SOFT = 'rgba(17,17,17,0.55)', RULE = 'rgba(17,17,17,0.12)';
const inr = (n: number) => n.toLocaleString('en-IN');

export const SalaryMath: React.FC<P> = ({g}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const c = g.cues;
  const income = g.income ?? 720000, lo = g.saveLo ?? 10, hi = g.saveHi ?? 15;
  const cue = (k: string, d = 1e9) => c[k] ?? d;
  const enter = ease(f, [0, 14], [0, 1], BACK_OUT), leave = ease(f, [g.dur - 10, g.dur], [0, 1], EXPO_IN);
  const count = Math.round(interpolate(f, [cue('income', 6), cue('income', 6) + 22], [0, income], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EXPO_OUT}) / 1000) * 1000;
  const shrink = ease(f, [cue('save'), cue('save') + 22], [0, 1], EXPO_OUT);
  const RED = t.colors.negative, GREEN = t.colors.positive ?? '#16A34A';
  const items = [['Tax', 'tax'], ['EMI', 'emi'], ['Rent', 'rent']] as const;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 90, top: 250, width: 900, background: '#FFFFFF', borderRadius: 18, padding: '34px 42px 38px',
        boxShadow: '0 30px 70px rgba(60,45,20,0.25), 0 0 0 1px rgba(17,17,17,0.06)', opacity: Math.min(1, enter * 1.5) * (1 - leave),
        transform: `translateY(${(1 - enter) * 80 - leave * 40}px) rotate(-0.8deg)`}}>
        <div style={{fontFamily: t.body, fontWeight: 600, fontSize: 22, letterSpacing: '0.16em', textTransform: 'uppercase', color: SOFT}}>The middle-class math</div>
        <div style={{display: 'flex', alignItems: 'baseline', gap: 14, marginTop: 14}}>
          <span style={{fontFamily: t.display, fontWeight: 800, fontSize: 92, letterSpacing: '-0.03em', color: INK, fontVariantNumeric: 'tabular-nums'}}>₹{inr(count)}</span>
          <span style={{fontFamily: t.body, fontWeight: 600, fontSize: 30, color: SOFT}}>a year</span>
        </div>
        <div style={{display: 'flex', gap: 12, marginTop: 18, minHeight: 58}}>
          {items.map(([label, k]) => {
            const o = ease(f, [cue(k), cue(k) + 9], [0, 1], BACK_OUT);
            return o > 0 ? <span key={k} style={{transform: `scale(${o})`, border: `3px solid ${RED}`, color: RED, borderRadius: 999, padding: '6px 22px',
              fontFamily: t.display, fontWeight: 800, fontSize: 32, background: 'rgba(220,38,38,0.06)'}}>− {label}</span> : null;
          })}
        </div>
        <div style={{marginTop: 26, paddingTop: 22, borderTop: `2px solid ${RULE}`, opacity: f >= cue('save') ? 1 : 0}}>
          <div style={{height: 36, background: 'rgba(17,17,17,0.08)', borderRadius: 8, overflow: 'hidden'}}>
            <div style={{height: '100%', width: `${100 - (100 - hi) * shrink}%`, background: shrink > 0.95 ? GREEN : '#B9B8B0', borderRadius: 8}} />
          </div>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: 14}}>
            <span style={{fontFamily: t.display, fontWeight: 800, fontSize: 40, color: INK}}>Left to save: <span style={{color: GREEN}}>{lo}–{hi}%</span></span>
            <span style={{fontFamily: t.body, fontWeight: 600, fontSize: 26, color: SOFT, opacity: ease(f, [cue('save') + 24, cue('save') + 34], [0, 1])}}>
              ≈ ₹{inr(income * lo / 100)}–{inr(income * hi / 100)}
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
