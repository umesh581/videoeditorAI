#!/usr/bin/env python3
"""Reel Studio — local web app for the reel pipeline.

Drop a raw clip → transcribe → Claude plans the edit (brief, hook, b-roll, storyboard, frame check)
→ you review the storyboard → optional one-line revisions → Render → download + Instagram caption.

  python3 reel_editor/app/server.py [--port 8765]

Claude runs headless per job, started only by your actions in the app, with a tool allowlist:
it can run reel_editor/reel.py and read/write files inside reel_editor/projects/ — nothing else.
"""
import argparse
import json
import mimetypes
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parent
EDITOR = APP.parent
REPO = EDITOR.parent
PROJECTS = EDITOR / "projects"
INBOX = EDITOR / "inbox"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
BRAND = "digital-entrepreneur"
sys.path.insert(0, str(EDITOR))
import editlog  # noqa: E402  (edit log: every raw clip by content fingerprint + its outcome)
STYLES = {"": "Standard brand edit", "varun-mayya": "Varun Mayya documentary"}

ALLOWED_TOOLS = [
    "Bash(python3 reel_editor/reel.py:*)",
    "Read",
    "Glob",
    "Grep",
    "Skill",
    "Write(reel_editor/projects/**)",
    "Edit(reel_editor/projects/**)",
    "Agent(broll-agent)",  # the creative director hands its shot list to the b-roll agent
    "mcp__af6e248c-7d39-42d6-8d8b-309218f194bc__vidiq_generate_broll",  # used by the b-roll agent when the CLI has the vidIQ connector
    "mcp__af6e248c-7d39-42d6-8d8b-309218f194bc__vidiq_generate_video",
    "mcp__af6e248c-7d39-42d6-8d8b-309218f194bc__vidiq_job_poll",
]

QA_FULL = """5. Quality loop (skill Step 7): `python3 reel_editor/reel.py qa {slug}` → fix every measured hard failure → Read every qa/sheet*.jpg and score every frame with the rubric → write qa_scores.json → fix → re-run qa. Repeat until 0 hard failures and every frame ≥ 8 (max 2 rounds; then report what is left — the owner decides)."""
QA_FAST = """5. Fast mode (owner chose speed): skip `reel.py qa`. Run `python3 reel_editor/reel.py frames {slug}` once and look at storyboard_frames.jpg for anything obviously broken."""

PLAN_PROMPT = """You are editing a reel inside the Reel Studio app. The owner is NOT watching this run live; they will review your storyboard in the app afterwards, so never ask questions — decide, and record your reasoning in brief.md.

Use the edit-reel skill. The raw clip is already ingested as project `{slug}`:
  reel_editor/projects/{slug}/transcript.txt, transcript.json, contact.jpg (+ contact.txt)
Language: {lang}. Brand: set "brand": "{brand}" in storyboard.json and follow the brand rules.
Look: set "brandMode": "{look}" in storyboard.json.{style_line}
FIRST read reel_editor/brands/{brand}_style.md (the owner's style guide) and obey it, including its Director's review on the rendered frames before you finish.
{notes}
{clips}
Do, in order:
1. Read the transcript and contact sheet. If the language is not English, write clean `captionText` per beat yourself (Telugu+English as spoken).
2. Act as creative director: read reel_editor/brands/{brand}_history.json and pick a TREATMENT from the skill's Creative direction table that fits this content and differs from the last two reels (set "treatment" in storyboard.json). Then write reel_editor/projects/{slug}/brief.md (audience, promise, strongest lines, 3 hook options, the one you chose and why, the treatment and why, visual plan).
3. Proof & real b-roll (never invented graphics):
   - every claim, number, trend or company in the news → `python3 reel_editor/reel.py news {slug} "<claim>"`, fact-check the headlines, use supporting ones as `clipping` graphics; if coverage contradicts the speaker, put it in "check" instead;
   - every named person, company, place or historic event → `python3 reel_editor/reel.py media-commons {slug} "<name>"`, look at the sheet, use the best real photo as `card` b-roll (credits print automatically; defamation guard: no recognisable person on negative lines);
   - library clips via `media-list {slug} --library`; `media-shot` for a named website/product. Leave the speaker full-screen rather than fill with anything fake.
4. Write reel_editor/projects/{slug}/storyboard.json and run `python3 reel_editor/reel.py build {slug}` until there are no retention warnings.
{qa_step}
6. Run `python3 reel_editor/reel.py frames {slug}` (storyboard frames for the app).
7. Write reel_editor/projects/{slug}/instagram_caption.txt in the brand voice (hook line, 3–6 short lines of value, CTA, 5–8 hashtags).
Do NOT render the video. Always run commands from the repo root exactly as `python3 reel_editor/reel.py ...`.

Your final message must be ONLY this JSON:
{{"hook": "<on-screen hook>", "summary": "<2 sentences on the edit>", "check": "<anything the owner should verify, e.g. uncertain caption lines, frames still under 8>"}}"""

