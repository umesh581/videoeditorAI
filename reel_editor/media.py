"""B-roll / asset sourcing for reel projects. Everything lands in projects/<slug>/public/media/.

Sources: Pexels stock (needs PEXELS_API_KEY), local files / the library/ folder, any direct URL
(e.g. an AI-generated clip), and website screenshots via Remotion's headless Chrome.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARY = ROOT / "library"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
UA = "reel-editor/1.0"


class MediaError(Exception):
    pass


def media_dir(project: Path) -> Path:
    d = project / "public" / "media"
    (d / "_thumbs").mkdir(parents=True, exist_ok=True)
    return d


def _safe(name):
    stem, ext = os.path.splitext(name)
    return (re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-")[:50] or "asset") + ext.lower()


def _probe(path: Path):
    ext = path.suffix.lower()
    if ext in IMAGE_EXT:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height", "-of", "json", str(path)], capture_output=True, text=True)
        s = (json.loads(out.stdout or "{}").get("streams") or [{}])[0]
        return {"kind": "image", "width": s.get("width"), "height": s.get("height"), "duration": None}
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,codec_type",
                          "-of", "json", str(path)], capture_output=True, text=True)
    data = json.loads(out.stdout or "{}")
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"kind": "video", "width": v.get("width"), "height": v.get("height"),
            "duration": round(float(data.get("format", {}).get("duration", 0)), 2)}


def _thumb(path: Path, info):
    t = path.parent / "_thumbs" / (path.stem + ".jpg")
    at = min(1.0, (info["duration"] or 0) / 2) if info["kind"] == "video" else 0
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(at), "-i", str(path), "-frames:v", "1", "-vf",
                    "scale=216:384:force_original_aspect_ratio=increase,crop=216:384,format=yuvj420p", str(t)],
                   capture_output=True)
    return t


def register(project: Path, path: Path, source: str, credit: str = ""):
    """Record an asset in media/index.json (kind, size, duration, where it came from)."""
    d = media_dir(project)
    idx_path = d / "index.json"
    idx = json.loads(idx_path.read_text()) if idx_path.exists() else {}
    info = _probe(path)
    info.update({"source": source, "credit": credit})
    idx[path.name] = info
    idx_path.write_text(json.dumps(idx, indent=1))
    _thumb(path, info)
    return info


def index(project: Path):
    p = media_dir(project) / "index.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _download(url, dest: Path, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


# ---------------------------------------------------------------- sources

def pexels_key():
    key = os.environ.get("PEXELS_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("PEXELS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        raise MediaError("No Pexels key. Get a free one at https://www.pexels.com/api/ and put "
                         "PEXELS_API_KEY=... in reel_editor/.env")
    return key


def pexels(project: Path, query: str, n=4, photos=False, orientation="portrait"):
    key = pexels_key()
    q = urllib.parse.urlencode({"query": query, "per_page": n, "orientation": orientation})
    url = f"https://api.pexels.com/v1/search?{q}" if photos else f"https://api.pexels.com/videos/search?{q}"
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    d = media_dir(project)
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:24]
    got = []
    for item in data.get("photos" if photos else "videos", []):
        credit = f"{item.get('photographer') or item.get('user', {}).get('name', '')} / Pexels {item.get('url', '')}"
        if photos:
            dest = d / f"px-{slug}-{item['id']}.jpg"
            if not dest.exists():
                _download(item["src"].get("portrait") or item["src"]["large2x"], dest)
        else:
            files = [f for f in item.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
            if not files:
                continue
            # smallest file that is still >= 1080 on its short side; else the biggest available
            ok = [f for f in files if min(f["width"], f["height"]) >= 1080]
            pick = min(ok, key=lambda f: f["width"] * f["height"]) if ok else max(files, key=lambda f: f["width"] * f["height"])
            dest = d / f"px-{slug}-{item['id']}.mp4"
            if not dest.exists():
                _download(pick["link"], dest)
        got.append((dest.name, register(project, dest, f"pexels:{query}", credit)))
    if not got:
        raise MediaError(f"Pexels returned nothing for '{query}' — try a broader, more visual query")
    return got


def add_files(project: Path, paths, source="local"):
    d = media_dir(project)
    got = []
    for p in paths:
        src = Path(p).expanduser().resolve()
        if src.suffix.lower() not in VIDEO_EXT | IMAGE_EXT:
            raise MediaError(f"{src.name}: unsupported type")
        dest = d / _safe(src.name)
        if dest.exists():
            dest.unlink()
        try:
            os.link(src, dest)
        except OSError:
            shutil.copy2(src, dest)
        got.append((dest.name, register(project, dest, source)))
    return got


def from_url(project: Path, url: str, name=None, source="url"):
    d = media_dir(project)
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or ".mp4"
    dest = d / _safe(name or f"dl-{abs(hash(url)) % 10**8}{ext}")
    if not dest.suffix:
        dest = dest.with_suffix(ext)
    _download(url, dest)
    return [(dest.name, register(project, dest, source))]


def _chrome():
    base = ROOT / "remotion" / "node_modules" / ".remotion" / "chrome-headless-shell"
    found = list(base.rglob("chrome-headless-shell")) if base.exists() else []
    found = [f for f in found if f.is_file()]
    if not found:
        raise MediaError("headless Chrome not found — run a render once so Remotion downloads it")
    return found[0]


def screenshot(project: Path, url: str, name=None, mobile=True):
    """Website screenshot for `cards` graphics (phone- or browser-shaped)."""
    d = media_dir(project)
    host = urllib.parse.urlparse(url).netloc.replace("www.", "") or "page"
    dest = d / _safe(name or f"shot-{host}.png")
    w, h = (430, 932) if mobile else (1440, 900)
    if dest.exists():
        dest.unlink()
    r = subprocess.run(["node", "--experimental-websocket", "--no-warnings", str(ROOT / "remotion" / "screenshot.mjs"),
                        str(_chrome()), url, str(dest), str(w), str(h), "1" if mobile else "0"],
                       capture_output=True, text=True, timeout=60)
    if not dest.exists():
        raise MediaError(f"screenshot failed: {r.stderr[-500:]}")
    return [(dest.name, register(project, dest, f"screenshot:{url}"))]


def sheet(project: Path, names=None):
    """Numbered-order contact sheet of media thumbnails, so Claude can look and pick."""
    d = media_dir(project)
    idx = index(project)
    names = names or sorted(idx)
    if not names:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        for i, n in enumerate(names):
            t = d / "_thumbs" / (Path(n).stem + ".jpg")
            if t.exists():
                shutil.copy(t, Path(tmp) / f"t{i:03d}.jpg")
        cols = min(6, len(names))
        rows = (len(names) + cols - 1) // cols
        out = project / "media_sheet.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(Path(tmp) / "t%03d.jpg"), "-vf",
                        f"tile={cols}x{rows}:padding=6:color=white", "-frames:v", "1", str(out)], capture_output=True)
    return out


def library_files():
    if not LIBRARY.exists():
        return []
    return sorted(p for p in LIBRARY.rglob("*") if p.suffix.lower() in VIDEO_EXT | IMAGE_EXT)


# ---------------------------------------------------------------- brand icons (simple-icons, CC0)

def _slugify_icon(title):
    s = title.lower().replace("+", "plus").replace(".", "dot").replace("&", "and")
    s = unicodedata.normalize("NFD", s)
    return re.sub(r"[^a-z0-9]", "", s)


_ICONS = None


def icon(name):
    """Return {'path','hex'} for a brand name/slug, or None (renderer falls back to a monogram)."""
    global _ICONS
    if _ICONS is None:
        _ICONS = {}
        data = ROOT / "remotion" / "node_modules" / "simple-icons" / "data" / "simple-icons.json"
        if data.exists():
            for e in json.loads(data.read_text()):
                slug = e.get("slug") or _slugify_icon(e["title"])
                for k in {slug, _slugify_icon(e["title"]), *map(_slugify_icon, e.get("aliases", {}).get("aka", []))}:
                    _ICONS.setdefault(k, (slug, e["hex"]))
    hit = _ICONS.get(_slugify_icon(name))
    if not hit:
        return None
    svg = ROOT / "remotion" / "node_modules" / "simple-icons" / "icons" / f"{hit[0]}.svg"
    m = re.search(r' d="([^"]+)"', svg.read_text()) if svg.exists() else None
    return {"path": m.group(1), "hex": hit[1]} if m else None


# ---------------------------------------------------------------- news (clippings)

def news(project: Path, query: str, n=8, region="IN"):
    """Real headlines for a spoken claim, from Google News RSS. Saved to news.json so a `clipping`
    graphic can only ever show a headline that was actually published (never an invented one)."""
    import email.utils
    import xml.etree.ElementTree as ET
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-{region}&gl={region}&ceid={region}:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    root = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
    p = project / "news.json"
    store = json.loads(p.read_text()) if p.exists() else {}
    got = []
    for it in list(root.iter("item"))[:n]:
        source = (it.findtext("source") or "").strip()
        title = (it.findtext("title") or "").strip()
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].strip()
        dt = email.utils.parsedate_to_datetime(it.findtext("pubDate"))
        import hashlib
        nid = "n" + hashlib.md5(f"{title}|{source}".encode()).hexdigest()[:6]  # stable across runs
        store[nid] = {"headline": title, "source": source, "date": dt.strftime("%-d %b %Y"),
                      "iso": dt.date().isoformat(), "link": it.findtext("link"), "query": query}
        got.append(nid)
    p.write_text(json.dumps(store, indent=1, ensure_ascii=False))
    return [(nid, store[nid]) for nid in got]


# ---------------------------------------------------------------- Wikimedia Commons (people, companies, places, history)

COMMONS_OK = ("public domain", "no restrictions", "cc0", "pd", "cc by", "godl")  # free to reuse with credit


def commons(project: Path, query: str, n=6, width=1600):
    """Real, freely licensed photos of a person/company/place/event from Wikimedia Commons. Each is saved with its
    licence and author so cards can show the credit CC BY requires. Never use for anything the speaker didn't name."""
    import html, re as _re, time
    ua = {"User-Agent": "ReelEditor/1.0 (personal video editing)"}
    api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6,
        "gsrlimit": n * 3, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": width})
    pages = json.loads(urllib.request.urlopen(urllib.request.Request(api, headers=ua), timeout=30).read()).get("query", {}).get("pages", {})
    got = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        ii = p["imageinfo"][0]; md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not any(k in lic.lower() for k in COMMONS_OK) or ii["width"] < 700:
            continue
        artist = _re.sub(r"<[^>]+>", "", html.unescape(md.get("Artist", {}).get("value", ""))).strip()[:60]
        name = _safe("wm-" + _re.sub(r"\.\w+$", "", p["title"][5:])[:44] + f"-{p['pageid']}") + ".jpg"  # pageid: no collisions
        dest = media_dir(project) / name
        for attempt in range(3):  # Commons rate-limits bursts
            try:
                _download(ii.get("thumburl") or ii["url"], dest, headers=ua); break
            except Exception:
                time.sleep(4 * (attempt + 1))
        else:
            continue
        credit = f"Photo: {artist + ', ' if artist else ''}{lic} via Wikimedia Commons"
        got.append((name, register(project, dest, f"commons: {p['title'][5:]}", credit)))
        if len(got) >= n:
            break
    return got
