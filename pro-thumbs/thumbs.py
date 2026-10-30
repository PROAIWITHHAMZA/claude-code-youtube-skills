"""pro-thumbs: design three thumbnail layouts, test them at real YouTube feed sizes, pick the winner.

    python thumbs.py <spec.json> [--out DIR]

spec.json:
  {"headline": ["ZERO", "EDITING"],      1-3 short lines, 4 words max in total is best
   "image": "face.jpg",                  optional subject photo (a face reading an emotion works best)
   "badge": "FREE",                      optional small label
   "accent": [239, 35, 50],              optional brand colour
   "focus": 0.5}                         optional: horizontal centre of the subject in the photo, 0..1

Writes thumb_A.png, thumb_B.png, thumb_C.png (1280x720), feed_test.png (every variant at 360, 168 and
120 px wide on dark and light feeds, with its score) and winner.png. Prints the score breakdown.

The score is measured, not guessed:
  text   35  headline letter height in pixels at 168 px wide (the suggested-videos size beside the player); 12 px+ is full marks
  contrast 25  WCAG contrast ratio between the headline colour and the pixels behind it; 7:1+ is full marks
  words  20  fewer words read faster; 3 or fewer is full marks
  subject 20 share of the frame taken by the subject photo; 30%+ is full marks
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

W, H = 1280, 720
WHITE, INK = (255, 255, 255), (8, 8, 11)


def font(names, size):
    for n in names:
        for root in ("C:/Windows/Fonts/", "/System/Library/Fonts/Supplemental/", "/usr/share/fonts/truetype/dejavu/", ""):
            try:
                return ImageFont.truetype(root + n, size)
            except OSError:
                pass
    return ImageFont.load_default()


HEAVY = lambda s: font(("seguibl.ttf", "ariblk.ttf", "Arial Black.ttf", "DejaVuSans-Bold.ttf"), s)
BOLD = lambda s: font(("segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"), s)


def fit_lines(lines, maxw, maxh, top=200):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for s in range(top, 30, -4):
        f = HEAVY(s)
        if max(d.textlength(l, font=f) for l in lines) <= maxw and len(lines) * s * 1.02 <= maxh:
            return f
    return HEAVY(30)


def stack(lines, limit=9):
    """Re-break the headline into short lines (a narrow text column reads bigger with fewer letters per line)."""
    if all(len(l) <= limit for l in lines):  # the given breaks already fit: keep them
        return list(lines)
    words = " ".join(lines).split()
    limit = max(limit, max(len(w) for w in words))
    out, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > limit:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return out + [cur]


def cover(src, w, h, focus=0.5):
    s = max(w / src.width, h / src.height)
    im = src.resize((int(src.width * s + 1), int(src.height * s + 1)), Image.LANCZOS)
    x = int(max(0, min(im.width - w, im.width * focus - w / 2)))
    return im.crop((x, (im.height - h) // 2, x + w, (im.height - h) // 2 + h))


def glow_bg(accent):
    img = Image.new("RGBA", (W, H), INK + (255,))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((-200, 200, 700, 1000), fill=accent + (130,))
    ImageDraw.Draw(layer).ellipse((900, -300, 1600, 400), fill=accent + (60,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(140)))
    return img


def draw_lines(img, lines, f, x, y, fill, stroke=0, colors=None, align="left", box_w=None, hide=False):
    d = ImageDraw.Draw(img)
    asc, desc = f.getmetrics()
    boxes = []
    for i, l in enumerate(lines):
        lw = d.textlength(l, font=f)
        lx = x if align == "left" else x + (box_w - lw) / 2
        ly = y + i * f.size * 1.02
        c = (colors[i] if colors else fill)
        if not hide:  # hide: measure only, so the scorer can sample the background behind the text
            d.text((lx, ly + asc), l, font=f, fill=c, anchor="ls", stroke_width=stroke, stroke_fill=INK)
        boxes.append((int(lx), int(ly + asc * 0.25), int(lx + lw), int(ly + asc)))
    return boxes


def badge(img, text, accent):
    if not text:
        return
    d = ImageDraw.Draw(img)
    f = BOLD(46)
    w = d.textlength(text, font=f) + 56
    d.rounded_rectangle((W - w - 36, 34, W - 36, 110), radius=20, fill=WHITE)
    d.text((W - w - 36 + 28, 40), text, font=f, fill=accent)


def layout_a(spec, src, accent):
    """Subject right, fading into a dark left side that carries the headline."""
    img = glow_bg(accent)
    area = 0.0
    if src:
        ph = cover(src, 780, H, spec.get("focus", 0.5)).convert("RGBA")
        fade = Image.new("L", ph.size, 255)
        fd = ImageDraw.Draw(fade)
        for x in range(240):
            fd.line([(x, 0), (x, H)], fill=int(255 * x / 240))
        ph.putalpha(fade)
        img.alpha_composite(ph, (W - 780, 0))
        area = 680 / W
    lines = stack(spec["headline"]) if src else spec["headline"]
    f = fit_lines(lines, 600 if src else 1100, 560)
    y = (H - len(lines) * f.size * 1.02) / 2
    cols = [WHITE] * (len(lines) - 1) + [accent if len(lines) > 1 else WHITE]
    boxes = draw_lines(img, lines, f, 50, y, WHITE, stroke=6, colors=cols, hide=spec.get("_bare"))
    badge(img, spec.get("badge"), accent)
    return img, f.size, cols, boxes, area


def layout_b(spec, src, accent):
    """Full-bleed subject, darkened at the bottom, headline across the lower third on an accent bar."""
    img = glow_bg(accent)
    area = 0.0
    if src:
        ph = cover(src, W, H, spec.get("focus", 0.5)).convert("RGBA")
        img.alpha_composite(ph)
        shade = Image.new("L", (W, H), 0)
        sd = ImageDraw.Draw(shade)
        for y in range(H // 3, H):
            sd.line([(0, y), (W, y)], fill=int(215 * (y - H / 3) / (H * 2 / 3)))
        black = Image.new("RGBA", (W, H), INK + (0,))
        black.putalpha(shade)
        img.alpha_composite(black)
        area = 0.55
    lines = [" ".join(spec["headline"])] if len(" ".join(spec["headline"])) <= 16 else spec["headline"]
    f = fit_lines(lines, 1180, 300)
    h = len(lines) * f.size * 1.02
    y = H - h - 50
    d = ImageDraw.Draw(img)
    d.rectangle((0, y - 18, W, H), fill=accent + (235,))
    boxes = draw_lines(img, lines, f, 0, y - 6, WHITE, stroke=0, align="center", box_w=W, hide=spec.get("_bare"))
    badge(img, spec.get("badge"), accent)
    return img, f.size, [WHITE] * len(lines), boxes, area


def layout_c(spec, src, accent):
    """Split frame: accent panel with dark headline on the left, subject on the right."""
    img = glow_bg(accent)
    area = 0.0
    if src:
        ph = cover(src, 660, H, spec.get("focus", 0.5)).convert("RGBA")
        img.alpha_composite(ph, (W - 660, 0))
        area = 660 / W
    pw = 660 if src else W
    panel = Image.new("RGBA", (pw + 60, H), accent + (255,))
    mask = Image.new("L", panel.size, 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (pw + 60, 0), (pw - 10, H), (0, H)], fill=255)
    img.paste(panel, (0, 0), mask)
    lines = stack(spec["headline"]) if src else spec["headline"]
    f = fit_lines(lines, pw - 110, 600)
    y = (H - len(lines) * f.size * 1.02) / 2
    boxes = draw_lines(img, lines, f, 50, y, INK, colors=[INK] * len(lines), hide=spec.get("_bare"))
    if spec.get("badge"):
        d = ImageDraw.Draw(img)
        bf = BOLD(46)
        w = d.textlength(spec["badge"], font=bf) + 56
        d.rounded_rectangle((50, 40, 50 + w, 116), radius=20, fill=INK)
        d.text((78, 46), spec["badge"], font=bf, fill=WHITE)
    return img, f.size, [INK] * len(lines), boxes, area


def lum(c):
    ch = [x / 255 for x in c[:3]]
    ch = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def score(img, size, colors, boxes, area, words, bg_only):
    cap_px = size * 0.72 * 168 / W  # letter height of the headline at suggested-videos width
    text = 35 * max(0.0, min(1.0, (cap_px - 4) / 8))
    ratios = []
    for (x0, y0, x1, y1), c in zip(boxes, colors):
        # sample the background *behind* the text, from the frame drawn without the headline
        region = bg_only.crop((max(0, x0), max(0, y0), min(W, x1), min(H, y1))).convert("RGB")
        avg = tuple(int(v) for v in ImageStat.Stat(region).mean) if region.width and region.height else INK
        ratios.append(contrast(c, avg))
    cr = min(ratios) if ratios else 1
    con = 25 * max(0.0, min(1.0, (cr - 1.5) / 5.5))
    w = 20 if words <= 3 else 15 if words == 4 else 8 if words == 5 else 0
    sub = 20 * min(1.0, area / 0.3) if area else 10
    return {"total": round(text + con + w + sub), "text": round(text), "contrast": round(con), "words": w,
            "subject": round(sub), "letter_px_at_168": round(cap_px, 1), "contrast_ratio": round(cr, 1)}


def feed_sheet(variants, scores, winner, path):
    sheet = Image.new("RGB", (1500, 300 * len(variants) + 60), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.rectangle((0, 0, 750, sheet.height), fill=(15, 15, 15))
    d.text((20, 14), "DARK FEED", font=BOLD(26), fill=(200, 200, 200))
    d.text((770, 14), "LIGHT FEED", font=BOLD(26), fill=(60, 60, 60))
    for i, (name, img) in enumerate(variants):
        y = 60 + i * 300
        rgb = img.convert("RGB")
        for half, x0 in ((0, 20), (1, 770)):
            x = x0
            for w in (360, 168, 120):
                h = w * 9 // 16
                sheet.paste(rgb.resize((w, h), Image.LANCZOS), (x, y))
                x += w + 18
            s = scores[name]
            col = (34, 160, 80) if name == winner else ((200, 200, 200) if half == 0 else (60, 60, 60))
            d.text((x0, y + 214), f"{name}  {s['total']}/100" + ("   WINNER" if name == winner else ""), font=BOLD(30), fill=col)
            d.text((x0, y + 252), f"text {s['text']}  contrast {s['contrast']}  words {s['words']}  subject {s['subject']}",
                   font=BOLD(20), fill=(150, 150, 150) if half == 0 else (110, 110, 110))
    sheet.save(path)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    spec_path = os.path.abspath(sys.argv[1])
    with open(spec_path, encoding="utf-8-sig") as fh:
        spec = json.load(fh)
    base = os.path.dirname(spec_path)
    out = os.path.abspath(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else os.path.join(base, "thumbs")
    os.makedirs(out, exist_ok=True)
    accent = tuple(spec.get("accent", (239, 35, 50)))
    src = None
    if spec.get("image"):
        p = spec["image"] if os.path.isabs(spec["image"]) else os.path.join(base, spec["image"])
        src = Image.open(p).convert("RGB")
    words = len(" ".join(spec["headline"]).split())
    variants, scores = [], {}
    for name, fn in (("A", layout_a), ("B", layout_b), ("C", layout_c)):
        img, size, colors, boxes, area = fn(spec, src, accent)
        bare = fn(dict(spec, _bare=True), src, accent)[0]  # same frame, headline not drawn
        scores[name] = score(img, size, colors, boxes, area, words, bare)
        img.convert("RGB").save(os.path.join(out, f"thumb_{name}.png"))
        variants.append((name, img))
    winner = max(scores, key=lambda k: scores[k]["total"])
    dict(variants)[winner].convert("RGB").save(os.path.join(out, "winner.png"))
    feed_sheet(variants, scores, winner, os.path.join(out, "feed_test.png"))
    for k, s in scores.items():
        print(f"  {k}: {s['total']:3d}/100   letters {s['letter_px_at_168']} px at 168 wide, contrast {s['contrast_ratio']}:1"
              f"{'   <- winner' if k == winner else ''}")
    if words > 4:
        print(f"  note: {words} words in the headline. Thumbnails read best at 4 or fewer.")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
