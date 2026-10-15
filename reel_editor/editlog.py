"""Edit log: every raw clip ever ingested, by content fingerprint, with its outcome.

Statuses: approved (owner OK'd the final) · delivered (final sent, no explicit verdict) · held (needs something from the
owner) · skipped (not worth editing, with the reason). `reel.py new` refuses a clip that is already logged unless --redo,
so a new chat never silently re-edits finished or rejected work.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

LOG = Path(__file__).resolve().parent / "edit_log.json"


def fingerprint(path):
    """Content hash (size + first and last 4 MB): survives renames and moves, cheap on big files."""
    p = Path(path)
    h = hashlib.sha1(str(p.stat().st_size).encode())
    with open(p, "rb") as f:
        h.update(f.read(4 << 20))
        if p.stat().st_size > 8 << 20:
            f.seek(-(4 << 20), 2)
            h.update(f.read())
    return h.hexdigest()[:16]


def load():
    return json.loads(LOG.read_text()) if LOG.exists() else {}


def find(path):
    return load().get(fingerprint(path))


def record(path, status, slug=None, final=None, note=""):
    log = load()
    fp = fingerprint(path)
    e = log.get(fp, {})
    e.update({"source": str(path), "status": status, "updated": dt.date.today().isoformat()})
    if slug: e["project"] = slug
    if final: e["final"] = final
    if note: e["note"] = note
    log[fp] = e
    LOG.write_text(json.dumps(log, indent=1, ensure_ascii=False))
    return fp
