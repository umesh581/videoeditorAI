"""B-roll library: every image/clip ever found or generated, described in words, so the b-roll agent can
reuse an existing asset before paying to make a new one.

  library/broll/<id>.<ext> + library/broll/index.json
  entry = {id, file, kind (video|image), description (what is VISIBLE), tags[], source (owner|stock|commons|ai|archival),
           ai (bool), model, prompt, credit, orientation, duration, width, height, created, used_in[]}

Search is offline: a weighted keyword match over description + tags + prompt (with light stemming and a synonym
table for the owner's topics). Scores 0–1; ≥0.55 is usually a reuse candidate, but the agent must LOOK at the
thumbnail sheet before reusing anything.
"""
import datetime as dt
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "library" / "broll"
INDEX = LIB / "index.json"
VIDEO = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE = {".jpg", ".jpeg", ".png", ".webp"}

STOP = set("a an the of in on at to for with and or but is are was were be being been this that these those it its "
           "his her their our your my from by as into over under near very some any shot clip image video photo b roll "
           "broll showing shows show view close up closeup wide medium vertical portrait landscape".split())
# the owner's recurring topics: words that mean the same thing on screen
SYN = {
    "rupee": "money", "rupees": "money", "cash": "money", "salary": "money", "paycheck": "money", "payslip": "money",
    "income": "money", "currency": "money", "notes": "money", "wallet": "money",
    "laptop": "computer", "macbook": "computer", "desktop": "computer", "pc": "computer", "monitor": "screen",
    "phone": "smartphone", "mobile": "smartphone", "iphone": "smartphone",
    "office": "workplace", "cubicle": "workplace", "corporate": "workplace", "desk": "workplace",
    "employee": "worker", "staff": "worker", "professional": "worker", "workers": "worker",
    "seminar": "audience", "conference": "audience", "crowd": "audience", "auditorium": "audience",
    "ai": "ai", "chatgpt": "ai", "claude": "ai", "gemini": "ai", "robot": "ai", "automation": "ai",
    "india": "india", "indian": "india", "bengaluru": "india", "bangalore": "india", "hyderabad": "india", "mumbai": "india",
    "family": "family", "parents": "family", "kids": "family", "children": "family",
    "factory": "factory", "assembly": "factory", "manufacturing": "factory",
    "school": "education", "classroom": "education", "students": "education", "college": "education", "degree": "education",
    "stress": "stress", "tired": "stress", "burnout": "stress", "worried": "stress", "anxious": "stress",
    "growth": "growth", "chart": "growth", "graph": "growth", "rising": "growth",
}


def _norm(word):
    w = word.lower()
    w = SYN.get(w, w)
    for suf in ("ing", "ers", "ies", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            w = w[: -len(suf)] + ("y" if suf == "ies" else "")
            break
    return SYN.get(w, w)


def tokens(text):
    return [_norm(t) for t in re.findall(r"[A-Za-z₹0-9]+", text or "") if t.lower() not in STOP and len(t) > 1]


def load():
    return json.loads(INDEX.read_text()) if INDEX.exists() else {}


def _save(idx):
    LIB.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(idx, indent=1, ensure_ascii=False))


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    j = json.loads(r.stdout or "{}")
    st = next((s for s in j.get("streams", []) if s.get("width")), {})
    w, h = st.get("width", 0), st.get("height", 0)
    dur = float(j.get("format", {}).get("duration") or 0)
    return {"width": w, "height": h, "duration": round(dur, 2) if path.suffix.lower() in VIDEO else 0,
            "orientation": "portrait" if h > w else "landscape" if w > h else "square"}


