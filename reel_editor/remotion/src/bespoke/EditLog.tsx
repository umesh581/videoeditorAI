import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {useTheme} from '../theme';
import {BACK_OUT, EXPO_IN, EXPO_OUT, ease} from '../motion';

// "This reel edited itself" — ReelEditor demo. The phone-filmed screen is unreadable, so the
// canvas shows the edit log of THIS reel, printing line by line as the speaker describes each
// stage. Every number on it is real (taken from this project's own run). It ends on the receipt.

type Line = {role: string; text: string; detail?: string; at: string};
type P = {g: {scene?: string; cues: Record<string, number>; dur: number; lines?: Line[]; stats?: [string, string][]; command?: string}};

const W = 940;
const TOP = 230;
const GREY = 'rgba(255,255,255,0.55)';
const LINE = 'rgba(255,255,255,0.10)';

const Window: React.FC<{title: string; children: React.ReactNode; dur: number}> = ({title, children, dur}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const i = ease(f, [0, 14], [0, 1], BACK_OUT);
  const o = ease(f, [dur - 10, dur], [0, 1], EXPO_IN);
  return (
    <div style={{position: 'absolute', left: (1080 - W) / 2, top: TOP, width: W, opacity: Math.min(1, i * 1.4) * (1 - o),
      transform: `translateY(${(1 - i) * 60 - o * 40}px) scale(${0.96 + 0.04 * i})`, transformOrigin: '50% 0',
      background: '#0E0E0E', border: `1px solid ${LINE}`, borderRadius: 18, boxShadow: '0 30px 80px rgba(0,0,0,0.6)', overflow: 'hidden'}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 10, padding: '16px 22px', borderBottom: `1px solid ${LINE}`}}>
        {[0, 1, 2].map((k) => <span key={k} style={{width: 12, height: 12, borderRadius: 6, background: 'rgba(255,255,255,0.18)'}} />)}
        <span style={{marginLeft: 14, fontFamily: t.body, fontWeight: 500, fontSize: 22, color: GREY, letterSpacing: '0.04em'}}>{title}</span>
      </div>
      <div style={{padding: '26px 30px 30px'}}>{children}</div>
    </div>
  );
};

const Cursor: React.FC = () => {
  const t = useTheme();
  const f = useCurrentFrame();
  return <span style={{display: 'inline-block', width: 14, height: 34, marginLeft: 6, background: t.colors.accent, verticalAlign: '-6px', opacity: Math.floor(f / 8) % 2 ? 0 : 1}} />;
};

