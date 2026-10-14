# videoeditorAI

This repository turns raw talking-head videos (Telugu + English) into finished 9:16 Instagram reels, with Claude Code as the editor. It also holds a few related experiments from the **Digital Entrepreneur** brand.

## What's inside

| Folder | What it is |
|---|---|
| [`reel_editor/`](reel_editor/) | The reel pipeline and the **Reel Studio** drag-and-drop app. Details are in its [README](reel_editor/README.md). |
| [`.claude/skills/edit-reel/`](.claude/skills/edit-reel/SKILL.md) | The Claude Code skill that runs an edit: brief, creative concept, storyboard, QA, then render. |
| [`bakeoff/ambition/`](bakeoff/ambition/) | A head-to-head test of HeyGen's HyperFrames against this pipeline on the same clip. |
| [`constituency_dashboard/`](constituency_dashboard/) | A Streamlit dashboard for constituency grievances, news and sentiment. |
| [`telugu_ai_news_agent.py`](telugu_ai_news_agent.py) | Curates weekly AI business news into a bilingual Telugu + English newsletter. |

## How a reel gets made

```
raw.mp4 ─▶ whisper.cpp transcript ─▶ Claude writes brief + concept + storyboard ─▶ you approve
                                                                                    │
     out/<slug>_vN.mp4 ◀── Remotion render ◀── frame QA (safe zones, face, lime budget) ◀┘
```

- **Edit:**
  - Pauses are removed by cutting only at points where the audio is silent, so no dialogue is chopped mid-word.
  - Footage gets a brand colour grade with auto-exposure, and loudness is normalised to −14 LUFS.
- **On screen:**
  - Word-synced captions in Plus Jakarta Sans and Inter, with Anek Telugu for Telugu text.
  - B-roll from stock footage, your own library, AI clips or website screenshots.
  - Motion graphics, overlays and sound effects.
- **Bespoke scenes:** each reel gets its own creative concept, with hand-built hero moments in `reel_editor/remotion/src/bespoke/`. Every moment is timed to a spoken word. For example, *The Payslip*: a salary slip prints, gets stamped, gains a second income line and tears into a webinar ticket. A concept is never reused for another reel.
- **QA:** before rendering, frames are checked against Instagram and Meta-ad UI zones. QA also checks that your face is never covered or darkened, and that brand lime stays within its ~10% share of the frame.

## Quick start (macOS)

**Requirements:** ffmpeg, `whisper-cpp` (Homebrew) with a model in `reel_editor/models/`, Node 20+, Python 3, and Claude Code.

```bash
cd reel_editor/remotion && npm install
```

```bash
python3 reel_editor/app/server.py --port 8765
```

Open http://127.0.0.1:8765 and drop in a raw clip. You can also double-click `reel_editor/Reel Studio.command`, or ask Claude Code from this folder:

> Edit ~/Downloads/my-take.mp4 into a reel

**Cost:** Reel Studio's planning runs a headless Claude session, at roughly $0.60–$1.30 of credits per video. Rendering, grading, transcription and QA run locally and cost nothing.

## Not in git

These are deliberately git-ignored:
- secrets (`.env`, `.streamlit/secrets.toml`)
- per-project working files (`reel_editor/projects/`)
- Whisper models
- `node_modules`
- the constituency database
- all rendered video and audio

## Licence note

Remotion is free for individuals and companies of up to 3 people; larger companies need a [Remotion licence](https://www.remotion.dev/license).
