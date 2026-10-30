"""pro-video: render a finished 1080p YouTube video from one JSON spec.

    python render.py <spec.json> [--out DIR] [--build DIR] [--check] [--stills]

  --check   validate the spec and exit (no rendering)
  --stills  write one PNG per animated scene (fast visual check, no voice, no video)

Every line of the spec becomes: a voice line (edge-tts), a visual (motion graphics rendered frame by
frame, a real screen recording, a screenshot, or a presenter clip), burned-in captions, and the
optional robot corner host whose mouth follows the voice. Clips are cached by content hash, so after
an edit only the changed lines re-render. Writes the mp4, captions.srt, chapters.txt and, if the spec
has one, description.txt with real chapter timestamps.
"""
import asyncio, hashlib, json, math, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "engine"))
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402
import video3 as v3  # noqa: E402

v2, bv = v3.v2, v3.bv
W, H, FPS = v3.W, v3.H, v3.FPS
RED, RED_HOT, GREEN, AMBER, WHITE, MUTED, DIM = v3.RED, v3.RED_HOT, v3.GREEN, v3.AMBER, v3.WHITE, v3.MUTED, v3.DIM
BOLD, BLACK, MONO, REG = v3.BOLD, v3.BLACK, v3.MONO, v3.REG
prog, paste_anim, kinetic_lines = v3.prog, v3.paste_anim, v3.kinetic_lines

COLORS = {"white": WHITE, "red": RED, "hot": RED_HOT, "green": GREEN, "amber": AMBER, "muted": MUTED, "dim": DIM}


def col(c, default=WHITE):
    if c is None:
        return default
    if isinstance(c, (list, tuple)):
        return tuple(c)
    return COLORS.get(c, default)


# ---------------------------------------------------------------- extra scene types (on top of video3's)

def a_step(img, t, dur, v):
    d = ImageDraw.Draw(img)
    k = BLACK(140)
    label = f"STEP {v['n']}"
    w = d.textlength(label, font=k)
    x_target = (1700 - w - 160) / 2
    x = -w + (x_target + w) * prog(t, 0.05, 0.55)
    d.text((x, 150), label, font=k, fill=RED)
    pf = prog(t, 0.45, 0.4)
    if pf > 0 and v.get("of"):
        d.text((x_target + w + 20, 190), f"/ {v['of']}", font=BLACK(90), fill=tuple(int(c * pf) for c in DIM))
    bw = int(900 * prog(t, 0.3, 0.7))
    d.rounded_rectangle((400, 345, 400 + bw, 357), radius=6, fill=RED)
    kinetic_lines(img, t, [(v["text"], WHITE)], v.get("size", 100), 420, start=0.55)


def a_bars(img, t, dur, v):
    """Groups of score bars that grow and count up, one group after another."""
    d = ImageDraw.Draw(img)
    bv.center(d, 70, v["heading"], BOLD(60))
    groups = v["groups"]
    span = 1500 / len(groups)
    lo, hi = v.get("weak", 55), v.get("strong", 72)
    for c, g in enumerate(groups):
        x = 150 + c * span
        start = 0.3 + c * dur * 0.42
        hp = prog(t, start - 0.2, 0.4)
        if hp <= 0:
            continue
        d.text((x, 180), g["name"], font=BLACK(54), fill=tuple(int(cc * hp) for cc in col(g.get("color"), RED)))
        bw = int(span - 300)
        for i, s in enumerate(g["values"]):
            p = prog(t, start + i * 0.12, 0.8)
            if p <= 0:
                continue
            y = 270 + i * 88
            d.rounded_rectangle((x, y, x + bw, y + 62), radius=14, fill=(26, 26, 32))
            val = s * p
            cc = GREEN if s >= hi else AMBER if s >= lo else RED
            d.rounded_rectangle((x, y, x + max(28, int(bw * val / 100)), y + 62), radius=14, fill=cc)
            d.text((x + 18, y + 6), str(int(round(val))), font=BLACK(42), fill=WHITE)
            if p >= 0.98:
                d.text((x + bw + 20, y + 12), "STRONG" if s >= hi else "WORKABLE" if s >= lo else "WEAK", font=BOLD(32), fill=cc)


