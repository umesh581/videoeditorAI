"""HyperFrames talking-head-recut — cards + composition for the bake-off (follows the skill's Step 6–9 contract).
Cards are HTML fragments (scoped <style>, no <script>, data-anim-* only); this script writes them and compiles every
data-anim declaration into the single master GSAP timeline, as the skill's Step 9 describes."""
import json
import re
from pathlib import Path

W, H, FPS, DUR = 1080, 1920, 30, 58.6
WORK = Path("videos/ambition")
PUB = WORK / "public"
(PUB / "cards").mkdir(parents=True, exist_ok=True)

# Portrait layout recipes (skill Step 7 table) — #video-wrap target rects
LAYOUT = {
    "overlay": dict(left=0, top=0, width=1080, height=1920),
    "stack": dict(left=0, top=0, width=1080, height=844),
    "pip": dict(left=690, top=28, width=360, height=203),
}
# card-host bounds per layout (portrait), kept clear of Instagram's bottom 20% / right rail for text
HOST = {
    "overlay": dict(left=0, top=0, width=1080, height=1920),
    "stack": dict(left=0, top=844, width=1080, height=692),
    "pip": dict(left=0, top=0, width=1080, height=1920),
}

BASE_CSS = """
.card[data-card-id="{id}"] .root {{ width:100%; height:100%; position:relative; overflow:hidden; color:#fff;
  font-family:'Inter', ui-sans-serif, system-ui, sans-serif; background:{bg}; }}
.card[data-card-id="{id}"] .kicker {{ display:inline-block; padding:10px 16px; background:#fff; color:#0a0a0a; font-weight:700;
  font-size:22px; letter-spacing:0.22em; text-transform:uppercase; }}
.card[data-card-id="{id}"] .title {{ font-weight:700; letter-spacing:-0.04em; line-height:0.98; margin:0; }}
.card[data-card-id="{id}"] .lime {{ color:#D4FF33; }}
.card[data-card-id="{id}"] .slab {{ background:#D4FF33; color:#0a0a0a; }}
.card[data-card-id="{id}"] .muted {{ color:#9a9a9a; }}
"""

def chars(text, cls=""):
    return "".join(f'<span class="char">{c if c != " " else "&nbsp;"}</span>' for c in text)