REVISE_PROMPT = """Revision request from the owner in Reel Studio for project `{slug}`:

"{text}"

Apply it: edit reel_editor/projects/{slug}/storyboard.json (bump "version"), run `python3 reel_editor/reel.py build {slug}` (no retention warnings), {qa_note}, then `python3 reel_editor/reel.py frames {slug}`. Update brief.md / instagram_caption.txt only if the change affects them. Do NOT render.
Final message ONLY JSON: {{"summary": "<what you changed, one or two sentences>", "check": "<anything to verify, or empty>"}}"""


CAPTION_PROMPT = """Write the Instagram caption for the finished reel in project `{slug}` (Digital Entrepreneur brand).

Read what the reel actually says and shows — never invent claims, numbers or promises. Every figure in the caption must appear
word-for-word in the transcript/captionText or in a headline shown on screen; do NOT add context figures (inflation rates, averages, percentages) from your own knowledge:
  reel_editor/projects/{slug}/transcript.txt (what was spoken), storyboard.json (captionText per beat = the clean English lines),
  brief.md if present, and props.json "graphics"/"broll" for the real headlines and photos shown on screen.
If the ig-caption skill is available, use it; then pass the draft through the ig-human skill if available.

Owner's choices: tone = {tone}; language = {lang}; call to action = {cta}.{extra}
Rules:
- Line 1 is the hook that survives the "… more" cut (≤ 125 characters): specific, curiosity or tension, no emoji at the start, not a repeat of the video's first line word-for-word.
- Then 3–6 short lines of value in the brand voice: direct, precise, warm, no fluff, no hype, no "In today's video".
- Cite a source in plain words if the reel shows a real headline or number (e.g. "Economic Times reported…").
- One clear ask that matches the call to action. Never promise earnings or results.
- End with 3–5 relevant hashtags (mix of niche and broad, Indian audience), on the last line.
- Total under 2,200 characters. No em dashes.
Write it to reel_editor/projects/{slug}/instagram_caption.txt (overwrite), then reply ONLY with JSON: {{"first_line": "<line 1>", "notes": "<anything to check, or empty>"}}"""


# ---------------------------------------------------------------- job state

LOCK = threading.Lock()
WORK = queue.Queue()
CURRENT = {"slug": None, "proc": None}  # the job the worker is running right now (for cancel)
PENDING = []  # slugs waiting in the queue, in order (for "N ahead" display)


def job_path(slug):
    return PROJECTS / slug / "job.json"


def load_job(slug):
    p = job_path(slug)
    return json.loads(p.read_text()) if p.exists() else None


def save_job(job):
    with LOCK:
        p = job_path(job["slug"])
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(job, indent=1, ensure_ascii=False))
        tmp.replace(p)


def update(slug, **kw):
    job = load_job(slug) or {"slug": slug}
    log = kw.pop("log", None)
    job.update(kw)
    if log:
        job.setdefault("log", []).append(f"{time.strftime('%H:%M:%S')}  {log}")
        job["log"] = job["log"][-80:]
    job["updated"] = time.time()
    save_job(job)
    return job


def slugify(name):
    base = re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")[:32] or "reel"
    slug, n = base, 2
    while (PROJECTS / slug).exists() or (INBOX / f"{slug}").exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


# ---------------------------------------------------------------- workers

