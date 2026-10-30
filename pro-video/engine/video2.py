"""Build "Claude Code Made My Entire Video (0 Other Paid Tools)": the making-of video.

    python video2.py <output_dir> <build_dir>

Reuses the drawing helpers from build_video.py, re-skinned in the channel's red + black brand, and
adds: a robot host that talks in sync with the voice (mouth driven by audio loudness, with blinks),
real-material visuals (YouTube search data, the security-review log, the real build log, real code,
real images and clips from the previous video), a synthesized music bed and chapter whooshes.
Everything shown on screen is real output from making the previous video.
"""
import array, asyncio, math, os, random, re, subprocess, sys, wave
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import build_video as bv
import robot

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMP = os.environ.get("TEMP", "")
W, H, FPS = 1920, 1080, 30
FFMPEG = bv.FFMPEG

# re-skin the shared helpers in the channel brand
RED, RED_HOT, RED_DK = (239, 35, 50), (255, 90, 90), (90, 12, 20)
bv.ACCENT, bv.ACCENT_DK = RED, RED_DK
bv.BG, bv.PANEL, bv.PANEL2 = (8, 8, 11), (24, 24, 30), (38, 38, 46)
GREEN, AMBER, WHITE, MUTED, DIM = bv.GREEN, bv.AMBER, bv.WHITE, (170, 172, 184), (96, 98, 110)
REG, BOLD, BLACK, MONO = bv.REG, bv.BOLD, bv.BLACK, bv.MONO

HOST_X, HOST_Y, HOST_S = 1600, 770, 280
CLIP_BOX = (210, 110, 1490, 830)  # 1280 x 720, 16:9

A = lambda *p: os.path.join(*p)
ASSETS = {
    "v1_frame": A(TEMP, "ytvideo-build", "001.png"),
    "v1_frame2": A(TEMP, "ytvideo-build", "015.png"),
    "v1_thumb": A(HERE, "output-v1", "thumbnail.png"),
    "v2_video": A(HERE, "output", "stop-getting-generic-answers-from-ai.mp4"),
    "v2_srt": A(HERE, "output", "captions.srt"),
    "v2_thumb": A(HERE, "output", "thumbnail.png"),
    "thumb_prev": A(HERE, "output", "thumb-variants", "thumb_previous.png"),
    "feed": A(HERE, "output", "thumb-variants", "feed_preview.png"),
    "profile_old": A(HERE, "output", "profile", "preview.png"),
    "robot_prev": A(HERE, "output", "robot", "preview.png"),
    "banner": A(HERE, "output", "banner.png"),
    "build_log": A(TEMP, "ytvideo-build2.log"),
    "build_code": A(HERE, "build_video.py"),
}


# ---------------------------------------------------------------- background and new visuals

def bg_red():
    img = Image.new("RGBA", (W, H), bv.BG + (255,))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse((-300, -350, 900, 520), fill=(160, 16, 30, 70))
    ld.ellipse((1250, 560, 2300, 1400), fill=(120, 10, 22, 60))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(170)))
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(0, W, 96):
        gd.line([(x, 0), (x, H)], fill=(255, 255, 255, 9), width=2)
    for y in range(0, H, 96):
        gd.line([(0, y), (W, y)], fill=(255, 255, 255, 9), width=2)
    img.alpha_composite(grid)
    return img


bv.bg_gradient = bg_red


def rounded(im, r):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), radius=r, fill=255)
    im = im.convert("RGBA")
    im.putalpha(mask)
    return im


def place(img, src, box, label=None, label_col=RED, r=26):
    """Fit an image into box (keeping aspect), with rounded corners, shadow and an optional label pill."""
    x0, y0, x1, y1 = box
    im = Image.open(src).convert("RGB")
    s = min((x1 - x0) / im.width, (y1 - y0) / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    px, py = x0 + (x1 - x0 - im.width) // 2, y0 + (y1 - y0 - im.height) // 2
    im = rounded(im, r)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 200), (px + 12, py + 18), im.split()[3])
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22)))
    img.alpha_composite(im, (px, py))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((px - 3, py - 3, px + im.width + 3, py + im.height + 3), radius=r + 3, outline=(70, 70, 82), width=3)
    if label:
        f = BOLD(34)
        w = d.textlength(label, font=f) + 44
        d.rounded_rectangle((px + 24, py - 26, px + 24 + w, py + 30), radius=28, fill=label_col)
        d.text((px + 46, py - 20), label, font=f, fill=WHITE)
    return (px, py, px + im.width, py + im.height)


def v_image(img, d, v):
    place(img, ASSETS[v["src"]], v.get("box", (150, 90, 1550, 820)), v.get("label"), v.get("color", RED))


def v_pair(img, d, v):
    (a, la, ca), (b, lb, cb) = v["left"], v["right"]
    place(img, ASSETS[a], (90, 140, 790, 800), la, ca)
    place(img, ASSETS[b], (850, 140, 1550, 800), lb, cb)


def v_collage(img, d, v):
    boxes = [(110, 90, 790, 470), (850, 90, 1530, 470), (110, 500, 790, 860), (850, 500, 1530, 860)]
    for (src, lab), box in zip(v["items"], boxes):
        place(img, ASSETS[src], box, lab, RED)