CARDS = [
    dict(id="card-01", layout="overlay", start=0.3, end=4.0, bg="transparent",
         intent="Hook: the speaker's opening question, set big over the full-bleed video",
         css="""
.card[data-card-id="card-01"] .wrap { position:absolute; left:64px; right:170px; top:1060px; }
.card[data-card-id="card-01"] .shade { position:absolute; left:0; right:0; top:900px; height:700px;
  background:linear-gradient(180deg, rgba(10,10,10,0) 0%, rgba(10,10,10,0.75) 45%, rgba(10,10,10,0.0) 100%); }
.card[data-card-id="card-01"] .title { font-size:112px; margin-top:26px; }
.card[data-card-id="card-01"] .bar { height:10px; width:0; background:#D4FF33; margin-top:30px; }""",
         body="""<div class="shade" id="c1-shade"></div><div class="wrap">
<div class="kicker" id="c1-k">An honest question</div>
<h1 class="title" id="c1-t">Does your salary match your <span class="lime">ambition?</span></h1>
<div class="bar" id="c1-bar"></div></div>""",
         anims=[("#c1-shade", "fade-in", 0.0, 0.4), ("#c1-k", "slide-in", 0.1, 0.45, "left"), ("#c1-t", "mask-reveal", 0.35, 0.7, "bottom"),
                ("#c1-bar", "grow-x", 1.4, 0.6, 360)]),
    dict(id="card-02", layout="stack", start=4.2, end=9.0, bg="#0a0a0a",
         intent="The salaried rhythm: monthly credit, yearly appraisal",
         css="""
.card[data-card-id="card-02"] .row { position:absolute; left:64px; right:170px; display:flex; align-items:baseline; gap:28px; }
.card[data-card-id="card-02"] .lab { font-weight:700; font-size:24px; letter-spacing:0.2em; color:#9a9a9a; width:230px; }
.card[data-card-id="card-02"] .val { font-weight:700; font-size:72px; letter-spacing:-0.035em; }
.card[data-card-id="card-02"] .rule { position:absolute; left:64px; height:3px; width:0; background:#333; }""",
         body="""<div class="row" id="c2-r1" style="top:110px"><div class="lab">EVERY MONTH</div><div class="val">Salary credited</div></div>
<div class="rule" id="c2-rule" style="top:262px"></div>
<div class="row" id="c2-r2" style="top:320px"><div class="lab">EVERY YEAR</div><div class="val">Wait for the <span class="lime">appraisal</span></div></div>""",
         anims=[("#c2-r1", "slide-in", 0.2, 0.5, "left"), ("#c2-rule", "grow-x", 1.6, 0.5, 840), ("#c2-r2", "slide-in", 2.5, 0.5, "left")]),
    dict(id="card-03", layout="stack", start=9.0, end=13.0, bg="#0a0a0a",
         intent="Appraisals have a limit — a growth bar that hits a cap",
         css="""
.card[data-card-id="card-03"] .title { position:absolute; left:64px; right:170px; top:90px; font-size:84px; }
.card[data-card-id="card-03"] .track { position:absolute; left:64px; top:330px; width:840px; height:40px; background:#1c1c1c; border-radius:6px; }
.card[data-card-id="card-03"] .fill { position:absolute; left:64px; top:330px; width:0; height:40px; background:#D4FF33; border-radius:6px; }
.card[data-card-id="card-03"] .cap { position:absolute; left:400px; top:300px; width:6px; height:100px; background:#fff; }
.card[data-card-id="card-03"] .capl { position:absolute; left:420px; top:410px; font-weight:700; font-size:26px; letter-spacing:0.2em; }
.card[data-card-id="card-03"] .sub { position:absolute; left:64px; top:470px; font-size:44px; font-weight:700; color:#9a9a9a; }""",
         body="""<h2 class="title" id="c3-t">Appraisals have a limit.</h2><div class="track"></div><div class="fill" id="c3-fill"></div>
<div class="cap" id="c3-cap"></div><div class="capl" id="c3-capl">CAP</div><div class="sub" id="c3-sub">So life moves slow.</div>""",
         anims=[("#c3-t", "mask-reveal", 0.0, 0.6, "bottom"), ("#c3-fill", "grow-x", 0.6, 1.4, 340), ("#c3-cap", "scale-pop", 1.9, 0.35),
                ("#c3-capl", "fade-in", 2.0, 0.3), ("#c3-sub", "slide-in", 2.6, 0.5, "left")]),
    dict(id="card-04", layout="stack", start=13.2, end=21.0, bg="#0a0a0a",
         intent="The safe script: job → salary → stable life, then the turn",
         css="""
.card[data-card-id="card-04"] .chain { position:absolute; left:64px; right:170px; top:110px; display:flex; gap:18px; align-items:center; flex-wrap:wrap; }
.card[data-card-id="card-04"] .chip { padding:20px 28px; border:3px solid #fff; border-radius:999px; font-weight:700; font-size:46px; }
.card[data-card-id="card-04"] .chip.on { background:#D4FF33; color:#0a0a0a; border-color:#D4FF33; }
.card[data-card-id="card-04"] .arr { font-weight:700; font-size:46px; color:#9a9a9a; }
.card[data-card-id="card-04"] .turn { position:absolute; left:64px; top:430px; font-weight:700; font-size:76px; letter-spacing:-0.035em; }""",
         body="""<div class="chain"><div class="chip" id="c4-a">Job</div><div class="arr" id="c4-x1">→</div><div class="chip" id="c4-b">Salary</div>
<div class="arr" id="c4-x2">→</div><div class="chip on" id="c4-c">Stable life</div></div>
<div class="turn" id="c4-turn">But to be honest…</div>""",
         anims=[("#c4-a", "scale-pop", 0.4, 0.4), ("#c4-x1", "fade-in", 1.0, 0.3), ("#c4-b", "scale-pop", 1.4, 0.4), ("#c4-x2", "fade-in", 2.4, 0.3),
                ("#c4-c", "scale-pop", 2.9, 0.45), ("#c4-turn", "mask-reveal", 5.8, 0.6, "bottom")]),
    dict(id="card-05", layout="pip", start=21.0, end=30.6, bg="#0a0a0a",
         intent="What you actually want — goals, family dreams, lifestyle, freedom — vs salary-growth speed",
         css="""
.card[data-card-id="card-05"] .head { position:absolute; left:64px; top:300px; }
.card[data-card-id="card-05"] .title { font-size:96px; margin-top:24px; }
.card[data-card-id="card-05"] .list { position:absolute; left:64px; right:170px; top:640px; }
.card[data-card-id="card-05"] .it { display:flex; gap:26px; align-items:center; font-weight:700; font-size:66px; letter-spacing:-0.03em; margin:22px 0; }
.card[data-card-id="card-05"] .dot { width:22px; height:22px; border-radius:50%; background:#D4FF33; flex:none; }
.card[data-card-id="card-05"] .slab { position:absolute; left:64px; right:170px; top:1180px; padding:34px 36px; font-weight:700; font-size:62px; line-height:1.05; letter-spacing:-0.03em; }""",
         body="""<div class="head"><div class="kicker" id="c5-k">What you actually want</div></div>
<div class="list"><div class="it" id="c5-1"><span class="dot"></span>Your goals</div><div class="it" id="c5-2"><span class="dot"></span>Family dreams</div>
<div class="it" id="c5-3"><span class="dot"></span>Lifestyle</div><div class="it" id="c5-4"><span class="dot"></span>Freedom plans</div></div>
<div class="slab" id="c5-slab">Can't move at salary-growth speed.</div>""",
         anims=[("#c5-k", "slide-in", 0.2, 0.4, "left"), ("#c5-1", "slide-in", 0.4, 0.45, "left"), ("#c5-2", "slide-in", 1.6, 0.45, "left"),
                ("#c5-3", "slide-in", 3.1, 0.45, "left"), ("#c5-4", "slide-in", 5.1, 0.45, "left"), ("#c5-slab", "mask-reveal", 6.3, 0.6, "left")]),
    dict(id="card-06", layout="overlay", start=31.0, end=39.0, bg="transparent",
         intent="The contrarian line as a pull-quote over full-bleed video",
         css="""
.card[data-card-id="card-06"] .shade { position:absolute; left:0; right:0; top:820px; height:820px;
  background:linear-gradient(180deg, rgba(10,10,10,0) 0%, rgba(10,10,10,0.8) 40%, rgba(10,10,10,0.0) 100%); }
.card[data-card-id="card-06"] .q { position:absolute; left:64px; right:170px; top:990px; font-weight:700; font-size:92px; line-height:1.0; letter-spacing:-0.04em; }
.card[data-card-id="card-06"] .q2 { position:absolute; left:64px; right:170px; top:1290px; font-weight:700; font-size:60px; line-height:1.05; letter-spacing:-0.03em; }
.card[data-card-id="card-06"] .mark { position:absolute; left:58px; top:870px; font-weight:700; font-size:160px; color:#D4FF33; line-height:1; }""",
         body="""<div class="shade" id="c6-shade"></div><div class="mark" id="c6-m">“</div>
<div class="q" id="c6-q">Smart professionals don't quit their jobs.</div>
<div class="q2" id="c6-q2">They build a <span class="lime">second income stream.</span></div>""",
         anims=[("#c6-shade", "fade-in", 0.0, 0.4), ("#c6-m", "scale-pop", 0.1, 0.4), ("#c6-q", "mask-reveal", 0.3, 0.7, "bottom"),
                ("#c6-q2", "mask-reveal", 4.2, 0.7, "bottom")]),
    dict(id="card-07", layout="stack", start=39.2, end=48.0, bg="#0a0a0a",
         intent="AI as the advantage — not random tools, but services, offers, systems, digital assets",
         css="""
.card[data-card-id="card-07"] .title { position:absolute; left:64px; right:170px; top:80px; font-size:80px; }
.card[data-card-id="card-07"] .not { position:absolute; left:64px; top:240px; font-weight:700; font-size:44px; color:#9a9a9a; text-decoration:line-through; text-decoration-color:#D4FF33; text-decoration-thickness:5px; }
.card[data-card-id="card-07"] .grid { position:absolute; left:64px; right:170px; top:330px; display:flex; flex-wrap:wrap; gap:16px; }
.card[data-card-id="card-07"] .chip { padding:18px 26px; border-radius:14px; background:#1a1a1a; border:2px solid #2a2a2a; font-weight:700; font-size:44px; }""",
         body="""<h2 class="title" id="c7-t">AI = your <span class="lime">advantage.</span></h2><div class="not" id="c7-not">Random tools</div>
<div class="grid"><div class="chip" id="c7-1">Services</div><div class="chip" id="c7-2">Offers</div><div class="chip" id="c7-3">Systems</div><div class="chip slab" id="c7-4">Digital assets</div></div>""",
         anims=[("#c7-t", "mask-reveal", 0.1, 0.6, "bottom"), ("#c7-not", "fade-in", 3.0, 0.4), ("#c7-1", "scale-pop", 5.0, 0.35),
                ("#c7-2", "scale-pop", 5.8, 0.35), ("#c7-3", "scale-pop", 6.6, 0.35), ("#c7-4", "scale-pop", 7.4, 0.4)]),
    dict(id="card-08", layout="pip", start=48.0, end=56.0, bg="#0a0a0a",
         intent="The offer: this Sunday, free live webinar, Telugu + English, for people with a stable job but bigger ambition",
         css="""
.card[data-card-id="card-08"] .day { position:absolute; left:64px; top:300px; padding:24px 34px; font-weight:700; font-size:120px; letter-spacing:-0.04em; }
.card[data-card-id="card-08"] .title { position:absolute; left:64px; right:170px; top:520px; font-size:104px; }
.card[data-card-id="card-08"] .det { position:absolute; left:64px; top:790px; font-weight:700; font-size:52px; color:#9a9a9a; }
.card[data-card-id="card-08"] .who { position:absolute; left:64px; right:170px; top:1000px; padding-top:34px; border-top:3px solid #333; font-weight:700; font-size:58px; line-height:1.1; letter-spacing:-0.03em; }""",
         body="""<div class="day slab" id="c8-day">This Sunday</div><h2 class="title" id="c8-t">Free live webinar</h2>
<div class="det" id="c8-det">Telugu + English</div>
<div class="who" id="c8-who">Stable job, but a bigger ambition? <span class="lime">This session is for you.</span></div>""",
         anims=[("#c8-day", "mask-reveal", 0.2, 0.5, "left"), ("#c8-t", "mask-reveal", 0.7, 0.6, "bottom"), ("#c8-det", "fade-in", 1.5, 0.4),
                ("#c8-who", "slide-in", 4.1, 0.5, "bottom")]),
    dict(id="card-09", layout="overlay", start=56.0, end=58.6, bg="transparent",
         intent="CTA: join the WhatsApp group for webinar details",
         css="""
.card[data-card-id="card-09"] .cta { position:absolute; left:64px; right:170px; top:1180px; padding:36px 40px; border-radius:22px; font-weight:700; font-size:62px; line-height:1.05; letter-spacing:-0.03em; }
.card[data-card-id="card-09"] .sub { display:block; font-size:34px; margin-top:12px; opacity:0.75; }""",
         body="""<div class="cta slab" id="c9-cta">Join the WhatsApp group<span class="sub">Webinar details inside →</span></div>""",
         anims=[("#c9-cta", "slide-in", 0.15, 0.5, "bottom")]),
]

