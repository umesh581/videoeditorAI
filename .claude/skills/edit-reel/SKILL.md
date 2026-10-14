---
name: edit-reel
description: Edit a raw talking-head or screen-recording clip into a finished, high-retention 9:16 Instagram reel/short — understand what's being said, restructure it around a hook, cut bad takes, add b-roll (stock, own clips, AI-generated, website screenshots), motion graphics (logo pop-ins, counters, checklists, comparisons, cards, slams), sound effects and captions — and apply one-sentence revisions. Use when the user gives a video file and asks to edit it, make a reel/short/TikTok from it, or asks for changes to a reel made earlier.
---

# Edit a reel

You are the **editor and the strategist**, not a caption machine. A reel that only has captions has failed this skill. The pipeline lives in `reel_editor/` (repo root); you write `storyboard.json` and the tool renders it with Remotion.

```
python3 reel_editor/reel.py new <video> [--name slug] [--lang en|te|hi|auto]
python3 reel_editor/reel.py build <slug>              # → storyboard.md (+ retention check)
python3 reel_editor/reel.py still <slug> --at <sec>   # PNG at OUTPUT time — look at it
python3 reel_editor/reel.py render <slug> [--draft]   # → projects/<slug>/out/<slug>_v<N>.mp4

python3 reel_editor/reel.py media-search <slug> "query" [--n 4] [--photos]   # Pexels stock
python3 reel_editor/reel.py media-add <slug> <files...> | --library [match]  # user's own clips
python3 reel_editor/reel.py media-url <slug> <url> --name x.mp4              # AI-generated clip etc.
python3 reel_editor/reel.py media-shot <slug> <url> [--desktop]              # website screenshot
python3 reel_editor/reel.py media-list <slug> [--library]                    # + media_sheet.jpg
```
Render speed on the M1: ~8s per output second with graphics; `--draft` is ~3× faster.

---

## Step 1 — Ingest and actually understand the video
`new` the clip, then read `transcript.txt` and look at `contact.jpg` (`contact.txt` gives tile timing). Then write `projects/<slug>/brief.md`:

```markdown
## What this is
Topic, who is speaking, who it's for (be specific: "Indian creators on a Mac who think they need an iPad to stream").
## The one promise
The single outcome a viewer gets by watching to the end. One sentence.
## Strongest lines (source timestamps)
The 3–5 most surprising, specific, emotional or contrarian things said. Numbers, names, before/after, "you don't need X".
## Hook options
1. Result-first: …   2. Contrarian/"stop doing X": …   3. Curiosity gap: …   (≤8 words each, on-screen text)
Chosen: # — why it stops the scroll for THIS audience.
## Structure
Hook (0–2s) → promise/context (≤5s) → payoff beats → proof → CTA. Which beats go where (reorder freely).
## Visual plan
Per beat: what the viewer SEES besides the speaker — b-roll query/file, graphic type + content, the spoken word it lands on.
## Assets needed
Stock queries, screenshots (URLs), user clips, AI clips (with prompts).
```

Show the user the hook options and visual plan in 5–8 lines before building — they know their audience.

## Step 2 — Hook rules (first 2 seconds decide everything)
- **Open on the strongest line**, not the first one. Cold-open beats are allowed: reuse a later line at the top (it may appear again later).
- Something must move in the **first 0.5s**: a `slam`, a `hook`/`magazine` overlay, a `prompt` typing, or a flash cut. `build` warns if not.
- On-screen hook text **complements** the spoken line, never repeats it word-for-word (spoken "I don't need to purchase" → screen "DON'T BUY AN iPad").
- Name the audience or the pain specifically; use numbers when you have them.
- Promise the payoff early ("in 3 steps", "for free"), deliver it last — that's what holds watch time.