def v_hero(img, d, v):
    bot = robot.robot_b().crop(robot.sc(80, 40, 720, 680)).resize((700, 700), Image.LANCZOS)
    mask = Image.new("L", bot.size, 0)
    ImageDraw.Draw(mask).ellipse((40, 40, 660, 660), fill=255)
    bot.putalpha(mask.filter(ImageFilter.GaussianBlur(30)))
    img.alpha_composite(bot, (90, 110))
    d = ImageDraw.Draw(img)
    for i, (word, col) in enumerate(v["lines"]):
        d.text((860, 230 + i * 150), word, font=BLACK(132), fill=col, stroke_width=4, stroke_fill=(0, 0, 0))
    if v.get("sub"):
        d.text((866, 230 + len(v["lines"]) * 150 + 20), v["sub"], font=BOLD(46), fill=MUTED)


def window(d, box, title, title_col=MUTED):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=24, fill=(14, 14, 18), outline=(52, 52, 62), width=3)
    d.rounded_rectangle((x0, y0, x1, y0 + 58), radius=24, fill=(30, 30, 38))
    d.rectangle((x0, y0 + 30, x1, y0 + 58), fill=(30, 30, 38))
    for i, c in enumerate(((239, 68, 68), (245, 158, 11), (34, 197, 94))):
        d.ellipse((x0 + 22 + i * 32, y0 + 20, x0 + 40 + i * 32, y0 + 38), fill=c)
    d.text((x0 + 140, y0 + 12), title, font=BOLD(28), fill=title_col)


TERM_COL = {"g": (110, 231, 160), "r": (255, 120, 120), "y": (252, 211, 77), "w": (230, 230, 236), "m": (140, 144, 160), "c": (125, 211, 252)}


def v_terminal(img, d, v):
    box = (150, 70, 1550, 830)
    window(d, box, v.get("title", "Terminal  ·  Claude Code"))
    f = MONO(v.get("size", 36))
    lh = f.size * 1.42
    for i, (col, text) in enumerate(v["lines"]):
        d.text((box[0] + 40, box[1] + 90 + i * lh), text, font=f, fill=TERM_COL[col])


KW = re.compile(r"\b(async|await|def|for|if|else|return|try|except|in|import|from|with|not|and|or|raise|while)\b")


def v_code(img, d, v):
    box = (150, 70, 1550, 830)
    window(d, box, v["title"])
    f = MONO(31)
    lh = 40
    hi = set(v.get("highlight", []))
    for i, line in enumerate(v["code"]):
        if len(line) > 70:
            line = line[:69] + "…"
        y = box[1] + 84 + i * lh
        if i in hi:
            d.rectangle((box[0] + 4, y - 4, box[2] - 4, y + lh - 6), fill=(70, 14, 22))
        d.text((box[0] + 24, y), f"{v.get('start', 1) + i:>3}", font=f, fill=DIM)
        x = box[0] + 110
        # tiny highlighter: comments, strings, keywords, numbers
        if line.strip().startswith("#"):
            d.text((x, y), line, font=f, fill=(120, 124, 140))
            continue
        pos = 0
        for m in re.finditer(r"(#.*$)|(f?\"[^\"]*\"|f?'[^']*')|" + KW.pattern + r"|(\b\d+(\.\d+)?\b)", line):
            if m.start() > pos:
                seg = line[pos:m.start()]
                d.text((x, y), seg, font=f, fill=(226, 226, 232))
                x += d.textlength(seg, font=f)
            tok = m.group(0)
            col = (120, 124, 140) if m.group(1) else (134, 239, 172) if m.group(2) else (252, 211, 77) if m.group(4) else (255, 120, 130)
            d.text((x, y), tok, font=f, fill=col)
            x += d.textlength(tok, font=f)
            pos = m.end()
        d.text((x, y), line[pos:], font=f, fill=(226, 226, 232))


def v_search(img, d, v):
    d.rounded_rectangle((150, 60, 1550, 140), radius=40, fill=(24, 24, 30), outline=(60, 60, 70), width=3)
    d.text((200, 78), v["query"], font=BOLD(38), fill=WHITE)
    d.text((1540 - d.textlength(v["note"], font=REG(28)) - 30, 152), v["note"], font=REG(28), fill=DIM)
    show_tags = v.get("tags", False)
    for i, (views, age, title, tags) in enumerate(v["rows"]):
        y = 200 + i * 104
        d.rounded_rectangle((150, y, 1550, y + 90), radius=18, fill=(22, 22, 28))
        d.text((180, y + 16), views, font=BLACK(46), fill=RED_HOT if i == 0 else WHITE)
        d.text((180, y + 16 + 0), "", font=BOLD(20))
        d.text((360, y + 10), title, font=BOLD(34), fill=WHITE)
        d.text((360, y + 52), age, font=REG(26), fill=DIM)
        if show_tags:
            tx = 360 + d.textlength(age, font=REG(26)) + 24
            for t in tags:
                tf = BOLD(26)
                w = d.textlength(t, font=tf) + 30
                d.rounded_rectangle((tx, y + 50, tx + w, y + 84), radius=17, fill=(90, 14, 22), outline=RED, width=2)
                d.text((tx + 15, y + 52), t, font=tf, fill=WHITE)
                tx += w + 12