def run_logged(slug, cmd, cwd=REPO, label=""):
    """Run a command, streaming its last output lines into the job log."""
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    CURRENT.update(slug=slug, proc=proc)
    tail = []
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            tail.append(line)
            if not line.startswith(("warning:",)) and len(line) < 200:
                update(slug, log=f"{label}{line}")
    proc.wait()
    return proc.returncode, "\n".join(tail[-30:])


def describe_tool(name, inp):
    if name == "Bash":
        cmd = inp.get("command", "")
        m = re.search(r"reel\.py (\w[\w-]*)", cmd)
        return {"new": "Ingesting clip", "build": "Building storyboard + retention check", "frames": "Rendering storyboard frames",
                "media-list": "Checking your b-roll library", "media-add": "Adding b-roll", "media-search": "Searching stock b-roll",
                "media-shot": "Screenshotting a website", "media-url": "Downloading b-roll", "still": "Checking a frame",
                "qa": "Quality check: measuring every frame (~4 min)"}.get(
            m.group(1) if m else "", f"Running {cmd[:60]}")
    if name in ("Write", "Edit"):
        return f"Writing {Path(inp.get('file_path', '')).name}"
    if name == "Read":
        f = Path(inp.get("file_path", "")).name
        if f.startswith("sheet"):
            return f"Art-direction pass: scoring {f}"
        return f"Looking at {f}" if f.endswith((".jpg", ".png")) else f"Reading {f}"
    if name == "Skill":
        return "Loading the edit-reel skill"
    return name


def run_claude(slug, prompt, resume=None):
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "dontAsk", "--allowedTools", *ALLOWED_TOOLS]
    if resume:
        cmd += ["--resume", resume]
    proc = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    CURRENT.update(slug=slug, proc=proc)
    result, session = None, resume
    for line in proc.stdout:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("session_id"):
            session = ev["session_id"]
        if ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    update(slug, activity=describe_tool(block["name"], block.get("input", {})),
                           log=f"claude · {describe_tool(block['name'], block.get('input', {}))}")
        if ev.get("type") == "result":
            result = ev
    proc.wait()
    err = proc.stderr.read()
    if not result:
        return None, session, (err or "claude produced no result")[-800:]
    text = result.get("result", "") or ""
    if result.get("is_error") or text.startswith("API Error"):
        return None, session, f"Claude stopped: {text[:600]}"
    m = re.search(r"\{.*\}", text, re.S)
    try:
        data = json.loads(m.group(0)) if m else {"summary": text[-400:]}
    except json.JSONDecodeError:
        data = {"summary": text[-400:]}
    data["cost_usd"] = result.get("total_cost_usd")
    return data, session, None


def do_ingest(slug):
    job = load_job(slug)
    update(slug, status="transcribing", activity="Transcribing + colour grading in parallel…", log="transcription started", t0=time.time())
    grade = json.loads((EDITOR / "brands" / f"{BRAND}.json").read_text()).get("defaults", {}).get("look", {}).get("grade", "natural")
    code, tail = run_logged(slug, [sys.executable, "reel_editor/reel.py", "new", job["raw"], "--name", slug, "--force",
                                   "--lang", job.get("lang", "auto"), "--pregrade", grade] + (["--redo"] if job.get("redo") else []),
                            label="ingest · ")
    if code != 0:
        return update(slug, status="error", activity="Transcription failed", error=tail[-600:])
    lang = (json.loads((PROJECTS / slug / "transcript.json").read_text()).get("language") or "auto")
    update(slug, lang=lang, status="queued", activity="Transcribed — waiting for Claude", log=f"transcribed ({lang})")
    enqueue("plan", slug, None)


def clips_text(job, only=None):
    clips = [c for c in job.get("clips", []) if only is None or c["file"] in only]
    if not clips:
        return ""
    lines = "\n".join(f"  - media/{c['file']} — {c.get('note') or 'no note: place where it fits best'}" for c in clips)
    return ("The owner added their own b-roll clips (already in the project's media/). Use every one, placed where its note says:\n"
            f"{lines}\nAI-generated clips (e.g. Google Flow/Veo) go in `\"mode\": \"card\"` b-roll — the speaker docks and the clip "
            "plays in a framed card. Never crop, blur, cover or scale a clip to hide a watermark; keep it fully visible.\n")


