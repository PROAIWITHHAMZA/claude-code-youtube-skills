"""Build "How to Make a YouTube Video With Claude Code (5 Steps)": real screen footage + motion graphics.

    python video3.py <output_dir> <build_dir> <recordings_dir>

Two kinds of scene:
  footage  real screen recordings (YouTube search, the scoring tools, the build, the result playing),
           cropped to the part that matters, time-fitted to the voice line, with a slow push-in
  anim     motion graphics rendered frame by frame in Python and piped into ffmpeg: words pop in,
           prompts type out, bars grow and count, a pipeline assembles, cards slide in
Both carry the talking robot host (mouth driven by the voice's loudness), burned-in captions,
chapter whooshes, and a music bed mixed under the whole video.
"""
import asyncio, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
import video2 as v2  # also re-skins build_video in the red + black brand
bv = v2.bv

W, H, FPS = 1920, 1080, 30
RED, RED_HOT, RED_DK, GREEN, AMBER, WHITE, MUTED, DIM = (v2.RED, v2.RED_HOT, v2.RED_DK, v2.GREEN, v2.AMBER,
                                                         v2.WHITE, v2.MUTED, v2.DIM)
REG, BOLD, BLACK, MONO = bv.REG, bv.BOLD, bv.BLACK, bv.MONO
BOX = (120, 100, 1560, 910)  # footage frame, 1440 x 810
HERE = os.path.dirname(os.path.abspath(__file__))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def prog(t, start, length):
    return ease((t - start) / length) if length > 0 else 1.0


# ---------------------------------------------------------------- shared animated background

_BG = None


def bg_frame(t):
    """A large brand background, panned slowly so even 'still' moments drift."""
    global _BG
    if _BG is None:
        big = Image.new("RGBA", (W + 240, H + 140), bv.BG + (255,))
        layer = Image.new("RGBA", big.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.ellipse((-300, -350, 1000, 560), fill=(170, 16, 30, 80))
        ld.ellipse((1300, 560, 2400, 1500), fill=(120, 10, 22, 70))
        big.alpha_composite(layer.filter(ImageFilter.GaussianBlur(170)))
        grid = Image.new("RGBA", big.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(grid)
        for x in range(0, big.width, 96):
            gd.line([(x, 0), (x, big.height)], fill=(255, 255, 255, 9), width=2)
        for y in range(0, big.height, 96):
            gd.line([(0, y), (big.width, y)], fill=(255, 255, 255, 9), width=2)
        big.alpha_composite(grid)
        _BG = big
    ox = int(120 + 110 * math.sin(t * 0.12))
    oy = int(70 + 60 * math.cos(t * 0.09))
    return _BG.crop((ox, oy, ox + W, oy + H))


_WORDS = {}


def word_img(text, size, color, stroke=0):
    key = (text, size, color, stroke)
    if key not in _WORDS:
        # every word gets the same ascent/descent box so words sit on one baseline
        f = BLACK(size)
        asc, desc = f.getmetrics()
        w = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(text, font=f)) + 2 * stroke + 20
        im = Image.new("RGBA", (w, asc + desc + 2 * stroke + 20), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10 + stroke, 10 + stroke + asc), text, font=f, fill=color, anchor="ls",
                                stroke_width=stroke, stroke_fill=(0, 0, 0))
        _WORDS[key] = im
    return _WORDS[key]


def paste_anim(img, layer, cx, cy, p, rise=40, scale_from=0.75):
    """Paste `layer` centred at (cx, cy) with entrance progress p (0..1): fade, rise and scale."""
    if p <= 0:
        return
    s = scale_from + (1 - scale_from) * p
    lw, lh = max(1, int(layer.width * s)), max(1, int(layer.height * s))
    im = layer if (lw, lh) == layer.size else layer.resize((lw, lh), Image.BILINEAR)
    if p < 1:
        a = im.split()[3].point(lambda v: int(v * p))
        im = im.copy()
        im.putalpha(a)
    img.alpha_composite(im, (int(cx - lw / 2), int(cy - lh / 2 + rise * (1 - p))))


def kinetic_lines(img, t, lines, size, top, stagger=0.11, start=0.1, gap=1.12):
    """Words pop in one after another; lines centred horizontally."""
    k = 0
    for li, (text, col) in enumerate(lines):
        words = text.split()
        ims = [word_img(w, size, col, 4) for w in words]
        space = size * 0.28
        total = sum(i.width for i in ims) + space * (len(ims) - 1)
        x = (W - total) / 2
        y = top + li * size * gap
        for im in ims:
            paste_anim(img, im, x + im.width / 2, y + im.height / 2, prog(t, start + k * stagger, 0.38))
            x += im.width + space
            k += 1
    return start + k * stagger


