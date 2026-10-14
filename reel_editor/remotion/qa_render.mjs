// QA renders: one low-res video per variant (full | overlay | footage), each with its OWN
// selectComposition — in Remotion v4 the selected composition carries the props that get rendered.
// node qa_render.mjs <props.json> <publicDir> <outDir> <scale> <labelStep> <variant,...>
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {readFileSync, mkdirSync, rmSync} from 'node:fs';
import {join, resolve} from 'node:path';
import {cpus} from 'node:os';

const [propsPath, publicDir, outDir, scaleArg, stepArg, variantArg] = process.argv.slice(2);
const base = JSON.parse(readFileSync(propsPath, 'utf8'));
mkdirSync(outDir, {recursive: true});
const serveUrl = await bundle({entryPoint: resolve('src/index.ts'), publicDir: resolve(publicDir)});
for (const variant of variantArg.split(',')) {
  const inputProps = {...base, qa: {variant, labelStep: variant === 'full' ? Number(stepArg) : undefined}};
  const composition = await selectComposition({serveUrl, id: 'Reel', inputProps});
  const outputLocation = join(outDir, `${variant}.mp4`);
  await renderMedia({serveUrl, composition, inputProps, codec: 'h264', outputLocation, scale: Number(scaleArg),
                     crf: 16, imageFormat: 'jpeg', jpegQuality: 92, muted: true, concurrency: cpus().length});
  console.log(outputLocation);
}

// bundles copy the whole public dir (graded masters included) — never leave them behind
rmSync(serveUrl, {recursive: true, force: true});
