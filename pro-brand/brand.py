"""pro-brand: channel profile picture and banner, checked against YouTube's real crop areas.

    python brand.py profile <photo> [--box x,y,size] [--ring 239,35,50] [--out DIR]
    python brand.py banner --title "Make AI work for you." [--sub "New video every Tuesday"] [--image art.png]
                           [--accent 239,35,50] [--out DIR]
    python brand.py check <banner.png> [--out DIR]

profile  square crop (default: centred on the upper middle, where faces are) to 800x800 with an optional brand
         ring, plus a preview sheet at the real circle sizes YouTube shows (176 down to 24 px), light and dark.
banner   2560x1440 banner with everything important inside the 1546x423 area every device shows.
check    marks the device crop areas on any banner and measures how much detail sits outside the safe area
         (text or a logo there gets cut off on phones).

Banner areas (YouTube's template):
  TV 2560x1440 (full) · desktop 2560x423 · tablet 1855x423 · mobile and safe area 1546x423 (all centred)
"""
import os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

SAFE = (1546, 423)
AREAS = [("TV (full)", (2560, 1440)), ("desktop", (2560, 423)), ("tablet", (1855, 423)), ("SAFE: all devices", SAFE)]


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


def rgb(s, default):
    return tuple(int(x) for x in s.split(",")) if s else default


def circle(img, size):
    im = img.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    im.putalpha(mask.resize((size, size), Image.LANCZOS))
    return im


def profile(photo, box, ring, out):
    src = Image.open(photo).convert("RGB")
    if box:
        x, y, s = box
    else:
        s = min(src.width, src.height)
        x, y = (src.width - s) // 2, max(0, int((src.height - s) * 0.2))
    img = src.crop((x, y, x + s, y + s)).resize((800, 800), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 50, 2)).convert("RGBA")
    if ring:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse((10, 10, 790, 790), outline=ring + (255,), width=24)
        img.alpha_composite(layer)
    img.convert("RGB").save(os.path.join(out, "profile.png"))
    sheet = Image.new("RGBA", (1180, 220), (255, 255, 255, 255))
    ImageDraw.Draw(sheet).rectangle((590, 0, 1180, 220), fill=(15, 15, 15, 255))
    for x0 in (20, 610):
        x = x0
        for size in (176, 98, 48, 32, 24):
            sheet.alpha_composite(circle(img, size), (x, 22 + (176 - size) // 2))
            x += size + 14
    sheet.convert("RGB").save(os.path.join(out, "profile_preview.png"))
    print(f"  wrote profile.png (800x800) and profile_preview.png in {out}")
    print("  check the preview: is the face still recognisable at 32 and 24 px? If not, crop tighter (--box).")


def banner(title, sub, image, accent, out):
    W, H = 2560, 1440
    img = Image.new("RGBA", (W, H), (8, 8, 11, 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((200, 300, 1300, 1150), fill=accent + (110,))
    gd.ellipse((1500, 400, 2500, 1100), fill=accent + (70,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(220)))
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(0, W, 80):
        gd.line([(x, 0), (x, H)], fill=(255, 255, 255, 10), width=2)
    for y in range(0, H, 80):
        gd.line([(0, y), (W, y)], fill=(255, 255, 255, 10), width=2)
    img.alpha_composite(grid)
    sx, sy = (W - SAFE[0]) // 2, (H - SAFE[1]) // 2
    text_x, text_w = sx + 40, SAFE[0] - 80
    if image:
        art = Image.open(image).convert("RGBA")
        s = (SAFE[1] - 40) / art.height
        art = art.resize((int(art.width * s), int(art.height * s)), Image.LANCZOS)
        img.alpha_composite(art, (sx + 20, sy + 20))
        text_x = sx + 20 + art.width + 50
        text_w = sx + SAFE[0] - 40 - text_x
    d = ImageDraw.Draw(img)
    size = 150
    while size > 40 and d.textlength(title, font=HEAVY(size)) > text_w:
        size -= 4
    f = HEAVY(size)
    sub_f = BOLD(max(36, int(size * 0.36)))
    block = size * 1.15 + (sub_f.size * 1.6 if sub else 0)
    ty = sy + (SAFE[1] - block) / 2
    d.text((text_x, ty), title, font=f, fill=(255, 255, 255))
    d.rectangle((text_x, ty + size * 1.15, text_x + min(text_w, d.textlength(title, font=f)) * 0.3, ty + size * 1.15 + 10), fill=accent)
    if sub:
        d.text((text_x, ty + size * 1.15 + 30), sub, font=sub_f, fill=(190, 190, 200))
    path = os.path.join(out, "banner.png")
    img.convert("RGB").save(path)
    print(f"  wrote {path} (2560x1440)")
    check(path, out)


def check(path, out):
    img = Image.open(path).convert("RGB")
    if img.size != (2560, 1440):
        print(f"  warn: banner is {img.size[0]}x{img.size[1]}; YouTube wants 2560x1440 (at least 2048x1152, under 6 MB)")
        img = img.resize((2560, 1440), Image.LANCZOS)
    W, H = img.size
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    sx, sy = (W - SAFE[0]) // 2, (H - SAFE[1]) // 2
    band = edges.crop((0, sy, W, sy + SAFE[1]))  # the desktop strip; detail outside the safe box here gets cut on phones
    inside = ImageStat.Stat(edges.crop((sx, sy, sx + SAFE[0], sy + SAFE[1]))).sum[0]
    total = ImageStat.Stat(band).sum[0] or 1
    outside = 1 - inside / total
    vis = img.copy().convert("RGBA")
    layer = Image.new("RGBA", vis.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle((0, 0, W, sy), fill=(0, 0, 0, 120))
    d.rectangle((0, sy + SAFE[1], W, H), fill=(0, 0, 0, 120))
    colors = [(120, 120, 130), (80, 160, 255), (255, 180, 0), (34, 197, 94)]
    for (name, (w, h)), c in zip(AREAS, colors):
        x0, y0 = (W - w) // 2, (H - h) // 2
        d.rectangle((x0 + 3, y0 + 3, x0 + w - 3, y0 + h - 3), outline=c + (255,), width=6)
        d.text((x0 + 16, y0 + 10), name, font=BOLD(40), fill=c + (255,))
    vis.alpha_composite(layer)
    p = os.path.join(out, os.path.splitext(os.path.basename(path))[0] + "_areas.png")
    vis.convert("RGB").save(p)
    print(f"  {100 * outside:.0f}% of the visible strip's detail is outside the safe area" +
          ("  <- text or logos there get cut on phones; move them into the green box" if outside > 0.25 else "  (ok)"))
    print(f"  areas overlay: {p}")
    kb = os.path.getsize(path) / 1024
    print(f"  file size {kb / 1024:.1f} MB" + ("  <- over YouTube's 6 MB limit; save as JPG" if kb > 6 * 1024 else ""))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    out = os.path.abspath(opt("--out") or ".")
    os.makedirs(out, exist_ok=True)
    if a[0] == "profile":
        box = tuple(int(x) for x in opt("--box").split(",")) if opt("--box") else None
        profile(a[1], box, rgb(opt("--ring"), None) if opt("--ring") else None, out)
    elif a[0] == "banner":
        banner(opt("--title") or "Your channel", opt("--sub"), opt("--image"), rgb(opt("--accent"), (239, 35, 50)), out)
    elif a[0] == "check":
        check(a[1], out)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