/** Cold open: the command that started this edit types itself. */
const Command: React.FC<{text: string; dur: number; zero: number}> = ({text, dur, zero}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const n = Math.round(interpolate(f, [4, 4 + text.length * 1.1], [0, text.length], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  const z = ease(f, [zero, zero + 10], [0, 1], BACK_OUT);
  return (
    <Window title="reel-studio — zsh" dur={dur}>
      <div style={{fontFamily: t.body, fontWeight: 600, fontSize: 54, color: '#fff', lineHeight: 1.25}}>
        <span style={{color: t.colors.accent}}>›</span> {text.slice(0, n)}{n < text.length && <Cursor />}
      </div>
      <div style={{marginTop: 28, display: 'flex', alignItems: 'baseline', gap: 18, opacity: z, transform: `translateY(${(1 - z) * 20}px)`}}>
        <span style={{fontFamily: t.body, fontWeight: 500, fontSize: 28, color: GREY, letterSpacing: '0.12em', textTransform: 'uppercase'}}>Hands on keyboard</span>
        <span style={{fontFamily: t.display, fontWeight: 800, fontSize: 220, lineHeight: 0.85, color: t.colors.accent, fontVariantNumeric: 'tabular-nums'}}>0</span>
      </div>
    </Window>
  );
};

/** The log: each stage prints when it is spoken; the newest line is live, older ones settle. */
const Log: React.FC<{lines: Line[]; cues: Record<string, number>; dur: number}> = ({lines, cues, dur}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const shown = lines.filter((l) => f >= (cues[l.at] ?? 1e9));
  const visible = shown.slice(-5); // the window scrolls: keep the newest five
  return (
    <Window title="edit log · ReelEditor.mp4" dur={dur}>
      <div style={{display: 'flex', flexDirection: 'column', gap: 4, minHeight: 5 * 76}}>
        {visible.map((l, k) => {
          const at = cues[l.at];
          const live = k === visible.length - 1;
          const n = Math.round(interpolate(f, [at, at + Math.max(8, l.text.length * 0.8)], [0, l.text.length], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
          const done = ease(f, [at + l.text.length * 0.8 + 4, at + l.text.length * 0.8 + 12], [0, 1]);
          const slide = ease(f, [at, at + 10], [0, 1], EXPO_OUT);
          return (
            <div key={l.at} style={{display: 'grid', gridTemplateColumns: '210px 1fr 40px', alignItems: 'baseline', columnGap: 16, padding: '10px 0',
              borderBottom: `1px solid ${LINE}`, opacity: (live ? 1 : 0.62) * slide, transform: `translateX(${(1 - slide) * -24}px)`}}>
              <span style={{fontFamily: t.body, fontWeight: 600, fontSize: 22, letterSpacing: '0.14em', textTransform: 'uppercase', color: live ? t.colors.accent : GREY}}>{l.role}</span>
              <span>
                <span style={{fontFamily: t.display, fontWeight: 700, fontSize: 36, color: '#fff'}}>{l.text.slice(0, n)}{live && n < l.text.length && <Cursor />}</span>
                {l.detail && <span style={{display: 'block', marginTop: 4, fontFamily: t.body, fontWeight: 500, fontSize: 24, color: GREY, opacity: done}}>{l.detail}</span>}
              </span>
              <svg width={34} height={34} viewBox="0 0 24 24" style={{opacity: done}}>
                <path d="M4 12.5l5 5L20 6.5" fill="none" stroke={live ? t.colors.accent : GREY} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={30} strokeDashoffset={30 * (1 - done)} />
              </svg>
            </div>
          );
        })}
      </div>
    </Window>
  );
};

/** Final receipt: raw take in, finished reel out, and what it took. */
const Receipt: React.FC<{stats: [string, string][]; cues: Record<string, number>; dur: number}> = ({stats, cues, dur}) => {
  const t = useTheme();
  const f = useCurrentFrame();
  const start = cues.stats ?? 6;
  return (
    <Window title="done · ReelEditor_v1.mp4" dur={dur}>
      {stats.map(([k, v], i) => {
        const a = ease(f, [start + i * 6, start + i * 6 + 10], [0, 1], EXPO_OUT);
        const last = i === stats.length - 1;
        return (
          <div key={k} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '16px 0',
            borderBottom: last ? 'none' : `1px solid ${LINE}`, opacity: a, transform: `translateY(${(1 - a) * 16}px)`}}>
            <span style={{fontFamily: t.body, fontWeight: 500, fontSize: 30, color: GREY}}>{k}</span>
            <span style={{fontFamily: t.display, fontWeight: 800, fontSize: last ? 76 : 44, color: last ? t.colors.accent : '#fff', fontVariantNumeric: 'tabular-nums', lineHeight: 1}}>{v}</span>
          </div>
        );
      })}
    </Window>
  );
};

export const EditLog: React.FC<P> = ({g}) => {
  const scene = g.scene ?? 'log';
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {scene === 'command' && <Command text={g.command ?? 'edit ReelEditor.mp4'} dur={g.dur} zero={g.cues.zero ?? 40} />}
      {scene === 'log' && <Log lines={g.lines ?? []} cues={g.cues} dur={g.dur} />}
      {scene === 'receipt' && <Receipt stats={g.stats ?? []} cues={g.cues} dur={g.dur} />}
    </AbsoluteFill>
  );
};