def do_plan(slug):
    job = load_job(slug)
    update(slug, status="planning", activity="Claude is reading your video…", log="planning started")
    notes = f"Owner's notes for this reel: {job['notes']}" if job.get("notes") else ""
    qa_step = (QA_FAST if job.get("fast") else QA_FULL).format(slug=slug)
    style = job.get("style") or ""
    style_line = (f' Style reference: set "styleRef": "{style}" and follow reel_editor/brands/presets/{style}.md.' if style else "")
    data, session, err = run_claude(slug, PLAN_PROMPT.format(slug=slug, lang=job.get("lang", "auto"), brand=BRAND, notes=notes,
                                                             qa_step=qa_step, clips=clips_text(job), look=job.get("look") or "bright",
                                                             style_line=style_line))
    if err or not (PROJECTS / slug / "storyboard.json").exists():
        return update(slug, status="error", activity="Planning failed", error=err or "no storyboard was written", session=session)
    job = load_job(slug)
    for c in job.get("clips", []):
        c["used"] = True
    update(slug, clips=job.get("clips", []))
    update(slug, status="review", activity="Storyboard ready for review", session=session, plan=data,
           cost=round((job.get("cost") or 0) + (data.get("cost_usd") or 0), 3), log="storyboard ready")
    if job.get("autoRender"):
        enqueue("render", slug, {"draft": False})


def do_revise(slug, text):
    job = load_job(slug)
    update(slug, status="planning", activity=f"Revising: {text[:60]}", log=f"revision: {text}")
    qa_note = ("skip QA (fast mode)" if job.get("fast") else
               "re-check quality ONCE (`reel.py qa {slug}`, fix measured failures, re-score only frames that changed, update qa_scores.json — no further rounds)").format(slug=slug)
    data, session, err = run_claude(slug, REVISE_PROMPT.format(slug=slug, text=text.replace('"', "'"), qa_note=qa_note), resume=job.get("session"))
    if err:
        return update(slug, status="review", activity="Revision failed — see log", log=f"revision failed: {err[:200]}")
    revs = job.get("revisions", []) + [{"text": text, "summary": data.get("summary"), "check": data.get("check")}]
    update(slug, status="review", activity="Revision applied", session=session, revisions=revs,
           cost=round((job.get("cost") or 0) + (data.get("cost_usd") or 0), 3), log="revision applied")
    if job.get("autoRender"):
        enqueue("render", slug, {"draft": False})


def do_render(slug, draft):
    update(slug, status="rendering", activity="Rendering draft (half-res)…" if draft else "Rendering final video…",
           renderStarted=time.time(), log="render started")
    code, tail = run_logged(slug, [sys.executable, "reel_editor/reel.py", "render", slug] + (["--draft"] if draft else []),
                            label="render · ")
    if code != 0:
        return update(slug, status="review", activity="Render failed — see log", error=tail[-600:])
    m = re.search(r"rendered: (.+\.mp4)", tail)
    out = Path(m.group(1)).relative_to(PROJECTS / slug).as_posix() if m else None
    job = load_job(slug)
    outs = [o for o in job.get("outputs", []) if o != out] + ([out] if out else [])
    t0 = load_job(slug).get("t0")
    took = f" · {round((time.time() - t0) / 60, 1)} min since upload" if t0 and len(outs) == 1 else ""
    update(slug, status="done", activity=f"Ready{took}", outputs=outs, latest=out, log=f"rendered {out}{took}")


