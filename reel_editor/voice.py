"""Voice check + cleanup for the raw clip, run at ingest before transcription.

measure() grades the recording (noise floor, speech level, signal-to-noise, clipping);
clean() writes public/source-voice.mp4 — the same video stream with the voice denoised by
RNNoise (ffmpeg arnndn) at a strength picked from the measured SNR. Compression and loudness
are left to the render master, which also mixes SFX/music on top of this cleaned voice.
"""
import json
import subprocess
from pathlib import Path

import numpy as np

MODEL = Path(__file__).resolve().parent / "models" / "rnnoise-cb.rnnn"
RATE = 48000


def _decode(path, rate=RATE):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate),
                        "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


def measure(path):
    """Loudness stats over 30 ms frames: the quietest 10% is the room, the loudest 10% is the voice."""
    x = _decode(path)
    n = int(RATE * 0.03)
    frames = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    floor, speech = float(np.percentile(db, 10)), float(np.percentile(db, 90))
    hot = np.abs(x) > 0.98
    clipped = float((hot[:-2] & hot[1:-1] & hot[2:]).mean() * 100)  # flat-topped runs = real clipping, not loud peaks
    return {"noise_floor_db": round(floor, 1), "speech_db": round(speech, 1),
            "snr_db": round(speech - floor, 1), "clipped_pct": round(clipped, 3), "hum_hz": hum(x)}


def hum(x):
    """Mains-hum lines (50 Hz India/EU, 60 Hz US, + harmonics) standing >10 dB above their neighbourhood."""
    seg = x[: RATE * 60]
    if len(seg) < RATE:
        return []
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1 / RATE)
    db = lambda v: 20 * np.log10(v + 1e-12)
    found = []
    for base in (50, 60):
        for k in (1, 2, 3, 4):
            c = base * k
            peak = S[(f > c - 0.5) & (f < c + 0.5)].max()
            around = np.median(S[((f > c - 15) & (f < c - 3)) | ((f > c + 3) & (f < c + 15))])
            if db(peak) - db(around) > 18:  # a sharp spectral line, not just voice energy
                found.append(c)
    return found


def grade(m):
    snr = m["snr_db"]
    return "A" if snr >= 40 else "B" if snr >= 28 else "C" if snr >= 18 else "D"


def chain(m):
    """Cleanup filter for these measurements — lighter on clean recordings to avoid a processed sound."""
    snr = m["snr_db"]
    mix = 0.5 if snr >= 40 else 0.8 if snr >= 28 else 1.0
    f = ["highpass=f=80"] + [f"bandreject=f={c}:width_type=h:w=4" for c in m.get("hum_hz", [])]
    f.append(f"arnndn=m='{MODEL}':mix={mix}")
    if snr < 28:  # steady hiss/hum the network leaves behind
        f.append(f"afftdn=nr=10:nf={max(-80, min(-20, round(m['noise_floor_db'])))}:tn=1")
    return ",".join(f), mix


def warnings(m):
    out = []
    if m["clipped_pct"] > 0.5:
        out.append(f"voice is distorted ({m['clipped_pct']}% clipped) — cleanup can't undo clipping; hold the phone further away or lower the mic gain")
    elif m["clipped_pct"] > 0.05:
        out.append(f"slight clipping on the loudest words ({m['clipped_pct']}%) — fine for reels; a little more distance from the mic would remove it")
    if m["speech_db"] < -38:
        out.append(f"recording is very quiet (voice peaks around {m['speech_db']} dBFS) — loudness is fixed in the master, but noise rises with it")
    if m["snr_db"] < 18:
        out.append(f"very noisy room (SNR {m['snr_db']} dB) — cleaned, but a re-record or a lapel mic would sound far better")
    return out


def process(d, src_rel):
    """Measure, clean, re-measure. Returns (public-relative path of the cleaned clip, report dict)."""
    pub = d / "public"
    src = pub / src_rel
    before = measure(src)
    flt, mix = chain(before)
    out_rel = "source-voice.mp4"
    out = pub / out_rel
    v = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name",
                        "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout.strip()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
                    *(["-tag:v", "hvc1"] if v == "hevc" else []), "-af", flt, "-ar", str(RATE),
                    "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(out)], check=True)
    after = measure(out)
    report = {"before": before, "after": after, "grade_before": grade(before), "grade_after": grade(after),
              "filter": flt, "strength": mix, "warnings": warnings(before)}
    (d / "voice.json").write_text(json.dumps(report, indent=1))
    return out_rel, report


def summary(r):
    b, a = r["before"], r["after"]
    s = (f"voice {r['grade_before']}→{r['grade_after']}: background {b['noise_floor_db']}→{a['noise_floor_db']} dBFS, "
         f"SNR {b['snr_db']}→{a['snr_db']} dB (RNNoise {int(r['strength'] * 100)}%)")
    if b.get("hum_hz"):
        s += f"; removed mains hum at {', '.join(map(str, b['hum_hz']))} Hz"
    return s + "".join(f"\n      ! {w}" for w in r["warnings"])
