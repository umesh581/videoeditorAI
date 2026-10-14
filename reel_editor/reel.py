#!/usr/bin/env python3
"""Reel editor pipeline: raw clip -> transcript -> storyboard (written by Claude) -> rendered reel.

  python3 reel.py new <video> [--name slug] [--lang auto]   transcribe + contact sheet
  python3 reel.py build <slug>                              storyboard.json -> props.json + storyboard.md
  python3 reel.py still <slug> --at 3.5                     render one frame (output time) to check the look
  python3 reel.py render <slug> [--draft]                   render the reel to projects/<slug>/out/

B-roll / assets (land in projects/<slug>/public/media/):
  media-search <slug> "query" [--n 4] [--photos]   Pexels stock (PEXELS_API_KEY in reel_editor/.env)
  media-add <slug> <files...> | --library [match]  your own clips/images (library/ folder)
  media-url <slug> <url> [--name x.mp4]            direct download, e.g. an AI-generated clip
  media-shot <slug> <url> [--desktop]              website screenshot for a cards graphic
  media-list <slug> [--library]                    what's available + thumbnail sheet
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import media
import qa as qa_mod

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"
REMOTION = ROOT / "remotion"
MODELS = ROOT / "models"
MUSIC = ROOT / "music"

SHOT_ZOOM = {"wide": 1.0, "medium": 1.12, "close": 1.25, "extreme": 1.45}
# Colour grades are applied by ffmpeg to the source (and b-roll) before Remotion sees it —
# real curves/white balance/denoise/sharpening instead of 8-bit CSS filters.
_BASE = ("curves=all='0/0.03 0.25/0.23 0.5/0.52 0.78/0.80 1/0.93',eq=contrast=1.05:saturation=1.06,"
         "vibrance=intensity=0.12")
_CLEAN = "hqdn3d=1.5:1.5:6:6," + _BASE + ",cas=strength=0.55"
GRADE_LOOK = {  # colour part of each look (applied to speaker footage and b-roll alike)
    "natural": "",
    "cinematic": "colortemperature=temperature=5700:mix=0.55,colorbalance=rs=-0.015:bs=0.025:rh=0.025:bh=-0.02",
    "warm": "colortemperature=temperature=5500:mix=0.65,eq=saturation=1.05",
    "moody": "exposure=exposure=-0.1,curves=all='0/0.05 0.5/0.49 1/0.93',colorbalance=rs=-0.05:bs=0.07:rh=0.04:bh=-0.03,eq=saturation=0.88",
    "punchy": "eq=contrast=1.1:saturation=1.18",
    "bw": "hue=s=0,eq=contrast=1.15",
    "film": "curves=all='0/0.07 0.5/0.5 1/0.9',colorbalance=rs=-0.02:bs=0.03:rh=0.04:bh=-0.03,eq=saturation=0.9",
    # Digital Entrepreneur: high contrast, deep blacks, minimal mid-tones, desaturated base
    # deep blacks but skin/mid-tones protected (the first version crushed faces: −29% brightness)
    "brand": "exposure=exposure=0.12,curves=all='0/0 0.06/0.02 0.2/0.2 0.45/0.52 0.7/0.78 0.9/0.94 1/0.97',eq=saturation=0.72:contrast=1.04",
}
# b-roll overrides: stock footage goes black & white under the brand look (guide: "B&W preferred")
GRADE_BROLL = {"brand": "hue=s=0,curves=all='0/0 0.15/0.03 0.45/0.4 0.7/0.75 1/0.97',eq=contrast=1.12"}
GRADE_VIGNETTE = {"brand": "PI/6", "natural": "", "cinematic": "PI/5", "warm": "PI/6", "moody": "PI/4.5", "punchy": "",
                  "bw": "PI/5", "film": "PI/5"}
GRADES = set(GRADE_LOOK)
CAPTION_STYLES = {"premium", "editorial", "kinetic", "bold-pop", "editorial-serif", "minimal", "huge"}
EMPHASIS = {"gold", "strike", "big", "color"}
OVERLAYS = {"hook", "magazine", "title", "label", "cta", "chapter", "statement", "lowerthird"}
TRANSITIONS = {"cut", "flash", "zoom", "wipe", "whip"}


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        die(f"{cmd[0]} failed:\n{r.stderr[-3000:]}")
    return r.stdout


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "reel"


def fmt(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def norm(w):
    return re.sub(r"[^\w']", "", w.lower())


def project_dir(slug):
    d = PROJECTS / slug
    if not d.exists():
        die(f"no project '{slug}' in {PROJECTS}")
    return d


# ---------------------------------------------------------------- new

def probe(path):
    data = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json",
                           "-show_streams", "-show_format", str(path)]))
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if not v:
        die("no video stream found")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = int(v.get("tags", {}).get("rotate", rot))
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = v.get("avg_frame_rate", "30/1").split("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    return {"duration": float(data["format"]["duration"]), "width": w, "height": h,
            "fps": round(fps, 3), "codec": v["codec_name"],
            "has_audio": any(s["codec_type"] == "audio" for s in data["streams"])}


def pick_model(lang="auto", override=None):
    # large-v3-turbo is far better for Indian languages and code-mixed speech; small is fine for English.
    order = ["ggml-small.bin", "ggml-base.bin", "ggml-large-v3-turbo.bin", "ggml-medium.bin"]
    if lang != "en":
        order = ["ggml-large-v3-turbo.bin", "ggml-medium.bin"] + order
    if override:
        order = [override if override.endswith(".bin") else f"ggml-{override}.bin"]
    for name in order:
        if (MODELS / name).exists():
            return MODELS / name
    die(f"no whisper model ({', '.join(order)}) in {MODELS}")


def transcribe(wav, out_base, lang, model_name=None, chunked=None):
    """Word-level transcript. Non-English is transcribed phrase-by-phrase (split at pauses):
    whisper falls into repetition loops on long Telugu/Hindi windows but is solid on short ones."""
    model = pick_model(lang, model_name)
    if lang == "auto":
        r = subprocess.run(["whisper-cli", "-m", str(model), "-f", str(wav), "-dl", "-np"], capture_output=True, text=True)
        m = re.search(r"auto-detected language: (\w+)", r.stderr + r.stdout)
        lang = m.group(1) if m else "en"
    print(f"      model: {model.name}, language: {lang}")
    if chunked is None:
        chunked = lang != "en"
    if not chunked:
        return _transcribe_file(wav, out_base, lang, model), lang

    total = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)]))
    # speech regions = gaps between silences; merge slivers so each chunk is a real phrase
    regions, pos = [], 0.0
    for s0, s1 in silences(wav) + [(total, total)]:
        if s0 - pos > 0.15:
            regions.append([pos, s0])
        pos = max(pos, s1)
    merged = []
    for r in regions:
        if merged and (r[1] - r[0] < 1.0 or merged[-1][1] - merged[-1][0] < 1.0) and r[0] - merged[-1][1] < 1.2:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    tmp = Path(f"{out_base}_chunks")
    tmp.mkdir(exist_ok=True)
    words = []
    cws = []
    for i, (a, b) in enumerate(merged):
        a0, b0 = max(0.0, a - 0.15), min(total, b + 0.15)
        cw = tmp / f"c{i:03d}.wav"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a0:.3f}", "-t", f"{b0 - a0:.3f}", "-i", str(wav), str(cw)])
        (tmp / f"c{i:03d}.wav.txt").unlink(missing_ok=True)
        cws.append(cw)
    # one model load for every phrase, greedy decoding (measured ~2x faster than beam search on Telugu
    # with equivalent accuracy; captions are rewritten from context by the editor anyway)
    args = [x for cw in cws for x in ("-f", str(cw))]
    subprocess.run(["whisper-cli", "-m", str(model), *args, "-l", lang, "-mc", "0", "-bs", "1", "-bo", "1",
                    "-otxt", "-nt", "-np", "-t", str(os.cpu_count() or 4)], capture_output=True)
    for i, (a, b) in enumerate(merged):
        txt = tmp / f"c{i:03d}.wav.txt"
        text = " ".join(txt.read_bytes().decode("utf-8", "replace").split()) if txt.exists() else ""
        toks = _drop_loops([{"w": t} for t in text.split()])
        # spread the phrase's words across its speech span, proportional to length
        n_chars = sum(len(t["w"]) + 1 for t in toks) or 1
        t, span = a, b - a
        for tok in toks:
            d = span * (len(tok["w"]) + 1) / n_chars
            words.append({"w": tok["w"], "start": round(t, 3), "end": round(t + d, 3), "chunk": i})
            t += d
    print(f"      {len(merged)} phrase chunks (phrase-level timing)")
    return words, lang


def _drop_loops(words):
    """Remove whisper hallucination loops (the same word 3+ times in a row)."""
    out = []
    for w in words:
        if len(out) >= 2 and norm(out[-1]["w"]) == norm(out[-2]["w"]) == norm(w["w"]):
            continue
        out.append(w)
    return out


def _transcribe_file(wav, out_base, lang, model, extra=()):
    # DTW token timestamps are far more accurate than segment offsets, but only work with
    # flash attention off (-nfa). Falls back to plain token offsets if DTW is unavailable.
    dtw = {"ggml-small.bin": "small", "ggml-base.bin": "base", "ggml-medium.bin": "medium",
           "ggml-large-v3-turbo.bin": "large.v3.turbo"}.get(model.name)
    base = ["whisper-cli", "-m", str(model), "-f", str(wav), "-l", lang, "-ojf",
            "-of", str(out_base), "-np", "-t", str(os.cpu_count() or 4), *extra]
    r = subprocess.run(base + (["-dtw", dtw, "-nfa"] if dtw else []), capture_output=True, text=True)
    if r.returncode != 0 and dtw:
        run(base)
    elif r.returncode != 0:
        die(f"whisper failed:\n{r.stderr[-3000:]}")
    # Non-Latin scripts: a token can end mid-character, so keep raw bytes (surrogateescape)
    # until tokens are joined into words, then decode.
    raw = json.loads(Path(f"{out_base}.json").read_bytes().decode("utf-8", "surrogateescape"))

    words = []  # {"w", "start", "end", "seg_end"}
    for seg in raw.get("transcription", []):
        seg_end = seg["offsets"]["to"] / 1000
        for tok in seg.get("tokens", []):
            text = tok["text"]
            if not text.strip() or re.fullmatch(r"\s*\[_.*_\]|\s*\[.*\]", text):
                continue
            t = tok["t_dtw"] / 100 if tok.get("t_dtw", -1) >= 0 else tok["offsets"]["from"] / 1000
            if words and not text.startswith(" "):  # continuation token / punctuation
                words[-1]["w"] += text
                continue
            if words:
                t = max(t, words[-1]["start"] + 0.02)  # keep word order monotonic
            words.append({"w": text.strip(), "start": round(t, 3), "seg_end": seg_end})
    for i, w in enumerate(words):
        nxt = words[i + 1]["start"] if i + 1 < len(words) else w["seg_end"]
        w["end"] = round(max(w["start"] + 0.08, min(nxt, w["start"] + 0.9, max(w["seg_end"], w["start"]))), 3)
        del w["seg_end"]
        w["w"] = w["w"].encode("utf-8", "surrogateescape").decode("utf-8", "replace")
    return [w for w in words if not re.fullmatch(r"\(.*\)|\[.*\]", w["w"])]


def silences(wav):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af",
                        "silencedetect=noise=-35dB:d=0.45", "-f", "null", "-"],
                       capture_output=True, text=True)
    out, start = [], None
    for line in r.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            out.append([round(start, 2), round(float(m.group(1)), 2)])
            start = None
    return out


def phrases(words, gap=0.35):
    out, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > gap or re.search(r"[.?!]$", cur[-1]["w"])):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def cmd_new(a):
    src = Path(a.video).expanduser().resolve()
    if not src.exists():
        die(f"{src} not found")
    slug = a.name or slugify(src.stem)
    d = PROJECTS / slug
    if d.exists() and not a.force:
        die(f"project '{slug}' exists (use --force to redo, or --name)")
    (d / "public").mkdir(parents=True, exist_ok=True)
    dest = d / "public" / f"source{src.suffix.lower()}"
    if dest.exists():
        dest.unlink()
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)

    meta = probe(dest)
    if not meta["has_audio"]:
        die("clip has no audio track — nothing to transcribe")
    meta["source"] = dest.name
    meta["original"] = str(src)
    print(f"[1/3] {src.name}: {fmt(meta['duration'])}, {meta['width']}x{meta['height']} @ {meta['fps']}fps")

    # colour-grade the master (+ its QA proxy) on a worker thread while whisper transcribes:
    # ffmpeg grading is CPU-bound, whisper runs mostly on the GPU, so they overlap almost perfectly
    pre = None
    if a.pregrade:
        import threading
        def _pregrade():
            try:
                rel = graded(d, dest.name, a.pregrade, speaker=True)
                qa_mod._proxy(d, rel)
            except Exception as e:  # never fail ingest over a cache warm-up
                print(f"      (pregrade skipped: {e})")
        pre = threading.Thread(target=_pregrade, daemon=True)
        pre.start()
    wav = d / "audio16k.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(dest), "-ac", "1", "-ar", "16000", str(wav)])
    print("[2/3] transcribing (whisper.cpp)…")
    words, lang = transcribe(wav, d / "whisper", a.lang, a.model)
    sil = silences(wav)

    transcript = {"meta": meta, "language": lang, "words": words, "silences": sil}
    (d / "transcript.json").write_text(json.dumps(transcript, indent=1, ensure_ascii=False))
    lines = [f"# {src.name} — {fmt(meta['duration'])} — lang={lang}",
             "# [start-end] phrase   (gaps > 0.35s split lines; times are SOURCE seconds)", ""]
    for p in phrases(words):
        lines.append(f"[{p[0]['start']:7.2f}-{p[-1]['end']:7.2f}] " + " ".join(w["w"] for w in p))
    lines += ["", "# silences (>0.45s): " + ", ".join(f"{s}-{e}" for s, e in sil)]
    (d / "transcript.txt").write_text("\n".join(lines), encoding="utf-8")

    print("[3/3] contact sheet…")
    n = 24
    step = meta["duration"] / n
    run(["ffmpeg", "-y", "-v", "error", "-i", str(dest), "-vf",
         f"fps=1/{step:.3f},scale=240:-2,tile=6x4:padding=4", "-frames:v", "1", str(d / "contact.jpg")])
    (d / "contact.txt").write_text(
        f"contact.jpg: 6x4 grid, left-to-right then top-to-bottom; tile k (0-based) ≈ {step:.2f}*k s\n")
    if pre:
        pre.join()
    print(f"\nproject: {d}\n  transcript.txt  ({len(words)} words)\n  contact.jpg     (tile k ≈ {step:.2f}s × k)")


# ---------------------------------------------------------------- build

def load_brand(name):
    if not name:
        return {}
    f = ROOT / "brands" / f"{name}.json"
    if not f.exists():
        die(f"brand '{name}' not found in {ROOT / 'brands'}")
    return json.loads(f.read_text())


def load(d):
    sb_path = d / "storyboard.json"
    if not sb_path.exists():
        die(f"{sb_path} missing — write the storyboard first")
    sb = json.loads(sb_path.read_text())
    brand = load_brand(sb.get("brand"))
    for key, val in brand.get("defaults", {}).items():  # storyboard values win over brand defaults
        sb[key] = {**val, **sb.get(key, {})} if isinstance(val, dict) else sb.get(key, val)
    theme = brand.get("theme")
    if theme and brand.get("video") and sb.get("brandMode", "video") == "video":
        v = {k: x for k, x in brand["video"].items() if not k.startswith("_")}
        theme = {**theme, **v, "colors": {**theme["colors"], **v.get("colors", {})}, "radius": {**theme["radius"], **v.get("radius", {})}}
    sb["_theme"] = theme
    return sb, json.loads((d / "transcript.json").read_text())


def validate(sb, meta):
    errs = []
    look, cap = sb.get("look", {}), sb.get("captions", {})
    if look.get("grade", "natural") not in GRADES:
        errs.append(f"look.grade must be one of {sorted(GRADES)}")
    if look.get("fit", "cover") not in ("cover", "blur"):
        errs.append("look.fit must be cover or blur")
    if cap.get("style", "bold-pop") not in CAPTION_STYLES:
        errs.append(f"captions.style must be one of {sorted(CAPTION_STYLES)}")
    if not sb.get("beats"):
        errs.append("no beats")
    for b in sb.get("beats", []):
        tag = f"beat {b.get('id', '?')}"
        if not (0 <= b["in"] < b["out"] <= meta["duration"] + 0.05):
            errs.append(f"{tag}: in/out {b['in']}-{b['out']} outside 0-{meta['duration']:.2f}")
        if b.get("shot", "wide") not in SHOT_ZOOM and "zoom" not in b:
            errs.append(f"{tag}: shot must be one of {list(SHOT_ZOOM)}")
        if b.get("transition", "cut") not in TRANSITIONS:
            errs.append(f"{tag}: transition must be one of {sorted(TRANSITIONS)}")
        for e in b.get("emphasis", []):
            if e.get("style") not in EMPHASIS:
                errs.append(f"{tag}: emphasis style must be one of {sorted(EMPHASIS)}")
        for o in b.get("overlays", []):
            if o.get("style") not in OVERLAYS:
                errs.append(f"{tag}: overlay style must be one of {sorted(OVERLAYS)}")
        for g in b.get("graphics", []):
            if g.get("type") not in GRAPHICS:
                errs.append(f"{tag}: graphic type must be one of {sorted(GRAPHICS)}")
        for r in b.get("broll", []):
            if r.get("mode", "full") not in BROLL_MODES:
                errs.append(f"{tag}: broll mode must be one of {sorted(BROLL_MODES)}")
            if "src" not in r:
                errs.append(f"{tag}: broll needs src")
    theme = sb.get("_theme") or {}
    if theme.get("icons") == "line":
        for b in sb.get("beats", []):
            for g in b.get("graphics", []):
                if g.get("type") == "sticker" and g.get("emoji"):
                    errs.append(f"beat {b.get('id')}: brand '{theme.get('name')}' uses line icons — "
                                f"replace emoji sticker with \"icon\": \"<lucide-name>\"")
    m = sb.get("music")
    if m and not (MUSIC / m["file"]).exists():
        errs.append(f"music file {m['file']} not in {MUSIC}")
    if errs:
        die("storyboard problems:\n  - " + "\n  - ".join(errs))


def sound_in(a, z, quiet):
    """Seconds of non-silence (by the audio, not the transcript) inside [a, z]."""
    if z <= a:
        return 0.0
    q = sum(max(0.0, min(z, e) - max(a, s0)) for s0, e in quiet)
    return (z - a) - q


def snap_to_silence(a, z, quiet, total, reach=0.9, pad=0.06):
    """Move a cut point that lands inside sound out to the nearest silence edge (within `reach` seconds):
    in-points move earlier to where the sound starts, out-points later to where it stops."""
    def inside_sound(t):
        return not any(s0 <= t <= e for s0, e in quiet)
    if inside_sound(a):
        prev = [e for s0, e in quiet if e <= a + 1e-6]
        if prev and a - max(prev) <= reach:
            a = max(0.0, max(prev) - pad)
    if inside_sound(z):
        nxt = [s0 for s0, e in quiet if s0 >= z - 1e-6]
        if nxt and min(nxt) - z <= reach:
            z = min(total, min(nxt) + pad)
    return a, z


def fix_text(text, corrections):
    for wrong, right in corrections.items():
        text = re.sub(rf"\b{re.escape(wrong)}\b", right, text, flags=re.IGNORECASE)
    return text


GRAPHICS = {"bespoke", "cards", "logos", "counter", "checklist", "flow", "notify", "event", "highlight", "compare", "prompt", "slam", "sticker"}
BROLL_MODES = {"full", "pip", "split", "card"}
SFX_NAMES = {"whoosh", "pop", "ding", "hit", "riser", "click", "type"}
# default sounds per element: list of (sound, frame offset from the element's start)
SFX_DEFAULT = {
    "cards": [("whoosh", 0)], "counter": [("riser", 0)], "highlight": [("whoosh", 0)],
    "compare": [("whoosh", 0), ("whoosh", 12)], "prompt": [("type", 6)], "sticker": [("pop", 0)], "event": [("pop", 2)],
    "hook": [("whoosh", 0)], "magazine": [("hit", 0)], "title": [("whoosh", 0)], "label": [("pop", 0)],
    "chapter": [("whoosh", 0)], "statement": [("hit", 2)], "lowerthird": [("click", 2)],
    "cta": [("pop", 0)], "full": [("whoosh", 0)], "split": [("whoosh", 0)], "pip": [("pop", 0)], "card": [("whoosh", 0)],
    "flash": [("hit", 0)], "zoom": [("whoosh", 0)], "wipe": [("whoosh", -6)], "whip": [("whoosh", -3)],
}


class Beat:
    """Per-beat context for turning storyboard times/word anchors into output frames."""

    def __init__(self, b, start, dur, fps, words, errs):
        self.b, self.start, self.dur, self.fps, self.words, self.errs = b, start, dur, fps, words, errs
        self.tag = f"beat {b.get('id', '?')}"

    def find(self, phrase):
        toks = [norm(t) for t in str(phrase).split()]
        for i in range(len(self.words) - len(toks) + 1):
            if all(norm(self.words[i + j]["text"]) == toks[j] for j in range(len(toks))):
                return self.words[i], self.words[i + len(toks) - 1]
        return None

    def at(self, spec, default=0.0):
        """Output frame for spec['on'] (a spoken word/phrase) or spec['at'] (seconds from beat start)."""
        if spec.get("on"):
            hit = self.find(spec["on"])
            if hit:
                return hit[0]["from"]
            self.errs.append(f"{self.tag}: '{spec['on']}' is not spoken in this beat")
        return self.start + round(spec.get("at", default) * self.fps)

    def until(self, spec, f0, default_end=None):
        if spec.get("until"):
            hit = self.find(spec["until"])
            if hit:
                return max(f0 + 6, hit[1]["to"])
            self.errs.append(f"{self.tag}: until '{spec['until']}' is not spoken in this beat")
        if "dur" in spec:
            return f0 + round(spec["dur"] * self.fps)
        return default_end if default_end is not None else self.start + self.dur


def media_path(project, name, errs, tag):
    name = name if name.startswith("media/") else f"media/{name}"
    if not (project / "public" / name).exists():
        errs.append(f"{tag}: {name} not found — add it with media-search / media-add / media-url / media-shot")
    return name


def resolve(sb, tr, project):
    meta = tr["meta"]
    fps = sb.get("fps", 30)
    errs, warns = [], []
    look = {"grade": "natural", "vignette": 0.0, "grain": False, "push": False, "fit": "cover",
            **sb.get("look", {})}
    cap = {"enabled": True, "style": "bold-pop", "size": 1.0, "position": "lower",
           "color": "#FFFFFF", "highlightColor": "#F5C542", "wordsPerChunk": 3, **sb.get("captions", {})}
    per_chunk = cap.pop("wordsPerChunk")
    corrections = sb.get("corrections", {})
    hide = {norm(w) for w in sb.get("hideWords", [])}
    default_focus = sb.get("focus", [0.5, 0.4])
    sfx_cfg = {"enabled": True, "volume": 0.5, **(sb.get("sfx") or {})}
    midx = media.index(project)

    beats, words_out, overlays, graphics, broll, sfx, cursor = [], [], [], [], [], [], 0
    docks, punches = [], []
    slam_windows = []
    deferred = []  # bespoke cues spoken in a later beat, resolved once every beat is placed

    def add_sfx(kind, f0, override=None):
        if not sfx_cfg["enabled"] or override is False:
            return
        cues = [(override, 0)] if isinstance(override, str) else SFX_DEFAULT.get(kind, [])
        for name, off in cues:
            if name in SFX_NAMES:
                sfx.append({"src": f"sfx/{name}.wav", "from": f0 + off, "volume": sfx_cfg["volume"]})

    tight = {"enabled": True, "minPause": 0.3, "keep": 0.1, "jumpZoom": 1.07, **(sb.get("tighten") or {})}
    tight["minPause"] = max(0.3, tight["minPause"])  # older storyboards asked for 0.22 — too aggressive
    tight["keep"] = max(0.1, tight["keep"])
    spoken = [(w["start"], w["end"]) for w in tr["words"]]
    quiet = tr.get("quiet", [])

    def speech_in(a, z, pad=0.06):
        """True if any transcribed word overlaps [a, z] — a cut there would chop dialogue."""
        return any(ws < z + pad and we > a - pad for ws, we in spoken)
    pauses = tr.get("pauses", []) if tight["enabled"] else []
    tightened = [0, 0.0]

    for i, b in enumerate(sb["beats"]):
        # --- tighten: drop pauses inside the beat (and dead air at its edges) as jump cuts
        b_in, b_out = b["in"], b["out"]
        # snap to the audio: a beat may only start/end inside measured silence (never mid-sound)
        if not b.get("noSnap"):
            b_in, b_out = snap_to_silence(b_in, b_out, quiet, tr["meta"]["duration"])
        for ps, pe in pauses:
            if ps <= b_in < pe and not speech_in(b["in"], pe - tight["keep"]):
                b_in = max(b_in, pe - tight["keep"])
            if ps < b_out <= pe and not speech_in(ps + tight["keep"], b["out"]):
                b_out = min(b_out, ps + tight["keep"])
        segs = [[b_in, b_out]]
        if not b.get("noTighten"):
            for ps, pe in pauses:
                a, z = ps + tight["keep"], pe - tight["keep"]
                if (pe - ps < tight["minPause"] or z - a < 0.12 or not (b_in < ps and pe < b_out) or speech_in(a, z)
                        or sound_in(a, z, quiet) > 0.03):
                    continue
                last = segs[-1]
                if last[0] < a and z < last[1]:
                    segs[-1:] = [[last[0], a], [z, last[1]]]
                    tightened[0] += 1
                    tightened[1] += z - a
        tightened[1] += (b_in - b["in"]) + (b["out"] - b_out)
        fsegs = [(round(x * fps), round(y * fps)) for x, y in segs]
        fsegs = [sg for sg in fsegs if sg[1] - sg[0] >= 4] or [(round(b_in * fps), round(b_out * fps))]
        tmap, pos = [], cursor  # (src_from, src_to, out_from)
        for x, y in fsegs:
            tmap.append((x, y, pos))
            pos += y - x
        dur = pos - cursor

        def src2out(t, tmap=tmap):
            f = t * fps
            for x, y, o in tmap:
                if f < y:
                    return o + max(0, round(f - x))
            x, y, o = tmap[-1]
            return o + (y - x)

        def out2src(f, tmap=tmap):
            for x, y, o in tmap:
                if f < o + (y - x):
                    return x + max(0, f - o)
            return tmap[-1][1]

        focus = b.get("focus", default_focus)
        base_zoom = b.get("zoom", SHOT_ZOOM.get(b.get("shot", "wide"), 1.0))
        for k, (x, y, o) in enumerate(tmap):
            beats.append({"id": b.get("id", i + 1), "group": i, "from": o, "duration": y - x, "trimBefore": x,
                          "zoom": round(base_zoom * (tight["jumpZoom"] if k % 2 else 1.0), 3),
                          "focusX": focus[0], "focusY": focus[1],
                          "transition": b.get("transition", "cut") if k == 0 else "cut",
                          **({"mono": True} if b.get("mono") else {})})
        if i > 0:
            add_sfx(beats[-len(tmap)]["transition"], cursor, b.get("sfx"))
        in_f = fsegs[0][0]

        bw = []
        emph = [dict(e, used=False) for e in b.get("emphasis", [])]
        for w in tr["words"]:
            mid = (w["start"] + w["end"]) / 2
            if not (b["in"] <= mid < b["out"]):
                continue
            text = fix_text(w["w"], corrections)
            f0 = src2out(w["start"])
            f1 = min(cursor + dur, src2out(w["end"]))
            rw = {"text": re.sub(r"[,.;:]+$", "", text), "from": f0, "to": max(f1, f0 + 2),
                  "beat": i, "end": bool(re.search(r"[.?!]$", text))}
            bw.append(rw)
        if b.get("captionText"):
            # Clean caption written by the editor (fixes ASR spelling, or translates): spread its
            # words over the span where speech was actually detected in this beat.
            toks = b["captionText"].split()
            f_a = bw[0]["from"] if bw else cursor
            f_b = bw[-1]["to"] if bw else cursor + dur
            n_chars = sum(len(t) + 1 for t in toks) or 1
            t_f, out = float(f_a), []
            for tok in toks:
                d = (f_b - f_a) * (len(tok) + 1) / n_chars
                out.append({"text": re.sub(r"[,.;:]+$", "", tok), "from": round(t_f), "to": max(round(t_f + d), round(t_f) + 2),
                            "beat": i, "end": bool(re.search(r"[.?!]$", tok))})
                t_f += d
            bw = out
        for rw in bw:
            for e in emph:
                if norm(e["word"]) == norm(rw["text"]) and (e.get("all") or not e["used"]):
                    rw["emphasis"], e["used"] = e["style"], True
                    break
        ctx = Beat(b, cursor, dur, fps, bw, errs)
        words_out += [w for w in bw if norm(w["text"]) not in hide]

        if b.get("layout") == "dock":
            docks.append([cursor, cursor + dur])
        for w in bw:
            if w.get("emphasis") == "big" or norm(w["text"]) in {norm(x) for x in b.get("punch", [])}:
                punches.append(w["from"])
        for o in b.get("overlays", []):
            f0 = ctx.at(o)
            overlays.append({"text": o["text"], "sub": o.get("sub"), "style": o["style"], "from": f0,
                             "to": ctx.until(o, f0)})
            if o["style"] in ("chapter", "statement"):
                slam_windows.append((f0, overlays[-1]["to"]))
            add_sfx(o["style"], f0, o.get("sfx"))

        for r in b.get("broll", []):
            tag = f"{ctx.tag} broll"
            src = media_path(project, r["src"], errs, tag)
            mode = r.get("mode", "full")
            f0 = ctx.at(r)
            f1 = ctx.until(r, f0)
            if mode in ("pip", "split"):
                f1 = min(f1, cursor + dur)  # pip/split re-render the speaker from this beat only
            info = midx.get(src.split("/", 1)[1], {})
            kind = info.get("kind") or ("image" if Path(src).suffix.lower() in media.IMAGE_EXT else "video")
            clip_start = round(r.get("clipStart", 0) * fps)
            if kind == "video" and info.get("duration"):
                avail = round(info["duration"] * fps) - clip_start
                if f1 - f0 > avail:
                    warns.append(f"{tag}: {src} only has {avail / fps:.1f}s from clipStart — shortened")
                    f1 = f0 + avail
            rf = r.get("focus", [0.5, 0.5])
            if mode == "card":
                docks.append([max(0, f0 - 4), f1 + 8])  # card clips live on the canvas; speaker docks below
            broll.append({"src": src, "kind": kind, "from": f0, "to": f1, "clipStart": clip_start, "mode": mode,
                          "speakerTrim": out2src(f0), "focusX": rf[0], "focusY": rf[1],
                          "label": r.get("label")})
            add_sfx(mode, f0, r.get("sfx"))

        for g in b.get("graphics", []):
            t = g.get("type")
            tag = f"{ctx.tag} {t}"
            f0 = ctx.at(g)
            f1 = ctx.until(g, f0)
            out = {k: v for k, v in g.items() if k not in ("at", "on", "dur", "until", "sfx")}
            out.update({"from": f0, "to": f1})
            if t == "cards":
                out["images"] = [media_path(project, im, errs, tag) for im in g.get("images", [])]
            elif t == "logos":
                items = []
                for it in g.get("items", []):
                    it = {"name": it} if isinstance(it, str) else dict(it)
                    if it.get("image"):
                        it["image"] = media_path(project, it["image"], errs, tag)
                    else:
                        it.update(media.icon(it.get("slug") or it["name"]) or {})
                    it.pop("slug", None)
                    items.append(it)
                out["items"] = items
                if sfx_cfg["enabled"] and g.get("sfx") is not False:
                    for k, it in enumerate(items):
                        sfx.append({"src": "sfx/pop.wav", "from": f0 + 4 + k * 5, "volume": sfx_cfg["volume"]})
                        if it.get("strike"):
                            sfx.append({"src": "sfx/click.wav", "from": f0 + 14 + k * 5, "volume": sfx_cfg["volume"]})
            elif t == "notify":
                out["items"] = [{**{k: v for k, v in it.items() if k not in ("at", "on")},
                                 "at": ctx.at(it, default=(f0 - cursor) / fps + 0.2 + 1.2 * k)}
                                for k, it in enumerate(g.get("items", []))]
                for it in out["items"]:
                    add_sfx("", it["at"], None if g.get("sfx") is False else "ding")
            elif t in ("checklist", "flow"):
                out["items"] = [{"text": it["text"], "at": ctx.at(it, default=(f0 - cursor) / fps + 0.3 + 0.6 * k),
                                 **({"icon": it["icon"]} if it.get("icon") else {})}
                                for k, it in enumerate(g.get("items", []))]
                for it in out["items"]:
                    add_sfx("", it["at"] + (6 if t == "checklist" else 0),
                            None if g.get("sfx") is False else ("ding" if t == "checklist" else "click"))
            elif t == "slam":
                words = [{"text": w} if isinstance(w, str) else dict(w) for w in g.get("words", [])]
                n = max(1, len(words))
                for k, w in enumerate(words):
                    if "on" not in w and "at" not in w and ctx.find(w["text"]):
                        w["on"] = w["text"]
                    even = (f0 - cursor) / fps + k * ((f1 - f0) / fps * 0.7 / n)
                    w["at"] = ctx.at(w, default=even) if ("on" in w or "at" in w) else cursor + round(even * fps)
                    w.pop("on", None)
                    add_sfx("", w["at"], None if g.get("sfx") is False else "hit")
                out["words"] = words
                slam_windows.append((f0, f1))
            elif t == "bespoke":
                # hand-built hero scene (remotion/src/bespoke/<name>): named cues anchor its moments to speech
                out["cues"] = {}
                for name, spec in (g.get("cues") or {}).items():
                    spec = {"on": spec} if isinstance(spec, str) else spec
                    if spec.get("on") and not ctx.find(spec["on"]):
                        deferred.append((out, name, spec, f"{tag} cue '{name}'"))
                        continue
                    out["cues"][name] = ctx.at(spec)
                    if spec.get("sfx"):
                        add_sfx("", out["cues"][name], spec["sfx"])
            elif t == "sticker" and g.get("image"):
                out["image"] = media_path(project, g["image"], errs, tag)
            elif t == "prompt" and g.get("status") and g.get("sfx") is not False:
                add_sfx("", f0 + round(min((f1 - f0) * 0.6, fps * 1.3)) + 4, "ding")
            if t not in ("logos", "checklist", "flow", "notify", "slam"):
                add_sfx(t, f0, g.get("sfx"))
            if g.get("dock"):
                docks.append([max(0, f0 - 4), f1 + 8])  # graphic exits first, then the speaker expands back
                if out.get("pos") in (None, "top", "center"):
                    out["pos"] = "canvas"  # docked speaker: graphic lives in the canvas above the window
            out.pop("dock", None)
            graphics.append(out)
        cursor += dur

    for out, name, spec, tag in deferred:
        toks = [norm(x) for x in str(spec["on"]).split()]
        hit = next((words_out[i]["from"] for i in range(len(words_out) - len(toks) + 1)
                    if words_out[i]["from"] >= out["from"]
                    and all(norm(words_out[i + j]["text"]) == toks[j] for j in range(len(toks)))), None)
        if hit is None:
            errs.append(f"{tag}: '{spec['on']}' is not spoken after the scene starts")
            continue
        out["cues"][name] = hit
        if hit >= out["to"]:
            warns.append(f"{tag}: cue lands after the scene ends")
        if spec.get("sfx"):
            add_sfx("", hit, spec["sfx"])

    # audio integrity: what the edit removes must be silence — measured from the audio, not the transcript
    kept = sorted((x["trimBefore"] / fps, (x["trimBefore"] + x["duration"]) / fps) for x in beats)
    gaps, pos = [], 0.0
    for a0, z0 in kept:
        if a0 - pos > 0.03:
            gaps.append((pos, a0))
        pos = max(pos, z0)
    cut_sound = [(a0, z0, round(sound_in(a0, z0, quiet), 2)) for a0, z0 in gaps if sound_in(a0, z0, quiet) > 0.15]
    for a0, z0, snd in cut_sound:
        # inside a kept beat range = tightening (must never happen); between beats = an editorial cut of sound
        inside = any(b["in"] < a0 and z0 < b["out"] for b in sb["beats"])
        (errs if inside else warns).append(
            f"the edit removes {snd:.2f}s of SOUND at {a0:.2f}–{z0:.2f}s — likely dialogue; "
            + ("tightening cut it" if inside else "widen the neighbouring beat or confirm it's intentional"))

    # dialogue integrity: a word inside a beat must not be chopped by tightening or beat edges
    for i, b in enumerate(sb["beats"]):
        segs = [(x["trimBefore"] / fps, (x["trimBefore"] + x["duration"]) / fps) for x in beats if x["group"] == i]
        for ws, we in spoken:
            if not (b["in"] <= (ws + we) / 2 < b["out"]) or we - ws <= 0:
                continue
            kept = sum(max(0.0, min(we, z) - max(ws, a)) for a, z in segs) / (we - ws)
            if kept < 0.85:
                errs.append(f"beat {b.get('id')}: a word at {ws:.2f}s would be cut ({kept:.0%} kept) — move in/out to a word boundary")
    if errs:
        die("storyboard problems:\n  - " + "\n  - ".join(errs))

    # full-screen slams replace the captions underneath them
    words_out = [w for w in words_out if not any(a <= w["from"] < z for a, z in slam_windows)]

    chunks, cur = [], []
    for w in words_out:
        if cur and (len(cur) >= per_chunk or cur[-1]["end"] or w["beat"] != cur[-1]["beat"]
                    or w["from"] - cur[-1]["to"] > 0.4 * fps):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    rchunks = []
    for i, c in enumerate(chunks):
        end = c[-1]["to"] + round(0.25 * fps)
        if i + 1 < len(chunks):
            nxt = chunks[i + 1][0]["from"]
            end = nxt if nxt - c[-1]["to"] < 0.5 * fps else min(end, nxt)
        end = min([end] + [a for a, z in slam_windows if c[0]["from"] < a < end])  # never under a slam
        rchunks.append({"from": c[0]["from"], "to": min(end, cursor),
                        "words": [{k: w[k] for k in ("text", "from", "to", "emphasis") if k in w} for w in c]})

    music = None
    if sb.get("music"):
        music = {"src": "music/" + sb["music"]["file"], "volume": sb["music"].get("volume", 0.12)}
    pb = look.pop("progressBar", None)
    if pb == "accent" and not sb.get("_theme"):
        pb = cap["highlightColor"]
    props = {"fps": fps, "width": sb.get("width", 1080), "height": sb.get("height", 1920),
             "durationInFrames": cursor, "src": meta["source"], "look": look, "captions": cap,
             "beats": beats, "chunks": rchunks, "overlays": overlays, "broll": broll, "graphics": graphics,
             "sfx": sorted(sfx, key=lambda x: x["from"]),
             "progressBar": (pb if isinstance(pb, str) else "#F5C542") if pb else None,
             "music": music, "sourceVolume": sb.get("sourceVolume", 1.0),
             "tightened": {"cuts": tightened[0], "seconds": round(tightened[1], 2)},
             "theme": sb.get("_theme"), "docks": _merge(docks), "punches": sorted(punches),
             "placement": sb.get("placement", "organic")}
    if look.get("dockStyle") == "top":
        props["docks"] = [[-30, cursor + 30]]  # podcast layout: speaker held in the top half throughout
    return props, warns


def _merge(windows, gap=10):
    out = []
    for a, z in sorted(windows):
        if out and a - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], z)
        else:
            out.append([a, z])
    return out


def retention(props):
    """Visual-change audit: every moment where something new appears on screen."""
    fps, total = props["fps"], props["durationInFrames"]
    ev = []
    prev = None
    for b in props["beats"]:
        if prev is None or b["zoom"] != prev["zoom"] or b["transition"] != "cut" or b["focusX"] != prev["focusX"]:
            ev.append((b["from"], f"beat {b['id']} ({b['transition']}, zoom {b['zoom']})"))
        prev = b
    ev += [(r["from"], f"b-roll {r['src']} ({r['mode']})") for r in props["broll"]]
    ev += [(f, "punch-in") for f in props.get("punches", [])]
    ev += [(a, "dock") for a, _ in props.get("docks", [])] + [(z, "undock") for _, z in props.get("docks", [])]
    ev += [(r["to"], "back to speaker") for r in props["broll"] if r["to"] < total]
    ev += [(g["from"], f"{g['type']}") for g in props["graphics"]]
    ev += [(i["at"], f"{g['type']} item") for g in props["graphics"] if g["type"] in ("checklist", "flow", "notify", "slam")
           for i in g.get("items", g.get("words", []))]
    ev += [(o["from"], f"{o['style']} \"{o['text']}\"") for o in props["overlays"]]
    ev += [(w["from"], f"emphasis '{w['text']}'") for c in props["chunks"] for w in c["words"] if w.get("emphasis")]
    ev.sort()
    times = sorted({f for f, _ in ev} | {total})
    gaps, last = [], 0
    for t in times:
        if t - last > 3 * fps:
            gaps.append((last / fps, t / fps))
        last = t
    hook = any(f < 0.6 * fps for f, d in ev if not d.startswith("beat") and not d.startswith("emphasis"))
    return ev, gaps, hook


def storyboard_md(sb, tr, props):
    fps = props["fps"]
    meta = tr["meta"]
    total = props["durationInFrames"] / fps
    look, cap = props["look"], props["captions"]
    L = [f"# Storyboard — {sb.get('title', 'reel')}  (v{sb.get('version', 1)})", "",
         f"**Output:** {fmt(total)} from {fmt(meta['duration'])} raw "
         f"({100 * (1 - total / meta['duration']):.0f}% cut) · {len(sb['beats'])} beats · "
         f"{props['width']}×{props['height']} @ {fps}fps",
         f"**Look:** grade `{look['grade']}`, fit {look['fit']}, vignette {look['vignette']}, grain {look['grain']}, push-in {look['push']}",
         f"**Captions:** `{cap['style']}` ×{cap['size']} at {cap['position']}"
         + ("" if cap["enabled"] else " (OFF)"),
         f"**Music:** {sb['music']['file'] + ' @ ' + str(sb['music'].get('volume', 0.12)) if sb.get('music') else 'none'}",
         "", "| # | Out time | Src in–out | Shot | Spoken | Emphasis / Overlays | Trans |",
         "|---|---|---|---|---|---|---|"]
    groups = {}
    for rb in props["beats"]:
        g = groups.setdefault(rb.get("group", rb["id"]), dict(rb, duration=0, cuts=-1))
        g["duration"] += rb["duration"]
        g["cuts"] += 1
    for b, rb in zip(sb["beats"], [groups[k] for k in sorted(groups)]):
        spoken = b.get("captionText") or " ".join(fix_text(w["w"], sb.get("corrections", {})) for w in tr["words"]
                                                  if b["in"] <= (w["start"] + w["end"]) / 2 < b["out"])
        extras = [f"*{e['word']}*→{e['style']}" for e in b.get("emphasis", [])]
        extras += [f"[{o['style']}] \"{o['text']}\"" + (f" / {o['sub']}" if o.get("sub") else "")
                   for o in b.get("overlays", [])]
        extras += [f"🎬 {r['src']} ({r.get('mode', 'full')}" + (f" on '{r['on']}'" if r.get("on") else "") + ")"
                   for r in b.get("broll", [])]
        extras += [f"✦ {g['type']}" + (f" on '{g['on']}'" if g.get("on") else "") + gdesc(g)
                   for g in b.get("graphics", [])]
        if b.get("note"):
            extras.append(f"_{b['note']}_")
        L.append(f"| {rb['id']} | {fmt(rb['from'] / fps)} ({rb['duration'] / fps:.1f}s) | "
                 f"{b['in']:.2f}–{b['out']:.2f} | {b.get('shot', 'wide')} | {spoken.replace('|', '/')} | "
                 f"{'; '.join(extras)} | {rb['transition']} |")
    # what got cut
    kept = sorted((b["in"], b["out"]) for b in sb["beats"])
    gaps, pos = [], 0.0
    for s, e in kept + [(meta["duration"], meta["duration"])]:
        if s - pos > 0.3:
            said = " ".join(w["w"] for w in tr["words"] if pos <= (w["start"] + w["end"]) / 2 < s)
            gaps.append(f"- {pos:.2f}–{s:.2f} ({s - pos:.1f}s): {said or '(silence)'}")
        pos = max(pos, e)
    t = props.get("tightened", {})
    if t.get("cuts") or t.get("seconds"):
        gaps.append(f"- tightened: {t['cuts']} pauses inside beats + edge trims, {t['seconds']:.1f}s removed")
    L += ["", "## Removed", *(gaps or ["- nothing"])]

    ev, dead, hook = retention(props)
    L += ["", "## Retention check",
          f"- Visual changes: {len(ev)} in {total:.1f}s (one every {total / max(1, len(ev)):.1f}s)",
          f"- Hook graphic in first 0.6s: {'yes' if hook else '**NO — add a hook overlay/graphic on beat 1**'}"]
    L += [f"- **Static {b - a:.1f}s at {fmt(a)}–{fmt(b)}** — add b-roll, a graphic or a shot change" for a, b in dead] \
        or ["- No stretch over 3s without something new on screen ✓"]
    return "\n".join(L) + "\n"


def gdesc(g):
    t = g["type"]
    if t == "logos":
        return ": " + ", ".join((i if isinstance(i, str) else ("~~" + i["name"] + "~~" if i.get("strike") else i["name"]))
                                for i in g.get("items", []))
    if t == "counter":
        return f": {g.get('prefix', '')}{g.get('value')}{g.get('suffix', '')} {g.get('label', '')}"
    if t in ("checklist", "flow"):
        return ": " + (" / " if t == "checklist" else " → ").join(i["text"] for i in g.get("items", []))
    if t == "slam":
        return ": " + " ".join(w if isinstance(w, str) else w["text"] for w in g.get("words", []))
    if t in ("prompt",):
        return f": \"{g.get('text', '')}\""
    if t == "compare":
        return f": {g['left']['title']} vs {g['right']['title']}"
    if t == "cards":
        return f": {len(g.get('images', []))} image(s)"
    return ""


def grade_filter(grade, speaker=True):
    look = GRADE_LOOK[grade] if speaker else GRADE_BROLL.get(grade, GRADE_LOOK[grade])
    chain = [_CLEAN if speaker else _BASE]
    if look:
        chain.append(look)
    if speaker and GRADE_VIGNETTE[grade]:
        chain.append(f"vignette=angle={GRADE_VIGNETTE[grade]}")
    return ",".join(chain)


def auto_exposure(src, vf, target=125.0, samples=6):
    """Exposure correction (in stops) so graded skin lands near `target` luma: measures the face on a few
    graded sample frames with Apple Vision. Dim webcam footage gets lifted; well-lit footage is left alone."""
    import math
    import tempfile
    dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)]) or 0)
    if dur <= 0 or not qa_mod.FACEDETECT.exists():
        return 0.0
    with tempfile.TemporaryDirectory() as tmp:
        pngs = []
        for k in range(samples):
            out = Path(tmp) / f"s{k}.png"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{dur * (k + 0.5) / samples:.2f}", "-i", str(src),
                            "-frames:v", "1", "-vf", vf + ",scale=360:-2", str(out)], capture_output=True)
            if out.exists():
                pngs.append(out)
        fr = subprocess.run([str(qa_mod.FACEDETECT), *map(str, pngs)], capture_output=True, text=True)
        lumas = []
        for line in fr.stdout.splitlines():
            j = json.loads(line)
            if j["faces"]:
                x, y, w, h = max(j["faces"], key=lambda b: b[2] * b[3])
                rgb = qa_mod._rgb(Path(j["path"]))
                if rgb:
                    l = qa_mod._luma_in(rgb, (x + w * 0.25, y + h * 0.3, x + w * 0.75, y + h * 0.8))
                    if l:
                        lumas.append(l)
    if len(lumas) < 2:
        return 0.0
    skin = sorted(lumas)[len(lumas) // 2]
    stops = max(0.0, min(0.9, math.log2(target / max(skin, 1))))  # only ever lift; the grade owns the blacks
    return round(stops, 2) if abs(stops) >= 0.08 else 0.0


def graded(d, rel, grade, speaker):
    """Graded copy of public/<rel> (cached by filter hash); returns the new public-relative path."""
    import hashlib
    vf = grade_filter(grade, speaker)
    if speaker and grade != "natural" and Path(rel).suffix.lower() not in media.IMAGE_EXT:
        ev = auto_exposure(d / "public" / rel, vf)
        if ev:
            print(f"auto-exposure: {ev:+.2f} stops to bring skin to a healthy level")
            vf = f"exposure=exposure={ev}," + vf
    tag = hashlib.sha1(vf.encode()).hexdigest()[:8]
    src = d / "public" / rel
    out_rel = f"graded/{Path(rel).stem}-{grade}-{tag}{src.suffix.lower() if src.suffix.lower() in media.IMAGE_EXT else '.mp4'}"
    out = d / "public" / out_rel
    if out.exists():
        return out_rel
    out.parent.mkdir(exist_ok=True)
    print(f"grading {rel} ({grade})…")
    if src.suffix.lower() in media.IMAGE_EXT:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, str(out)])
    else:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf + ",format=yuv420p",
             "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-colorspace", "bt709", "-color_primaries", "bt709",
             "-color_trc", "bt709", "-c:a", "copy", "-movflags", "+faststart", str(out)])
    return out_rel


def apply_grade(d, props):
    grade = props["look"]["grade"]
    if grade == "natural" and not props["look"].get("polish", True):
        return
    props["src"] = graded(d, props["src"], grade, speaker=True)
    for r in props["broll"]:
        if r["src"].startswith("media/"):
            r["src"] = graded(d, r["src"], grade, speaker=False)
    props["look"]["grade"] = "natural"  # colour is baked into the footage; no CSS filter on top


def pauses(d, tr, noise=-36, dur=0.2):
    key = f"{noise}:{dur}"
    if tr.get("pauses_key") != key:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(d / "audio16k.wav"), "-af",
                            f"silencedetect=noise={noise}dB:d={dur}", "-f", "null", "-"], capture_output=True, text=True)
        out, st = [], None
        for line in r.stderr.splitlines():
            m = re.search(r"silence_start: ([\d.]+)", line)
            if m:
                st = float(m.group(1))
            m = re.search(r"silence_end: ([\d.]+)", line)
            if m and st is not None:
                out.append([round(st, 3), round(float(m.group(1)), 3)])
                st = None
        tr["pauses"], tr["pauses_key"] = out, key
        (d / "transcript.json").write_text(json.dumps(tr, indent=1, ensure_ascii=False))
    return tr["pauses"]


def sweep_temp(max_age_h=2):
    """Remotion leaves webpack bundles (each a full copy of public/, ~0.7 GB) in $TMPDIR — remove stale ones."""
    import tempfile
    import time as _t
    for b in Path(tempfile.gettempdir()).glob("remotion-webpack-bundle-*"):
        try:
            if _t.time() - b.stat().st_mtime > max_age_h * 3600:
                shutil.rmtree(b, ignore_errors=True)
        except OSError:
            pass


def quiet_map(d, tr, noise=-40, dur=0.12):
    """Silences measured from the audio itself (not the transcript) — the ground truth for where a cut is safe."""
    key = f"{noise}:{dur}"
    if tr.get("quiet_key") != key:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(d / "audio16k.wav"), "-af",
                            f"silencedetect=noise={noise}dB:d={dur}", "-f", "null", "-"], capture_output=True, text=True)
        out, st = [], None
        for line in r.stderr.splitlines():
            m = re.search(r"silence_start: ([\d.]+)", line)
            if m:
                st = float(m.group(1))
            m = re.search(r"silence_end: ([\d.]+)", line)
            if m and st is not None:
                out.append([round(st, 3), round(float(m.group(1)), 3)])
                st = None
        if st is not None:
            out.append([round(st, 3), round(tr["meta"]["duration"], 3)])
        tr["quiet"], tr["quiet_key"] = out, key
        (d / "transcript.json").write_text(json.dumps(tr, indent=1, ensure_ascii=False))
    return tr["quiet"]


def build(slug):
    sweep_temp()
    d = project_dir(slug)
    sb, tr = load(d)
    tset = sb.get("tighten") or {}
    pauses(d, tr, tset.get("noise", -36), tset.get("minPause", 0.22) - 0.02)
    quiet_map(d, tr)
    validate(sb, tr["meta"])
    props, warns = resolve(sb, tr, d)
    apply_grade(d, props)
    for w in warns:
        print(f"warning: {w}")
    used = {x["src"].split("/", 1)[1] for x in props["sfx"]}
    if used:
        (d / "public" / "sfx").mkdir(exist_ok=True)
        for name in used:
            shutil.copy2(ROOT / "sfx" / name, d / "public" / "sfx" / name)
    if sb.get("music"):
        (d / "public" / "music").mkdir(exist_ok=True)
        dst = d / "public" / "music" / sb["music"]["file"]
        if not dst.exists():
            shutil.copy2(MUSIC / sb["music"]["file"], dst)
    (d / "props.json").write_text(json.dumps(props, ensure_ascii=False))
    md_props = dict(props, look=dict(props["look"], grade=sb.get("look", {}).get("grade", "natural")))
    (d / "storyboard.md").write_text(storyboard_md(sb, tr, md_props), encoding="utf-8")
    return d, sb, props


def cmd_build(a):
    d, _, props = build(a.slug)
    ev, dead, hook = retention(props)
    print(f"ok — {props['durationInFrames'] / props['fps']:.1f}s, {len(props['beats'])} beats, "
          f"{len(props['broll'])} b-roll, {len(props['graphics'])} graphics, {len(props['sfx'])} sfx\n{d / 'storyboard.md'}")
    if not hook:
        print("retention: no hook graphic in the first 0.6s")
    for x, y in dead:
        print(f"retention: static {y - x:.1f}s at {fmt(x)}–{fmt(y)}")


def remotion(args):
    r = subprocess.run(["npx", "remotion", *args], cwd=REMOTION)
    if r.returncode != 0:
        die("remotion failed (see output above)")


def cmd_still(a):
    d, _, props = build(a.slug)
    frame = min(props["durationInFrames"] - 1, max(0, round(a.at * props["fps"])))
    out = d / "stills" / f"t{a.at:06.2f}.png"
    out.parent.mkdir(exist_ok=True)
    remotion(["still", "src/index.ts", "Reel", str(out), f"--props={d / 'props.json'}",
              f"--public-dir={d / 'public'}", f"--frame={frame}", "--scale=0.5", "--log=error"])
    print(out)


def cmd_frames(a):
    """One frame per storyboard beat (at its first graphic/overlay/b-roll entrance) → storyboard_frames.jpg."""
    d, sb, props = build(a.slug)
    fps = props["fps"]
    groups = {}
    for rb in props["beats"]:
        g = groups.setdefault(rb.get("group", rb["id"]), {"from": rb["from"], "to": rb["from"] + rb["duration"]})
        g["to"] = rb["from"] + rb["duration"]
    picks = []
    for gi in sorted(groups):
        a0, z = groups[gi]["from"], groups[gi]["to"]
        evs = [x["from"] for key in ("graphics", "overlays", "broll") for x in props[key] if a0 <= x["from"] < z]
        f = (min(evs) + 14) if evs else (a0 + z) // 2
        picks.append(max(a0, min(f, z - 2)))
    out = d / "stills" / "frames"
    if out.exists():
        shutil.rmtree(out)
    r = subprocess.run(["node", "frames.mjs", str(d / "props.json"), str(d / "public"), str(out),
                        ",".join(map(str, picks))], cwd=REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        die(f"frame render failed:\n{r.stderr[-2000:]}")
    beats = []
    for i, (b, f) in enumerate(zip(sb["beats"], picks)):
        beats.append({"id": b.get("id", i + 1), "frame": f"stills/frames/f{i:03d}.png", "t": round(f / fps, 2),
                      "spoken": b.get("captionText", ""), "note": b.get("note", "")})
    (d / "frames.json").write_text(json.dumps(beats, indent=1, ensure_ascii=False))
    cols = min(7, len(picks))
    run(["ffmpeg", "-y", "-v", "error", "-i", str(out / "f%03d.png"), "-vf",
         f"scale=240:-2,tile={cols}x{(len(picks) + cols - 1) // cols}:padding=6:color=black",
         "-frames:v", "1", str(d / "storyboard_frames.jpg")])
    print(d / "storyboard_frames.jpg")


def cmd_qa(a):
    """Measured frame QA + labelled sheets for the art-direction pass. Exit code 2 = hard failures."""
    d, sb, props = build(a.slug)
    rep = qa_mod.run(d, props, step=a.step)
    fails = rep["hard_failures"]
    lines = [f"# QA — {sb.get('title', a.slug)} (v{sb.get('version', 1)})", "",
             f"{len(rep['frames'])} frames sampled every {rep['step']}s. Hard failures: **{len(fails)}**", ""]
    lines += [f"- frame {f.get('i', '–')} @ {f['t']:.1f}s — {f['issue']}" for f in fails] or ["- none ✓"]
    lines += ["", "Sheets (red boxes = Instagram UI zones; label = frame number):", *[f"- {s}" for s in rep["sheets"]]]
    (d / "qa.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    sys.exit(2 if fails else 0)


def cmd_render(a):
    d, sb, props = build(a.slug)
    (d / "out").mkdir(exist_ok=True)
    v = sb.get("version", 1)
    out = d / "out" / f"{a.slug}_v{v}{'_draft' if a.draft else ''}.mp4"
    raw = out.with_name(out.stem + "_raw.mp4")
    args = ["render", "src/index.ts", "Reel", str(raw), f"--props={d / 'props.json'}",
            f"--public-dir={d / 'public'}", "--codec=h264", "--color-space=bt709", "--log=error"]
    args += ["--scale=0.5", "--crf=28", "--jpeg-quality=80"] if a.draft else ["--crf=16", "--jpeg-quality=95"]
    remotion(args)
    # master the audio: rumble cut, gentle compression, loudness to -14 LUFS (Instagram/TikTok), -1.5 dBTP ceiling
    run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-c:v", "copy", "-af",
         "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=1.5,"
         "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", "48000", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(out)])
    raw.unlink()
    if sb.get("brand") and not a.draft:
        hist_p = ROOT / "brands" / f"{sb['brand']}_history.json"
        hist = json.loads(hist_p.read_text()) if hist_p.exists() else []
        hist.append({"slug": a.slug, "version": v, "treatment": sb.get("treatment", "explainer-canvas"),
                     "hook": next((o["text"] for b in sb["beats"] for o in b.get("overlays", []) if o["style"] in ("hook", "statement")), ""),
                     "date": __import__("time").strftime("%Y-%m-%d")})
        hist_p.write_text(json.dumps(hist[-30:], indent=1, ensure_ascii=False))
    print(f"\nrendered: {out}")


def _show(project, got):
    for name, info in got:
        dims = f"{info.get('width')}x{info.get('height')}"
        dur = f"{info['duration']:.1f}s" if info.get("duration") else "image"
        print(f"  media/{name}  {dims}  {dur}  {info.get('credit') or ''}")
    sh = media.sheet(project, [n for n, _ in got])
    if sh:
        print(f"thumbnails (same order, left→right): {sh}")


def cmd_media(a):
    d = project_dir(a.slug)
    try:
        if a.cmd == "media-search":
            got = media.pexels(d, a.query, n=a.n, photos=a.photos, orientation=a.orientation)
        elif a.cmd == "media-add":
            files = a.files
            if a.library:
                files = [str(f) for f in media.library_files() if not a.files or any(x in f.name for x in a.files)]
            got = media.add_files(d, files, source="library" if a.library else "local")
        elif a.cmd == "media-url":
            got = media.from_url(d, a.url, a.name, source=a.source)
        elif a.cmd == "media-shot":
            got = media.screenshot(d, a.url, a.name, mobile=not a.desktop)
        else:  # media-list
            idx = media.index(d)
            got = sorted(idx.items())
            if a.library:
                print("library/ (add with: media-add <slug> --library <name-substring>):")
                for f in media.library_files():
                    print(f"  {f.relative_to(media.LIBRARY)}")
        _show(d, got)
    except (media.MediaError, OSError) as e:
        die(str(e))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("video")
    n.add_argument("--name")
    n.add_argument("--lang", default="auto", help="whisper language code, e.g. en, te, hi, auto")
    n.add_argument("--force", action="store_true")
    n.add_argument("--model", help="whisper model: small | large-v3-turbo | … (default: by language)")
    n.add_argument("--pregrade", help="colour-grade the master in parallel with transcription (e.g. brand)")
    n.set_defaults(fn=cmd_new)
    b = sub.add_parser("build")
    b.add_argument("slug")
    b.set_defaults(fn=cmd_build)
    s = sub.add_parser("still")
    s.add_argument("slug")
    s.add_argument("--at", type=float, required=True, help="output time in seconds")
    s.set_defaults(fn=cmd_still)
    f = sub.add_parser("frames", help="one preview frame per beat → storyboard_frames.jpg")
    f.add_argument("slug")
    f.set_defaults(fn=cmd_frames)
    q = sub.add_parser("qa", help="frame-level QA: face/safe-zone/lime/dead-frame checks + labelled sheets")
    q.add_argument("slug")
    q.add_argument("--step", type=float, default=0.5)
    q.set_defaults(fn=cmd_qa)
    r = sub.add_parser("render")
    r.add_argument("slug")
    r.add_argument("--draft", action="store_true", help="half resolution, faster")
    r.set_defaults(fn=cmd_render)
    m = sub.add_parser("media-search", help="Pexels stock b-roll (needs PEXELS_API_KEY)")
    m.add_argument("slug")
    m.add_argument("query")
    m.add_argument("--n", type=int, default=4)
    m.add_argument("--photos", action="store_true")
    m.add_argument("--orientation", default="portrait", choices=["portrait", "landscape", "square"])
    m = sub.add_parser("media-add", help="add local files (or --library matches) to the project")
    m.add_argument("slug")
    m.add_argument("files", nargs="*")
    m.add_argument("--library", action="store_true")
    m = sub.add_parser("media-url", help="download a clip/image from a direct URL (e.g. AI-generated b-roll)")
    m.add_argument("slug")
    m.add_argument("url")
    m.add_argument("--name")
    m.add_argument("--source", default="url")
    m = sub.add_parser("media-shot", help="screenshot a website for a cards graphic")
    m.add_argument("slug")
    m.add_argument("url")
    m.add_argument("--name")
    m.add_argument("--desktop", action="store_true")
    m = sub.add_parser("media-list", help="list project media (+ --library)")
    m.add_argument("slug")
    m.add_argument("--library", action="store_true")
    for name in ("media-search", "media-add", "media-url", "media-shot", "media-list"):
        sub.choices[name].set_defaults(fn=cmd_media)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