def do_caption(slug, opts):
    before = (load_job(slug) or {}).get("activity")  # caption runs must not overwrite the reel's own status line
    update(slug, captionStatus="working", log=f"caption: {opts.get('tone')}, {opts.get('lang')}, {opts.get('cta')}")
    cta = {"follow": "follow for more", "comment": f"comment the keyword \"{opts.get('keyword') or 'AI'}\" to get the details",
           "link": "link in bio", "whatsapp": "join the WhatsApp group (link in bio)", "save": "save and share this"}.get(opts.get("cta"), "follow for more")
    lang = {"en": "English", "te-en": "Telugu + English mix (Telugu words in Telugu script, like the owner speaks)", "te": "Telugu"}.get(opts.get("lang"), "English")
    extra = f"\nOwner's extra direction: {opts['note']}" if opts.get("note") else ""
    data, _, err = run_claude(slug, CAPTION_PROMPT.format(slug=slug, tone=opts.get("tone") or "direct", lang=lang, cta=cta, extra=extra))
    if err or not (PROJECTS / slug / "instagram_caption.txt").exists():
        return update(slug, captionStatus="error", captionError=(err or "no caption was written")[-300:], activity=before, log="caption failed")
    job = load_job(slug)
    update(slug, captionStatus="ready", captionError=None, captionNotes=(data or {}).get("notes"), activity=before,
           cost=round((job.get("cost") or 0) + ((data or {}).get("cost_usd") or 0), 3), log="caption written")


def enqueue(kind, slug, arg):
    PENDING.append(slug)
    WORK.put((kind, slug, arg))


def worker():
    while True:
        kind, slug, arg = WORK.get()
        if slug in PENDING:
            PENDING.remove(slug)
        job = load_job(slug) or {}
        if job.get("cancelled"):
            WORK.task_done()
            continue
        try:
            if kind == "ingest":
                do_ingest(slug)
            elif kind == "plan":
                do_plan(slug)
            elif kind == "revise":
                do_revise(slug, arg)
            elif kind == "render":
                do_render(slug, arg.get("draft", False))
            elif kind == "caption":
                do_caption(slug, arg or {})
        except Exception as e:  # keep the worker alive; surface the error on the job
            if kind == "caption":
                update(slug, captionStatus="error", captionError=repr(e))
            else:
                update(slug, status="error", activity="Unexpected error", error=repr(e))
        finally:
            CURRENT.update(slug=None, proc=None)
            if (load_job(slug) or {}).get("cancelled"):
                update(slug, status="error", activity="Cancelled", error="Cancelled by you.")
            WORK.task_done()


def settings():
    f = EDITOR / "settings.json"
    return json.loads(f.read_text()) if f.exists() else {}


def sources_of(slug):
    """Raw clips behind a project (joined reels list theirs in storyboard "sources")."""
    d = PROJECTS / slug
    out = []
    if (d / "transcript.json").exists():
        out.append(json.loads((d / "transcript.json").read_text())["meta"].get("original"))
    if (d / "storyboard.json").exists():
        out += json.loads((d / "storyboard.json").read_text()).get("sources", [])
    return [Path(x) for x in out if x and Path(x).exists()]


def new_job(name, raw, q):
    slug = slugify(name)
    update(slug, name=name, raw=str(raw), size=Path(raw).stat().st_size, status="queued", activity="Waiting to start",
           created=time.time(), notes=q.get("notes", "").strip(), lang=q.get("lang", "auto"), look=q.get("look", "bright"),
           style=q.get("style", ""), redo=bool(q.get("redo")), autoRender=bool(q.get("auto")), fast=bool(q.get("fast")),
           log=f"added {name} ({Path(raw).stat().st_size / 1e6:.1f} MB)")
    enqueue("ingest", slug, None)
    return slug


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


# ---------------------------------------------------------------- http