## Step 3 — Edit rules
- **Bad takes:** keep the LAST complete version of a repeated line. Cut false starts, "um/so yeah/let me check", off-topic asides, dead air.
- **Cut points:** `in` ~0.05–0.1s before the first kept word, `out` ~0.05–0.15s after the last; a word belongs to the beat containing its midpoint — check the *Spoken* column in `storyboard.md` for stray words.
- **Pauses:** `tighten` (on by default) jump-cuts every pause ≥0.22s inside beats and trims dead air at beat edges, alternating a 1.07 punch-in so cuts feel intentional. Set `"noTighten": true` on a beat that needs a dramatic pause; `"tighten": {"minPause": 0.3}` for a calmer pace.
- **Typography:** one sans family (Manrope + Anek Telugu). No serif, no italics, no condensed meme fonts.
- **Pacing:** beats 1–4s. Alternate `shot` (wide → close → medium) across cuts from the same take.
- **Retention:** something new on screen at least every **2–3s** (b-roll, graphic, overlay, shot change, emphasis). `build` lists any static stretch over 3s — fix every one before showing the user.
- **Target** 15–45s unless told otherwise. Cutting 30–50% of a raw take is normal.

## Step 4 — B-roll (cover ~30–50% of runtime when the speaker is talking about things, not feelings)
Get assets, then look at `media_sheet.jpg` before using them — never place footage you haven't seen.
- **User's own** (best): `media-list <slug> --library` then `media-add <slug> --library <match>`; or files the user names.
- **Stock**: `media-search <slug> "<concrete visual noun phrase>"` — e.g. "typing on macbook dark desk", not "productivity". Needs `PEXELS_API_KEY` in `reel_editor/.env` (free at pexels.com/api); if missing, tell the user once and carry on with other sources. Credits land in `media/index.json`.
- **Website/product shots**: `media-shot <slug> <url>` (phone-shaped; `--desktop` for wide) → use in a `cards` graphic.
- **AI-generated**: the vidIQ connector has `vidiq_generate_broll` (costs vidIQ credits — **ask the user before generating**, say how many clips). Poll the job, then `media-url <slug> <resultUrl> --name <name>.mp4 --source ai`.
- Never invent or download music; only use tracks the user put in `reel_editor/music/`.

Place b-roll on the word it illustrates: `{"src": "px-coffee-123.mp4", "on": "coffee", "dur": 1.8, "mode": "full"}`.
Modes: `full` (cutaway, voice continues), `pip` (b-roll full + speaker in a circle), `split` (b-roll top / speaker bottom). `clipStart` = seconds into the clip; `label` = small tag; `focus` = crop point.

