import type React from 'react';
import {EditLog} from './EditLog';
import {Handover, Seminar, Timecard, Week} from './Oct15';
import {Payslip} from './Payslip';

// Hand-built hero scenes, one per reel concept. Storyboards use them as
// {"type": "bespoke", "name": "<key>", "scene": "...", "cues": {"name": "spoken word"}}.
// A concept is never reused for a second reel — add a new component instead.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const BESPOKE: Record<string, React.FC<{g: any}>> = {
  payslip: Payslip,
  editlog: EditLog,
  timecard: Timecard,
  handover: Handover,
  week: Week,
  seminar: Seminar,
};
