import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {useTheme, type Theme} from '../theme';
import {BACK_OUT, EXPO_IN, EXPO_OUT, ease} from '../motion';

// "The Payslip" — AmbitionSalar 2. One salary slip carries the whole argument: it prints, gets
// stamped, runs out of room, gains a second income line, and tears into the webinar ticket.
// It always sits in the canvas above the docked speaker (y < 0.55), clear of Instagram's rail.

type Cues = Record<string, number>;
type P = {g: {scene?: string; cues: Cues; dur: number; enter?: 'print' | 'slide'}};

const W = 700; // slip width (px)
const TOP = 250; // slip top — below Instagram's header zone
const INK = (t: Theme) => t.colors.onPaper ?? '#0A0A0A';
const PAPER = (t: Theme) => t.colors.paper ?? '#F6F5F0';
const FAINT = 'rgba(10,10,10,0.14)';
const MID = 'rgba(10,10,10,0.55)';

const cue = (c: Cues, k: string, fallback = 0) => c[k] ?? fallback;

/** Printer slot the slip feeds out of (first appearance only). */
const Slot: React.FC<{o: number}> = ({o}) => {
  const t = useTheme();
  return (
    <div style={{position: 'absolute', top: TOP - 26, left: (1080 - W - 80) / 2, width: W + 80, height: 26, borderRadius: 13,
      background: '#151515', border: '1px solid rgba(255,255,255,0.12)', opacity: o, boxShadow: '0 10px 30px rgba(0,0,0,0.6)'}}>
      <div style={{position: 'absolute', right: 22, top: 9, width: 8, height: 8, borderRadius: 4, background: t.colors.accent}} />
    </div>
  );
};

/** Zig-zag perforation strip, used for the slip's bottom edge and the ticket tear line. */
const Zigzag: React.FC<{color: string; flip?: boolean}> = ({color, flip}) => {
  const n = 28, w = W / n;
  const pts = Array.from({length: n + 1}, (_, i) => `${i * w},0 ${i * w + w / 2},14`).join(' ');
  return (
    <svg width={W} height={14} style={{display: 'block', transform: flip ? 'scaleY(-1)' : undefined}}>
      <polygon points={`0,0 ${pts} ${W},0`} fill={color} />
    </svg>
  );
};

const Header: React.FC<{right: React.ReactNode}> = ({right}) => {
  const t = useTheme();
  return (
    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', paddingBottom: 18, borderBottom: `2px solid ${INK(t)}`}}>
      <span style={{fontFamily: t.display, fontWeight: 800, fontSize: 30, letterSpacing: '0.22em', color: INK(t)}}>PAYSLIP</span>
      <span style={{fontFamily: t.body, fontWeight: 500, fontSize: 22, color: MID, fontVariantNumeric: 'tabular-nums', letterSpacing: '0.06em'}}>{right}</span>
    </div>
  );
};

/** Rubber stamp that slams onto the paper. */
const Stamp: React.FC<{at: number; text: string; sub?: string; x: number; y: number; rot?: number}> = ({at, text, sub, x, y, rot = -11}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  if (f < at) return null;
  const s = ease(f, [at, at + 7], [1.9, 1], EXPO_IN);
  const o = ease(f, [at, at + 4], [0, 0.9]);
  const shake = f < at + 10 ? Math.sin((f - at) * 2.2) * (1 - (f - at) / 10) * 6 : 0;
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: `translate(${shake}px, ${shake * 0.6}px) rotate(${rot}deg) scale(${s})`,
      opacity: o, whiteSpace: 'nowrap', border: `5px solid ${INK(t)}`, borderRadius: 10, padding: '10px 22px', color: INK(t), textAlign: 'center', mixBlendMode: 'multiply'}}>
      <div style={{fontFamily: t.display, fontWeight: 800, fontSize: 46, letterSpacing: '0.08em', lineHeight: 1}}>{text}</div>
      {sub && <div style={{fontFamily: t.body, fontWeight: 600, fontSize: 20, letterSpacing: '0.2em', marginTop: 6}}>{sub}</div>}
    </div>
  );
};