def v_scores(img, d, v):
    bv.center(d, 80, "Hook scores (hookscore.py)", BOLD(58))
    cols = [("ROUND 1", v["r1"], RED), ("ROUND 2", v["r2"], GREEN)]
    hi = v.get("highlight")
    for c, (name, vals, col) in enumerate(cols):
        x = 150 + c * 760
        on = hi is None or hi == c
        d.text((x, 190), name, font=BLACK(52), fill=col if on else DIM)
        for i, s in enumerate(vals):
            y = 280 + i * 86
            d.rounded_rectangle((x, y, x + 460, y + 60), radius=14, fill=(26, 26, 32))
            w = int(460 * s / 100)
            band_col = GREEN if s >= 72 else AMBER if s >= 55 else RED
            d.rounded_rectangle((x, y, x + w, y + 60), radius=14, fill=band_col if on else (60, 60, 70))
            d.text((x + 20, y + 6), str(s), font=BLACK(40), fill=WHITE)
            band = "STRONG" if s >= 72 else "WORKABLE" if s >= 55 else "WEAK"
            d.text((x + 480, y + 10), band, font=BOLD(32), fill=band_col if on else DIM)


def v_clipframe(img, d, v):
    x0, y0, x1, y1 = CLIP_BOX
    d.rounded_rectangle((x0 - 8, y0 - 8, x1 + 8, y1 + 8), radius=20, fill=(0, 0, 0), outline=RED, width=5)
    if v.get("label"):
        f = BOLD(32)
        w = d.textlength(v["label"], font=f) + 44
        # above the frame: the clip is overlaid on top of everything inside it
        d.rounded_rectangle((x0, y0 - 76, x0 + w, y0 - 22), radius=27, fill=RED)
        d.text((x0 + 22, y0 - 70), v["label"], font=f, fill=WHITE)


def v_chapter6(img, d, v):
    k = BLACK(120)
    label, total = f"STEP {v['n']}", "  / 6"
    w1, w2 = d.textlength(label, font=k), d.textlength(total, font=BLACK(84))
    x = (1700 - w1 - w2) / 2
    d.text((x, 170), label, font=k, fill=RED)
    d.text((x + w1, 202), total, font=BLACK(84), fill=DIM)
    bv.center(d, 370, v["text"], BLACK(104), maxw=1400)


for k, fn in {"image": v_image, "pair": v_pair, "collage": v_collage, "hero": v_hero, "terminal": v_terminal,
              "code": v_code, "search": v_search, "scores": v_scores, "clip": v_clipframe, "step": v_chapter6}.items():
    bv.VISUALS[k] = fn


def render_caption(text, pill, progress, path, host=True, pills=6):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cf = BOLD(42)
    right = 1560 if host else 1820
    lines = bv.wrap(d, text, cf, right - 100 - 60)
    lh = 54
    top = 1048 - len(lines) * lh - 26
    d.rounded_rectangle((100, top, right, 1058), radius=22, fill=(0, 0, 0, 190))
    cx = (100 + right) / 2
    for i, ln in enumerate(lines):
        d.text((cx - d.textlength(ln, font=cf) / 2, top + 12 + i * lh), ln, font=cf, fill=WHITE)
    d.rectangle((0, 0, int(W * progress), 7), fill=RED)
    if pill:
        for i in range(1, pills + 1):
            x = 1876 - (pills - i + 1) * 56
            on = i == pill
            d.rounded_rectangle((x, 22, x + 46, 64), radius=12, fill=RED if on else (40, 40, 50, 210))
            nf = BOLD(26)
            d.text((x + 23 - d.textlength(str(i), font=nf) / 2, 27), str(i), font=nf, fill=WHITE if on else MUTED)
    img.save(path)


# ---------------------------------------------------------------- the robot host