def gsap(card, a):
    sel = f'.card[data-card-id="{card["id"]}"] {a[0]}'
    kind, at, d = a[1], round(round((card["start"] + a[2]) * FPS) / FPS, 4), a[3]
    s = json.dumps(sel)
    if kind == "fade-in":
        return f"tl.fromTo({s},{{opacity:0}},{{opacity:1,duration:{d},ease:'power2.out'}},{at});"
    if kind == "slide-in":
        frm = a[4] if len(a) > 4 else "left"
        ax, dist = ("x", -80) if frm == "left" else ("x", 80) if frm == "right" else ("y", 80) if frm == "bottom" else ("y", -80)
        return f"tl.fromTo({s},{{opacity:0,{ax}:{dist}}},{{opacity:1,{ax}:0,duration:{d},ease:'power3.out'}},{at});"
    if kind == "scale-pop":
        return f"tl.fromTo({s},{{opacity:0,scale:0.6}},{{opacity:1,scale:1,duration:{d},ease:'back.out(1.6)'}},{at});"
    if kind == "grow-x":
        return f"tl.fromTo({s},{{width:0}},{{width:{a[4]},duration:{d},ease:'power2.out'}},{at});"
    if kind == "mask-reveal":
        dirn = a[4] if len(a) > 4 else "left"
        frm = {"left": "inset(0 100% 0 0)", "right": "inset(0 0 0 100%)", "bottom": "inset(100% 0 0 0)", "top": "inset(0 0 100% 0)"}[dirn]
        return f"tl.fromTo({s},{{clipPath:'{frm}'}},{{clipPath:'inset(0 0 0 0)',duration:{d},ease:'power2.inOut'}},{at});"
    raise ValueError(kind)

