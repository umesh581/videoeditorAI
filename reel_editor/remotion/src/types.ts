// Resolved render props. Produced by reel.py from storyboard.json + transcript.json —
// everything here is already in OUTPUT frames, so the components never do timeline math.

export type Grade = 'natural' | 'warm' | 'moody' | 'punchy' | 'bw' | 'film';
export type CaptionStyle = 'premium' | 'editorial' | 'kinetic' | 'bold-pop' | 'editorial-serif' | 'minimal' | 'huge';
export type EmphasisStyle = 'gold' | 'strike' | 'big' | 'color';
export type OverlayStyle = 'hook' | 'magazine' | 'title' | 'label' | 'cta' | 'chapter' | 'statement' | 'lowerthird';
export type Transition = 'cut' | 'flash' | 'zoom' | 'wipe' | 'whip';

export interface RWord {
  text: string;
  from: number; // output frame
  to: number;
  emphasis?: EmphasisStyle;
}

export interface RChunk {
  from: number;
  to: number;
  words: RWord[];
}

export interface ROverlay {
  text: string;
  sub?: string;
  style: OverlayStyle;
  from: number;
  to: number;
}

export interface RBeat {
  id: number;
  from: number; // output frame where the beat starts
  duration: number; // frames
  trimBefore: number; // source frame
  zoom: number;
  focusX: number; // 0..1
  focusY: number;
  transition: Transition;
  mono?: boolean;
}

export type BrollMode = 'full' | 'pip' | 'split' | 'card';

export interface RBroll {
  src: string; // path under public/
  kind: 'video' | 'image';
  from: number;
  to: number;
  clipStart: number; // frame offset into the b-roll clip
  mode: BrollMode;
  speakerTrim: number; // source frame of the speaker at `from` (pip/split)
  focusX: number;
  focusY: number;
  label?: string;
}

export interface RIcon {
  name: string;
  path?: string; // simple-icons SVG path (24x24 viewBox); absent -> monogram tile
  hex?: string;
  strike?: boolean;
  image?: string; // or an image under public/
}

// Graphics are a tagged union; `from`/`to` are output frames, `items[].at` is output frames too.
export type RGraphic = {from: number; to: number; pos?: 'top' | 'center' | 'bottom' | 'canvas'} & (
  | {type: 'bespoke'; name: string; scene?: string; cues: Record<string, number>; [k: string]: unknown}
  | {type: 'cards'; images: string[]; frame?: 'plain' | 'browser' | 'phone'; caption?: string}
  | {type: 'logos'; items: RIcon[]; title?: string}
  | {type: 'counter'; value: number; prefix?: string; suffix?: string; label?: string; decimals?: number}
  | {type: 'checklist'; title?: string; items: {text: string; at: number}[]}
  | {type: 'flow'; title?: string; items: {text: string; at: number; icon?: string}[]}
  | {type: 'notify'; items: {app: string; title: string; body: string; icon?: string; time?: string; at: number}[]}
  | {type: 'event'; day: string; date?: string; title: string; details?: string[]; tag?: string}
  | {type: 'highlight'; box: [number, number, number, number]; label?: string}
  | {type: 'compare'; left: {title: string; items: string[]}; right: {title: string; items: string[]}}
  | {type: 'prompt'; text: string; who?: string; status?: string}
  | {type: 'slam'; words: {text: string; at: number}[]; bg?: string; color?: string}
  | {type: 'sticker'; emoji?: string; icon?: string; accent?: boolean; image?: string; x: number; y: number; size?: number}
);

export interface RSfx {
  src: string;
  from: number;
  volume: number;
}

import type {ThemeSpec} from './theme';

export interface ReelProps {
  theme?: Partial<ThemeSpec>;
  placement?: 'organic' | 'meta-ad';
  docks?: [number, number][]; // output-frame windows where the speaker is docked
  punches?: number[]; // output frames of snap punch-ins
  qa?: {variant: 'full' | 'overlay' | 'footage'; label?: string; labelStep?: number}; // QA renders: footage = no overlays (for occlusion masks)
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  src: string; // path under public/
  look: {grade: Grade; vignette: number; grain: boolean; push: boolean; fit: 'cover' | 'blur'; letterbox?: boolean | number; dockStyle?: 'bottom' | 'top'};
  captions: {
    enabled: boolean;
    style: CaptionStyle;
    size: number;
    position: 'lower' | 'center' | 'upper';
    color: string;
    highlightColor: string;
  };
  beats: RBeat[];
  chunks: RChunk[];
  overlays: ROverlay[];
  broll: RBroll[];
  graphics: RGraphic[];
  sfx: RSfx[];
  progressBar: string | null; // color, or null for none
  music: {src: string; volume: number} | null;
  sourceVolume: number;
}
