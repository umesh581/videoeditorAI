// Render many stills from one bundle + one browser (much faster than `remotion still` per frame).
// node frames.mjs <props.json> <publicDir> <outDir> <frame,frame,...> [variants=full] [scale=0.5] [labels=0]
// variants: comma list of full|footage (footage = no overlays/graphics/captions, for occlusion masks)
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import {readFileSync, mkdirSync, rmSync} from 'node:fs';
import {join, resolve} from 'node:path';

const [propsPath, publicDir, outDir, list, variantArg = 'full', scaleArg = '0.5', labels = '0'] = process.argv.slice(2);
const variants = variantArg.split(',');
const scale = Number(scaleArg);
const inputProps = JSON.parse(readFileSync(propsPath, 'utf8'));
const frames = list.split(',').map(Number);
mkdirSync(outDir, {recursive: true});

const serveUrl = await bundle({entryPoint: resolve('src/index.ts'), publicDir: resolve(publicDir)});
const browser = await openBrowser('chrome');
// v4: the selected composition carries the props that get rendered, so select once per props variant
const comps = new Map();
const compFor = async (props) => {
  const k = JSON.stringify(props.qa ?? null);
  if (!comps.has(k)) comps.set(k, await selectComposition({serveUrl, id: 'Reel', inputProps: props, puppeteerInstance: browser}));
  return comps.get(k);
};
for (const [i, frame] of frames.entries()) {
  for (const variant of variants) {
    const suffix = variants.length > 1 || variant !== 'full' ? `_${variant}` : '';
    const output = join(outDir, `f${String(i).padStart(3, '0')}${suffix}.png`);
    const props = variant === 'full' && labels !== '1' ? inputProps : {...inputProps, qa: {variant, label: labels === '1' && variant === 'full' ? String(i) : undefined}};
    await renderStill({serveUrl, composition: await compFor(props), inputProps: props, frame, output, scale, puppeteerInstance: browser});
    console.log(output);
  }
}
await browser.close({silent: true});

// bundles copy the whole public dir (graded masters included) — never leave them behind
rmSync(serveUrl, {recursive: true, force: true});
