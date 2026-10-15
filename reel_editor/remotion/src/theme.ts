import React, {createContext, useContext} from 'react';
import {fontStack} from './fonts';

// Brand theme, resolved by reel.py from reel_editor/brands/<name>.json. Every on-screen
// component takes its colours, type, radii and effects from here — nothing is hard-coded.
export interface ThemeSpec {
  name: string;
  colors: {
    accent: string; // highlights, CTAs, active states (use sparingly)
    bg: string; // canvas (slams, full-screen cards)
    text: string; // primary text
    muted: string; // secondary text, captions-in-waiting, meta
    card: string; // card / surface background
    border: string; // card borders, dividers
    onAccent: string; // text placed on the accent colour
    negative: string; // strike-throughs / "bad" side of comparisons
    paper?: string; // light card for contrast moments (video mode)
    positive?: string; // right / gain / rich (bright mode: green)
    money?: string; // ₹ amounts (bright mode: gold)
    onPaper?: string;
  };
  fonts: {display: string; body: string};
  weights: {display: number; headline: number; sub: number; body: number; label: number};
  radius: {card: number; tag: number; button: number};
  shadows: boolean; // false = flat: depth only from borders and contrast
  scrim: number; // 0..1 black gradient behind text over footage
  icons: 'line' | 'emoji';
  eyebrow?: string; // small caps label above hooks, e.g. "DIGITAL ENTREPRENEUR"
  strictAccent?: boolean;
  noScrims?: boolean;
  canvas?: 'flat' | 'lit';
  placement?: 'organic' | 'meta-ad';
  dockStyle?: 'bottom' | 'top'; // top = podcast layout: speaker in the top half, canvas below // meta-ad: keep clear of the ad header (top 14%) and CTA/primary text (bottom 35%) // lit = soft light + grain behind graphics (video mode)
  grain?: number;
  light?: boolean; // bright mode: warm-white canvas, ink text, meaning-coded colours
  dockRect?: {x: number; y: number; w: number; h: number; r: number}; // per-reel window, e.g. a round face-cam
  dockFrame?: {x: number; y: number; zoom: number};
  captionUndocked?: number; // full-screen beats: caption block top (0..1) — for close webcam shots where the face fills the lower half // what the docked window shows: source point (0..1) centred, zoomed // QA only: drop scrims/dims so overlay masks contain just text + graphics // accent budget: emphasis = underline, only the spoken word gets solid accent
}

export const DEFAULT_THEME: ThemeSpec = {
  name: 'default',
  colors: {
    accent: '#E9C46A', bg: '#111111', text: '#FFFFFF', muted: '#9A9A9A', card: '#141414',
    border: '#2A2A2A', onAccent: '#111111', negative: '#E5484D',
  },
  fonts: {display: 'Manrope', body: 'Inter'},
  weights: {display: 800, headline: 700, sub: 600, body: 400, label: 500},
  radius: {card: 24, tag: 999, button: 12},
  shadows: true,
  scrim: 0.5,
  icons: 'emoji',
};

export interface Theme extends ThemeSpec {
  display: string; // resolved CSS font stacks
  body: string;
  shadow: (css: string) => string | undefined;
  cardStyle: React.CSSProperties;
}

export const makeTheme = (spec?: Partial<ThemeSpec>): Theme => {
  const s: ThemeSpec = {
    ...DEFAULT_THEME,
    ...spec,
    colors: {...DEFAULT_THEME.colors, ...spec?.colors},
    fonts: {...DEFAULT_THEME.fonts, ...spec?.fonts},
    weights: {...DEFAULT_THEME.weights, ...spec?.weights},
    radius: {...DEFAULT_THEME.radius, ...spec?.radius},
  };
  return {
    ...s,
    display: fontStack(s.fonts.display),
    body: fontStack(s.fonts.body),
    shadow: (css) => (s.shadows ? css : undefined),
    cardStyle: {
      background: s.colors.card,
      border: `2px solid ${s.colors.border}`,
      borderRadius: s.radius.card,
      boxShadow: s.shadows ? '0 30px 80px rgba(0,0,0,0.6), 0 8px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.06)' : undefined,
    },
  };
};

export const ThemeContext = createContext<Theme>(makeTheme());
export const useTheme = () => useContext(ThemeContext);
