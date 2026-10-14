// Website screenshot via Remotion's headless Chrome + the DevTools protocol.
// node --experimental-websocket screenshot.mjs <chrome> <url> <out.png> <width> <height> <mobile 0|1>
import {spawn} from 'node:child_process';
import {mkdtempSync, readFileSync, writeFileSync, existsSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const [chrome, url, out, w, h, mobile] = process.argv.slice(2);
const width = Number(w), height = Number(h), isMobile = mobile === '1';
const dir = mkdtempSync(join(tmpdir(), 'shot-'));
const proc = spawn(chrome, ['--remote-debugging-port=0', `--user-data-dir=${dir}`, '--hide-scrollbars', 'about:blank'], {stdio: 'ignore'});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const done = (code) => { proc.kill(); try { rmSync(dir, {recursive: true, force: true}); } catch {} process.exit(code); };
setTimeout(() => { console.error('timeout'); done(1); }, 45000);

let port;
for (let i = 0; i < 100 && !port; i++) {
  const f = join(dir, 'DevToolsActivePort');
  if (existsSync(f)) port = readFileSync(f, 'utf8').split('\n')[0];
  else await sleep(100);
}
if (!port) { console.error('chrome did not start'); done(1); }

const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = targets.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const events = [];
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  else if (msg.method) events.push(msg.method);
};
await new Promise((r) => (ws.onopen = r));
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({id: i, method, params})); });

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 2, mobile: isMobile});
if (isMobile) {
  await send('Emulation.setUserAgentOverride', {userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'});
}
await send('Page.navigate', {url});
for (let i = 0; i < 150 && !events.includes('Page.loadEventFired'); i++) await sleep(100);
await sleep(1500); // let fonts/hero images settle; don't wait on endless analytics
const shot = await send('Page.captureScreenshot', {format: 'png'});
if (!shot.result) { console.error(JSON.stringify(shot.error)); done(1); }
writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
done(0);
