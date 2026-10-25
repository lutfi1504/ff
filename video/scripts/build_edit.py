"""Generate the HyperFrames edit (edit/index.html + overlay scenes) from one cut list.

All times below are SOURCE seconds in assets/footage.mp4 (96.688 s). The script lays
the kept ranges end to end and maps every overlay, punch-in and sound to output time.
Re-run after changing a range:  python3 -I video/scripts/build_edit.py
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2] / "edit"
SRC_LEN = 96.688
W, H = 1080, 1920

# Kept ranges, in playback order. The cold open is lifted from 21.88-25.88 and NOT
# played again in the body, so nothing repeats.
SEGMENTS = [
    # --- HOOK (cold open): "saya suka kandungan protein dia, ada 30g ... low kalori gila"
    (21.88, 24.50, "hook"),  # pause 24.44-24.92 between "30g" and "rasanya" trimmed
    (24.84, 25.80, "hook"),  # caption flips to the next line at 25.80
    # --- BODY
    (0.00, 10.98, "body"),   # pause 10.92-11.24
    (11.18, 17.62, "body"),  # repeat: 2nd "Coklat Indulgent" 17.62-18.86 removed
    (19.00, 20.72, "body"),  # pause 20.66-20.92; resumes on the caption change at 19.02
    (20.86, 21.80, "body"),  # 21.80-25.88 is the hook (caption flips at 21.80)
    (25.88, 31.82, "body"),  # pause 31.76-32.14
    (32.08, 40.96, "body"),  # pause 40.90-41.20
    (41.14, 53.98, "body"),  # pause 53.92-54.18
    (54.12, 63.96, "body"),  # repeat: 63.96-70.32 restates the 33.5-38 "on set" point
    (70.32, 78.56, "body"),  # pause 78.48-79.12; caption changes at 70.32
    (79.04, 80.36, "body"),  # pause 80.28-80.96
    (80.88, 84.04, "body"),  # pause 83.98-84.24
    (84.18, 90.40, "body"),  # pause 90.34-90.68
    (90.62, 91.56, "body"),  # pause 91.44-91.92 shortened, keeps a beat before "to the world"
    (91.82, SRC_LEN, "body"),
]

FRAME = 1 / 25

# Grade "A natural portrait lift", applied with `hyperframes media-treatment --apply` and
# saved here in its normalized form so a re-run keeps it on every clip.
GRADE = (pathlib.Path(__file__).resolve().parents[1] / "grade.json").read_text().strip()


def layout():
    out, t = [], 0.0
    for a, b, tag in SEGMENTS:
        out.append({"src_in": a, "src_out": b, "start": round(t, 3), "dur": round(b - a, 3), "tag": tag})
        t += b - a
    return out, round(t, 3)


CLIPS, TOTAL = layout()
BODY_START = next(c["start"] for c in CLIPS if c["tag"] == "body")


def at(src_t, tag=None):
    """Output time of a source time (first kept range that contains it)."""
    for c in CLIPS:
        if (tag is None or c["tag"] == tag) and c["src_in"] <= src_t < c["src_out"]:
            return round(c["start"] + src_t - c["src_in"], 3)
    raise ValueError(f"source time {src_t} was cut")


# ---- Beats (source time -> what happens) -------------------------------------------
PUNCH_INS = [  # (source time, scale, shot cut where it resets) on talking-head shots only
    (25.00, 1.12, 25.80, "hook"),   # "low kalori gila"
    (37.00, 1.14, 38.20, None),     # "sangat sangat baguslah"
    (89.00, 1.20, 90.00, None),     # "power"
]

SCENES = {
    "hook": {"start": 0.0, "end": at(25.78, "hook")},
    "scoop": {"start": at(26.0), "end": at(28.5)},
    "tiptop": {"start": at(53.1), "end": at(54.9)},
    "power": {"start": at(88.96), "end": at(89.98)},
}

# Sound: (file, picture time, seconds from file start to its hit, volume)
SFX = [
    ("whoosh", BODY_START, 0.065, 0.45),           # hook -> story seam
    ("pop", at(25.0, "hook") + 0.1, 0.11, 0.35),  # LOW KALORI chip
    ("pop", SCENES["scoop"]["start"] + 0.1, 0.11, 0.35),
    ("pop", at(27.2) + 0.08, 0.11, 0.3),
    ("whoosh-short", SCENES["tiptop"]["start"] + 0.08, 0.065, 0.35),
    ("impact-bass-1", at(89.0), 0.045, 0.5),       # POWER, the payoff
]


def r(x):
    return f"{x:.3f}".rstrip("0").rstrip(".")


# ---- index.html ---------------------------------------------------------------------
def build_index():
    vids = []
    for i, c in enumerate(CLIPS):
        vids.append(
            f'        <video id="v{i:02d}" class="clip shot" src="assets/footage.mp4" playsinline '
            f'data-has-audio="true" data-volume="1" data-fade-in="0.03" data-fade-out="0.03" '
            f'data-start="{r(c["start"])}" data-duration="{r(c["dur"])}" '
            f'data-media-start="{r(c["src_in"])}" data-track-index="{i % 2}" '
            f'data-color-grading="{html.escape(GRADE)}"></video>'
        )
    hosts = []
    for n, (sid, s) in enumerate(SCENES.items()):
        hosts.append(
            f'      <div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" '
            f'data-track-kind="graphics" data-start="{r(s["start"])}" data-duration="{r(s["end"] - s["start"])}" '
            f'data-track-index="{2 + n % 2}" data-width="{W}" data-height="{H}"></div>'
        )
    sfx = []
    for n, (name, pic_t, hit, vol) in enumerate(SFX):
        start = max(0.0, pic_t + FRAME - hit)
        dur = {"whoosh": 0.575, "whoosh-short": 0.575, "pop": 0.72, "impact-bass-1": 2.116}[name]
        sfx.append(
            f'      <audio id="sfx{n}" class="clip" src="assets/sfx/{name}.mp3" data-start="{r(start)}" '
            f'data-duration="{r(dur)}" data-volume="{vol}" data-audio-group="sfx" data-track-index="{4 + n % 2}"></audio>'
        )
    punch = []
    for src_t, scale, reset_src, tag in PUNCH_INS:
        t0, t1 = at(src_t, tag), at(reset_src - 0.001, tag) + 0.001
        punch.append(f'      tl.to("#cam", {{ scale: {scale}, duration: 0.18, ease: "expo.out" }}, {r(t0)});')
        punch.append(f'      tl.set("#cam", {{ scale: 1 }}, {r(t1)});')

    return f"""<!doctype html>