# ---------------------------------------------------------------- animated scene types

def a_kinetic(img, t, dur, v):
    end = kinetic_lines(img, t, v["lines"], v.get("size", 120), v.get("top", 260))
    if v.get("sub"):
        f = BOLD(50)
        layer = Image.new("RGBA", (1700, 80), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((850 - ImageDraw.Draw(layer).textlength(v["sub"], font=f) / 2, 10), v["sub"], font=f, fill=MUTED)
        paste_anim(img, layer, W / 2 - 80, v.get("top", 260) + len(v["lines"]) * v.get("size", 120) * 1.12 + 70, prog(t, end + 0.1, 0.5))


def a_step(img, t, dur, v):
    d = ImageDraw.Draw(img)
    k = BLACK(140)
    label = f"STEP {v['n']}"
    w = d.textlength(label, font=k)
    x_target = (1700 - w - 160) / 2
    p = prog(t, 0.05, 0.55)
    x = -w + (x_target + w) * p
    d.text((x, 150), label, font=k, fill=RED)
    pf = prog(t, 0.45, 0.4)
    if pf > 0:
        d.text((x_target + w + 20, 190), "/ 5", font=BLACK(90), fill=tuple(int(c * pf) for c in DIM))
    bw = int(900 * prog(t, 0.3, 0.7))
    d.rounded_rectangle(((1700 - 900) / 2, 345, (1700 - 900) / 2 + bw, 357), radius=6, fill=RED)
    kinetic_lines(img, t, [(v["text"], WHITE)], 100, 420, start=0.55)


def a_prompt(img, t, dur, v):
    p = prog(t, 0.0, 0.45)
    x0, y0, x1, y1 = 140, 90, 1560, 860
    oy = int(70 * (1 - p))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    v2.window(d, (x0, y0 + oy, x1, y1 + oy), v.get("title", "Claude Code  ·  your prompt"))
    tag = v.get("tag", "PROMPT  ·  copy it from the description")
    d.text((x1 - 30 - d.textlength(tag, font=BOLD(28)), y0 + oy + 14), tag, font=BOLD(28), fill=GREEN)
    f, lines, lh = bv.fit(d, v["text"], MONO, x1 - x0 - 140, y1 - y0 - 170, (62, 58, 54, 50, 46, 42, 38), gap=1.4)
    total = sum(len(l) for l in lines)
    type_time = min(dur * 0.62, max(1.2, total / 48))
    shown = int(total * clamp((t - 0.45) / type_time))
    d.text((x0 + 50, y0 + oy + 90), ">", font=f, fill=RED_HOT)
    cx, cy = x0 + 100, y0 + oy + 90
    left = shown
    for i, ln in enumerate(lines):
        y = y0 + oy + 90 + i * lh
        part = ln[:max(0, left)]
        d.text((x0 + 100, y), part, font=f, fill=WHITE)
        if left >= 0:
            cx, cy = x0 + 100 + d.textlength(part, font=f), y
        left -= len(ln)
        if left < 0:
            break
    if int(t * 2.2) % 2 == 0 or shown < total:
        d.rectangle((cx + 4, cy + 6, cx + 4 + f.size * 0.5, cy + f.size + 4), fill=RED_HOT)
    if p < 1:
        layer.putalpha(layer.split()[3].point(lambda a: int(a * p)))
    img.alpha_composite(layer)


def a_list(img, t, dur, v):
    d = ImageDraw.Draw(img)
    hp = prog(t, 0, 0.4)
    if hp > 0:
        bv.center(d, 90 - 20 * (1 - hp), v["heading"], BOLD(62), fill=tuple(int(c * hp) for c in WHITE))
    n = len(v["items"])
    step = min(1.0, (dur * 0.55) / max(1, n))
    for i, (text, ok) in enumerate(v["items"]):
        p = prog(t, 0.35 + i * step, 0.45)
        if p <= 0:
            continue
        y = 210 + i * 132
        x = 230 + int(260 * (1 - p))
        layer = Image.new("RGBA", (1340, 110), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle((0, 0, 1339, 109), radius=26, fill=(26, 26, 32, 240), outline=(60, 60, 70), width=2)
        f, lines, lh = bv.fit(ld, text, BOLD, 1100, 90, (48, 44, 40, 36), gap=1.15)
        ty = 55 - len(lines) * lh / 2
        for j, ln in enumerate(lines):
            ld.text((130, ty + j * lh), ln, font=f, fill=WHITE)
        cp = prog(t, 0.55 + i * step, 0.35)
        col = GREEN if ok else AMBER
        ld.ellipse((30, 20, 100, 90), fill=col if cp > 0 else (50, 50, 60))
        if cp > 0:
            if ok:
                pts = [(48, 56), (60, 70), (84, 40)]
                ld.line(pts[:2] if cp < 0.5 else pts, fill=WHITE, width=9, joint="curve")
            else:
                ld.text((56, 22), "!", font=BLACK(52), fill=WHITE)
        layer.putalpha(layer.split()[3].point(lambda a: int(a * p)))
        img.alpha_composite(layer, (x, y))


def a_bars(img, t, dur, v):
    d = ImageDraw.Draw(img)
    bv.center(d, 70, v["heading"], BOLD(60))
    half = dur * 0.42
    for c, (name, vals, start) in enumerate((("ROUND 1", v["r1"], 0.3), ("ROUND 2", v["r2"], half))):
        x = 150 + c * 760
        hp = prog(t, start - 0.2, 0.4)
        if hp <= 0:
            continue
        d.text((x, 180), name, font=BLACK(54), fill=tuple(int(cc * hp) for cc in (RED if c == 0 else GREEN)))
        for i, s in enumerate(vals):
            p = prog(t, start + i * 0.12, 0.8)
            if p <= 0:
                continue
            y = 270 + i * 88
            d.rounded_rectangle((x, y, x + 460, y + 62), radius=14, fill=(26, 26, 32))
            val = s * p
            col = GREEN if s >= 72 else AMBER if s >= 55 else RED
            d.rounded_rectangle((x, y, x + max(28, int(460 * val / 100)), y + 62), radius=14, fill=col)
            d.text((x + 18, y + 6), str(int(round(val))), font=BLACK(42), fill=WHITE)
            if p >= 0.98:
                d.text((x + 480, y + 12), "STRONG" if s >= 72 else "WORKABLE" if s >= 55 else "WEAK", font=BOLD(32), fill=col)


def a_pipeline(img, t, dur, v):
    nodes = v["nodes"]
    n = len(nodes)
    gap = 1300 / (n - 1)
    cy = 430
    step = (dur * 0.7) / n
    d = ImageDraw.Draw(img)
    bv.center(d, 120, v["heading"], BOLD(60))
    for i, (label, sub) in enumerate(nodes):
        cx = 210 + i * gap
        start = 0.3 + i * step
        if i > 0:
            lp = prog(t, start - step * 0.45, step * 0.45)
            if lp > 0:
                px = 210 + (i - 1) * gap + 115
                d.line([(px, cy), (px + (gap - 230) * lp, cy)], fill=RED, width=10)
        p = prog(t, start, 0.45)
        if p <= 0:
            continue
        layer = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        latest = i == n - 1 or t < 0.3 + (i + 1) * step
        pulse = 0.5 + 0.5 * math.sin(t * 6) if latest else 0
        ld.ellipse((20, 20, 240, 240), fill=(36, 14, 20), outline=RED_HOT if latest else RED, width=8 + int(4 * pulse))
        tf = BLACK(46 if len(label) < 8 else 38)
        ld.text((130 - ld.textlength(label, font=tf) / 2, 105), label, font=tf, fill=WHITE)
        paste_anim(img, layer, cx, cy, p, rise=0, scale_from=0.4)
        sp = prog(t, start + 0.25, 0.4)
        if sp > 0:
            f = BOLD(34)
            sl = Image.new("RGBA", (360, 60), (0, 0, 0, 0))
            sd = ImageDraw.Draw(sl)
            sd.text((180 - sd.textlength(sub, font=f) / 2, 8), sub, font=f, fill=MUTED)
            paste_anim(img, sl, cx, cy + 175, sp, rise=20, scale_from=1)


_IMGS = {}


def a_thumbs(img, t, dur, v):
    for p in v["images"]:
        if p not in _IMGS:
            _IMGS[p] = Image.open(p).convert("RGBA").resize((520, 293), Image.LANCZOS)
    srcs = [_IMGS[p] for p in v["images"]]
    d = ImageDraw.Draw(img)
    bv.center(d, 70, v["heading"], BOLD(58))
    shrink = prog(t, dur * 0.45, 1.2)
    for i, im in enumerate(srcs):
        p = prog(t, 0.2 + i * 0.25, 0.5)
        if p <= 0:
            continue
        big_w, small_w = 520, 170
        w = int(big_w + (small_w - big_w) * shrink)
        h = int(w * 9 / 16)
        th = v2.rounded(im.resize((w, h), Image.BILINEAR), max(8, w // 20))
        cx = 300 + i * 540
        cy = 470
        win = v.get("winner") == i and shrink > 0.9
        if win:
            d.rounded_rectangle((cx - w / 2 - 12, cy - h / 2 - 12, cx + w / 2 + 12, cy + h / 2 + 12), radius=16, outline=GREEN, width=8)
        paste_anim(img, th, cx, cy, p)
        if shrink > 0.2:
            lab = "FEED SIZE" if not win else "STILL READS"
            f = BOLD(34)
            d.text((cx - d.textlength(lab, font=f) / 2, cy + h / 2 + 26), lab, font=f, fill=GREEN if win else MUTED)


def a_card(img, t, dur, v):
    p = prog(t, 0.05, 0.5)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    col = v.get("color", RED)
    d.rounded_rectangle((230, 190, 1450, 700), radius=40, fill=(24, 24, 30, 245), outline=col, width=5)
    f = BOLD(44)
    d.text((840 - d.textlength(v["kicker"], font=f) / 2, 240), v["kicker"], font=f, fill=col)
    lines = bv.wrap(d, v["text"], BOLD(72), 1080)
    for i, ln in enumerate(lines):
        lp = prog(t, 0.35 + i * 0.2, 0.4)
        if lp > 0:
            ff = BOLD(72)
            d.text((840 - d.textlength(ln, font=ff) / 2, 340 + i * 90 + 20 * (1 - lp)), ln, font=ff,
                   fill=tuple(int(c * lp) for c in WHITE))
    paste_anim(img, layer, W / 2, H / 2, p, rise=30, scale_from=0.92)


_HOST = None


def a_host(img, t, dur, v):
    """The presenter card: Zayn's master photo full-frame with a slow push-in and a sliding name strip."""
    global _HOST
    if _HOST is None:
        src = Image.open(os.path.join(HERE, "presenter", "zayn_master.jpg")).convert("RGB")
        _HOST = src.resize((2112, 1188), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))
    z = 1.0 + 0.06 * (t / max(dur, 0.1))
    cw, ch = int(2112 / (1.1 * z)), int(1188 / (1.1 * z))
    x0, y0 = (2112 - cw) // 2, (1188 - ch) // 2 - int(30 * t / max(dur, 0.1))
    img.paste(_HOST.crop((x0, max(0, y0), x0 + cw, max(0, y0) + ch)).resize((W, H), Image.BILINEAR), (0, 0))
    p = prog(t, 0.45, 0.6)
    if p <= 0:
        return
    d = ImageDraw.Draw(img)
    # lower third, kept left of the face (which sits around x 760-1160)
    x = int(-640 + 680 * p)
    d.rectangle((x, 640, x + 16, 790), fill=RED)
    d.rectangle((x + 16, 640, x + 600, 725), fill=(6, 6, 9))
    d.text((x + 44, 644), v["name"], font=BLACK(66), fill=WHITE)
    d.rectangle((x + 16, 725, x + 600, 790), fill=RED)
    d.text((x + 44, 734), v["role"], font=BOLD(32), fill=WHITE)


ANIM = {"host": a_host, "kinetic": a_kinetic, "step": a_step, "prompt": a_prompt, "list": a_list, "bars": a_bars,
        "pipeline": a_pipeline, "thumbs": a_thumbs, "card": a_card}


# ---------------------------------------------------------------- per-frame overlays

def overlay_frame(img, t, cap, host_frames, levels, blink_at, host=True):
    img.alpha_composite(cap)
    if host:
        i = min(len(levels) - 1, int(t * FPS))
        x = levels[i]
        m = 0 if x < 0.13 else 1 if x < 0.42 else 2
        eyes = not any(b <= t < b + 0.13 for b in blink_at)
        img.alpha_composite(host_frames[(eyes, m)], (v2.HOST_X, v2.HOST_Y))


def blink_times(dur, seed):
    import random
    rnd = random.Random(seed)
    out, t = [], rnd.uniform(0.8, 2.5)
    while t < dur:
        out.append(t)
        t += rnd.uniform(2.5, 4.5)
    return out


def render_anim(v, dur, audio, cap_path, host_paths, out, whoosh, seed):
    frames = int(dur * FPS)
    cap = Image.open(cap_path).convert("RGBA")
    host_frames = {k: Image.open(p).convert("RGBA") for k, p in host_paths.items()}
    levels = v2.loudness(audio, dur)
    blinks = blink_times(dur, seed)
    args = [bv.FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio]
    fc = f"[1:a]apad=pad_dur={dur}[a0];"
    if whoosh:
        args += ["-i", whoosh]
        fc += "[2:a]volume=0.55[w];[a0][w]amix=inputs=2:duration=first:normalize=0[a]"
    else:
        fc += "[a0]anull[a]"
    args += ["-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-t", f"{dur:.3f}", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
             "-ar", "48000", "-ac", "2", out]
    p = subprocess.Popen(args, stdin=subprocess.PIPE)
    fn = ANIM[v["type"]]
    for f in range(frames):
        t = f / FPS
        img = bg_frame(t)
        fn(img, t, dur, v)
        if f < 9:  # quick fade in from black at every scene start for smooth cuts
            img = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, f / 9)
        overlay_frame(img, t, cap, host_frames, levels, blinks, host=not v.get("nohost"))
        p.stdin.write(img.convert("RGB").tobytes())
    p.stdin.close()
    if p.wait():
        sys.exit(f"ffmpeg failed on {out}")


def render_footage(v, dur, audio, cap_path, host_txt, frame_png, out, whoosh, rec_dir):
    src = os.path.join(rec_dir, v["rec"])
    cw, ch, cx, cy = v["crop"]
    speed = dur / v["len"]
    x0, y0, x1, y1 = BOX
    bw, bh = x1 - x0, y1 - y0
    n = int(dur * FPS) + 1
    args = ["-loop", "1", "-framerate", str(FPS), "-i", frame_png,
            "-ss", f"{v['start']:.2f}", "-t", f"{v['len']:.2f}", "-i", src,
            "-loop", "1", "-framerate", str(FPS), "-i", cap_path,
            "-f", "concat", "-safe", "0", "-i", host_txt, "-i", audio]
    fc = (f"[1:v]crop={cw}:{ch}:{cx}:{cy},setpts={speed:.4f}*(PTS-STARTPTS),fps={FPS},scale={bw}:{bh},"
          f"zoompan=z='1+0.05*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={bw}x{bh}:fps={FPS}[fv];"
          f"[0:v][fv]overlay={x0}:{y0}:eof_action=repeat[b];[b][2:v]overlay=0:0[c];"
          f"[3:v]fps={FPS},format=rgba[h];[c][h]overlay={v2.HOST_X}:{v2.HOST_Y},fade=t=in:st=0:d=0.3,format=yuv420p[v];"
          f"[4:a]apad=pad_dur={dur}[a0];")
    if whoosh:
        args += ["-i", whoosh]
        fc += "[5:a]volume=0.55[w];[a0][w]amix=inputs=2:duration=first:normalize=0[a]"
    else:
        fc += "[a0]anull[a]"
    bv.ff(*args, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-r", str(FPS),
          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out)


def name_strip(name, role, path):
    img = Image.new("RGBA", (620, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 16, 150), fill=RED)
    d.rectangle((16, 0, 600, 85), fill=(6, 6, 9))
    d.text((44, 4), name, font=BLACK(66), fill=WHITE)
    d.rectangle((16, 85, 600, 150), fill=RED)
    d.text((44, 94), role, font=BOLD(32), fill=WHITE)
    img.save(path)


def render_hostclip(v, dur, caps, strip, out):
    """A real talking-presenter clip: full-frame, its own voice, the name strip sliding in, timed captions."""
    args = ["-i", v["src"], "-loop", "1", "-framerate", str(FPS), "-i", strip]
    for _, _, cap in caps:
        args += ["-loop", "1", "-framerate", str(FPS), "-i", cap]
    fc = (f"[0:v]scale={W}:{H},fps={FPS},setsar=1[base];"
          f"[base][1:v]overlay=x='if(lt(t,0.5),-640,if(lt(t,1.1),-640+(t-0.5)/0.6*680,40))':y=640[c0];")
    last = "c0"
    for k, (a, b, _) in enumerate(caps):
        fc += f"[{last}][{k + 2}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[c{k + 1}];"
        last = f"c{k + 1}"
    fc += f"[{last}]fade=t=in:st=0:d=0.3,format=yuv420p[v];[0:a]apad=pad_dur=1[a]"
    bv.ff(*args, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-r", str(FPS),
          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out)


def footage_frame(label, path):
    img = bg_frame(0)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = BOX
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((x0 - 10, y0 - 10, x1 + 10, y1 + 10), radius=24, fill=(200, 20, 36, 120))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(28)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0 - 7, y0 - 7, x1 + 7, y1 + 7), radius=18, fill=(0, 0, 0), outline=RED, width=5)
    f = BOLD(32)
    w = d.textlength(label, font=f) + 70
    d.rounded_rectangle((x0, y0 - 74, x0 + w, y0 - 20), radius=27, fill=RED)
    d.ellipse((x0 + 20, y0 - 56, x0 + 38, y0 - 38), fill=WHITE)  # "rec" dot
    d.text((x0 + 50, y0 - 68), label, font=f, fill=WHITE)
    img.convert("RGB").save(path)


