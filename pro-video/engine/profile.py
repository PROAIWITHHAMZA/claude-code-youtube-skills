"""Channel profile picture concepts, 800x800, in the thumbnail palette.

    python profile.py <output_dir>

YouTube crops the avatar to a circle and shows it as small as ~24px, so each concept is one bold
shape inside the central circle, and preview.png shows them cropped at real display sizes.
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 800
F = "C:/Windows/Fonts/"
PURPLE, PURPLE_DK, GREEN, YELLOW, WHITE, INK = (124, 92, 255), (36, 24, 92), (34, 197, 94), (250, 204, 21), (255, 255, 255), (10, 12, 26)


def radial(inner, outer):
    img = Image.new("RGBA", (S, S), outer + (255,))
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((80, 40, 720, 680), fill=inner + (255,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(170)))
    return img


def sparkle(d, cx, cy, r, color):
    k = r * 0.28
    d.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k),
               (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)], fill=color)


def check(d, cx, cy, s, color, w):
    d.line([(cx - s * 0.5, cy), (cx - s * 0.12, cy + s * 0.38), (cx + s * 0.55, cy - s * 0.38)],
           fill=color, width=w, joint="curve")
    for x, y in ((cx - s * 0.5, cy), (cx + s * 0.55, cy - s * 0.38)):
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=color)


# A: a chat bubble with a green check: "prompts that work"
def concept_a():
    img = radial((150, 110, 255), (40, 22, 110))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((170, 210, 630, 540), radius=90, fill=WHITE)
    d.polygon([(260, 520), (240, 640), (360, 535)], fill=WHITE)
    check(d, 400, 380, 190, GREEN, 46)
    sparkle(d, 610, 200, 70, YELLOW)
    return img


# B: "AI" monogram inside a purple-to-green ring
def concept_b():
    img = Image.new("RGBA", (S, S), INK + (255,))
    d = ImageDraw.Draw(img)
    steps = 180
    for i in range(steps):
        t = i / steps
        col = tuple(int(PURPLE[j] + (GREEN[j] - PURPLE[j]) * t) for j in range(3))
        d.arc((90, 90, 710, 710), -90 + 360 * t, -90 + 360 * (t + 1 / steps) + 1, fill=col, width=46)
    f = ImageFont.truetype(F + "seguibl.ttf", 330)
    w = d.textlength("AI", font=f)
    d.text(((S - w) / 2, 175), "AI", font=f, fill=WHITE)
    sparkle(d, 560, 250, 52, YELLOW)
    return img


# C: three connected nodes: prompts today, agents and automations tomorrow
def concept_c():
    img = radial((60, 40, 150), INK)
    d = ImageDraw.Draw(img)
    pts = [(400, 220), (240, 520), (560, 520)]
    for a in range(3):
        for b in range(a + 1, 3):
            d.line([pts[a], pts[b]], fill=(200, 190, 255), width=26)
    for (x, y), col, r in zip(pts, (PURPLE, GREEN, YELLOW), (100, 82, 82)):
        d.ellipse((x - r - 12, y - r - 12, x + r + 12, y + r + 12), fill=INK)
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    sparkle(d, 400, 220, 58, WHITE)
    return img


def circle(im, size):
    im = im.convert("RGB").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask.resize((size, size), Image.LANCZOS))
    return out


def main(out):
    os.makedirs(out, exist_ok=True)
    imgs = {"A": concept_a(), "B": concept_b(), "C": concept_c()}
    for k, im in imgs.items():
        im.convert("RGB").save(os.path.join(out, f"profile_{k}.png"))
    sizes = (176, 98, 48, 32, 24)
    sheet = Image.new("RGBA", (1000, 3 * 210 + 20), (255, 255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.rectangle((500, 0, 1000, sheet.height), fill=(15, 15, 15, 255))  # light and dark mode
    lab = ImageFont.truetype(F + "seguibl.ttf", 48)
    for i, (k, im) in enumerate(imgs.items()):
        y = 20 + i * 210
        for half, x0 in ((0, 10), (1, 510)):
            d.text((x0, y + 60), k, font=lab, fill=(20, 20, 20) if half == 0 else WHITE)
            x = x0 + 50
            for s in sizes:
                sheet.alpha_composite(circle(im, s), (x, y + (176 - s) // 2))
                x += s + 14
    sheet.convert("RGB").save(os.path.join(out, "preview.png"))


if __name__ == "__main__":
    main(sys.argv[1])