<html lang="ms" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="assets/gsap.min.js"></script>
    <!-- Generated by video/scripts/build_edit.py from its cut list. Edit there and re-run,
         or edit here directly in the HyperFrames preview. -->
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: #050506; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
      #cam {{ position: absolute; inset: 0; transform-origin: 50% 38%; }}
      .shot {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{r(TOTAL)}" data-width="{W}" data-height="{H}">
      <div id="cam">
{chr(10).join(vids)}
      </div>
{chr(10).join(hosts)}
{chr(10).join(sfx)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      // Story enters on the whoosh: lands slightly large and settles.
      tl.fromTo("#cam", {{ scale: 1.08 }}, {{ scale: 1, duration: 0.5, ease: "expo.out", immediateRender: false }}, {r(BODY_START)});
      // Punch-ins on emphasis words; each resets on the next shot cut.
{chr(10).join(punch)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


# ---- Overlay scenes -------------------------------------------------------------------
BASE_CSS = """
    #root { position: absolute; inset: 0; pointer-events: none; }
    .chip { position: absolute; left: 0; right: 0; top: 1060px; display: flex; justify-content: center; }
    .chip-in { display: inline-flex; align-items: baseline; gap: 18px; padding: 22px 40px;
      background: rgba(12, 12, 14, 0.8); border: 2px solid var(--gold); border-radius: 999px;
      font-family: "Poppins", sans-serif; font-weight: 800; font-size: 64px; letter-spacing: 0.01em;
      color: #fff; box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45); }
    .gold { color: var(--gold); }
"""
VARS = ":root { --gold: #d9b26a; --red: #e3262f; }"


def scene(sid, dur, css, body, script):
    return f"""<template>
  <style>
    {VARS}
{BASE_CSS}
{css}
  </style>
  <div id="root" data-composition-id="{sid}" data-start="0" data-duration="{r(dur)}" data-width="{W}" data-height="{H}">
{body}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{script}
    window.__timelines["{sid}"] = tl;
  </script>
</template>
"""


def build_hook():
    s = SCENES["hook"]
    dur = s["end"] - s["start"]
    title_out = 2.15
    chip_t = at(25.0, "hook") - s["start"]
    css = """
    #hook-scrim { position: absolute; left: 0; right: 0; top: 0; height: 760px;
      background: linear-gradient(180deg, rgba(0,0,0,0.72) 0%, rgba(0,0,0,0.45) 55%, rgba(0,0,0,0) 100%); }
    #hook-copy { position: absolute; left: 70px; right: 70px; top: 170px; text-align: center; }
    #hook-kicker { font-family: "Poppins", sans-serif; font-weight: 700; font-size: 46px; letter-spacing: 0.22em;
      text-transform: uppercase; color: var(--gold); }
    #hook-title { margin-top: 14px; font-family: "Archivo Black", sans-serif; font-size: 108px; line-height: 1;
      letter-spacing: -0.02em; text-transform: uppercase; color: #fff; text-shadow: 0 10px 40px rgba(0,0,0,0.5); }
    #hook-title .w { display: inline-block; }
    #hook-title .accent { color: var(--red); }
    #hook-chip { top: 1080px; }
"""
    body = f"""    <div id="hook-scrim" class="clip" data-start="0" data-duration="{r(title_out + 0.3)}" data-track-index="0"></div>
    <div id="hook-copy" class="clip" data-start="0" data-duration="{r(title_out + 0.3)}" data-track-index="1">
      <div id="hook-kicker" data-var-text="kicker">Pelakon ni dedah</div>
      <div id="hook-title"><span class="w">Rahsia</span> <span class="w">badan</span><br /><span class="w accent">fit</span> <span class="w">dia</span></div>
    </div>
    <div id="hook-chip" class="chip clip" data-start="{r(chip_t)}" data-duration="{r(dur - chip_t)}" data-track-index="2">
      <div class="chip-in" id="hook-chip-in">LOW <span class="gold">KALORI</span></div>
    </div>"""
    script = f"""    // Frame 0 is the thumbnail: the whole line is already on screen; the accent word floods red.
    tl.fromTo("#hook-title .accent", {{ color: "#ffffff" }}, {{ color: "#e3262f", duration: 0.3, ease: "power2.inOut" }}, 0.35);
    tl.to("#hook-title .w", {{ opacity: 0, filter: "blur(8px)", duration: 0.18, stagger: 0.05, ease: "power2.in" }}, {r(title_out - 0.15)});
    tl.to(["#hook-kicker", "#hook-scrim"], {{ opacity: 0, duration: 0.25, ease: "power2.in" }}, {r(title_out - 0.1)});
    tl.fromTo("#hook-chip-in", {{ scale: 0.7, opacity: 0, filter: "blur(6px)" }}, {{ scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.35, ease: "back.out(1.3)" }}, {r(chip_t)});
    tl.to("#hook-chip-in", {{ opacity: 0, duration: 0.12, ease: "power2.in" }}, {r(dur - 0.14)});"""
    return scene("hook", dur, css, body, script)


def build_scoop():
    s = SCENES["scoop"]
    dur = s["end"] - s["start"]
    t2 = at(27.2) - s["start"]
    body = f"""    <div id="scoop-chip" class="chip clip" data-start="0.05" data-duration="{r(dur - 0.05)}" data-track-index="0">
      <div class="chip-in" id="scoop-in"><span>2 SCOOP</span><span id="scoop-x2" class="gold">× 2 KALI</span></div>
    </div>"""
    script = f"""    tl.fromTo("#scoop-in", {{ scale: 0.7, opacity: 0, filter: "blur(6px)" }}, {{ scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.35, ease: "back.out(1.3)" }}, 0.05);
    tl.fromTo("#scoop-x2", {{ opacity: 0, filter: "blur(6px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.15, ease: "power4.out" }}, {r(t2)});
    tl.to("#scoop-in", {{ opacity: 0, filter: "blur(6px)", duration: 0.2, ease: "power2.in" }}, {r(dur - 0.22)});"""
    return scene("scoop", dur, "", body, script)


def build_tiptop():
    s = SCENES["tiptop"]
    dur = s["end"] - s["start"]
    css = """
    #tiptop-word { position: absolute; left: 0; right: 0; top: 1000px; text-align: center;
      font-family: "Archivo Black", sans-serif; font-size: 170px; letter-spacing: -0.01em; color: #fff;
      text-shadow: 0 12px 50px rgba(0,0,0,0.55); }
    #tiptop-word .gold { color: var(--gold); }
"""
    body = f"""    <div id="tiptop-word" class="clip" data-start="0.05" data-duration="{r(dur - 0.05)}" data-track-index="0">
      <span id="tiptop-a">TIP</span> <span id="tiptop-b" class="gold">TOP</span>
    </div>"""
    script = f"""    tl.fromTo("#tiptop-a", {{ x: -140, opacity: 0, filter: "blur(10px)" }}, {{ x: 0, opacity: 1, filter: "blur(0px)", duration: 0.32, ease: "expo.out" }}, 0.05);
    tl.fromTo("#tiptop-b", {{ x: 140, opacity: 0, filter: "blur(10px)" }}, {{ x: 0, opacity: 1, filter: "blur(0px)", duration: 0.32, ease: "expo.out" }}, 0.15);
    tl.to("#tiptop-word", {{ opacity: 0, filter: "blur(8px)", duration: 0.2, ease: "power2.in" }}, {r(dur - 0.22)});"""
    return scene("tiptop", dur, css, body, script)


def build_power():
    s = SCENES["power"]
    dur = s["end"] - s["start"]
    hit = at(89.0) - s["start"]
    css = """
    #power-flash { position: absolute; inset: 0; background: #fff; opacity: 0; }
    #power-word { position: absolute; left: 0; right: 0; top: 960px; text-align: center;
      font-family: "Archivo Black", sans-serif; font-size: 250px; letter-spacing: -0.02em; color: var(--red);
      text-shadow: 0 16px 60px rgba(0,0,0,0.6); }
"""
    body = f"""    <div id="power-flash" class="clip" data-start="{r(hit)}" data-duration="0.2" data-track-index="0"></div>
    <div id="power-word" class="clip" data-start="{r(hit)}" data-duration="{r(dur - hit)}" data-track-index="1">POWER</div>"""
    script = f"""    tl.fromTo("#power-flash", {{ opacity: 0.55 }}, {{ opacity: 0, duration: 0.18, ease: "power2.out" }}, {r(hit)});
    tl.fromTo("#power-word", {{ scale: 1.6, opacity: 0, filter: "blur(14px)" }}, {{ scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.16, ease: "power4.out" }}, {r(hit)});
    tl.to("#power-word", {{ opacity: 0, filter: "blur(10px)", duration: 0.16, ease: "power2.in" }}, {r(dur - 0.18)});"""
    return scene("power", dur, css, body, script)


if __name__ == "__main__":
    (ROOT / "compositions").mkdir(exist_ok=True)
    (ROOT / "index.html").write_text(build_index())
    for sid, fn in [("hook", build_hook), ("scoop", build_scoop), ("tiptop", build_tiptop), ("power", build_power)]:
        (ROOT / "compositions" / f"{sid}.html").write_text(fn())
    cut = SRC_LEN - TOTAL
    print(f"output {TOTAL:.2f}s (source {SRC_LEN:.2f}s, {cut:.2f}s removed), {len(CLIPS)} clips, body starts {BODY_START:.2f}s")
    print(json.dumps({k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in SCENES.items()}))