## Step 5 — Motion graphics catalog
All graphics/overlays/b-roll take timing as `"on": "<spoken word or phrase in this beat>"` (preferred — lands exactly when it's said) or `"at": <sec from beat start>`, plus `"dur": <sec>` or `"until": "<word>"` (default: to beat end). `pos`: top | center | bottom. `sfx`: name or `false`. Centre graphics auto-dim the footage (`"dim": false` to disable).

| type | use it for | fields |
|---|---|---|
| `slam` | full-screen cold-open / pattern interrupt; words slam in one by one (captions hide under it) | `words`: strings or `{text, on}`; `bg`, `color` |
| `logos` | tools/apps/brands mentioned; strike the one being replaced | `items`: `"Notion"` or `{name, slug?, strike?, image?}`; `title`. Brand icons from simple-icons (3,400 brands; unknown → monogram) |
| `cards` | screenshots, websites, products, thumbnails, proof | `images` (1–4 media files), `frame`: plain/browser/phone, `caption` |
| `counter` | any number, money, %, views, time saved | `value`, `prefix`, `suffix`, `decimals`, `label` |
| `checklist` | steps, lists, "3 things" | `title`, `items`: `{text, on}` — each ticks when said |
| `compare` | before/after, old way vs new way, X vs Y | `left`/`right`: `{title, items[]}` (left = bad, right = good) |
| `highlight` | point at part of a screen recording | `box`: [x, y, w, h] as 0–1 of the 1080×1920 frame, `label` |
| `prompt` | show a typed instruction/search/chat ("TO CLAUDE: …") | `text`, `who`, `status` |
| `sticker` | emoji/image reaction pop | `emoji` or `image`, `x`, `y` (0–1), `size` |

Text overlays (in `overlays`): `hook` (serif title + gold sub), `magazine` (giant masthead + `sub` rule line), `title` (centred card), `label` (pill tag), `cta` (bottom card).
Captions: `premium` (default — Manrope, karaoke highlight, clean) · `bold-pop` · `minimal` · `huge`; `size`, `position` lower/center/upper. Move captions to `upper` if a beat's graphic sits low.

Density guide for a 30s reel: 1 slam or hook, 3–6 graphics, 3–6 b-roll inserts, 1 CTA. Don't stack two centre graphics at once; one idea on screen at a time.

## Brand
The owner's brand is `reel_editor/brands/digital-entrepreneur.json` (from their brand guidelines PDF). **Always set `"brand": "digital-entrepreneur"`** in storyboard.json unless told otherwise; it supplies colours (Digital Lime #D4FF33 accent on black), fonts (Plus Jakarta Sans + Inter), flat bordered cards, line icons, the `brand` grade (desaturated, deep blacks; b-roll in B&W) and caption defaults. Follow its `rules` list, especially:
- Lime ≤10% of any frame — don't add lime colour props; the theme handles accent placement.
- Stickers use `"icon": "<lucide-name>"` (e.g. graduation-cap, house, car, trending-down, indian-rupee, briefcase, brain, target), never emoji — `build` rejects emoji.
- On-screen copy follows the brand voice: direct, precise, specific numbers, no fluff, no emoji.
- Avoid stock clichés / posed smiles when picking b-roll.
Storyboard keys still override brand defaults (e.g. `look.grade`).

## The meaning test (apply to EVERY graphic before adding it)
Ask: *what does the viewer see or feel here that the voice alone doesn't give them?* If the honest answer is "nothing",
cut the graphic. The owner rejected generic chapter cards ("01 The ceiling / 02 The move") as meaningless decoration.
Prefer graphics the audience **recognises from their own life**: `notify` (bank SMS, HR mail, app alerts that drop in
and stack — "salary credited", "appraisal letter"), `event` (calendar card for dates/offers), real screenshots
(`media-shot`), the actual numbers they'd see. `chapter` cards only when the speaker literally structures the talk into
named parts ("three mistakes: one…"). Never invent figures (salary amounts, % hikes) — keep UI copy generic or spoken.

Graphic types: `notify` (`items: [{app, title, body, icon, time, on|at}]`, stack of up to 3) · `event` (`day`, `date`, `title`, `details[]`, `tag`).

## Creative direction — pick a TREATMENT (never the same template twice in a row)
Before writing beats, read `reel_editor/brands/<brand>_history.json` (treatments of recent reels). Choose the treatment
that fits THIS content and is **different from the last two** unless the owner asks otherwise. Set `"treatment": "<name>"`
in storyboard.json and justify it in brief.md (content → treatment → 3 signature moments). The owner explicitly
complained that reels "all follow the same template" — variety is a requirement, not a nice-to-have.

| treatment | when | signature (combine, don't mix with other treatments' signatures) |
|---|---|---|
| `explainer-canvas` | processes, comparisons, frameworks | `dock` + `flow`/`compare`/`checklist`, `wipe`/`whip`, `premium` captions with keyword boxes |
| `editorial` | personal, reflective, opinion, story | `look.letterbox: true`, `mono: true` on the cold open (and a callback beat), real-life UI moments (`notify`, `event`) instead of diagrams, `lowerthird` name tag early, `editorial` captions (left-aligned, wordsPerChunk 4), hard cuts only, at most one `title` card, no docks/diagrams |
| `kinetic` | punchy claims, myths, contrarian takes | `statement` overlays (full-screen paper type) for the 2–4 strongest lines, `kinetic` captions (wordsPerChunk 1–2), fast cuts + `punch` on most beats, `slam` allowed, no docks |
| `podcast` | conversational, advice, Q&A, long thoughts | `look.dockStyle: "top"` (speaker top half all reel), `kinetic` or `premium` captions in the lower canvas, `lowerthird` topic tags per section, `label` overlays, minimal transitions |

New overlay styles: `chapter` (text = "01", sub = title; full-screen ~1.0–1.3s), `statement` (text = the line, sub optional; ~1.5–2.2s), `lowerthird` (text = name, sub = role/topic). These hide captions while on screen; the voice continues.

## Meta ads (`"placement": "meta-ad"` in storyboard.json)
When the owner says the reel is for ads: make a separate project (clone the organic one), set `placement: meta-ad`
(moves captions/overlays/canvas clear of Meta's top 14% header and bottom 35% CTA + primary text; the docked
window extends under that zone because footage there is fine; QA checks Meta's zones). Also: 15–30s, offer on
screen within 3s for sound-off, on-screen CTA must match the Ads Manager button (ask), cut spoken CTAs that
contradict it, no earnings claims or personal-attribute phrasing, flag relative dates ("this Sunday"), and write
`meta_ad_copy.txt` (primary text, headline, description, button).

## Restraint (the difference between clean and cluttered)
- **Max 2 things on screen**: captions + ONE graphic/overlay. No icon stickers on top of a graphic, no labels on top of a diagram, no progress bar.
- **Real over abstract**: when the speaker names a product, site, app, number or document, show the real thing (`media-shot` screenshot in a `cards` graphic or `card` b-roll) instead of a text diagram.
- **Bigger and fewer**: one big card with generous empty space beats three small ones. Diagrams max 4 nodes.
- Brand runs in **video mode** (owner-approved): lit canvas + grain, soft card shadows, paper (cream) cards for contrast moments — prompts/messages and the "good" side of comparisons use paper automatically.

## Direction — edit like a premium agency (learned from the owner's reference reels)
Every reference the owner admires shares these; use them deliberately, not decoratively:
1. **Dock the speaker for explanations.** Any diagram, comparison, UI, list or message gets `"dock": true` on the graphic (or `"layout": "dock"` on the beat): the speaker animates into a rounded window at the bottom, the top becomes a black brand-grid canvas, graphics go `pos: "canvas"` automatically, captions sit in the band between. Undock for emotional / punchline beats. Aim for 30–50% of runtime docked in explainer reels.
2. **Turn the core idea into a diagram.** Sequences ("degree → job → EMI") become one `flow` that builds across beats, each node landing on its spoken word (use `at` seconds from the beat start when nodes are spoken in later beats).
3. **Keyword highlight boxes**: one `gold`/`color` emphasis per beat (renders as an accent box behind the word).
4. **Snap punch-ins** on punchlines: `"emphasis": [{"word": "x", "style": "big"}]` or `"punch": ["word"]` on the beat — 10% snap, held to the next cut.
5. **Transitions with motion**: `whip` (directional motion blur) for energy shifts, `wipe` (brand panel) for section changes, `zoom` for emphasis; plain cuts elsewhere. Never `flash`.
6. **Nothing static**: graphics drift, type masks in word-by-word and leaves with a designed exit; every element entrance has a synced SFX.
7. **Music bed**: if the owner supplies a track (reel_editor/music/), set `"music": {"file": "...", "volume": 0.08}` — it auto-ducks under speech and lifts in gaps. Otherwise remind them to add trending audio in Instagram at ~10–15% volume.

**Owner's clips (incl. Google Flow / Veo AI clips):** place each where its note says. AI-generated clips use b-roll `"mode": "card"` — the speaker docks and the clip plays in a framed 16:9 card on the canvas (optional `label`). Never crop, blur, cover, zoom or reposition a clip to hide a watermark; it stays fully visible.

Graphic types now also include `flow` (`items: [{text, icon, at|on}]`, `title`). Graphic option `dock: true`. Beat options `layout: "dock"`, `punch: [words]`. Transitions: cut · zoom · whip · wipe.

## Step 6 — storyboard.json
```json
{
  "title": "…", "version": 1, "fps": 30, "focus": [0.5, 0.4],
  "look": {"grade": "warm", "vignette": 0.3, "grain": false, "push": true, "fit": "cover", "progressBar": "#F5C542"},
  "captions": {"style": "premium", "size": 1.12, "position": "lower", "highlightColor": "#F5C542", "wordsPerChunk": 3},
  "sfx": {"enabled": true, "volume": 0.45},
  "corrections": {"cloud": "Claude"}, "hideWords": ["um", "uh"],
  "beats": [
    {"id": 1, "in": 22.70, "out": 23.55, "shot": "close", "transition": "cut", "note": "cold open",
     "emphasis": [{"word": "purchase", "style": "big"}],
     "overlays": [{"style": "hook", "text": "…", "sub": "…", "on": "don't", "dur": 2}],
     "broll": [{"src": "clip.mp4", "on": "purchase", "dur": 1.5, "mode": "full"}],
     "graphics": [{"type": "slam", "words": [{"text": "Don't", "on": "don't"}, "buy an", "iPad"]}]}
  ],
  "music": null
}
```
- `look.grade`: cinematic (default for talking heads: warm skin, subtle cool shadows) · natural · warm · moody · punchy · bw · film. Grades are baked into the footage AND b-roll by ffmpeg (denoise, curves, white balance, sharpening, vignette) at build time — so keep `look.vignette` 0 and `grain` false unless asked, and never stack darkening. The speaker's face must stay the brightest thing in frame; check a still against a raw frame. `fit`: `cover` (faces) / `blur` (landscape screen recordings). `progressBar`: color or omit.
- `shot`: wide/medium/close/extreme or `"zoom": 1.3`. `transition`: cut/zoom (zoom gets a whoosh). `flash` exists but reads as cheap/glitchy — don't use it for the owner's brand.
- `emphasis` style: gold/strike/big/color — max one per beat.
- SFX are automatic (whoosh on cards/b-roll, pop on logos/stickers, ding on checklist ticks, hit on slams, riser on counters, typing on prompts).

## Step 7 — Quality loop (no AI slop ships)
`build` until there are no retention warnings, then run **`python3 reel_editor/reel.py qa <slug>`** (~4–5 min for a 45s reel). It samples a frame every 0.5s and reports **measured hard failures** (exit code 2):
- overlay covering >12% of a detected face · text/graphics in Instagram's right action rail or bottom caption area · accent colour >10% of a frame · dead stretches ≥1.5s with no visual change.

Then do the **art-direction pass**: Read every `projects/<slug>/qa/sheet*.jpg` (frame numbers top-left, red boxes = Instagram UI zones) and score EVERY frame 1–10 against this rubric:
- **Hierarchy & readability** — one focal point; text legible at phone size; nothing fighting for the centre.
- **Composition** — face unobstructed and well framed; graphics aligned to the safe area; no awkward crops (cut-off chins/foreheads in split panels).
- **Brand fidelity** — Plus Jakarta/Inter only, lime used sparingly, flat cards, line icons, desaturated imagery.
- **Polish** — no blank/black frames (especially frame 0 — it's the cover), no washed-out transition frames, no half-visible elements stuck mid-animation for long, no overlaps.
- **Slop smells (auto ≤5)** — centred all-caps on a gradient, emoji, posed-smile stock, generic "success" imagery, flash/glitch transitions used as decoration, a graphic that just repeats the caption, more than one new element entering at once.

Write `projects/<slug>/qa_scores.json`: `{"round": N, "frames": [{"i": 0, "score": 3, "issue": "...", "fix": "..."}...], "min": 3, "mean": 7.9}` (every sampled frame; issue/fix only where score < 9). Fix the storyboard (or ask for a component fix if it's systemic), `build`, re-run `qa`. **Repeat until: 0 hard failures AND every frame ≥ 8**, max 2 rounds (1 for revisions); if it still fails, report exactly which frames and why — QA advises, the owner decides. Skip QA entirely when the owner asks for fast mode. Only then show the user the storyboard + QA summary and ask "Render it, or change anything?"

## Step 8 — Render + revise
`render` → send the mp4 with SendUserFile. Revisions: edit `storyboard.json`, bump `version`, `build`, re-render.
| User says | Do |
|---|---|
| stronger hook | new cold-open slam on the most contrarian line; hook text with a number or "stop/don't" |
| more b-roll | cover every noun-heavy line; target 50% coverage |
| more graphics / more engaging | add a graphic every 2–3s: logos for tools, counter for numbers, checklist for steps |
| make it aesthetic | warm grade, editorial-serif captions, magazine overlay, `cards` with plain frames |
| make it moody | moody grade, vignette 0.6, grain, huge captions, slam with dark bg |
| tighter | trim 0.1–0.2s per cut, drop the weakest beat |
| cleaner | fewer graphics, minimal captions, sfx volume 0.25 |

Always report what changed in a short list, then the new file path.