/** A receipt line: label, dotted leader, value — types on from `at`. */
const Line: React.FC<{at: number; label: string; value?: React.ReactNode; strike?: number; bold?: boolean; marker?: number}> = ({at, label, value, strike, bold, marker}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const n = Math.round(interpolate(f, [at, at + Math.max(6, label.length * 0.9)], [0, label.length], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  const o = f >= at ? 1 : 0;
  const st = strike !== undefined ? ease(f, [strike, strike + 8], [0, 1]) : 0;
  const mk = marker !== undefined ? ease(f, [marker, marker + 10], [0, 1]) : 0;
  return (
    <div style={{display: 'flex', alignItems: 'baseline', gap: 14, opacity: o, padding: '9px 0', color: st > 0.5 ? MID : INK(t)}}>
      <span style={{position: 'relative', fontFamily: t.display, fontWeight: bold ? 800 : 600, fontSize: 36, whiteSpace: 'nowrap'}}>
        <span style={{position: 'absolute', left: -8, right: -8, top: '18%', bottom: '8%', background: t.colors.accent, transform: `scaleX(${mk})`, transformOrigin: 'left', zIndex: 0}} />
        <span style={{position: 'relative'}}>{label.slice(0, n)}</span>
        <span style={{position: 'absolute', left: -4, right: -4, top: '55%', height: 4, background: INK(t), transform: `scaleX(${st})`, transformOrigin: 'left'}} />
      </span>
      <span style={{flex: 1, borderBottom: `3px dotted ${FAINT}`, transform: 'translateY(-8px)', opacity: n >= label.length ? 1 : 0}} />
      {value && <span style={{fontFamily: t.body, fontWeight: 600, fontSize: 30, fontVariantNumeric: 'tabular-nums', opacity: n >= label.length ? 1 : 0}}>{value}</span>}
    </div>
  );
};

/** Horizontal bar; grows from `at` to `to` (0..1 of track, may exceed 1 to run off the paper). */
const Bar: React.FC<{at: number; len: number; to: number; h?: number; fill: string; outline?: boolean; ease?: (n: number) => number}> = ({at, len, to, h = 30, fill, outline, ease: e = EXPO_OUT}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const w = interpolate(f, [at, at + len], [0, to], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: e});
  return <div style={{height: h, width: `${w * 100}%`, background: fill, borderRadius: 4, border: outline ? `2px solid ${INK(t)}` : undefined}} />;
};

const Label: React.FC<{children: React.ReactNode; muted?: boolean}> = ({children, muted}) => {
  const t = useTheme();
  return <div style={{fontFamily: t.body, fontWeight: 600, fontSize: 22, letterSpacing: '0.16em', textTransform: 'uppercase', color: muted ? MID : INK(t), marginBottom: 12}}>{children}</div>;
};

// ---------------------------------------------------------------- scenes

const Hook: React.FC<{c: Cues}> = ({c}) => {
  const t = useTheme();
  const s = cue(c, 'salary', 4), a = cue(c, 'ambition', 30);
  const f = useCurrentFrame();
  return (
    <>
      <Header right="MONTHLY" />
      <div style={{marginTop: 36}}>
        <Label>Salary growth</Label>
        <div style={{display: 'flex', alignItems: 'center', gap: 20}}>
          <div style={{flex: 1}}><Bar at={s} len={60} to={0.16} fill="#B9B8B0" /></div>
          <span style={{fontFamily: t.body, fontWeight: 600, fontSize: 28, color: MID, opacity: f >= s + 8 ? 1 : 0}}>+8% / yr</span>
        </div>
      </div>
      <div style={{marginTop: 40, position: 'relative'}}>
        <Label>Your ambition</Label>
        {/* runs straight off the paper and out of frame */}
        <div style={{width: 1000}}>
          <Bar at={a} len={16} to={1} h={44} fill={t.colors.accent} outline ease={EXPO_IN} />
        </div>
      </div>
    </>
  );
};

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const GROWTH = [1, 1.08, 1.17, 1.26, 1.36, 1.47];

const Appraisal: React.FC<{c: Cues}> = ({c}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const m = cue(c, 'month', 6), ap = cue(c, 'appraisal', 70), lim = cue(c, 'limit', 130);
  const mi = Math.min(11, Math.max(0, Math.floor((f - m) / 3)));
  const H = 300;
  const limitY = H - (1.5 / 1.6) * H;
  return (
    <>
      <Header right={<>CREDITED · <span style={{color: INK(t), fontWeight: 700}}>{MONTHS[mi]}</span></>} />
      <div style={{marginTop: 30, position: 'relative', height: H + 60}}>
        <Label muted>Salary · year by year</Label>
        <div style={{position: 'absolute', left: 0, right: 0, bottom: 40, height: H, display: 'flex', alignItems: 'flex-end', gap: 22}}>
          {GROWTH.map((g, i) => {
            const at = m + 8 + i * Math.max(4, (ap - m - 30) / 6);
            const h = ease(f, [at, at + 14], [0, (g / 1.6) * H], BACK_OUT);
            return <div key={i} style={{flex: 1, height: Math.max(0, h), background: i === GROWTH.length - 1 ? INK(t) : '#B9B8B0', borderRadius: 4}} />;
          })}
        </div>
        <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, display: 'flex', gap: 22}}>
          {GROWTH.map((_, i) => <span key={i} style={{flex: 1, textAlign: 'center', fontFamily: t.body, fontWeight: 600, fontSize: 20, color: MID}}>Y{i + 1}</span>)}
        </div>
        {/* the ceiling */}
        <div style={{position: 'absolute', left: -20, right: -20, bottom: 40 + H - limitY, height: 0, borderTop: `4px dashed ${INK(t)}`,
          clipPath: `inset(-10px ${(1 - ease(f, [lim, lim + 14], [0, 1])) * 100}% -10px 0)`}} />
        <div style={{position: 'absolute', right: -20, bottom: 40 + H - limitY + 12, opacity: ease(f, [lim + 8, lim + 14], [0, 1]),
          background: t.colors.accent, color: t.colors.onAccent, fontFamily: t.body, fontWeight: 700, fontSize: 22, letterSpacing: '0.16em', padding: '6px 14px', borderRadius: 6}}>
          LIMIT
        </div>
      </div>
      <Stamp at={ap} text="APPRAISAL" sub="+8% · APPROVED" x={6} y={150} rot={-7} />
    </>
  );
};