def _strip_bars(path):
    """AI video models sometimes letterbox (e.g. Veo: 3:4 picture inside a 9:16 frame). Crop the black bars away."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", "cropdetect=24:16:0", "-f", "null", "-"],
                       capture_output=True, text=True)
    crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
    if not crops:
        return
    w, h, x, y = max(set(crops), key=crops.count)
    full = _probe(path)
    if int(h) >= full["height"] * 0.96 and int(w) >= full["width"] * 0.96:
        return  # no real bars
    tmp = path.with_name(path.stem + ".crop" + path.suffix)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", f"crop={w}:{h}:{x}:{y}", "-c:v", "libx264", "-crf", "16",
                    "-preset", "fast", "-c:a", "copy", str(tmp)], check=True)
    tmp.replace(path)


def add(file, description, tags=(), source="owner", prompt="", model="", credit="", ai=False):
    """Copy a file into the library and describe it. Returns the new entry."""
    src = Path(file).expanduser()
    idx = load()
    base = re.sub(r"[^a-z0-9]+", "-", description.lower())[:40].strip("-") or "broll"
    n = 1
    while f"{base}-{n}" in idx:
        n += 1
    bid = f"{base}-{n}"
    LIB.mkdir(parents=True, exist_ok=True)
    dest = LIB / f"{bid}{src.suffix.lower()}"
    shutil.copy2(src, dest)
    if dest.suffix.lower() in VIDEO:
        _strip_bars(dest)
    e = {"id": bid, "file": dest.name, "kind": "video" if dest.suffix in VIDEO else "image", "description": description,
         "tags": [t.strip() for t in tags if t.strip()], "source": source, "ai": bool(ai), "model": model, "prompt": prompt,
         "credit": credit or (f"AI-generated ({model})" if ai else ""), "created": dt.date.today().isoformat(), "used_in": [],
         **_probe(dest)}
    subprocess.run(["ffmpeg", "-v", "error", "-y", *(["-ss", "0.5"] if e["kind"] == "video" else []), "-i", str(dest),
                    "-frames:v", "1", "-vf", "scale=320:-2", str(LIB / f"{bid}.thumb.jpg")])
    idx[bid] = e
    _save(idx)
    return e


def search(query, kind=None, orientation=None, n=6):
    """Rank library assets for a request. Returns [(score, entry)], best first."""
    idx = load()
    if not idx:
        return []
    docs = {k: tokens(" ".join([e["description"], " ".join(e["tags"]), e.get("prompt", "")])) for k, e in idx.items()}
    df = {}
    for toks in docs.values():
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    N = len(docs)
    idf = lambda t: math.log(1 + N / (1 + df.get(t, 0))) + 0.5
    q = set(tokens(query))
    if not q:
        return []
    qw = sum(idf(t) for t in q)
    out = []
    for k, e in idx.items():
        if kind and e["kind"] != kind:
            continue
        d = set(docs[k])
        s = sum(idf(t) for t in q & d) / qw
        if orientation and e.get("orientation") not in (orientation, "square"):
            s *= 0.85  # usable (cropped / carded) but not ideal
        out.append((round(s, 2), e))
    return sorted(out, key=lambda x: -x[0])[:n]


def sheet(entries, out):
    """Thumbnail sheet of candidates (so the agent can look before reusing)."""
    thumbs = [LIB / f"{e['id']}.thumb.jpg" for e in entries if (LIB / f"{e['id']}.thumb.jpg").exists()]
    if not thumbs:
        return None
    args, f, s = [], "", ""
    for i, t in enumerate(thumbs):
        args += ["-i", str(t)]
        f += f"[{i}]scale=-2:240[v{i}];"
        s += f"[v{i}]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", f + s + f"hstack={len(thumbs)}" if len(thumbs) > 1
                    else f"[0]scale=-2:240", str(out)])
    return out


def use(slug, bid, projects):
    """Copy a library asset into a project's media/ (keeping its credit) and record the reuse."""
    import media
    idx = load()
    e = idx[bid]
    proj = projects / slug
    got = media.add_files(proj, [str(LIB / e["file"])], source=f"library:{bid}")
    name = got[0][0] if got else None
    if name:  # carry the credit into the project so cards print it
        pi = media.index(proj)
        if name in pi:
            pi[name]["credit"] = e.get("credit") or ""
            (media.media_dir(proj) / "index.json").write_text(json.dumps(pi, indent=1))
    e["used_in"] = sorted(set(e.get("used_in", []) + [slug]))
    _save(idx)
    return name, e