storyboard = {"schemaVersion": 3,
              "composition": {"fps": FPS, "width": W, "height": H, "durationSeconds": DUR, "layout": "portrait", "themeId": "noir", "seed": 42},
              "videoTrack": {"sourcePath": "input-video.mp4", "startSec": 0, "endSec": DUR, "bounds": {"x": 0, "y": 0, "width": W, "height": H}},
              "subtitles": {"enabled": False}, "cards": []}
hosts, tl = [], []
prev_layout = "overlay"
for i, c in enumerate(CARDS):
    zone = {"overlay": "video-overlay", "stack": "lower-third", "pip": "fullscreen"}[c["layout"]]
    storyboard["cards"].append({"id": c["id"], "intent": c["intent"], "startSec": c["start"], "endSec": c["end"], "accentIndex": i % 2,
                                "zone": zone, "contentHints": {"layout": c["layout"]}})
    html = (f'<div class="card" data-card-id="{c["id"]}"><style>{BASE_CSS.format(id=c["id"], bg=c["bg"])}{c["css"]}</style>'
            f'<div class="root">{c["body"]}</div></div>')
    (PUB / "cards" / f'{c["id"]}.html').write_text(html, encoding="utf-8")
    b = HOST[c["layout"]]
    hosts.append(f'<div class="card-host clip" id="host-{c["id"]}" data-card-id="{c["id"]}" data-start="{c["start"]:.4f}" data-duration="{c["end"] - c["start"]:.4f}" '
                 f'data-track-index="2" style="left:{b["left"]}px;top:{b["top"]}px;width:{b["width"]}px;height:{b["height"]}px;visibility:hidden;opacity:0;">{html}</div>')
    # video framing transition into this card's layout
    if c["layout"] != prev_layout:
        t = max(0, round(round((c["start"] - 0.35) * FPS) / FPS, 4))
        r = LAYOUT[c["layout"]]
        # transforms + clip-path only (hyperframes lint: no left/top tweens). stack = clip to top 44%;
        # pip = the whole 9:16 frame scaled into the top-right corner; overlay = full frame.
        target = {"overlay": "x:0,y:0,scale:1,clipPath:'inset(0px 0px 0px 0px round 0px)'",
                  "stack": "x:0,y:0,scale:1,clipPath:'inset(0px 0px 1076px 0px round 0px)'",
                  "pip": "x:795,y:28,scale:0.24,clipPath:'inset(0px 0px 0px 0px round 100px)'"}[c["layout"]]
        tl.append(f"tl.to('#video-wrap',{{{target},duration:0.6,ease:'power2.inOut'}},{t});")
        # pip: the video window floats above the full-canvas card; otherwise cards sit above the video
        tl.append(f"tl.set(['#video-wrap','#pip-ring'],{{zIndex:{5 if c['layout'] == 'pip' else 0}}},{t});")
        if c["layout"] == "pip":
            tl.append(f"tl.to('#pip-ring',{{opacity:1,duration:0.3}},{round(t + 0.4, 4)});")
        elif prev_layout == "pip":
            tl.append(f"tl.to('#pip-ring',{{opacity:0,duration:0.2}},{t});")
        prev_layout = c["layout"]
    s0, s1 = round(c["start"], 4), round(c["end"], 4)
    hs = json.dumps(f'.card-host[data-card-id="{c["id"]}"]')
    tl.append(f"tl.set({hs},{{visibility:'visible'}},{s0});")
    tl.append(f"tl.fromTo({hs},{{opacity:0}},{{opacity:1,duration:0.35,ease:'power2.out'}},{s0});")
    for a in c["anims"]:
        tl.append(gsap(c, a))
    tl.append(f"tl.to({hs},{{opacity:0,duration:0.3,ease:'power2.in'}},{round(s1 - 0.3, 4)});")
    tl.append(f"tl.set({hs},{{visibility:'hidden'}},{s1});")