const Goals: React.FC<{c: Cues}> = ({c}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const gl = cue(c, 'goals', 4), fa = cue(c, 'family', 30), li = cue(c, 'lifestyle', 60), fr = cue(c, 'freedom', 90);
  const mv = cue(c, 'move', 130), st = cue(c, 'stamp', 150);
  return (
    <>
      <Header right="WHAT YOU NEED" />
      <div style={{marginTop: 18}}>
        <Line at={gl} label="Your goals" />
        <Line at={fa} label="Family dreams" />
        <Line at={li} label="Lifestyle" />
        <Line at={fr} label="Freedom plans" />
      </div>
      <div style={{marginTop: 22, paddingTop: 22, borderTop: `2px solid ${INK(t)}`, opacity: f >= mv ? 1 : 0}}>
        <div style={{display: 'grid', gridTemplateColumns: '150px 1fr', rowGap: 16, alignItems: 'center'}}>
          <Label>Needed</Label>
          <Bar at={mv} len={18} to={1} fill={INK(t)} />
          <Label muted>Salary</Label>
          <Bar at={mv + 6} len={40} to={0.24} fill="#B9B8B0" />
        </div>
      </div>
      <Stamp at={st} text="TOO SLOW" sub="AT SALARY SPEED" x={318} y={96} rot={-8} />
    </>
  );
};

const Second: React.FC<{c: Cues}> = ({c}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const q = cue(c, 'quit', 10), s2 = cue(c, 'second', 70);
  const tick = ease(f, [q + 4, q + 14], [0, 1]);
  return (
    <>
      <Header right="NEXT MONTH" />
      <div style={{marginTop: 30}}>
        <Label muted>Income 1 · Salary</Label>
        <div style={{display: 'flex', alignItems: 'center', gap: 20}}>
          <div style={{flex: 1}}><Bar at={-30} len={1} to={0.42} fill="#B9B8B0" /></div>
          <span style={{display: 'flex', alignItems: 'center', gap: 10, fontFamily: t.display, fontWeight: 700, fontSize: 28, color: INK(t), opacity: tick}}>
            <svg width={34} height={34} viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5" fill="none" stroke={INK(t)} strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={30} strokeDashoffset={30 * (1 - tick)} /></svg>
            Keep it
          </span>
        </div>
      </div>
      <div style={{marginTop: 38, opacity: f >= s2 ? 1 : 0}}>
        <Line at={s2} label="+ Income 2 · Yours" bold marker={s2 + 10} />
        <div style={{marginTop: 10}}><Bar at={s2 + 8} len={30} to={0.78} h={36} fill={t.colors.accent} outline /></div>
      </div>
    </>
  );
};

const Assets: React.FC<{c: Cues}> = ({c}) => {
  const r = cue(c, 'random', 4);
  return (
    <>
      <Header right="INCOME 2 · BUILT WITH AI" />
      <div style={{marginTop: 18}}>
        <Line at={r} label="Random tools" value="—" strike={r + 14} />
        <Line at={cue(c, 'services', 30)} label="Services" value="✓" />
        <Line at={cue(c, 'offers', 45)} label="Offers" value="✓" />
        <Line at={cue(c, 'systems', 60)} label="Systems" value="✓" />
        <Line at={cue(c, 'digital', 75)} label="Digital assets" value="✓" bold marker={cue(c, 'digital', 75) + 12} />
      </div>
    </>
  );
};

