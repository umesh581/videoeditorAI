#!/usr/bin/env python3
"""Autopilot: edit every raw clip that lands in the inbox folder (e.g. a Google Drive folder
synced by Drive for Desktop) and drop the finished reel in the outbox.

  python3 watch.py --once        process whatever is ready, then exit (what launchd runs)
  python3 watch.py --loop        keep polling (for testing in a terminal)
  python3 watch.py --status      show config, queue and recent jobs

Config: autopilot/config.json. One job at a time; a lock file guards against overlapping runs.
"""
import argparse
import datetime as dt
import fcntl
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDITOR = HERE.parent  # reel_editor/
REPO = EDITOR.parent  # where .claude/skills/edit-reel lives
STATE = HERE / "state.json"
LOGS = HERE / "logs"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}

DEFAULTS = {
    "inbox": "",  # e.g. ~/Library/CloudStorage/GoogleDrive-<you>/My Drive/Reels/1-Raw
    "outbox": "",  # e.g. …/Reels/2-Edited
    "done": "",  # raw files are moved here after a successful edit (empty = leave in place)
    "settle_seconds": 30,  # file size must be unchanged this long (Drive still syncing otherwise)
    "language": "auto",
    "style_notes": "",  # standing creative direction, e.g. "warm grade, editorial-serif captions, 20-35s"
    "allow_ai_broll": False,  # vidIQ AI b-roll costs credits; off unless you opt in
    "model": "",  # empty = Claude Code default
    "max_minutes": 45,
    "notify": True,  # macOS notification when a reel is ready / fails
}


def log(msg):
    LOGS.mkdir(exist_ok=True)
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOGS / "watch.log", "a") as f:
        f.write(line + "\n")


def config():
    p = HERE / "config.json"
    cfg = {**DEFAULTS, **(json.loads(p.read_text()) if p.exists() else {})}
    for k in ("inbox", "outbox", "done"):
        cfg[k] = str(Path(cfg[k]).expanduser()) if cfg[k] else ""
    if not cfg["inbox"] or not cfg["outbox"]:
        sys.exit("autopilot/config.json needs inbox and outbox paths")
    return cfg


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"jobs": {}, "seen": {}}


def save_state(s):
    STATE.write_text(json.dumps(s, indent=1))


def notify(cfg, title, text):
    if cfg["notify"]:
        safe = lambda x: x.replace('"', "'")
        subprocess.run(["osascript", "-e", f'display notification "{safe(text)}" with title "{safe(title)}"'],
                       capture_output=True)


def slug_for(path: Path):
    base = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")[:32] or "reel"
    return f"{base}-{dt.datetime.now():%m%d-%H%M}"


def ready_files(cfg, state):
    """Video files in the inbox whose size has been stable for settle_seconds."""
    inbox = Path(cfg["inbox"])
    if not inbox.exists():
        log(f"inbox not found: {inbox} (is Google Drive for Desktop running?)")
        return []
    out, now = [], time.time()
    for f in sorted(inbox.iterdir()):
        if f.suffix.lower() not in VIDEO_EXT or f.name.startswith("."):
            continue
        key = str(f)
        st = f.stat()
        sig = f"{st.st_size}:{int(st.st_mtime)}"
        if state["jobs"].get(key, {}).get("sig") == sig:
            continue  # already handled this exact file
        seen = state["seen"].get(key)
        if not seen or seen["sig"] != sig:
            state["seen"][key] = {"sig": sig, "since": now}
            continue
        if now - seen["since"] >= cfg["settle_seconds"] and st.st_size > 0:
            out.append((f, sig))
    return out


PROMPT = """AUTOPILOT RUN — no human is watching. Use the edit-reel skill and follow its **Autopilot** section.

Raw clip: {src}
Project slug: {slug}   (run: python3 reel_editor/reel.py new "{src}" --name {slug} --lang {lang})
Standing creative direction from the owner: {style}
AI-generated b-roll allowed: {ai}

Finish with a full-quality render. Your final message must be ONLY a JSON object:
{{"status": "ok"|"failed", "video": "<absolute path of the rendered mp4>", "hook": "<on-screen hook>",
  "summary": "<2 sentences: what the reel says and the main edit decisions>", "problems": "<anything the owner should check, or empty>"}}"""


