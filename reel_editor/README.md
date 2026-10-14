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