def a_grid(img, t, dur, v):
    """A map of tiles popping in one by one (e.g. every skill in a pack), with optional highlighted tiles."""
    d = ImageDraw.Draw(img)
    hp = prog(t, 0, 0.4)
    if hp > 0:
        bv.center(d, 60 - 20 * (1 - hp), v["heading"], BOLD(58), fill=tuple(int(c * hp) for c in WHITE))
    tiles = v["tiles"]
    cols = v.get("cols", 4)
    rows = math.ceil(len(tiles) / cols)
    x0, y0, x1, y1 = 120, 165, 1560, 900
    gx, gy = 22, 20
    tw, th = (x1 - x0 - gx * (cols - 1)) / cols, min(170, (y1 - y0 - gy * (rows - 1)) / rows)
    step = min(0.18, dur * 0.5 / max(1, len(tiles)))
    hl = set(v.get("highlight", []))
    for i, tile in enumerate(tiles):
        name, sub = (tile, "") if isinstance(tile, str) else (tile[0], tile[1])
        p = prog(t, 0.3 + i * step, 0.4)
        if p <= 0:
            continue
        r, c = divmod(i, cols)
        layer = Image.new("RGBA", (int(tw), int(th)), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        on = i in hl and t > 0.3 + len(tiles) * step + 0.3
        ld.rounded_rectangle((0, 0, tw - 1, th - 1), radius=22, fill=(60, 12, 20, 245) if on else (24, 24, 30, 240),
                             outline=RED_HOT if on else (62, 62, 72), width=4 if on else 2)
        ld.rectangle((0, 18, 7, th - 18), fill=RED if (on or not hl) else (70, 70, 80))
        ns = int(min(44, th * 0.3))
        while ns > 18 and ld.textlength(name, font=BLACK(ns)) > tw - 44:
            ns -= 2
        nf = BLACK(ns)
        ld.text((28, th * 0.18), name, font=nf, fill=WHITE)
        if sub:
            f, lines, lh = bv.fit(ld, sub, BOLD, tw - 50, th * 0.45, (30, 28, 26, 24, 22), gap=1.15)
            for j, ln in enumerate(lines):
                ld.text((28, th * 0.52 + j * lh), ln, font=f, fill=MUTED if not on else (255, 210, 210))
        paste_anim(img, layer, x0 + c * (tw + gx) + tw / 2, y0 + r * (th + gy) + th / 2, p, rise=30, scale_from=0.6)


def a_table(img, t, dur, v):
    """A comparison table: header, then rows sliding in. Cells are text, true (tick) or false (cross)."""
    d = ImageDraw.Draw(img)
    bv.center(d, 60, v["heading"], BOLD(58))
    cols = v["columns"]
    rows = v["rows"]
    x0, x1 = 140, 1560
    first = v.get("first_width", 560)
    cw = (x1 - x0 - first) / (len(cols) - 1)
    rh = min(110, 700 / (len(rows) + 1))
    y = 170
    hp = prog(t, 0.15, 0.4)
    for j, name in enumerate(cols):
        if not name or hp <= 0:
            continue
        cx = x0 + first + (j - 1) * cw + cw / 2 if j else x0 + 30
        good = j == v.get("ours", len(cols) - 1)
        f = BLACK(40)
        if good:
            d.rounded_rectangle((cx - cw / 2 + 10, y - 6, cx + cw / 2 - 10, y + rh * (len(rows) + 1) + 10), radius=24, fill=(48, 10, 16))
        d.text((cx - d.textlength(name, font=f) / 2 if j else cx, y + 14), name, font=f,
               fill=tuple(int(c * hp) for c in (RED_HOT if good else MUTED)))
    step = min(0.9, dur * 0.6 / max(1, len(rows)))
    for i, row in enumerate(rows):
        p = prog(t, 0.6 + i * step, 0.45)
        if p <= 0:
            continue
        ry = y + rh * (i + 1)
        layer = Image.new("RGBA", (x1 - x0, int(rh)), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.line([(0, 2), (x1 - x0, 2)], fill=(52, 52, 62), width=2)
        f, lines, lh = bv.fit(ld, row[0], BOLD, first - 50, rh - 16, (40, 36, 32, 28), gap=1.12)
        for k, ln in enumerate(lines):
            ld.text((30, rh / 2 - len(lines) * lh / 2 + k * lh), ln, font=f, fill=WHITE)
        for j, cell in enumerate(row[1:], start=1):
            cx = first + (j - 1) * cw + cw / 2
            s = rh * 0.42
            if cell is True:
                bv.check(ld, cx - s / 2, rh / 2 - s / 2, s, GREEN, 10)
            elif cell is False:
                bv.cross(ld, cx - s * 0.4, rh / 2 - s * 0.4, s * 0.8, (150, 60, 66), 9)
            else:
                good = j == v.get("ours", len(cols) - 1)
                cf, cl, clh = bv.fit(ld, str(cell), BOLD, cw - 40, rh - 16, (36, 32, 28, 24), gap=1.12)
                for k, ln in enumerate(cl):
                    ld.text((cx - ld.textlength(ln, font=cf) / 2, rh / 2 - len(cl) * clh / 2 + k * clh), ln, font=cf,
                            fill=GREEN if good else MUTED)
        layer.putalpha(layer.split()[3].point(lambda a: int(a * p)))
        img.alpha_composite(layer, (x0 + int(120 * (1 - p)), int(ry)))


def a_stat(img, t, dur, v):
    """One big number counting up, with a label and an optional source line."""
    p = prog(t, 0.15, min(1.6, dur * 0.5))
    val = v["value"]
    shown = val * p
    txt = v.get("prefix", "") + (f"{shown:,.{v.get('decimals', 0)}f}") + v.get("suffix", "")
    d = ImageDraw.Draw(img)
    f = BLACK(v.get("size", 230))
    c = col(v.get("color"), RED_HOT)
    d.text((840 - d.textlength(txt, font=f) / 2, 230), txt, font=f, fill=c)
    lp = prog(t, 0.5, 0.5)
    if lp > 0:
        bv.center(d, 560 + 20 * (1 - lp), v["label"], BOLD(64), fill=tuple(int(x * lp) for x in WHITE), maxw=1400)
    if v.get("source") and t > 1.0:
        bv.center(d, 800, v["source"], REG(30), fill=DIM, maxw=1400)


def a_compare(img, t, dur, v):
    """Before / after: two panels, items appear on the left, then on the right."""
    d = ImageDraw.Draw(img)
    bv.center(d, 60, v["heading"], BOLD(58))
    sides = ((v.get("left_title", "BEFORE"), v["left"], (150, 60, 66), 0.4),
             (v.get("right_title", "AFTER"), v["right"], GREEN, 0.4 + dur * 0.4))
    for s, (title, items, c, start) in enumerate(sides):
        x = 140 + s * 730
        p = prog(t, start - 0.2, 0.45)
        if p <= 0:
            continue
        layer = Image.new("RGBA", (690, 720), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle((0, 0, 689, 719), radius=30, fill=(22, 22, 28, 240), outline=c, width=4)
        ld.text((40, 26), title, font=BLACK(50), fill=c)
        for i, it in enumerate(items):
            ip = prog(t, start + 0.2 + i * 0.25, 0.3)
            if ip <= 0:
                continue
            y = 120 + i * 118
            if s:
                bv.check(ld, 40, y + 16, 40, GREEN, 9)
            else:
                bv.cross(ld, 44, y + 20, 32, c, 8)
            f, lines, lh = bv.fit(ld, it, BOLD, 560, 104, (40, 36, 32, 28), gap=1.12)
            for k, ln in enumerate(lines):
                ld.text((110, y + 8 + k * lh), ln, font=f, fill=tuple(int(x * ip) for x in WHITE))
        paste_anim(img, layer, x + 345, 160 + 360, p, rise=40, scale_from=0.94)


def a_terminal(img, t, dur, v):
    """A terminal window where lines appear one by one, like a command running."""
    p = prog(t, 0.0, 0.4)
    x0, y0, x1, y1 = 140, 90, 1560, 880
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    v2.window(d, (x0, y0, x1, y1), v.get("title", "Terminal"))
    lines = v["lines"]
    f = MONO(v.get("size", 36))
    lh = f.size * 1.35
    per = min(0.35, dur * 0.7 / max(1, len(lines)))
    shown = int(max(0, t - 0.4) / per) + 1
    vis = lines[:shown]
    maxl = int((y1 - y0 - 120) / lh)
    for i, ln in enumerate(vis[-maxl:]):
        c = GREEN if ln.startswith(("✓", "OK", "PASS", "done")) else RED_HOT if ln.startswith((">", "$")) else \
            AMBER if ln.startswith(("!", "WARN")) else (215, 215, 222)
        d.text((x0 + 50, y0 + 80 + i * lh), ln, font=f, fill=c)
    if p < 1:
        layer.putalpha(layer.split()[3].point(lambda a: int(a * p)))
    img.alpha_composite(layer)


_STILLS = {}


def a_image(img, t, dur, v):
    """A screenshot or picture in the footage frame, with a slow push-in and a label pill."""
    path = v["src"]
    if path not in _STILLS:
        x0, y0, x1, y1 = v3.BOX
        im = Image.open(path).convert("RGB")
        s = max((x1 - x0) / im.width, (y1 - y0) / im.height) if v.get("fill") else min((x1 - x0) / im.width, (y1 - y0) / im.height)
        _STILLS[path] = im.resize((int(im.width * s * 1.05), int(im.height * s * 1.05)), Image.LANCZOS)
    big = _STILLS[path]
    x0, y0, x1, y1 = v3.BOX
    bw, bh = x1 - x0, y1 - y0
    z = 1.0 + 0.05 * (t / max(dur, 0.1))  # starts on the whole image, ends 5 % closer
    cw, ch = int(big.width / z), int(big.height / z)
    ox, oy = (big.width - cw) // 2, (big.height - ch) // 2
    crop = big.crop((ox, oy, ox + cw, oy + ch))
    s = min(bw / crop.width, bh / crop.height)
    crop = crop.resize((int(crop.width * s), int(crop.height * s)), Image.BILINEAR)
    d = ImageDraw.Draw(img)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((x0 - 10, y0 - 10, x1 + 10, y1 + 10), radius=24, fill=(200, 20, 36, 110))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(28)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0 - 7, y0 - 7, x1 + 7, y1 + 7), radius=18, fill=(0, 0, 0), outline=RED, width=5)
    img.paste(crop, (x0 + (bw - crop.width) // 2, y0 + (bh - crop.height) // 2))
    if v.get("label"):
        f = BOLD(32)
        lw = d.textlength(v["label"], font=f) + 50
        d.rounded_rectangle((x0, y0 - 74, x0 + lw, y0 - 20), radius=27, fill=RED)
        d.text((x0 + 25, y0 - 68), v["label"], font=f, fill=WHITE)


_PRESENTER = {}


def a_host(img, t, dur, v):
    if "img" not in _PRESENTER:
        src = Image.open(v["photo"]).convert("RGB")
        _PRESENTER["img"] = src.resize((2112, 1188), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 50, 2))
    v3._HOST = _PRESENTER["img"]
    v3.a_host(img, t, dur, v)


ANIM = dict(v3.ANIM)
ANIM.update({"step": a_step, "bars": a_bars, "grid": a_grid, "table": a_table, "stat": a_stat, "compare": a_compare,
             "terminal": a_terminal, "image": a_image, "host": a_host})
v3.ANIM = ANIM  # render_anim looks the scene type up here

REQUIRED = {"kinetic": ["lines"], "step": ["n", "text"], "prompt": ["text"], "list": ["heading", "items"],
            "bars": ["heading", "groups"], "pipeline": ["heading", "nodes"], "thumbs": ["heading", "images"],
            "card": ["kicker", "text"], "host": ["name", "role"], "grid": ["heading", "tiles"],
            "table": ["heading", "columns", "rows"], "stat": ["value", "label"], "compare": ["heading", "left", "right"],
            "terminal": ["lines"], "image": ["src"], "footage": ["rec"], "hostclip": ["src", "segments"]}


# ---------------------------------------------------------------- spec handling

def normalise(v, spec):
    """Turn JSON-friendly values into what the renderers expect."""
    v = dict(v)
    if v["type"] == "kinetic":
        v["lines"] = [(l, WHITE) if isinstance(l, str) else (l[0], col(l[1])) for l in v["lines"]]
    if v["type"] == "list":
        v["items"] = [(i, True) if isinstance(i, str) else (i[0], bool(i[1])) for i in v["items"]]
    if v["type"] == "pipeline":
        v["nodes"] = [tuple(n) if not isinstance(n, str) else (n, "") for n in v["nodes"]]
    if v["type"] == "card":
        v["color"] = col(v.get("color"), RED)
    if v["type"] == "host":
        v.setdefault("photo", spec.get("presenter", {}).get("photo"))
        v["nohost"] = True
    if v["type"] == "hostclip":
        v["nohost"] = True
        v["segments"] = [tuple(s) for s in v["segments"]]
        v.setdefault("name", spec.get("presenter", {}).get("name", ""))
        v.setdefault("role", spec.get("presenter", {}).get("role", ""))
    return v


def probe(path):
    r = subprocess.run([bv.FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", r)
    return (int(m[1]), int(m[2])) if m else None


def check(spec, base):
    errs = []
    lines = [(c, l) for c in spec.get("chapters", []) for l in c.get("lines", [])]
    if not lines:
        errs.append("spec has no chapters/lines")
    for n, (c, l) in enumerate(lines, 1):
        v = l.get("visual", {})
        tp = v.get("type")
        if tp not in REQUIRED:
            errs.append(f"line {n}: unknown visual type {tp!r} (known: {', '.join(sorted(REQUIRED))})")
            continue
        for k in REQUIRED[tp]:
            if k not in v:
                errs.append(f"line {n} ({tp}): missing '{k}'")
        if tp != "hostclip" and not l.get("say", "").strip():
            errs.append(f"line {n}: empty 'say'")
        for k in ("src", "rec", "photo"):
            p = v.get(k) or (spec.get("presenter", {}).get("photo") if tp == "host" and k == "photo" else None)
            if p and not os.path.exists(resolve(p, base, spec)):
                errs.append(f"line {n}: file not found: {p}")
        for p in v.get("images", []):
            if not os.path.exists(resolve(p, base, spec)):
                errs.append(f"line {n}: file not found: {p}")
    return errs


def resolve(p, base, spec=None):
    if os.path.isabs(p):
        return p
    rec = (spec or {}).get("recordings")
    for root in ([os.path.join(base, rec)] if rec else []) + [base]:
        q = os.path.join(root, p)
        if os.path.exists(q):
            return q
    return os.path.join(base, p)


def key(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:70] or "video"


def stills(spec, base, out):
    os.makedirs(out, exist_ok=True)
    n = 0
    for c in spec["chapters"]:
        for l in c["lines"]:
            n += 1
            v = normalise(l["visual"], spec)
            for k in ("src", "photo"):
                if v.get(k):
                    v[k] = resolve(v[k], base, spec)
            if "images" in v:
                v["images"] = [resolve(p, base, spec) for p in v["images"]]
            if v["type"] not in ANIM:
                continue
            dur = l.get("est", 5.0)
            img = v3.bg_frame(dur * 0.8)
            ANIM[v["type"]](img, dur * 0.8, dur, v)
            p = os.path.join(out, f"still_{n:03d}_{v['type']}.png")
            img.convert("RGB").save(p)
            print("  ", p)


async def render(spec, base, out, build):
    os.makedirs(out, exist_ok=True)
    os.makedirs(build, exist_ok=True)
    bv.VOICE = spec.get("voice", bv.VOICE)
    bv.RATE = spec.get("rate", "+2%")
    robot = spec.get("host", "robot") == "robot"
    host_paths = v2.make_host_frames(build)
    if not robot:
        blank = os.path.join(build, "host_blank.png")
        Image.new("RGBA", (v2.HOST_S, v2.HOST_S), (0, 0, 0, 0)).save(blank)
        host_paths = {k: blank for k in host_paths}
    music, whoosh = os.path.join(build, "music.wav"), os.path.join(build, "whoosh.wav")
    v2.make_music(music)
    v2.make_whoosh(whoosh)
    chapters = spec["chapters"]
    pills = max([c.get("pill") or 0 for c in chapters] + [0])
    lines = [(ci, c.get("pill"), l, j == 0) for ci, c in enumerate(chapters) for j, l in enumerate(c["lines"])]
    clips, t, marks, srt = [], 0.0, [], []
    for i, (ci, pill, l, first) in enumerate(lines):
        v = normalise(l["visual"], spec)
        for k in ("src", "rec", "photo"):
            if v.get(k):
                v[k] = resolve(v[k], base, spec)
        if "images" in v:
            v["images"] = [resolve(p, base, spec) for p in v["images"]]
        text, hold = l.get("say", ""), l.get("hold", 0.3)
        show_host = robot and not v.get("nohost")
        k = key(v, text, hold, pill, i, len(lines), pills, robot, bv.VOICE, bv.RATE)
        base_ = os.path.join(build, f"{i:03d}_{k}")
        a = os.path.join(build, f"tts_{key(text, bv.VOICE, bv.RATE)}.mp3")
        cap, mp4 = base_ + "_c.png", base_ + ".mp4"
        if v["type"] == "hostclip":
            dur = bv.duration(v["src"]) + hold
            caps = []
            for n, (s0, s1, seg) in enumerate(v["segments"]):
                cp = f"{base_}_c{n}.png"
                v2.render_caption(seg, pill, (i + 1) / len(lines), cp, False, pills=pills)
                caps.append((s0, s1, cp))
            strip = base_ + "_strip.png"
            v3.name_strip(v["name"], v["role"], strip)
            if not os.path.exists(mp4):
                v3.render_hostclip(v, dur, caps, strip, mp4)
            for s0, s1, seg in v["segments"]:
                srt.append((t + s0, t + s1, seg))
        else:
            await bv.speak(text, a)
            dur = bv.duration(a) + 0.35 + hold
            v2.render_caption(text, pill, (i + 1) / len(lines), cap, show_host, pills=pills)
            w = whoosh if (first and i > 0) else None
            if not os.path.exists(mp4):
                tmp = mp4 + ".part.mp4"
                if v["type"] == "footage":
                    size = probe(v["rec"])
                    v.setdefault("crop", (size[0], size[1], 0, 0))
                    v.setdefault("start", 0.0)
                    v.setdefault("len", bv.duration(v["rec"]) - v["start"])
                    ht, fr = base_ + "_host.txt", base_ + "_frame.png"
                    v2.host_track(host_paths, a, dur, ht, i)
                    v3.footage_frame(v.get("label", "REAL FOOTAGE"), fr)
                    v3.render_footage(v, dur, a, cap, ht, fr, tmp, w, "")
                else:
                    v["nohost"] = not show_host
                    v3.render_anim(v, dur, a, cap, host_paths, tmp, w, i)
                os.replace(tmp, mp4)
            srt.append((t, t + bv.duration(a), text))
        if first:
            marks.append((ci, t))
        d = bv.duration(mp4)
        t += d
        clips.append(mp4)
        print(f"  [{i + 1:2d}/{len(lines)}] {d:5.2f}s  {v['type']:<9} {text[:56]}", flush=True)
    lst = os.path.join(build, "list.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        fh.writelines(f"file '{c.replace(os.sep, '/')}'\n" for c in clips)
    joined = os.path.join(build, "joined.mp4")
    bv.ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined)
    total = bv.duration(joined)
    final = os.path.join(out, spec.get("file", slug(spec.get("title", "video")) + ".mp4"))
    vol = spec.get("music_volume", 0.11)
    if vol > 0:
        bv.ff("-i", joined, "-stream_loop", "-1", "-i", music, "-filter_complex",
              f"[1:a]volume={vol},afade=t=in:d=2,afade=t=out:st={max(0, total - 4):.2f}:d=4[m];"
              f"[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
              "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final)
    else:
        bv.ff("-i", joined, "-c", "copy", "-movflags", "+faststart", final)
    with open(os.path.join(out, "captions.srt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(f"{n}\n{bv.ts(a, True)} --> {bv.ts(b, True)}\n{x}\n" for n, (a, b, x) in enumerate(srt, 1)))
    chap = "\n".join(f"{bv.ts(st)} {chapters[ci]['title']}" for ci, st in marks)
    with open(os.path.join(out, "chapters.txt"), "w", encoding="utf-8") as fh:
        fh.write(chap + "\n")
    if spec.get("description"):
        with open(os.path.join(out, "description.txt"), "w", encoding="utf-8") as fh:
            fh.write(spec["description"].replace("{chapters}", chap) + "\n")
    print(f"\n  done: {final}  ({bv.ts(bv.duration(final))}, {len(lines)} lines)\n\n{chap}")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    spec_path = os.path.abspath(args[0])
    base = os.path.dirname(spec_path)
    with open(spec_path, encoding="utf-8-sig") as fh:  # tolerate the BOM Windows editors add
        spec = json.load(fh)
    opt = lambda name, default: args[args.index(name) + 1] if name in args else default
    out = os.path.abspath(opt("--out", os.path.join(base, "output")))
    build = os.path.abspath(opt("--build", os.path.join(os.environ.get("TEMP", base), "pro-video-build", slug(spec.get("title", "video")))))
    errs = check(spec, base)
    if errs:
        print("Spec problems:\n  " + "\n  ".join(errs))
        sys.exit(1)
    if "--check" in args:
        n = sum(len(c["lines"]) for c in spec["chapters"])
        words = sum(len(l.get("say", "").split()) for c in spec["chapters"] for l in c["lines"])
        print(f"spec OK: {len(spec['chapters'])} chapters, {n} lines, {words} words, about {words / 2.6 / 60:.1f} min of voice")
        return
    if "--stills" in args:
        stills(spec, base, os.path.join(out, "stills"))
        return
    asyncio.run(render(spec, base, out, build))


if __name__ == "__main__":
    main()
