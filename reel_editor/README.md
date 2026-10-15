# Reel editor

Raw clip → edited 9:16 reel, with Claude Code as the editor.

```
raw.mov ─▶ whisper.cpp (word timestamps) ─▶ transcript.txt + contact.jpg
                                                  │  Claude reads, decides cuts
                                                  ▼
                                          storyboard.json ─▶ storyboard.md  (you review)
                                                  │
                                                  ▼
                               Remotion (React) render ─▶ out/<slug>_v<N>.mp4
```

Before editing, Claude writes `brief.md` (audience, promise, hook options, visual plan). The render then layers:
b-roll (stock / your clips / AI / website screenshots) · 9 motion-graphic types (slam, logos, cards, counter,
checklist, compare, highlight, prompt, sticker) · text overlays · word-synced captions · synthesized SFX ·
progress bar · colour grade. `build` runs a retention check that flags any 3s+ stretch with nothing new on screen.

Optional: put `PEXELS_API_KEY=...` in `reel_editor/.env` (free key from https://www.pexels.com/api/) to enable stock b-roll.
Put reusable personal b-roll in `library/`.

## Reel Studio (the app)
Double-click **`reel_editor/Reel Studio.command`** (or run `python3 reel_editor/app/server.py`) → http://127.0.0.1:8765.
Drop a raw clip → it transcribes, Claude plans the edit (brief, hook, b-roll, storyboard, frame check) → review the
storyboard → type changes ("stronger hook") → Render → download + Instagram caption. Nothing renders until you click Render
(unless "Render automatically" is ticked). Headless Claude can only run `reel.py` and write inside `projects/`.
Each plan costs roughly $0.50–$1.50 of Claude usage; revisions ~$0.30–$1.

## Use it (from Claude Code chat)
In Claude Code, from the repo root:

> Edit ~/Movies/raw-take.mov into a reel

The `edit-reel` skill (`.claude/skills/edit-reel/SKILL.md`) runs the steps, shows you the storyboard, and renders on approval. Then just say "make it moody", "bigger captions", "tighter cut".

## Manual commands
```
python3 reel.py new <video> [--name slug] [--lang auto]
python3 reel.py build <slug>
python3 reel.py still <slug> --at 2.0
python3 reel.py render <slug> [--draft]
```
Preview interactively: `cd remotion && npx remotion studio --props=../projects/<slug>/props.json --public-dir=../projects/<slug>/public`

## Requirements (already installed on this Mac)
- ffmpeg, `whisper-cpp` (Homebrew), `models/ggml-small.bin`
- Node 20, `remotion/` deps (`npm install`). Remotion is free for individuals and companies of ≤3 people; larger companies need a license.

## Newer features (Oct 2026)
- **Voice check + cleanup** (`voice.py`): grades the recording, removes background noise with RNNoise and notches mains
  hum. It needs the model file once:
  `curl -L -o reel_editor/models/rnnoise-cb.rnnn https://raw.githubusercontent.com/GregorR/rnnoise-models/master/conjoined-burgers-2018-08-28/cb.rnnn`
- **Safe cuts:** every cut snaps to a gap in the waveform (10 ms envelope). The build refuses any cut that would clip a word.
- **Real proof, not filler:**
  - `reel.py news <slug> "claim"` fetches real headlines for `clipping` graphics, in newsprint or article style;
  - `reel.py media-commons <slug> "Elon Musk"` fetches real, freely licensed photos, with the credit shown on screen.
- **Style:** Bright Ledger is the default look (`brands/digital-entrepreneur.json`). The owner's style guide and Director's
  review are in `brands/digital-entrepreneur_style.md`. `"styleRef": "varun-mayya"` turns on the documentary preset
  (`brands/presets/`).
- **Edit log:** `reel.py log` / `log-set` record every raw clip by content fingerprint (approved, delivered, held or
  skipped). `new` refuses logged clips unless you pass `--redo`. The log itself (`edit_log.json`) stays local.
- **Export:** finished reels are also copied to the folder in `settings.json` (`export_dir`).
- **B-roll agent** (`.claude/agents/broll-agent.md`):
  - The creative director writes a shot list (`broll_requests.json`).
  - The agent fills each shot from the cheapest honest source: the shared library (`reel.py broll-find / broll-use`),
    then real photos and headlines, then vidIQ stock (1 credit), then Canva AI images (owner's plan), then Veo AI video
    (≈120 vidIQ credits per 4 s).
  - Every new asset is saved to `library/broll/` (local, git-ignored) with a visual description, so it can be reused.
  - AI never depicts real people or brands, or fakes news.
- **Visual balance:** speaker 40–60 %, proof 10–20 %, b-roll 15–30 %, motion graphics 5–15 %, never more than two
  cutaways in a row. This is enforced in the skill and the Director's review.
- **Reel Studio:**
  - bright UI;
  - look and style switches per upload;
  - edit-log guard, folder import and Library tab;
  - Approve button, "Proof on screen" card, Show in Finder;
  - on-demand Instagram captions (tone, language, call to action), built only from what the reel says and shows.