def host_frame(eyes_open, mouth):
    S, sc = robot.S, robot.sc
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.alpha_composite(robot.glow_layer(lambda g: g.rounded_rectangle(sc(150, 160, 650, 630), radius=130 * 3,
                                                                       fill=(200, 20, 36, 150)), 40 * 3))
    d = ImageDraw.Draw(img)
    d.line([sc(400, 175), sc(400, 120)], fill=(70, 70, 80), width=42)
    d.ellipse(sc(374, 80, 426, 132), fill=RED, outline=(6, 6, 9), width=12)
    d.ellipse(sc(386, 90, 402, 106), fill=(255, 190, 190))
    for x0 in (128, 622):
        d.rounded_rectangle(sc(x0, 330, x0 + 50, 470), radius=54, fill=RED, outline=(6, 6, 9), width=18)
    box = sc(160, 170, 640, 620)
    head = robot.vgrad((box[2] - box[0], box[3] - box[1]), (70, 70, 80), (24, 24, 30))
    mask = Image.new("L", head.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, head.size[0] - 1, head.size[1] - 1), radius=360, fill=255)
    img.paste(head, box[:2], mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=360, outline=RED, width=36)
    d.rounded_rectangle(sc(205, 285, 595, 545), radius=240, fill=(6, 6, 9), outline=(40, 40, 48), width=18)
    shapes = []
    for cx in (315, 485):
        if eyes_open:
            shapes.append(lambda g, cx=cx: (g.ellipse(sc(cx - 46, 360, cx + 46, 452), fill=RED_HOT),
                                             g.ellipse(sc(cx - 24, 374, cx - 4, 394), fill=(255, 225, 225))))
        else:
            shapes.append(lambda g, cx=cx: g.line([sc(cx - 46, 410), sc(cx + 46, 410)], fill=RED_HOT, width=54))
    if mouth == 0:
        shapes.append(lambda g: g.arc(sc(340, 440, 460, 510), 20, 160, fill=RED_HOT, width=42))
    elif mouth == 1:
        shapes.append(lambda g: g.rounded_rectangle(sc(360, 470, 440, 500), radius=40, fill=RED_HOT))
    else:
        shapes.append(lambda g: g.ellipse(sc(352, 458, 448, 522), fill=RED_HOT))
    for blur in (16 * 3, 5 * 3):
        img.alpha_composite(robot.glow_layer(lambda g: [f(g) for f in shapes], blur))
    d = ImageDraw.Draw(img)
    for f in shapes:
        f(d)
    return img.crop(sc(80, 40, 720, 680)).resize((HOST_S, HOST_S), Image.LANCZOS)


def make_host_frames(build):
    paths = {}
    for e in (True, False):
        for m in (0, 1, 2):
            p = os.path.join(build, f"host_{int(e)}{m}.png")
            if not os.path.exists(p):
                host_frame(e, m).save(p)
            paths[(e, m)] = p
    return paths


