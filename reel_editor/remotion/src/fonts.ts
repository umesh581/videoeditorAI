import {loadFont as loadManrope} from '@remotion/google-fonts/Manrope';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadJakarta} from '@remotion/google-fonts/PlusJakartaSans';
import {loadFont as loadAnekTelugu} from '@remotion/google-fonts/AnekTelugu';

// Fonts a brand theme may name. Telugu glyphs always fall through to Anek Telugu, whose
// geometry matches these sans families, so mixed Telugu/English lines read as one typeface.
const TELUGU = loadAnekTelugu('normal', {weights: ['500', '600', '700', '800'], subsets: ['telugu']}).fontFamily;

const FAMILIES: Record<string, string> = {
  'Plus Jakarta Sans': loadJakarta('normal', {weights: ['500', '600', '700', '800'], subsets: ['latin']}).fontFamily,
  Manrope: loadManrope('normal', {weights: ['500', '600', '700', '800'], subsets: ['latin']}).fontFamily,
  Inter: loadInter('normal', {weights: ['400', '500', '600', '700'], subsets: ['latin']}).fontFamily,
};

export const fontStack = (name: string) => `${FAMILIES[name] ?? FAMILIES.Manrope}, ${TELUGU}`;