(WORK / "storyboard.json").write_text(json.dumps(storyboard, indent=1, ensure_ascii=False))
index = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" />
<style>
@font-face {{ font-family:"Inter"; src:url("fonts/Inter-400-latin.woff2") format("woff2"); font-weight:400; font-display:block; }}
@font-face {{ font-family:"Inter"; src:url("fonts/Inter-700-latin.woff2") format("woff2"); font-weight:700; font-display:block; }}
:root {{ --bg:#0a0a0a; --text:#ffffff; --accent-0:#D4FF33; --accent-1:#ffffff; --accent-2:#9a9a9a; --accent-3:#2a2a2a; --accent-4:#D4FF33; }}
* {{ box-sizing:border-box; }}
html, body {{ margin:0; padding:0; width:100%; height:100%; overflow:hidden; background:#0a0a0a; font-family:"Inter", ui-sans-serif, system-ui, sans-serif; }}
#stage {{ position:relative; width:100%; height:100%; overflow:hidden; background:#0a0a0a; }}
.video-wrapper {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; overflow:hidden; transform-origin:0 0; }}
#pip-ring {{ position:absolute; left:795px; top:28px; width:{round(W*0.24)}px; height:{round(H*0.24)}px; border-radius:24px; box-shadow:0 0 0 4px #D4FF33, 0 18px 40px rgba(0,0,0,0.5); opacity:0; pointer-events:none; }}
.video-wrapper video {{ width:100%; height:100%; object-fit:cover; }}
.video-wrapper.pip-pill {{ border-radius:24px; box-shadow:0 0 0 4px #D4FF33, 0 18px 40px rgba(0,0,0,0.5); }}
.card-host {{ position:absolute; pointer-events:none; overflow:hidden; z-index:2; }}
.card-host .card {{ position:relative; width:100%; height:100%; overflow:hidden; }}
.card-host .char {{ display:inline-block; visibility:visible; }}
</style></head>
<body>
<div id="stage" data-composition-id="talking-head-recut" data-start="0" data-duration="{DUR}" data-fps="{FPS}" data-width="{W}" data-height="{H}">
<div id="pip-ring"></div><div class="video-wrapper" id="video-wrap"><video id="bg-video" src="input-video.mp4" playsinline data-has-audio="true" data-start="0" data-duration="{DUR}" data-track-index="1"></video></div>
{chr(10).join(hosts)}
<script src="vendor/gsap.min.js"></script>
<script>
(function () {{
  const tl = window.gsap.timeline({{ paused: true }});
  {chr(10).join('  ' + x for x in tl)}
  window.__timelines = window.__timelines || {{}};
  window.__timelines["talking-head-recut"] = tl;
}})();
</script>
</div></body></html>"""
(PUB / "index.html").write_text(index, encoding="utf-8")
print(f"{len(CARDS)} cards, {len(tl)} timeline statements")
