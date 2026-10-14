import React from 'react';
import {Composition} from 'remotion';
import {Reel} from './Reel';
import type {ReelProps} from './types';

// Placeholder props so the composition registers; real props always come from --props.
const defaultProps: ReelProps = {
  fps: 30,
  width: 1080,
  height: 1920,
  durationInFrames: 30,
  src: '',
  look: {grade: 'natural', vignette: 0, grain: false, push: false, fit: 'cover'},
  captions: {
    enabled: true,
    style: 'bold-pop',
    size: 1,
    position: 'lower',
    color: '#FFFFFF',
    highlightColor: '#F5C542',
  },
  beats: [],
  chunks: [],
  overlays: [],
  broll: [],
  graphics: [],
  sfx: [],
  progressBar: null,
  music: null,
  sourceVolume: 1,
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel as unknown as React.FC<Record<string, unknown>>}
    defaultProps={defaultProps as unknown as Record<string, unknown>}
    fps={30}
    width={1080}
    height={1920}
    durationInFrames={30}
    calculateMetadata={({props}) => {
      const p = props as unknown as ReelProps;
      return {
        durationInFrames: Math.max(1, p.durationInFrames),
        fps: p.fps,
        width: p.width,
        height: p.height,
      };
    }}
  />
);