def loudness(audio, dur):
    raw = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", audio, "-f", "s16le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True).stdout
    s = array.array("h")
    s.frombytes(raw[: len(raw) // 2 * 2])
    per = 16000 // FPS
    n = int(dur * FPS) + 1
    out = []
    for i in range(n):
        chunk = s[i * per:(i + 1) * per]
        out.append(math.sqrt(sum(x * x for x in chunk[::4]) / max(1, len(chunk[::4]))) if chunk else 0.0)
    peak = max(out) or 1
    return [x / peak for x in out]


def host_track(frames, audio, dur, out_txt, seed):
    lv = loudness(audio, dur)
    rnd = random.Random(seed)
    seq, next_blink, blink_left, hold, cur = [], rnd.uniform(1.0, 3.0), 0, 0, 0
    for i, x in enumerate(lv):
        t = i / FPS
        want = 0 if x < 0.13 else 1 if x < 0.42 else 2
        if hold > 0:
            hold -= 1
        elif want != cur:
            cur, hold = want, 1
        if t >= next_blink and blink_left == 0:
            blink_left, next_blink = 4, t + rnd.uniform(2.5, 4.5)
        eyes = blink_left == 0
        blink_left = max(0, blink_left - 1)
        seq.append(frames[(eyes, cur)])
    with open(out_txt, "w", encoding="utf-8") as fh:
        run, start = seq[0], 0
        for i in range(1, len(seq) + 1):
            if i == len(seq) or seq[i] != run:
                fh.write(f"file '{run.replace(os.sep, '/')}'\nduration {(i - start) / FPS:.4f}\n")
                if i < len(seq):
                    run, start = seq[i], i
        fh.write(f"file '{run.replace(os.sep, '/')}'\n")


# ---------------------------------------------------------------- audio beds

def write_wav(path, samples, rate=44100):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        buf = array.array("h")
        for l, r in samples:
            buf.append(max(-32767, min(32767, int(l * 32767))))
            buf.append(max(-32767, min(32767, int(r * 32767))))
        w.writeframes(buf.tobytes())


def make_music(path, rate=44100):
    """A 16 s ambient pad loop: Am - F - C - G, soft sine partials with slow envelopes."""
    if os.path.exists(path):
        return
    hz = lambda n: 440 * 2 ** ((n - 69) / 12)
    chords = [(45, 57, 60, 64), (41, 53, 57, 60), (48, 55, 60, 64), (43, 55, 59, 62)]
    seg, n = 4.0, int(16 * rate)
    out = []
    for i in range(n):
        t = i / rate
        k = int(t // seg)
        u = t - k * seg
        env = min(1, u / 0.9) * min(1, (seg - u) / 0.9 + 0.15)
        prev = chords[(k - 1) % 4]
        tail = max(0, 1 - u / 0.9)
        l = r = 0.0
        for notes, e in ((chords[k], env), (prev, tail * 0.85)):
            if e <= 0:
                continue
            for j, note in enumerate(notes):
                f = hz(note)
                a = (0.55 if j == 0 else 0.32) * e
                s = math.sin(2 * math.pi * f * t) + 0.18 * math.sin(4 * math.pi * f * t)
                pan = 0.5 + (j - 1.5) * 0.15
                l += a * s * (1 - pan)
                r += a * s * pan
        trem = 0.9 + 0.1 * math.sin(2 * math.pi * 0.25 * t)
        out.append((l * 0.32 * trem, r * 0.32 * trem))
    write_wav(path, out, rate)


def make_whoosh(path, rate=44100):
    if os.path.exists(path):
        return
    rnd = random.Random(7)
    n = int(0.75 * rate)
    y, out = 0.0, []
    for i in range(n):
        t = i / n
        a = 0.02 + 0.5 * t ** 1.6          # rising cutoff
        y += a * (rnd.uniform(-1, 1) - y)
        env = math.sin(math.pi * min(1, t * 1.15)) ** 2
        out.append((y * env * 0.9, y * env * 0.9))
    write_wav(path, out, rate)


# ---------------------------------------------------------------- real material

def real_log_lines():
    lines = open(ASSETS["build_log"], encoding="utf-8", errors="replace").read().splitlines()
    pick, retry = [], None
    for i, ln in enumerate(lines):
        if "tts retry" in ln and retry is None:
            retry = i
    body = [l for l in lines if l.strip().startswith("[")]
    pick += [("w", body[0].strip()[:62]), ("w", body[1].strip()[:62]), ("m", "  ...")]
    if retry:
        pick += [("w", lines[retry - 1].strip()[:62]), ("y", lines[retry].strip()), ("w", lines[retry + 1].strip()[:62])]
    pick += [("m", "  ..."), ("w", body[-1].strip()[:62])]
    done = next((l for l in lines if "done:" in l), "")
    m = re.search(r"\((\d+:\d+)\)", done)
    pick += [("g", f"done: stop-getting-generic-answers-from-ai.mp4  ({m.group(1) if m else ''})")]
    chap = [l.strip() for l in lines if re.match(r"\s*\d+:\d\d ", l)]
    pick += [("c", c) for c in chap[:3]]
    return pick


def real_code(name, n):
    src = open(ASSETS["build_code"], encoding="utf-8").read().splitlines()
    start = next(i for i, l in enumerate(src) if l.startswith(name))
    return src[start:start + n], start + 1


def srt_time(contains):
    blocks = open(ASSETS["v2_srt"], encoding="utf-8").read().split("\n\n")
    for b in blocks:
        if contains in b:
            m = re.search(r"(\d+):(\d+):(\d+),(\d+) -->", b)
            return int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000
    return 0.0


SEARCH_ROWS = [
    ("1.1M", "4 months ago", "Claude Code (Free Plan) + YouTube = $77,000/Month", ["ElevenLabs", "Google Flow", "$77K/month claim"]),
    ("746K", "3 months ago", "How to Use Claude to Grow Your YouTube Channel", ["strategy only", "no video made"]),
    ("345K", "9 days ago", "How to Create Insane Motion Graphics With Claude", ["animations only"]),
    ("180K", "1 month ago", "Build ANY Faceless YouTube Channel with Claude", ["Higgsfield (paid)"]),
    ("179K", "2 weeks ago", "Claude Opus 5.5 Edited This ENTIRE Video In 5 Minutes", ["needs your own footage"]),
    ("76K", "5 months ago", "Watch Me Make a Faceless YouTube Video With Claude Code", ["Higgsfield (paid)"]),
]
SEARCH = {"type": "search", "query": "make youtube video with claude code",
          "note": "Real YouTube results  ·  Oct 29, 2026", "rows": SEARCH_ROWS}

SECURITY = [("c", "> review github.com/Jakeschincariol/youtube-agent-skill"), ("w", "  files read ........................ 24 / 24"),
            ("w", "  python tools ...... 6, standard library only"), ("w", "  network calls ..................... none"),
            ("w", "  hooks / settings changes .......... none"), ("w", "  hidden instructions / characters .. none"),
            ("g", "  OK  safe to install -> ~/.claude/skills/yt-*"), ("g", "  OK  11 skills installed")]

TITLE_CHECK = [("c", "> python title.py --title \"...\" --thumb \"COPY THESE\""), ("w", ""),
               ("w", "  \"Stop Getting Generic Answers From AI: 7 Fixes\""),
               ("g", "  45 chars   score 100/100"), ("g", "  ok  inside the 60-character desktop cut"),
               ("g", "  ok  carries a concrete figure (7)"), ("g", "  ok  thumbnail and title carry different words")]


def step(n, text):
    return {"type": "step", "n": n, "text": text}


def build_scenes():
    speak_code, speak_start = real_code("async def speak", 15)
    clip_code, clip_start = real_code("def make_clip", 16)
    t_compare = srt_time("Here's the same request")
    t_stat = srt_time("more than sixty percent")
    t_chat = srt_time("Paste this, and swap in")
    return [
        ("Claude Code made this video", None, [
            ({"type": "hero", "lines": [("MADE BY", WHITE), ("CLAUDE", RED_HOT), ("CODE", RED_HOT)], "sub": "Script · Voice · Visuals · Thumbnail", "nohost": True},
             "Stop paying for five AI video tools.", 0),
            ({"type": "collage", "items": [("v2_thumb", "THUMBNAIL"), ("banner", "BANNER"), ("v1_frame2", "SLIDES"), ("robot_prev", "LOGO")]},
             "Claude Code made this entire video on its own. The script, the voice, the visuals, the thumbnail. Even me.", 0.3),
            ({"type": "pair", "left": ("v1_frame", "VERSION 1", RED), "right": ("v1_thumb", "IT FAILED", RED)},
             "But first, you need to see why version one failed. That's where the real lesson is.", 0),
            ({"type": "card", "kicker": "EVERYTHING IS REAL", "text": "The real files. The real code. The real mistakes."},
             "Everything you'll see is real. The actual files, the actual code, and the actual mistakes.", 0),
        ]),
        ("Step 1: Find a real gap", 1, [
            (step(1, "Find a gap, not a trend"), "Step one. Find a gap, not a trend.", 0),
            (SEARCH, "Claude Code searched YouTube for: make YouTube video with Claude Code. The top result has over a million views.", 0.5),
            (dict(SEARCH, tags=True), "But look at what these videos rely on. Paid voice tools, paid video generators, your own footage, and a title promising seventy-seven thousand dollars a month.", 1.0),
            ({"type": "card", "kicker": "THE GAP", "text": "Nobody showed it with zero other paid tools."},
             "Nobody showed the version that uses zero other paid tools. So that became this video.", 0),
        ]),
        ("Step 2: Install skills safely", 2, [
            (step(2, "Install skills, safely"), "Step two. Give Claude Code new skills. But check them first.", 0),
            ({"type": "terminal", "lines": SECURITY[:6], "title": "Claude Code  ·  security review"},
             "I gave it a free, open-source YouTube skill pack from GitHub. Before installing anything, it read all twenty-four files.", 0.3),
            ({"type": "terminal", "lines": SECURITY, "title": "Claude Code  ·  security review"},
             "No network calls, no hidden instructions, nothing that runs on its own. Only then did it install eleven skills.", 0.3),
            ({"type": "warning", "head": "Read before you install", "text": "A skill is a set of instructions your AI will follow. Never install one nobody has read."},
             "That step matters. A skill is a set of instructions your AI will follow. Never install one that nobody has read.", 0),
        ]),
        ("Step 3: Version 1 failed", 3, [
            (step(3, "Version 1 failed"), "Step three. The first attempt.", 0),
            ({"type": "image", "src": "v1_frame", "label": "VERSION 1  ·  2:55"},
             "Version one was a two minute fifty-five video. One still slide per line, and generic advice.", 0),
            ({"type": "quote", "text": "ITS VERY VERY VERY BASIC", "who": "my actual feedback, word for word"},
             "My feedback was exactly this. It's very, very, very basic.", 0.5),
            ({"type": "card", "kicker": "THE LESSON", "text": "Without research and a standard, AI gives you the average."},
             "And that's the lesson. Without research and a clear standard, AI gives you the average of everything it has seen.", 0),
        ]),
        ("Step 4: Research, then score", 4, [
            (step(4, "Research, then score"), "Step four. Research first. Then score everything.", 0),
            ({"type": "steps", "heading": "What it actually checked", "steps": [
                "Anthropic's official prompting guide", "Columbia Journalism Review study: 1,600 queries",
                "Google's own NotebookLM help page", "Skipped: blog prices that contradicted each other"]},
             "So it researched properly. Official documentation, a Columbia University study, and Google's own help pages.", 0),
            ({"type": "steps", "highlight": 3, "heading": "What it actually checked", "steps": [
                "Anthropic's official prompting guide", "Columbia Journalism Review study: 1,600 queries",
                "Google's own NotebookLM help page", "Skipped: blog prices that contradicted each other"]},
             "And when blogs disagreed about prices and limits, it left those numbers out, instead of guessing.", 0),
            ({"type": "scores", "r1": [59, 53, 52, 48, 46, 43], "r2": [73, 72, 66, 63, 59], "highlight": 0},
             "Then it wrote opening hooks and scored them with a tool from the skill pack. The first round was weak. Forty-three to fifty-nine.", 0),
            ({"type": "scores", "r1": [59, 53, 52, 48, 46, 43], "r2": [73, 72, 66, 63, 59], "highlight": 1},
             "It rewrote them using the tool's feedback, and the winner hit seventy-three. Strong.", 0.5),
            ({"type": "terminal", "lines": TITLE_CHECK, "title": "Claude Code  ·  title.py"},
             "The title went through a second checker. One hundred out of one hundred.", 0.5),
        ]),
        ("Step 5: Build the video with code", 5, [
            (step(5, "Build it with code, not an editor"), "Step five. Build the video. With code, not an editor.", 0),
            ({"type": "code", "title": "build_video.py  ·  real code", "code": speak_code, "start": speak_start, "highlight": [6]},
             "Here's the actual code it wrote. Every line of the script becomes a natural voice through a free library called edge-tts.", 1.0),
            ({"type": "code", "title": "build_video.py  ·  real code", "code": clip_code, "start": clip_start, "highlight": [4, 5]},
             "Then Python draws each slide, and ffmpeg adds a slow camera push, the captions, and fades between chapters.", 1.0),
            ({"type": "terminal", "lines": real_log_lines(), "title": "Claude Code  ·  real build log", "size": 32},
             "Fifty-nine lines, rendered one by one. When the voice service dropped a request, it retried on its own. You can see it right here.", 1.0),
            ({"type": "clip", "label": "THE RESULT", "video": t_compare + 0.5},
             "And this is the result. Six and a half minutes, ten chapters, and every prompt on screen.", 0.5),
            ({"type": "clip", "label": "THE RESULT", "video": t_stat},
             "No editing timeline. No paid voice. No stock footage.", 0.5),
            ({"type": "clip", "label": "THE RESULT", "video": t_chat},
             "Just code that Claude Code wrote, tested, and fixed.", 0.5),
        ]),
        ("Step 6: Thumbnail and brand", 6, [
            (step(6, "Thumbnail and brand"), "Step six. The thumbnail, tested the way viewers actually see it.", 0),
            ({"type": "image", "src": "thumb_prev", "label": "EARLY ATTEMPT"},
             "This was an early thumbnail. It looks fine on a big screen.", 0),
            ({"type": "image", "src": "feed", "label": "TESTED AT REAL FEED SIZES"},
             "But YouTube shows thumbnails tiny. So it tested three designs at real feed sizes, all the way down to a hundred and twenty pixels wide.", 0.5),
            ({"type": "image", "src": "v2_thumb", "label": "WINNER", "color": (22, 140, 70)},
             "This one won. The red and green split still reads at the smallest size.", 0.3),
            ({"type": "pair", "left": ("profile_old", "REJECTED", RED), "right": ("robot_prev", "CHOSEN", (22, 140, 70))},
             "Same for the logo. My answer to the first three designs was: not at all. So it asked what I wanted, and made this robot. Which is me, talking to you right now.", 0.5),
            ({"type": "image", "src": "banner", "label": "BANNER  ·  SAFE-AREA CHECKED"},
             "Then the banner, checked against the safe area that phones, desktops and TVs each show.", 0.3),
        ]),
        ("The honest part", None, [
            ({"type": "card", "kicker": "THE HONEST PART", "text": "What it can't do, and what it costs."}, "Now, the honest part.", 0),
            ({"type": "steps", "heading": "What it can't do", "steps": [
                "No real camera footage: slides, real screenshots, real outputs", "The voice is good, but it isn't human",
                "You still fact-check and press upload yourself", "Claude Code itself needs a paid Claude plan"]},
             "It can't film anything real. The voice is good, but it isn't human. And you still check the facts and press upload yourself.", 0),
            ({"type": "steps", "highlight": 3, "heading": "What it can't do", "steps": [
                "No real camera footage: slides, real screenshots, real outputs", "The voice is good, but it isn't human",
                "You still fact-check and press upload yourself", "Claude Code itself needs a paid Claude plan"]},
             "And Claude Code itself needs a paid Claude plan. Everything else, the voice, Python, ffmpeg, the image tools, was free.", 0),
            ({"type": "stat", "big": "0", "line": "other paid tools", "color": GREEN, "source": "edge-tts  ·  Python  ·  Pillow  ·  ffmpeg  ·  all free"},
             "So the honest number is: zero other paid tools.", 0.5),
        ]),
        ("Copy the master prompt", None, [
            ({"type": "card", "kicker": "FREE", "text": "The master prompt is in the description.", "color": GREEN},
             "The master prompt to start this whole process is in the description. Paste it into Claude Code, and change it for your channel.", 0.5),
            ({"type": "card", "kicker": "NEXT ON THIS CHANNEL", "text": "Build a real AI agent in n8n, step by step."},
             "Next on this channel: we build a real AI agent in n8n, step by step.", 0),
            ({"type": "hero", "lines": [("SUBSCRIBE", WHITE), ("REAL AI.", RED_HOT), ("NO HYPE.", RED_HOT)], "nohost": True},
             "If you want to see that, subscribe. And tell me in the comments what you'd want Claude Code to make for you next.", 1.5),
        ]),
    ]


# ---------------------------------------------------------------- assembly

def make_clip(vis, cap, audio, hold, fade, out, host_txt=None, whoosh=None, video_at=None):
    dur = bv.duration(audio) + 0.35 + hold
    frames = int(dur * FPS) + 1
    args, n = [], 0

    def add(*a):
        nonlocal n
        args.extend(a)
        n += 1
        return n - 1

    if video_at is None:
        iv = add("-i", vis)
        fc = (f"[{iv}:v]scale=2880:-1,zoompan=z='1+0.03*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={W}x{H}:fps={FPS}[bg];")
    else:
        iv = add("-loop", "1", "-framerate", str(FPS), "-i", vis)
        im = add("-ss", f"{video_at:.2f}", "-t", f"{dur:.2f}", "-i", ASSETS["v2_video"])
        x0, y0, x1, y1 = CLIP_BOX
        fc = f"[{im}:v]scale={x1 - x0}:{y1 - y0},setpts=PTS-STARTPTS,fps={FPS}[cv];[{iv}:v][cv]overlay={x0}:{y0}[bg];"
    ic = add("-loop", "1", "-framerate", str(FPS), "-i", cap)
    fc += f"[bg][{ic}:v]overlay=0:0[c0];"
    last = "c0"
    if host_txt:
        ih = add("-f", "concat", "-safe", "0", "-i", host_txt)
        fc += f"[{ih}:v]fps={FPS},format=rgba[h];[{last}][h]overlay={HOST_X}:{HOST_Y}[c1];"
        last = "c1"
    fc += f"[{last}]" + ("fade=t=in:st=0:d=0.35," if fade else "") + "format=yuv420p[v];"
    ia = add("-i", audio)
    fc += f"[{ia}:a]apad=pad_dur={0.35 + hold}[a0];"
    if whoosh:
        iw = add("-i", whoosh)
        fc += f"[{iw}:a]volume=0.55[w];[a0][w]amix=inputs=2:duration=first:normalize=0[a]"
    else:
        fc += "[a0]anull[a]"
    bv.ff(*args, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out)


MASTER_PROMPT = """You are my YouTube producer. Make one complete, faceless video for my channel about [TOPIC], for [AUDIENCE].
1. Research: search YouTube for [TOPIC]. List the top results with views and age, and tell me the gap nobody covers.
2. Facts: only use official docs or primary studies. If sources disagree, leave the number out and tell me.
3. Script: 6-8 minutes, chapters, one idea per beat, every beat marked with what is ON SCREEN. Score 5 hooks and keep the best.
4. Title + thumbnail: write 10 titles, lint them, and test 3 thumbnail designs at real feed sizes before picking one.
5. Build: use only free tools (edge-tts voice, Python + Pillow for visuals, ffmpeg for video). Render 1080p with captions.
6. Deliver: the mp4, thumbnail, description with chapters, and an .srt captions file.
Check each step's output yourself before moving on, and tell me honestly what is weak."""


async def main(out, build):
    os.makedirs(out, exist_ok=True)
    os.makedirs(build, exist_ok=True)
    frames = make_host_frames(build)
    music, whoosh = os.path.join(build, "music.wav"), os.path.join(build, "whoosh.wav")
    make_music(music)
    make_whoosh(whoosh)
    scenes = build_scenes()
    lines = [(si, pill, v, text, hold, j == 0) for si, (_, pill, items) in enumerate(scenes)
             for j, (v, text, hold) in enumerate(items)]
    clips, t, chapters, srt = [], 0.0, [], []
    for i, (si, pill, v, text, hold, first) in enumerate(lines):
        base = os.path.join(build, f"{i:03d}")
        a, vis, cap, mp4, ht = base + ".mp3", base + "_v.png", base + "_c.png", base + ".mp4", base + "_host.txt"
        await bv.speak(text, a)
        host = not v.get("nohost")
        bv.render_visual(v, pill, vis)
        render_caption(text, pill, (i + 1) / len(lines), cap, host)
        dur = bv.duration(a) + 0.35 + hold
        if host:
            host_track(frames, a, dur, ht, i)
        # V2_ONLY=clip,image re-renders just those visual types and reuses every other clip already built
        only = os.environ.get("V2_ONLY")
        if not (only and os.path.exists(mp4) and v["type"] not in only.split(",")):
            make_clip(vis, cap, a, hold, first, mp4, ht if host else None,
                      whoosh if (first and i > 0) else None, v.get("video") if v["type"] == "clip" else None)
        if first:
            chapters.append((si, t))
        d = bv.duration(mp4)
        srt.append(f"{i + 1}\n{bv.ts(t, True)} --> {bv.ts(t + d - 0.3 - hold, True)}\n{text}\n")
        t += d
        clips.append(mp4)
        print(f"  [{i + 1:2d}/{len(lines)}] {d:5.2f}s  {text[:60]}", flush=True)
    lst = os.path.join(build, "list.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        fh.writelines(f"file '{c.replace(os.sep, '/')}'\n" for c in clips)
    joined = os.path.join(build, "joined.mp4")
    bv.ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined)
    total = bv.duration(joined)
    final = os.path.join(out, "claude-code-made-my-entire-video.mp4")
    bv.ff("-i", joined, "-stream_loop", "-1", "-i", music, "-filter_complex",
          f"[1:a]volume=0.11,afade=t=in:d=2,afade=t=out:st={total - 4:.2f}:d=4[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final)
    with open(os.path.join(out, "captions.srt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(srt))
    chap = "\n".join(f"{bv.ts(st)} {scenes[si][0]}" for si, st in chapters)
    with open(os.path.join(out, "description.txt"), "w", encoding="utf-8") as fh:
        fh.write("Claude Code made this entire video: research, script, voice, visuals, thumbnail, even the robot host. "
                 "No video editor and zero other paid tools. Here is every real step, including the version that failed.\n\n"
                 + chap + "\n\n---- THE MASTER PROMPT (copy into Claude Code) ----\n\n" + MASTER_PROMPT +
                 "\n\n---- WHAT IT USED (all free) ----\nedge-tts (voice)  ·  Python + Pillow (visuals)  ·  ffmpeg (video)\n"
                 "Skill pack: https://github.com/Jakeschincariol/youtube-agent-skill (MIT)\n"
                 "Honest note: Claude Code itself needs a paid Claude plan.\n\n"
                 "#claudecode #aiautomation #youtubeautomation\n")
    with open(os.path.join(out, "master-prompt.md"), "w", encoding="utf-8") as fh:
        fh.write("# Master prompt\n\n```\n" + MASTER_PROMPT + "\n```\n")
    print(f"\n  done: {final}  ({bv.ts(bv.duration(final))})\n\n{chap}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