def run_job(cfg, src: Path, slug: str):
    LOGS.mkdir(exist_ok=True)
    prompt = PROMPT.format(src=src, slug=slug, lang=cfg["language"], style=cfg["style_notes"] or "none — use your judgment",
                           ai="yes (still keep it to ≤3 clips)" if cfg["allow_ai_broll"] else "no")
    allowed = ["Bash(python3 reel_editor/reel.py:*)", "Bash(python3 reel_editor/reel.py *)",
               "Read", "Write", "Edit", "Glob", "Grep", "Skill"]
    allowed += cfg.get("extra_allowed_tools", [])  # e.g. exact vidIQ MCP tool names for AI b-roll
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--permission-mode", "dontAsk",
           "--allowedTools", *allowed, "--add-dir", str(src.parent)]
    if cfg["model"]:
        cmd += ["--model", cfg["model"]]
    log(f"[{slug}] claude autopilot starting")
    with open(LOGS / f"{slug}.log", "w") as lf:
        try:
            r = subprocess.run(cmd, cwd=REPO, stdout=subprocess.PIPE, stderr=lf, text=True,
                               timeout=cfg["max_minutes"] * 60)
        except subprocess.TimeoutExpired:
            return {"status": "failed", "problems": f"timed out after {cfg['max_minutes']} min"}
        lf.write(r.stdout)
    try:
        outer = json.loads(r.stdout)
        text = outer.get("result", "")
        m = re.search(r"\{.*\}", text, re.S)
        res = json.loads(m.group(0)) if m else {"status": "failed", "problems": text[-500:]}
        res["cost_usd"] = outer.get("total_cost_usd")
        return res
    except (json.JSONDecodeError, AttributeError):
        return {"status": "failed", "problems": f"unparseable claude output (exit {r.returncode}); see logs/{slug}.log"}


def deliver(cfg, src: Path, slug: str, res):
    out = Path(cfg["outbox"]) / src.stem
    out.mkdir(parents=True, exist_ok=True)
    proj = EDITOR / "projects" / slug
    if res.get("status") == "ok" and res.get("video") and Path(res["video"]).exists():
        shutil.copy2(res["video"], out / f"{src.stem}_reel.mp4")
    for name in ("brief.md", "storyboard.md"):
        if (proj / name).exists():
            shutil.copy2(proj / name, out / name)
    note = [f"# {src.name}", f"status: {res.get('status')}", f"hook: {res.get('hook', '')}", "",
            res.get("summary", ""), "", f"check: {res.get('problems') or '—'}",
            "", f"project: reel_editor/projects/{slug}  (ask Claude to revise it there)"]
    (out / "README.txt").write_text("\n".join(note))
    return out


def pending(cfg, state):
    """Files seen but not yet settled/handled — worth a second look shortly."""
    return [k for k, v in state["seen"].items()
            if Path(k).exists() and state["jobs"].get(k, {}).get("sig") != v["sig"]]


def process(cfg):
    state = load_state()
    files = ready_files(cfg, state)
    save_state(state)
    for src, sig in files:
        slug = slug_for(src)
        state["jobs"][str(src)] = {"sig": sig, "slug": slug, "status": "running", "started": time.time()}
        save_state(state)
        notify(cfg, "Reel autopilot", f"Editing {src.name}…")
        t0 = time.time()
        res = run_job(cfg, src, slug)
        out = deliver(cfg, src, slug, res)
        ok = res.get("status") == "ok" and any(out.glob("*_reel.mp4"))
        state["jobs"][str(src)].update({"status": "ok" if ok else "failed", "finished": time.time(),
                                        "minutes": round((time.time() - t0) / 60, 1), "out": str(out),
                                        "cost_usd": res.get("cost_usd")})
        save_state(state)
        if ok and cfg["done"]:
            Path(cfg["done"]).mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(Path(cfg["done"]) / src.name))
        log(f"[{slug}] {'done' if ok else 'FAILED'} in {(time.time() - t0) / 60:.1f} min → {out}")
        notify(cfg, "Reel ready ✅" if ok else "Reel failed ❌", f"{src.name}: {res.get('hook') or res.get('problems', '')}"[:180])


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true")
    g.add_argument("--loop", action="store_true")
    g.add_argument("--status", action="store_true")
    a = ap.parse_args()
    cfg = config()
    if a.status:
        print(json.dumps({k: cfg[k] for k in ("inbox", "outbox", "done", "style_notes", "allow_ai_broll")}, indent=1))
        for k, v in load_state()["jobs"].items():
            print(f"{v['status']:8} {Path(k).name}  {v.get('minutes', '')} min  {v.get('out', '')}")
        return
    with open(HERE / ".lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return  # a job is already running
        if a.once:
            # two passes so a file seen for the first time can settle within one launchd run
            process(cfg)
            if pending(cfg, load_state()):
                time.sleep(cfg["settle_seconds"] + 2)
                process(cfg)
        else:
            while True:
                process(cfg)
                time.sleep(15)


if __name__ == "__main__":
    main()
