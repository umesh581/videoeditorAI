"""Frame-level QA for a built reel: measured checks + labelled sheets for Claude's art-direction pass.

Samples a frame every `step` seconds and renders three variants of each:
  full     — the real look, with a frame number label (for sheets, lime budget, dead frames)
  overlay  — overlays without scrims/dims (so the mask is only text + graphics)
  footage  — no overlays at all
overlay − footage = exactly the pixels the editor put on top of the video. Combined with Apple Vision
face boxes and Instagram's UI zones, that gives objective checks Claude can't talk itself out of.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REMOTION = ROOT / "remotion"
FACEDETECT = ROOT / "tools" / "facedetect"

W, H = 72, 128  # analysis resolution (9:16)
# Instagram Reels UI (fractions of the 9:16 frame): action rail on the right, caption/username/audio at the bottom
ZONES = {
    "right rail": (0.86, 0.45, 1.0, 0.88),
    "bottom caption area": (0.0, 0.80, 0.86, 1.0),
}
# Meta ads (Reels/Stories): ad header up top, primary text + CTA button across the bottom ~35%
ZONES_AD = {
    "Meta ad header": (0.0, 0.0, 1.0, 0.14),
    "Meta ad text + CTA button": (0.0, 0.65, 1.0, 1.0),
    "right rail": (0.86, 0.40, 1.0, 0.65),
}
LABEL_BOX = (0.0, 0.0, 0.22, 0.06)  # QA frame-number label; ignored by every metric
LIMITS = {"face": 0.12, "zone": 0.05, "lime": 0.10, "static_s": 1.5, "face_luma": 85}


def _rgb(png):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-vf", f"scale={W}:{H}:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return out if len(out) == W * H * 3 else None


def _in(box, x, y):
    return box[0] <= x < box[2] and box[1] <= y < box[3]


def _mask(over, foot):
    m = []
    for i in range(W * H):
        x, y = (i % W + 0.5) / W, (i // W + 0.5) / H
        if _in(LABEL_BOX, x, y) or y < 0.012:  # label + progress bar
            m.append(False)
            continue
        d = sum(abs(over[3 * i + c] - foot[3 * i + c]) for c in range(3))
        m.append(d > 60)
    return m


def _text_mask(rgb):
    """Pixels that stand out from a full-screen card's own background (dark slam or light paper card)."""
    from collections import Counter
    bg = Counter((rgb[3 * i] // 24, rgb[3 * i + 1] // 24, rgb[3 * i + 2] // 24) for i in range(W * H)).most_common(1)[0][0]
    bg = [c * 24 + 12 for c in bg]
    m = []
    for i in range(W * H):
        x, y = (i % W + 0.5) / W, (i // W + 0.5) / H
        far = sum(abs(rgb[3 * i + c] - bg[c]) for c in range(3)) > 150
        m.append(not (_in(LABEL_BOX, x, y) or y < 0.012) and far)
    return m


def _frac(mask, box):
    tot = hit = 0
    for i, v in enumerate(mask):
        x, y = (i % W + 0.5) / W, (i // W + 0.5) / H
        if _in(box, x, y):
            tot += 1
            hit += v
    return hit / tot if tot else 0.0


def _lime(rgb, accent):
    ar, ag, ab = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
    n = hit = 0
    for i in range(W * H):
        x, y = (i % W + 0.5) / W, (i // W + 0.5) / H
        if _in(LABEL_BOX, x, y):
            continue
        r, g, b = rgb[3 * i:3 * i + 3]
        n += 1
        hit += abs(r - ar) + abs(g - ag) + abs(b - ab) < 90
    return hit / n if n else 0.0


def _luma_in(rgb, box):
    tot = n = 0
    for i in range(W * H):
        x, y = (i % W + 0.5) / W, (i // W + 0.5) / H
        if _in(box, x, y):
            r, g, b = rgb[3 * i:3 * i + 3]
            tot += 0.299 * r + 0.587 * g + 0.114 * b
            n += 1
    return tot / n if n else None


def _diff(a, b):
    return sum(abs(a[i] - b[i]) for i in range(0, len(a), 3)) / (len(a) / 3)


def _proxy(d: Path, rel: str) -> str:
    src = d / "public" / rel
    prox_rel = f"proxy/{Path(rel).stem}-540.mp4"
    prox = d / "public" / prox_rel
    if not prox.exists() or prox.stat().st_mtime < src.stat().st_mtime:
        prox.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", "scale=540:-2", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "23", "-g", "15", "-an", str(prox)], check=True)
    return prox_rel


_CODE = None


def _code_hash():
    """Hash of the renderer source — any visual code change invalidates every cached QA frame."""
    global _CODE
    if _CODE is None:
        import hashlib
        h = hashlib.sha1()
        for f in sorted((REMOTION / "src").glob("*.ts*")) + [REMOTION / "frames.mjs"]:
            h.update(f.read_bytes())
        _CODE = h.hexdigest()[:12]
    return _CODE


def _frame_key(p, f, variant, scale):
    """Fingerprint of everything that can change frame f's pixels in this variant."""
    import hashlib
    beat = next((b for b in p["beats"] if b["from"] <= f < b["from"] + b["duration"]), None)
    act = lambda xs: [dict(x, _t=f - x["from"]) for x in xs if x["from"] - 3 <= f < x["to"] + 3]
    state = {
        "v": variant, "s": scale, "code": _code_hash(), "src": p["src"], "look": p["look"], "theme": p.get("theme"),
        "beat": beat and dict(beat, _t=f - beat["from"]),
        "punch": [f - x for x in p.get("punches", []) if beat and beat["from"] <= x <= f],
        "dock": [[f - a, z - f] for a, z in p.get("docks", []) if a <= f < z],
        "broll": act(p.get("broll", [])),
    }
    if variant != "footage":
        near_cut = [b["from"] - f for b in p["beats"] if abs(b["from"] - f) <= 12]
        state.update({"cap": p["captions"], "chunks": act(p.get("chunks", [])), "ov": act(p.get("overlays", [])),
                      "gfx": act(p.get("graphics", [])), "cuts": near_cut, "pb": [p.get("progressBar"), f, p["durationInFrames"]],
                      "label": f})
    return hashlib.sha1(json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def run(d: Path, props: dict, step=0.5, scale=0.25):
    fps, total = props["fps"], props["durationInFrames"]
    frames = list(range(0, total, max(1, round(step * fps))))
    out = d / "qa"
    if out.exists():
        subprocess.run(["rm", "-rf", str(out)])
    every = max(1, round(step * fps))
    # QA decodes 540p proxies of the (graded) footage and b-roll — same framing, ~4x less decoding
    qprops = json.loads(json.dumps(props))
    qprops["src"] = _proxy(d, props["src"])
    for b in qprops.get("broll", []):
        if b.get("kind") == "video":
            b["src"] = _proxy(d, b["src"])
    (d / "qa_props.json").write_text(json.dumps(qprops))
    # Per-frame cache: each sampled frame is fingerprinted by everything that can affect its pixels
    # (cut, b-roll, dock, punch, captions, overlays, graphics, transition, theme). Only frames whose
    # fingerprint changed since the last QA are re-rendered — a one-beat revision re-renders one beat.
    import shutil
    cache = d / "qa_cache"
    cache.mkdir(exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    keys = {v: [_frame_key(qprops, f, v, scale) for f in frames] for v in ("full", "overlay", "footage")}
    missing = {v: [i for i, k in enumerate(keys[v]) if not (cache / f"{k}.png").exists()] for v in keys}
    for group in (("full", "overlay"), ("footage",)):
        idx = sorted(set(i for v in group for i in missing[v]))
        if not idx:
            continue
        tmp = out / "_render"
        r = subprocess.run(["node", "frames.mjs", str(d / "qa_props.json"), str(d / "public"), str(tmp),
                            ",".join(str(frames[i]) for i in idx), ",".join(group), str(scale), "1"],
                           cwd=REMOTION, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"QA render failed:\n{r.stderr[-1500:]}")
        for n, i in enumerate(idx):
            for v in group:
                shutil.move(str(tmp / f"f{n:03d}_{v}.png"), str(cache / f"{keys[v][i]}.png"))
        shutil.rmtree(tmp, ignore_errors=True)
    for v in keys:
        for i, k in enumerate(keys[v]):
            shutil.copy2(cache / f"{k}.png", out / f"f{i:03d}_{v}.png")
    rendered = sum(len(m) for m in missing.values())
    print(f"QA frames: rendered {rendered}, reused {3 * len(frames) - rendered}")
    foot_pngs = [out / f"f{i:03d}_footage.png" for i in range(len(frames))]
    faces = {}
    if FACEDETECT.exists():
        fr = subprocess.run([str(FACEDETECT), *map(str, foot_pngs)], capture_output=True, text=True)
        for line in fr.stdout.splitlines():
            j = json.loads(line)
            faces[Path(j["path"]).name] = j["faces"]

    zones_for = ZONES_AD if props.get("placement") == "meta-ad" else ZONES
    slams = [(g["from"], g["to"]) for g in props.get("graphics", []) if g["type"] == "slam"]
    slams += [(o["from"], o["to"]) for o in props.get("overlays", []) if o["style"] in ("chapter", "statement")]
    # designed full-frame transitions (wipes cover everything for ~8 frames around the cut)
    wipes = [(b["from"] - 8, b["from"] + 8) for i, b in enumerate(props["beats"])
             if b["transition"] == "wipe" and i > 0 and props["beats"][i - 1]["id"] != b["id"]]
    wipes += [(z - 12, z) for _, z in slams]  # a slam card lifting away is a transition too
    wipes += [(a, a + 12) for a, _ in slams]  # …and so is a full-screen card opening
    accent = ((props.get("theme") or {}).get("colors") or {}).get("accent") or props["captions"]["highlightColor"]
    rows, prev = [], None
    for i, f in enumerate(frames):
        full, over, foot = (_rgb(out / f"f{i:03d}_{v}.png") for v in ("full", "overlay", "footage"))
        if not (full and over and foot):
            continue
        fullscreen = any(a <= f < z for a, z in slams)
        lb = props["look"].get("letterbox")
        lb = (lb if isinstance(lb, (int, float)) and lb is not True else 0.085) if lb else 0
        # on a full-screen card the "overlay" is the card itself — measure only its text against the card bg
        mask = _text_mask(over) if fullscreen else _mask(over, foot)
        if lb:
            mask = [v and lb + 0.01 < (i // W + 0.5) / H < 1 - lb - 0.01 for i, v in enumerate(mask)]
        coverage = sum(mask) / len(mask)
        fboxes = faces.get(foot_pngs[i].name, [])
        occl = 0.0 if fullscreen else max((_frac(mask, (x, y, x + w, y + h)) for x, y, w, h in fboxes), default=0.0)
        zones = {z: round(_frac(mask, b), 3) for z, b in zones_for.items()}
        # face exposure in the real look (central half of the face box = skin, not hair/background)
        skin_box = lambda b: (b[0] + b[2] * 0.25, b[1] + b[3] * 0.3, b[0] + b[2] * 0.75, b[1] + b[3] * 0.8)
        lumas = [_luma_in(full, skin_box(b)) for b in fboxes]
        bare = [_luma_in(foot, skin_box(b)) for b in fboxes]
        face_luma = round(max([l for l in lumas if l is not None], default=0), 1) if fboxes and not fullscreen else None
        face_bare = round(max([l for l in bare if l is not None], default=0), 1) if fboxes and not fullscreen else None
        row = {"i": i, "t": round(f / fps, 2), "frame": f, "coverage": round(coverage, 3), "fullscreen": fullscreen, "face_luma": face_luma, "face_bare": face_bare,
               "faces": len(fboxes), "face_cover": round(occl, 3), "zones": zones,
               "lime": round(_lime(full, accent), 3), "motion": round(_diff(full, prev), 2) if prev else None}
        issues = []
        if occl > LIMITS["face"]:
            issues.append(f"overlay covers {occl:.0%} of the face")
        for z, v in zones.items():
            if v > LIMITS["zone"]:
                issues.append(f"text/graphics in Instagram's {z} ({v:.0%})")
        # overlays (scrims, cards) must not darken the face; the footage's own lighting is the owner's call
        if face_luma and face_bare and face_bare > 40 and face_luma < 0.8 * face_bare:
            issues.append(f"overlays darken the face {100 - 100 * face_luma / face_bare:.0f}% (skin {face_bare:.0f} → {face_luma:.0f})")
        if row["lime"] > LIMITS["lime"]:
            issues.append(f"accent colour is {row['lime']:.0%} of the frame (>10%)")
        if any(a <= f < z for a, z in wipes):
            issues = []  # mid-transition frame: intentional full-frame cover
            row["transition"] = True
        row["issues"] = issues
        rows.append(row)
        prev = full

    skins = sorted(r["face_bare"] for r in rows if r.get("face_bare"))
    reel_skin = skins[len(skins) // 2] if skins else None

    # dead stretches: consecutive samples with almost no pixel change
    static, run_start = [], None
    for a, b in zip(rows, rows[1:]):
        if b["motion"] is not None and b["motion"] < 1.0:
            run_start = a["t"] if run_start is None else run_start
            end = b["t"]
        elif run_start is not None:
            if end - run_start >= LIMITS["static_s"]:
                static.append([run_start, end])
            run_start = None
    if run_start is not None and rows and rows[-1]["t"] - run_start >= LIMITS["static_s"]:
        static.append([run_start, rows[-1]["t"]])

    # labelled sheets (24 frames each) with Instagram UI zones outlined in red
    fw, fh = round(1080 * scale), round(1920 * scale)
    boxes = ",".join(
        f"drawbox=x={round(b[0] * fw)}:y={round(b[1] * fh)}:w={round((b[2] - b[0]) * fw)}:h={round((b[3] - b[1]) * fh)}:color=red@0.8:t=2"
        for b in (ZONES_AD if props.get("placement") == "meta-ad" else ZONES).values())
    sheets = []
    for s0 in range(0, len(frames), 24):
        n = min(24, len(frames) - s0)
        sheet = out / f"sheet{s0 // 24 + 1}.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-start_number", str(s0), "-i", str(out / "f%03d_full.png"),
                        "-frames:v", str(n), "-vf", f"{boxes},scale=180:-2,tile=8x{(n + 7) // 8}:padding=4:color=black",
                        str(sheet)], capture_output=True)
        sheets.append(sheet)

    report = {"step": step, "frames": rows, "static": static, "sheets": [str(s) for s in sheets],
              "reel_skin": reel_skin,
              "hard_failures": [{"i": r["i"], "t": r["t"], "issue": x} for r in rows for x in r["issues"]]
                               + ([{"t": 0, "issue": f"graded footage is too dark overall (median skin {reel_skin:.0f}, want ≥ {LIMITS['face_luma']})"}]
                                  if reel_skin is not None and reel_skin < LIMITS["face_luma"] else [])
                               + [{"t": a, "issue": f"no visual change {a:.1f}–{b:.1f}s"} for a, b in static],
              "limits": LIMITS}
    (d / "qa_report.json").write_text(json.dumps(report, indent=1))
    return report
