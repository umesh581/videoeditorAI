# Style standard: "Varun Mayya" documentary edit

This standard is reverse-engineered frame by frame from 5 @thevarunmayya reels the owner chose (Oct 2026):

| Reel | Length | Format |
|---|---|---|
| [DZYMtCJzy-1](https://www.instagram.com/p/DZYMtCJzy-1/) | 74s | AI model news |
| [DZfWwHOzLqX](https://www.instagram.com/p/DZfWwHOzLqX/) | 69s | Live product demo |
| [DZf38CCTuki](https://www.instagram.com/p/DZf38CCTuki/) | 47s | Business news |
| [DZVjiBxzhjU](https://www.instagram.com/p/DZVjiBxzhjU/) | 77s | Tech explainer |
| [DYhGMZZBflJ](https://www.instagram.com/p/DYhGMZZBflJ/) | 50s | Legal news |

Turn it on with `"styleRef": "varun-mayya"` in storyboard.json. That sets pill captions, the 50/50 split window and
quieter SFX. Everything below is the editor's job. Bright Ledger colours still apply, and so does the owner's style guide
(`brands/digital-entrepreneur_style.md`).

## The idea
**The speaker is the anchor, and the screen is the evidence.** The voice runs continuously. The picture is almost always
proof of what's being said: the article, the tweet, the document, the product, the footage. The speaker appears on camera
for the hook, the pivots and the close.

## 1. Hook (0–3 s): always a 50/50 split
- **Top half:** the single most striking real visual for the claim. Examples: the headline with a highlighted line, the
  product UI doing the thing, the archival moment. Optionally a vs.-split of two people or companies.
- **Bottom half:** the speaker, full width, delivering the thesis in the first sentence.
- **Between the halves:** a dark pill tag giving context ("Breaking News:", "New:", the person's role).
- Visual changes every 0.6–1 s inside the first 3 s.

## 2. Layout rhythm
- Four layouts, chosen by what's being said:
  - **split:** proof on top, speaker below. The default while explaining a source.
  - **full speaker:** opinion, story, emotion.
  - **full proof:** footage or a document fills the 9:16 frame.
  - **floating card:** UI or a screen recording in a rounded card on a clean canvas (white, cream or black).
- The speaker is full-screen for at most ~10–30% of runtime, and for demos ~70% split.
- **Average shot length is 1.5–2.5 s.** Every change lands on a key noun or verb ("Google", "Siri", "$2 trillion").
- Climaxes use rapid 1 s micro-cuts across 3–5 real clips.

## 3. B-roll is evidence, never decoration
- Ranked by preference:
  1. **News articles and documents** with a marker sweeping the exact line as it's spoken
     (`clipping` with `"look": "article"` and a `highlight`).
  2. **Tweets/X posts** as social proof (real screenshots only).
  3. **Real product UI / screen recordings** in floating cards (`broll` `"mode": "card"`).
  4. **Real footage:** keynote and interview clips, archival, or the owner's own recordings.
  5. **Logo/identity cards:** one centred logo on white, only when a company is first named.
- Each piece holds 1.5–3 s. A pill tag labels who's speaking or what the source is.
- **Kinetic type** is rare: one big number or phrase on a white or black canvas, serif + sans pairing
  ("9 out of 14 diseases"). Only for a number or term the viewer must remember.

## 4. Captions
- `pill` style: small (~46 px) sentence-case Inter SemiBold, white, inside a dark translucent rounded pill.
- 1–3 words per burst, revealed as spoken. No karaoke colours, no all-caps, no emoji.
- Sit on the split line (lower-middle) and never over the face.

## 5. Transitions and sound
- **Hard cuts.** The only motion is the content itself, card scale-pops (~250 ms) and slow pushes inside stills.
- No glitch, flash or zoom-blur transitions.
- **SFX are quiet and tactile:**
  - paper slide when a document lands;
  - marker friction on highlights;
  - UI clicks and keyboard taps on screen recordings;
  - a soft whoosh on topic shifts.
- **Music:** a low synth/ambient bed ducked to −18…−22 dB under the voice. The owner supplies the track in
  `reel_editor/music/`. Never download music.

## 6. Look
- Speaker: soft diffused key light, natural warm skin, a bright, softly blurred modern background (shallow depth of field).
- Graphics: clean editorial. Off-white documents, white/black canvases, one soft highlight colour (warm orange or the
  brand lime), rounded corners, no drop-shadow clutter.

## Named people and companies (automatic)
A named person, company or event gets a real photo on the word: `media-commons <slug> "<name>"` (Wikimedia Commons,
licence credit shown on screen), paired with a real headline when the line is about something they did. Moving footage
of public figures is copyrighted, so it comes only from files the owner supplies.

## What this needs per reel (be honest with the owner)
- These reels show **15–30 distinct real assets per minute**. The editor finds what it can by itself:
  - news headlines (`news`);
  - archival photos (Wikimedia Commons);
  - website and product screenshots (`media-shot`).
- The rest must come from the owner:
  - their screen recordings;
  - tweets they want cited;
  - keynote clips they have rights to use.
- When a reel can't reach ~1 asset per 2–3 s with real material, fall back to the speaker full-screen with punch-ins
  for those stretches. **Never fill the gap with invented graphics.**
- Record new videos with this format in mind: a light, modern background, soft front light, and a 2–3 s pause before
  each new point (it gives the split hook and the cuts room).

## Director's review additions (on top of the owner's style guide)
1. Do the first 3 s use a 50/50 split with a real visual on top?
2. Is the speaker full-screen only where it's opinion or story?
3. Is every source shown with its name and date, with the quoted line highlighted as it's spoken?
4. Are captions pill-style, 1–3 words, sentence case, and clear of the face?
5. Hard cuts only, with SFX quiet and tied to on-screen actions?