def job_view(slug):
    job = load_job(slug)
    if not job:
        return None
    d = PROJECTS / slug
    read = lambda n: (d / n).read_text(encoding="utf-8") if (d / n).exists() else None
    job["brief"] = read("brief.md")
    job["storyboard"] = read("storyboard.md")
    job["caption"] = read("instagram_caption.txt")
    job["frames"] = json.loads(read("frames.json")) if (d / "frames.json").exists() else []
    job["framesVersion"] = int((d / "frames.json").stat().st_mtime) if (d / "frames.json").exists() else 0
    rep = json.loads(read("qa_report.json")) if (d / "qa_report.json").exists() else None
    sc = json.loads(read("qa_scores.json")) if (d / "qa_scores.json").exists() else None
    if rep or sc:
        low = [f for f in (sc or {}).get("frames", []) if f.get("score", 10) < 8]
        job["qa"] = {"hard": len(rep["hard_failures"]) if rep else None, "frames": len(rep["frames"]) if rep else None,
                     "min": (sc or {}).get("min"), "mean": (sc or {}).get("mean"), "round": (sc or {}).get("round"),
                     "low": low[:6], "failures": (rep or {}).get("hard_failures", [])[:6]}
    job["voice"] = json.loads(read("voice.json")) if (d / "voice.json").exists() else None
    if (d / "props.json").exists():
        pr = json.loads(read("props.json"))
        fps = pr.get("fps", 30)
        proof = [{"kind": "headline", "t": round(g["from"] / fps, 1), "text": it["headline"], "meta": f"{it['source']} · {it['date']}"}
                 for g in pr.get("graphics", []) if g.get("type") == "clipping" for it in g.get("items", [])]
        idx = json.loads((d / "public" / "media" / "index.json").read_text()) if (d / "public" / "media" / "index.json").exists() else {}

        def credit(r):  # credit line, else where the file came from (Wikimedia, a URL…), else it's the owner's own footage
            if r.get("credit"):
                return r["credit"]
            name = re.sub(r"-(bright|brand|natural|cinematic|warm|moody)-[0-9a-f]{8}(?=\.)", "", Path(r["src"]).name)
            info = idx.get(Path(name).with_suffix(Path(name).suffix).name) or next((v for k, v in idx.items() if Path(k).stem == Path(name).stem), {})
            src = info.get("credit") or info.get("source") or ""
            return "" if src in ("", "local", "library") else src
        proof += [{"kind": "photo" if Path(r["src"]).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") else "clip", "t": round(r["from"] / fps, 1),
                   "src": r["src"], "text": r.get("label") or Path(r["src"]).stem.replace("-", " ")[:60], "meta": credit(r)}
                  for r in pr.get("broll", [])]
        job["proof"] = sorted(proof, key=lambda x: x["t"])
    exp = settings().get("export_dir")
    if exp and job.get("latest"):
        f = Path(exp).expanduser() / Path(job["latest"]).name
        job["exported"] = str(f) if f.exists() else None
    job["queue"] = WORK.qsize()
    job["ahead"] = (PENDING.index(slug) + (1 if CURRENT["slug"] and CURRENT["slug"] != slug else 0)) if slug in PENDING else 0
    job["busyWith"] = CURRENT["slug"] if CURRENT["slug"] != slug else None
    return job


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def send_file(self, path: Path):
        if not path.is_file():
            return self.send_json({"error": "not found"}, 404)
        size = path.stat().st_size
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = size - int(m.group(2))
            end = min(end, size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-cache")
        if self.path.split("?")[0].endswith(".mp4") and "download=1" in self.path:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        parts = [urllib.parse.unquote(p) for p in url.path.strip("/").split("/") if p]
        if not parts:
            return self.send_file(APP / "index.html")
        if parts == ["api", "jobs"]:
            jobs = []
            for p in sorted(PROJECTS.glob("*/job.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                j = json.loads(p.read_text())
                jobs.append({k: j.get(k) for k in ("slug", "name", "status", "activity", "created", "latest")})
            return self.send_json(jobs)
        if parts == ["api", "log"]:
            rows = sorted(editlog.load().values(), key=lambda e: e.get("updated", ""), reverse=True)
            return self.send_json([{**e, "name": Path(e["source"]).name, "folder": Path(e["source"]).parent.name} for e in rows])
        if parts == ["api", "settings"]:
            return self.send_json({"export_dir": settings().get("export_dir"), "styles": STYLES})
        if len(parts) == 3 and parts[:2] == ["api", "jobs"]:
            j = job_view(parts[2])
            return self.send_json(j) if j else self.send_json({"error": "no such job"}, 404)
        if parts[0] == "files" and len(parts) >= 3:
            root = (PROJECTS / parts[1]).resolve()
            target = (root / "/".join(parts[2:])).resolve()
            if root not in target.parents:  # no path traversal out of the project
                return self.send_json({"error": "forbidden"}, 403)
            return self.send_file(target)
        if parts[0] == "assets" and len(parts) == 2:
            return self.send_file(APP / parts[1])
        self.send_json({"error": "not found"}, 404)

    def do_PUT(self):
        # raw upload: PUT /api/upload?name=clip.mp4&notes=...&auto=0  (body = file bytes)
        url = urllib.parse.urlparse(self.path)
        parts = [p for p in url.path.strip("/").split("/") if p]
        if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "media":
            return self.add_clip(parts[2], urllib.parse.parse_qs(url.query))
        if url.path != "/api/upload":
            return self.send_json({"error": "not found"}, 404)
        q = urllib.parse.parse_qs(url.query)
        name = q.get("name", ["clip.mp4"])[0]
        if Path(name).suffix.lower() not in VIDEO_EXT:
            return self.send_json({"error": "Drop an .mp4, .mov, .m4v or .webm video"}, 400)
        size = int(self.headers.get("Content-Length") or 0)
        for p in PROJECTS.glob("*/job.json"):  # same file dropped again recently → reuse that reel
            j = json.loads(p.read_text())
            if (j.get("name") == name and j.get("size") == size and not j.get("cancelled")
                    and j.get("status") != "error" and time.time() - (j.get("created") or 0) < 6 * 3600):
                left = size
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        break
                    left -= len(chunk)
                return self.send_json({"slug": j["slug"], "duplicate": True})
        INBOX.mkdir(exist_ok=True)
        raw = INBOX / f"{slugify(name)}{Path(name).suffix.lower()}"
        left = int(self.headers.get("Content-Length") or 0)
        with open(raw, "wb") as f:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        one = {k: v[0] for k, v in q.items()}
        prev = editlog.find(raw)
        if prev and one.get("redo") != "1":  # already approved / delivered / held / skipped → don't silently redo it
            raw.unlink()
            return self.send_json({"logged": prev, "name": name})
        slug = new_job(name, raw, {**one, "auto": one.get("auto") == "1", "fast": one.get("fast") == "1", "redo": one.get("redo") == "1"})
        self.send_json({"slug": slug})

    def add_clip(self, slug, q):
        job = load_job(slug)
        name = q.get("name", ["clip.mp4"])[0]
        left = int(self.headers.get("Content-Length") or 0)
        if not job or Path(name).suffix.lower() not in VIDEO_EXT | {".png", ".jpg", ".jpeg", ".webp"}:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                left -= len(chunk)
            return self.send_json({"error": "Add a video (.mp4/.mov) or image clip"}, 400)
        folder = INBOX / f"{slug}-clips"
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / re.sub(r"[^A-Za-z0-9._-]+", "-", name)
        with open(dest, "wb") as f:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        r = subprocess.run([sys.executable, "reel_editor/reel.py", "media-add", slug, str(dest)], cwd=REPO, capture_output=True, text=True)
        m = re.search(r"media/(\S+)", r.stdout)
        if r.returncode != 0 or not m:
            return self.send_json({"error": (r.stderr or r.stdout)[-300:]}, 500)
        clip = {"file": m.group(1), "name": name, "note": q.get("note", [""])[0].strip(), "used": False}
        clips = [c for c in job.get("clips", []) if c["file"] != clip["file"]] + [clip]
        update(slug, clips=clips, log=f"b-roll clip added: {name}")
        return self.send_json({"ok": True, "clip": clip})

    def do_POST(self):
        parts = [p for p in urllib.parse.urlparse(self.path).path.strip("/").split("/") if p]
        if parts == ["api", "import"]:
            return self.import_folder(self.body_json())
        if len(parts) == 4 and parts[:2] == ["api", "jobs"] and load_job(parts[2]):
            slug, action = parts[2], parts[3]
            data = self.body_json()
            if action == "revise" and data.get("text", "").strip():
                if not load_job(slug).get("session"):
                    return self.send_json({"error": "plan this reel first"}, 400)
                update(slug, status="queued", activity="Revision queued")
                enqueue("revise", slug, data["text"].strip())
                return self.send_json({"ok": True})
            if action == "render":
                update(slug, status="queued", activity="Render queued")
                enqueue("render", slug, {"draft": bool(data.get("draft"))})
                return self.send_json({"ok": True})
            if action == "use-clips":
                job = load_job(slug)
                new = [c["file"] for c in job.get("clips", []) if not c.get("used")]
                if not new or not job.get("session"):
                    return self.send_json({"error": "add clips first (and let the plan finish)"}, 400)
                for c in job["clips"]:
                    c["used"] = True
                update(slug, clips=job["clips"], status="queued", activity="Re-edit with your clips queued")
                enqueue("revise", slug, "Use my new b-roll clips.\n" + clips_text(job, only=new))
                return self.send_json({"ok": True})
            if action == "cancel":
                update(slug, cancelled=True, status="error", activity="Cancelled", error="Cancelled by you.")
                if CURRENT["slug"] == slug and CURRENT["proc"]:
                    CURRENT["proc"].terminate()
                return self.send_json({"ok": True})
            if action == "caption":
                if not (PROJECTS / slug / "storyboard.json").exists() and not (PROJECTS / slug / "transcript.txt").exists():
                    return self.send_json({"error": "the video has to be transcribed first"}, 400)
                update(slug, captionStatus="queued")
                enqueue("caption", slug, {k: str(v)[:300] for k, v in data.items()})
                return self.send_json({"ok": True})
            if action == "caption-save":
                text = str(data.get("text", ""))[:2400]
                (PROJECTS / slug / "instagram_caption.txt").write_text(text, encoding="utf-8")
                update(slug, captionStatus="ready", log="caption edited by you")
                return self.send_json({"ok": True})
            if action == "approve":
                job = load_job(slug)
                srcs = sources_of(slug) or ([Path(job["raw"])] if job.get("raw") and Path(job["raw"]).exists() else [])
                for src in srcs:
                    editlog.record(src, "approved", slug, Path(job.get("latest") or "").name or None, job.get("name", ""))
                update(slug, approved=True, log="approved by you — logged so it is never re-edited")
                return self.send_json({"ok": True, "logged": len(srcs)})
            if action == "reveal":
                job = load_job(slug)
                exp = settings().get("export_dir")
                f = Path(exp).expanduser() / Path(job.get("latest") or "x").name if exp else None
                target = f if f and f.exists() else (PROJECTS / slug / job["latest"] if job.get("latest") else PROJECTS / slug)
                subprocess.run(["open", "-R", str(target)])
                return self.send_json({"ok": True})
            if action == "replan":
                update(slug, cancelled=False, error=None)
                enqueue("plan", slug, None)
                update(slug, status="queued", activity="Re-plan queued")
                return self.send_json({"ok": True})
        self.send_json({"error": "bad request"}, 400)


def _import(self, data):  # bound below as Handler.import_folder
    folder = Path(str(data.get("path", "")).strip()).expanduser()
    if not folder.is_dir():
        return self.send_json({"error": f"Not a folder: {folder}"}, 400)
    min_s = float(data.get("minSec") or 30)
    vids = sorted(f for f in folder.rglob("*") if f.suffix.lower() in VIDEO_EXT and f.is_file() and not f.name.startswith("."))
    queued, done, short = [], [], []
    for f in vids[:60]:
        if editlog.find(f):
            done.append(f.name)
            continue
        if duration(f) < min_s:
            editlog.record(f, "skipped", note=f"under {int(min_s)} s")
            short.append(f.name)
            continue
        queued.append(new_job(f"{f.parent.name[:18]}/{f.name}" if f.parent != folder else f.name, f, data))
    return self.send_json({"queued": len(queued), "alreadyDone": len(done), "tooShort": len(short), "first": queued[0] if queued else None})


Handler.import_folder = _import


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    if not shutil.which("claude"):
        sys.exit("claude CLI not found on PATH")
    # jobs interrupted by a restart go back to a usable state
    for p in PROJECTS.glob("*/job.json"):
        j = json.loads(p.read_text())
        if j.get("status") in ("queued", "transcribing", "planning", "rendering"):
            j.update(status="review" if (p.parent / "storyboard.json").exists() else "error",
                     activity="Interrupted by app restart — continue from here")
            p.write_text(json.dumps(j, indent=1, ensure_ascii=False))
    threading.Thread(target=worker, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"Reel Studio on http://127.0.0.1:{a.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
