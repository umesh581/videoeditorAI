# Digital Entrepreneur: editing style guide

This guide comes from the owner's 12 reference reels and every correction made in edit sessions (Oct 2026). Every edit
must pass the **Director's review** at the bottom before the owner sees it. The owner should never have to point out
anything on this list again.

## What the reference reels have in common
| Reference | What it teaches |
|---|---|
| DcjS7H_NHUg | Clean motion: cards swap with springy scale moves (~250 ms) and smooth pushes (~350 ms ease-out). Restraint. |
| Dd7ff16RUBV, DbuiIulorkz | A/B rhythm: each visual beat lasts 1.2–2 s, and every element lands on a key noun ("Claude", "Skill", "April"). |
| DbuiIulorkz, Dea-bNpIYPU, Dd31nWHhc4G | Real UI is the hero: screen recordings, phone mockups, tap circles, highlighted buttons. |
| DeTKpFbzJLY | Speaker alternates with supporting visual anchors; fast 4–6 frame whip/zoom transitions with motion blur. |
| DWTsSGKDcIy | Captions are bold sans-serif with one key word in a highlight box; one big kinetic callout for the CTA only. |
| DdguMaWSihK, DebDy_sOV4_ (money niche, 2–7M views) | Bright, airy and warm. Colour carries meaning: green = right, red = wrong, gold = ₹. White app-style cards with REAL numbers. |
| DdxeNqQzK_y (Telugu AI) | Warm studio and real tool demos inside phone mockups: prompt → result. |

## The rules
**Look**
- Bright Ledger is the default: warm-white canvas, warm full-colour skin, green/red/gold meaning colours, lime only as a highlighter.
- The speaker's face must be fully in frame at all times. Measure it; never assume it. Captions never cover the face.

**Graphics: proof or nothing**
- A graphic exists only if the viewer learns something the voice doesn't say:
  - a real headline (`news`);
  - a real number with its source;
  - real UI or a screen recording of the work;
  - a real photo or archival image;
  - a real before/after.
- Banned:
  - restating the spoken words (stamps, cards or lists of what he just said);
  - invented props (fake time cards, tickets, dashboards, calendars, manager messages);
  - logo tiles;
  - docking the speaker just to fill space.
- Nothing invented may look like data. Numbers come from a source, or from the owner.

**Footage and b-roll (where the reels get their richness)**
- Use whatever real footage exists, in this order:
  1. the owner's own screen recordings or photos;
  2. real archival images (Wikimedia Commons, public domain);
  3. real product UI;
  4. news clippings.
- Every claim about "what AI does in my business" needs the owner's real screen. If it's missing, ask for it with a
  precise shot list (3–5 s each). Never fake it, and never leave the reel bare without saying what's missing.
- B-roll lands on the noun it shows and lasts 1.5–3 s. Speaker and visuals alternate.

**Edit**
- Never clip, chop or repeat dialogue. Cuts sit on gaps in the waveform; consecutive beats share their in/out points.
- Remove only pauses, false starts, and off-platform plugs ("subscribe", "link in description").
- Pick clips that are complete thoughts. Skip mid-list fragments ("the third category…") and clips under 30 s.
- Use punch-ins on the words that carry the argument, alternate framing between beats, and add whip/zoom moves only
  when switching layouts.

**Captions**
- 2–4 word bursts, bold sans, with the spoken word highlighted.
- English captions written from what he actually means. Flag any line where the meaning is uncertain.

**Audio**
- Clean the voice (RNNoise); master to −14 LUFS.
- Report mic clipping honestly. It can't be undone in the edit.

## Visual balance (creative director)
- Speaker 40–60%, proof 10–20%, b-roll 15–30%, motion graphics 5–15%. Never more than two non-speaker beats in a row.
- B-roll comes from the **b-roll agent**, in this order:
  1. the shared library (`reel.py broll-find`), checked first so nothing is paid for twice;
  2. real photos or footage;
  3. stock (1 credit);
  4. AI image or video, only for generic illustrative scenes, within the per-reel budget.
- Everything new is saved back to `library/broll/`, described by what's visible.
- AI never depicts real people or brands, or fakes news or data.

## Director's review (run on the final frames, every reel, before sending)
Answer each question honestly from the rendered frames. Fix anything that fails, then re-check.
1. Pick any graphic. What does the viewer learn from it that the voice didn't say? If the answer is "nothing", delete it.
2. Is anything on screen invented: a prop, a fake UI, a number with no source? Delete it.
3. Is the face fully in frame in every sampled frame, with no caption over it?
4. Is there a stretch longer than ~5 s with no change? Fix it with a punch-in, a cut or real footage, never a card.
5. Does every visual land on the word it belongs to?
6. Is any dialogue clipped, repeated or cut mid-thought? Listen at every cut.
7. Is there a moment worth screenshotting (proof, a number, a contrast)? If not, find real material or ask the owner for it.
8. Is the visual mix in range (speaker 40–60%, proof, b-roll, graphics), with no more than two non-speaker beats in a row?
9. Would this pass next to the reference reels on the same phone screen? If not, say exactly why. Don't ship it quietly.

Send only reels that pass. In the message, name anything that needs the owner (missing screen recordings,
uncertain captions), stated once, with a shot list.