/** The slip's stub tears off along the perforation and becomes the webinar ticket. */
const Ticket: React.FC<{c: Cues}> = ({c}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const sun = cue(c, 'sunday', 6);
  const tear = ease(f, [sun - 2, sun + 14], [0, 1], BACK_OUT);
  const free = cue(c, 'free', sun + 30);
  return (
    <div style={{position: 'relative'}}>
      <div style={{fontFamily: t.body, fontWeight: 600, fontSize: 22, letterSpacing: '0.24em', color: MID}}>ADMIT ONE</div>
      <div style={{fontFamily: t.display, fontWeight: 800, fontSize: 92, lineHeight: 1.0, letterSpacing: '-0.02em', color: INK(t), marginTop: 14}}>This Sunday</div>
      <div style={{display: 'flex', alignItems: 'center', gap: 16, marginTop: 18}}>
        <span style={{fontFamily: t.display, fontWeight: 700, fontSize: 40, color: INK(t)}}>Live webinar</span>
        <span style={{background: t.colors.accent, color: t.colors.onAccent, fontFamily: t.body, fontWeight: 700, fontSize: 24, letterSpacing: '0.14em',
          padding: '6px 14px', borderRadius: 6, transform: `scale(${ease(f, [free, free + 8], [0, 1], BACK_OUT)})`}}>FREE</span>
      </div>
      <div style={{marginTop: 16, fontFamily: t.body, fontWeight: 500, fontSize: 28, color: MID}}>Telugu + English · Online</div>
      {/* the payslip it tore from: lifts away along the perforation */}
      <div style={{position: 'absolute', left: -52, right: -52, top: -56 - 150, height: 150, background: PAPER(t), padding: '40px 52px 0',
        transform: `translate(${tear * -60}px, ${tear * -220}px) rotate(${tear * -9}deg)`, transformOrigin: '0 100%', opacity: 1 - ease(f, [sun + 8, sun + 18], [0, 1])}}>
        <Header right="MONTHLY" />
      </div>
      <div style={{position: 'absolute', left: -52, right: -52, top: -56, borderTop: `4px dashed ${FAINT}`}} />
    </div>
  );
};

// ---------------------------------------------------------------- shell

export const Payslip: React.FC<P> = ({g}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const {dur, cues: c} = g;
  const scene = g.scene ?? 'hook';
  const print = (g.enter ?? 'slide') === 'print';
  // entry: printed out of the slot (with stepper judder) or slid back up into view
  const inP = print ? interpolate(f, [0, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : ease(f, [0, 14], [0, 1], BACK_OUT);
  const judder = print && f < 22 ? (Math.floor(f / 2) % 2) * 3 : 0;
  const out = ease(f, [dur - 10, dur], [0, 1], EXPO_IN);
  const ticket = scene === 'ticket';
  const tear = ticket ? ease(f, [cue(c, 'sunday', 6) - 2, cue(c, 'sunday', 6) + 14], [0, 1], BACK_OUT) : 0;
  const ty = print ? (inP - 1) * 820 + judder : (1 - inP) * 140;
  const rot = ticket ? -1.5 + tear * 4 : -1.5;
  const body = {
    hook: <Hook c={c} />,
    appraisal: <Appraisal c={c} />,
    goals: <Goals c={c} />,
    second: <Second c={c} />,
    assets: <Assets c={c} />,
    ticket: <Ticket c={c} />,
  }[scene];
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {print && <Slot o={1 - out} />}
      <div style={{position: 'absolute', left: 0, right: 0, top: TOP, bottom: 0, overflow: print ? 'hidden' : 'visible'}}>
        <div style={{position: 'absolute', left: (1080 - W) / 2, top: 0, width: W,
          transform: `translateY(${ty - out * 60}px) rotate(${rot}deg) scale(1.1)`, transformOrigin: '50% 0', opacity: (print ? 1 : inP) * (1 - out),
          filter: 'drop-shadow(0 30px 40px rgba(0,0,0,0.55))'}}>
          <div style={{background: PAPER(t), padding: ticket ? '56px 52px 48px' : '40px 52px 44px', position: 'relative'}}>
            {/* paper tooth */}
            <div style={{position: 'absolute', inset: 0, opacity: 0.35, mixBlendMode: 'multiply',
              backgroundImage: 'radial-gradient(rgba(0,0,0,0.05) 1px, transparent 1px)', backgroundSize: '5px 5px'}} />
            <div style={{position: 'relative'}}>{body}</div>
          </div>
          <Zigzag color={PAPER(t)} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