# ---------------------------------------------------------------- the tutorial

P1 = "Search YouTube for [your topic]. List the top 10 results with views and upload age. Then tell me what nobody covers well."
P2 = ("Write a 6-minute script about [the gap]. Use chapters, and mark what's on screen for every line. "
      "Write 5 opening hooks, score them, and keep the best one.")
P3 = ("Build the video with free tools only: edge-tts for the voice, Python and Pillow for the visuals, "
      "ffmpeg to render 1080p with captions and chapter fades.")
P4 = "Design 3 thumbnails. Test each one at YouTube feed sizes, down to 120 pixels wide, and pick the one that still reads."
P5 = "Write the title, a description with chapters, and a captions file."

SEARCH = {"rec": "rec_search.mp4", "crop": (2256, 1269, 0, 95)}
PLAY = {"rec": "rec_play.mp4", "crop": (2256, 1269, 0, 100)}
SCORE = {"rec": "rec_score.mp4", "crop": (1200, 675, 0, 36)}
BUILD = {"rec": "rec_build.mp4", "crop": (1200, 675, 0, 30)}
TV = os.path.join(HERE, "output", "thumb-variants")


def foot(base, label, start, length):
    return dict(base, type="footage", label=label, start=start, len=length)


SCENES = [
    ("Make a full video with Claude Code", None, [
        ({"type": "hostclip", "src": os.path.join(HERE, "presenter", "clips", "intro.mp4"),
          "name": "ZAYN", "role": "AI host  ·  real work, no hype", "nohost": True,
          "segments": [(0.0, 2.58, "Hi, I'm Zayn, the AI host of this channel."),
                       (3.46, 6.56, "Today I'll show you how to make a full YouTube video with Claude Code."),
                       (7.38, 9.9, "Zero editing. Let's get into it.")]},
         "Hi, I'm Zayn, the AI host of this channel. Today I'll show you how to make a full YouTube video with Claude Code. Zero editing. Let's get into it.", 0.2),
        ({"type": "kinetic", "lines": [("A FULL YOUTUBE VIDEO.", WHITE), ("ZERO EDITING.", RED_HOT)], "size": 120, "top": 280,
          "sub": "Script · Voice · Visuals · Thumbnail"},
         "The script, the voice, the visuals and the thumbnail. Claude Code makes all of it.", 0),
        (foot(PLAY, "REAL RESULT", 1.0, 13.0),
         "This is one I made. Every frame and every word of the voiceover was rendered by Claude Code, on a normal laptop.", 0.3),
        ({"type": "list", "heading": "5 steps", "items": [("Set up Claude Code", True), ("Find the gap", True),
                                                         ("Script and score the hook", True), ("Build the video", True),
                                                         ("Thumbnail and publish", True)]},
         "Here's exactly how, in five steps. Every prompt is on screen, so you can pause and copy it.", 0.5),
    ]),
    ("Step 1: Set up", 1, [
        ({"type": "step", "n": 1, "text": "Set up Claude Code"}, "Step one. Set up.", 0),
        ({"type": "list", "heading": "What you need", "items": [
            ("Claude desktop app, then open the Code tab", True), ("An empty folder for your project", True),
            ("Python installed. Claude Code installs the rest", True), ("A paid Claude plan for Claude Code", False)]},
         "Get the Claude desktop app, open the Code tab, and pick an empty folder for your project. Install Python if you don't have it. Claude Code installs the other free tools for you.", 0.5),
        ({"type": "card", "kicker": "HONEST NOTE", "text": "Claude Code needs a paid Claude plan. Every other tool here is free.", "color": AMBER},
         "One honest note: Claude Code itself needs a paid Claude plan. Every other tool in this video is free.", 0.3),
    ]),
    ("Step 2: Find the gap", 2, [
        ({"type": "step", "n": 2, "text": "Find the gap"}, "Step two. Find the gap, before you write anything.", 0),
        ({"type": "prompt", "text": P1}, "Type this. Put your own topic in the brackets.", 1.0),
        (foot(SEARCH, "REAL SEARCH", 5.5, 19.0),
         "It searches YouTube and reads the real results. When I did this, the top videos all relied on paid voice and video tools.", 0.3),
        ({"type": "card", "kicker": "THE GAP", "text": "High views, but nobody covers it well.", "color": GREEN},
         "That's a gap. Lots of views, but nobody doing it the way you would. That became my video.", 0.3),
    ]),
    ("Step 3: Script and score the hook", 3, [
        ({"type": "step", "n": 3, "text": "Script and score the hook"}, "Step three. The script.", 0),
        ({"type": "prompt", "text": P2}, "Ask for five hooks, not one. The first fifteen seconds decide whether anyone stays.", 1.0),
        (foot(SCORE, "REAL TOOL RUNNING", 0.3, 13.0),
         "Here it's scoring the hooks with a free checker. Each hook gets a score for specificity, stakes, curiosity and length.", 0.3),
        ({"type": "bars", "heading": "Hook scores", "r1": [59, 53, 52, 48, 46, 43], "r2": [73, 72, 66]},
         "My first round was weak, forty-three to fifty-nine. So it rewrote them, and the best one hit seventy-three. Don't accept the first draft.", 0.5),
    ]),
    ("Step 4: Build the video", 4, [
        ({"type": "step", "n": 4, "text": "Build the video"}, "Step four. Build the video.", 0),
        ({"type": "prompt", "text": P3}, "Name the free tools in your prompt, so it doesn't reach for paid ones.", 1.0),
        ({"type": "pipeline", "heading": "What happens next", "nodes": [("Script", "every line"), ("Voice", "edge-tts"),
                                                                       ("Visuals", "Python"), ("Video", "ffmpeg")]},
         "It turns every line into a natural voice, draws the visuals, and stitches everything into one video.", 0.3),
        (foot(BUILD, "REAL BUILD RUNNING", 0.0, 34.0),
         "This is the real build running. Forty-two lines, rendered one by one, with no editing timeline.", 0.3),
        ({"type": "card", "kicker": "THEN WATCH IT", "text": "Be honest. Tell it exactly what's weak.", "color": RED},
         "Then watch it, and be honest. My first version was too basic. I said so, and it researched more and rebuilt it.", 0.3),
    ]),
    ("Step 5: Thumbnail and publish", 5, [
        ({"type": "step", "n": 5, "text": "Thumbnail and publish"}, "Step five. The thumbnail.", 0),
        ({"type": "prompt", "text": P4}, "Test it the way viewers actually see it: tiny.", 1.0),
        ({"type": "thumbs", "heading": "Tested at feed size", "winner": 2,
          "images": [os.path.join(TV, "thumb_A.png"), os.path.join(TV, "thumb_B.png"), os.path.join(TV, "thumb_C.png")]},
         "Most thumbnails look great big, and fall apart small. This test catches it before your viewers do.", 0.5),
        ({"type": "prompt", "text": P5}, "Last, ask for the title, a description with chapters, and a captions file.", 0.8),
        ({"type": "list", "heading": "Before you publish", "items": [
            ("Watch the whole video once", True), ("Check every fact and number", True),
            ("Upload and press publish yourself", True)]},
         "Watch it once, check every fact, and then you upload and press publish yourself.", 0.3),
    ]),
    ("Your turn", None, [
        ({"type": "kinetic", "lines": [("ALL 5 PROMPTS", WHITE), ("IN THE DESCRIPTION", RED_HOT)], "size": 110, "top": 300},
         "All five prompts are in the description.", 0.5),
        ({"type": "kinetic", "lines": [("NEXT:", RED_HOT), ("A REAL AI AGENT", WHITE), ("IN n8n", WHITE)], "size": 110, "top": 230},
         "Next video, we build a real AI agent in n8n, step by step. Tell me in the comments what you'd make first.", 0.5),
        ({"type": "host", "name": "ZAYN", "role": "Subscribe for real AI work", "nohost": True},
         "I'm Zayn. Subscribe, and I'll see you there.", 1.5),
    ]),
]


async def main(out, build, rec_dir):
    os.makedirs(out, exist_ok=True)
    os.makedirs(build, exist_ok=True)
    host_paths = v2.make_host_frames(build)
    music, whoosh = os.path.join(build, "music.wav"), os.path.join(build, "whoosh.wav")
    v2.make_music(music)
    v2.make_whoosh(whoosh)
    lines = [(si, pill, v, text, hold, j == 0) for si, (_, pill, items) in enumerate(SCENES)
             for j, (v, text, hold) in enumerate(items)]
    only = os.environ.get("V3_ONLY")
    clips, t, chapters, srt = [], 0.0, [], []
    for i, (si, pill, v, text, hold, first) in enumerate(lines):
        base = os.path.join(build, f"{i:03d}")
        a, cap, mp4 = base + ".mp3", base + "_c.png", base + ".mp4"
        if v["type"] == "hostclip":
            # the presenter speaks in their own voice: no TTS, captions timed to the clip's own speech
            dur = bv.duration(v["src"]) + hold
            caps = []
            for k, (s0, s1, seg) in enumerate(v["segments"]):
                cp = f"{base}_c{k}.png"
                v2.render_caption(seg, pill, (i + 1) / len(lines), cp, False, pills=5)
                caps.append((s0, s1, cp))
            strip = base + "_strip.png"
            name_strip(v["name"], v["role"], strip)
            if not (only and os.path.exists(mp4) and v["type"] not in only.split(",")):
                render_hostclip(v, dur, caps, strip, mp4)
            if first:
                chapters.append((si, t))
            for s0, s1, seg in v["segments"]:
                srt.append(f"{len(srt) + 1}\n{bv.ts(t + s0, True)} --> {bv.ts(t + s1, True)}\n{seg}\n")
            d = bv.duration(mp4)
            t += d
            clips.append(mp4)
            print(f"  [{i + 1:2d}/{len(lines)}] {d:5.2f}s  {v['type']:<8} {text[:52]}", flush=True)
            continue
        await bv.speak(text, a)
        dur = bv.duration(a) + 0.35 + hold
        v2.render_caption(text, pill, (i + 1) / len(lines), cap, True, pills=5)
        w = whoosh if (first and i > 0) else None
        if not (only and os.path.exists(mp4) and v["type"] not in only.split(",")):
            if v["type"] == "footage":
                ht, fr = base + "_host.txt", base + "_frame.png"
                v2.host_track(host_paths, a, dur, ht, i)
                footage_frame(v["label"], fr)
                render_footage(v, dur, a, cap, ht, fr, mp4, w, rec_dir)
            else:
                render_anim(v, dur, a, cap, host_paths, mp4, w, i)
        if first:
            chapters.append((si, t))
        d = bv.duration(mp4)
        srt.append(f"{i + 1}\n{bv.ts(t, True)} --> {bv.ts(t + d - 0.3 - hold, True)}\n{text}\n")
        t += d
        clips.append(mp4)
        print(f"  [{i + 1:2d}/{len(lines)}] {d:5.2f}s  {v['type']:<8} {text[:52]}", flush=True)
    lst = os.path.join(build, "list.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        fh.writelines(f"file '{c.replace(os.sep, '/')}'\n" for c in clips)
    joined = os.path.join(build, "joined.mp4")
    bv.ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined)
    total = bv.duration(joined)
    final = os.path.join(out, "how-to-make-a-youtube-video-with-claude-code.mp4")
    bv.ff("-i", joined, "-stream_loop", "-1", "-i", music, "-filter_complex",
          f"[1:a]volume=0.11,afade=t=in:d=2,afade=t=out:st={total - 4:.2f}:d=4[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final)
    with open(os.path.join(out, "captions.srt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(srt))
    chap = "\n".join(f"{bv.ts(st)} {SCENES[si][0]}" for si, st in chapters)
    prompts = "\n\n".join(f"Step {k}:\n{p}" for k, p in ((2, P1), (3, P2), (4, P3), ("5a", P4), ("5b", P5)))
    with open(os.path.join(out, "description.txt"), "w", encoding="utf-8") as fh:
        fh.write("How to make a complete YouTube video with Claude Code in 5 steps: research, script, voice, visuals "
                 "and thumbnail, with zero editing and no paid video tools. Every prompt is below.\n\n"
                 + chap + "\n\n---- THE PROMPTS (copy into Claude Code) ----\n\n" + prompts +
                 "\n\n---- WHAT YOU NEED ----\nClaude desktop app (Code tab)  ·  Python\n"
                 "Free tools Claude Code installs: edge-tts (voice), Pillow (visuals), ffmpeg (video)\n"
                 "Honest note: Claude Code needs a paid Claude plan. Everything else is free.\n"
                 "Presented by Zayn, this channel's AI host (AI-generated image and voice).\n\n"
                 "#claudecode #aiautomation #youtubeautomation\n")
    print(f"\n  done: {final}  ({bv.ts(bv.duration(final))})\n\n{chap}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))
