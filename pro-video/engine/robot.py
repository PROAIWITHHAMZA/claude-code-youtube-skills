"""Robot mascot profile pictures, red + black, three expressions.

    python robot.py <output_dir>

Drawn at 3x and downsampled for smooth edges. Writes robot_A/B/C.png (800x800) and preview.png
with each cropped to a circle at real YouTube sizes on light and dark backgrounds.
"""
import os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from profile import circle

OUT_S, K = 800, 3
S = OUT_S * K
RED, RED_HOT, RED_DK = (239, 35, 50), (255, 90, 90), (120, 10, 20)
BLACK = (6, 6, 9)


def sc(*v):
    return tuple(int(x * K) for x in v)


def vgrad(size, top, bottom):
    w, h = size
    g = Image.new("RGBA", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,))
    return g.resize((w, h))


def glow_layer(draw_fn, blur):
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def base():
    img = Image.new("RGBA", (S, S), BLACK + (255,))
    img.alpha_composite(glow_layer(lambda d: d.ellipse(sc(40, 40, 760, 760), fill=(150, 14, 28, 255)), 110 * K))
    # antenna
    d = ImageDraw.Draw(img)
    d.line([sc(400, 175), sc(400, 120)], fill=(70, 70, 80), width=14 * K)
    img.alpha_composite(glow_layer(lambda g: g.ellipse(sc(368, 74, 432, 138), fill=RED + (255,)), 18 * K))
    d = ImageDraw.Draw(img)
    d.ellipse(sc(374, 80, 426, 132), fill=RED, outline=BLACK, width=4 * K)
    d.ellipse(sc(386, 90, 402, 106), fill=(255, 190, 190))
    # ears
    for x0 in (128, 622):
        d.rounded_rectangle(sc(x0, 330, x0 + 50, 470), radius=18 * K, fill=RED, outline=BLACK, width=6 * K)
    # head with gradient, red rim and a soft top highlight
    box = sc(160, 170, 640, 620)
    head = vgrad((box[2] - box[0], box[3] - box[1]), (70, 70, 80), (24, 24, 30))
    mask = Image.new("L", head.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, head.size[0] - 1, head.size[1] - 1), radius=120 * K, fill=255)
    img.paste(head, box[:2], mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=120 * K, outline=RED, width=12 * K)
    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse(sc(210, 190, 470, 290), fill=(255, 255, 255, 40))
    img.alpha_composite(hl.filter(ImageFilter.GaussianBlur(14 * K)))
    # visor
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(sc(205, 285, 595, 545), radius=80 * K, fill=BLACK, outline=(40, 40, 48), width=6 * K)
    return img


def eyes(img, shapes):
    """shapes: callables drawing on a Draw; drawn once blurred for glow, once crisp."""
    def all_(d):
        for f in shapes:
            f(d)
    img.alpha_composite(glow_layer(all_, 16 * K))
    img.alpha_composite(glow_layer(all_, 5 * K))
    all_(ImageDraw.Draw(img))


def arc_eye(cx):
    return lambda d: d.arc(sc(cx - 55, 360, cx + 55, 470), 200, 340, fill=RED_HOT, width=24 * K)


def round_eye(cx):
    def f(d):
        d.ellipse(sc(cx - 46, 360, cx + 46, 452), fill=RED_HOT)
        d.ellipse(sc(cx - 24, 374, cx - 4, 394), fill=(255, 225, 225))
    return f


def smile(d):
    d.arc(sc(340, 440, 460, 510), 20, 160, fill=RED_HOT, width=14 * K)


# A: happy, friendly ^ ^ eyes and a smile
def robot_a():
    img = base()
    eyes(img, [arc_eye(320), arc_eye(480), smile])
    return img


# B: big round glowing eyes, curious
def robot_b():
    img = base()
    eyes(img, [round_eye(315), round_eye(485), smile])
    return img


# C: confident wink: one round eye, one wink, smirk
def robot_c():
    img = base()
    wink = lambda d: d.line([sc(440, 410), sc(530, 410)], fill=RED_HOT, width=22 * K)
    smirk = lambda d: d.arc(sc(350, 430, 480, 505), 10, 120, fill=RED_HOT, width=14 * K)
    eyes(img, [round_eye(315), wink, smirk])
    return img


def main(out):
    os.makedirs(out, exist_ok=True)
    imgs = {"A": robot_a(), "B": robot_b(), "C": robot_c()}
    for k, im in imgs.items():
        # crop tight around the robot so it fills YouTube's circle instead of floating in black
        imgs[k] = im.crop(sc(80, 40, 720, 680)).resize((OUT_S, OUT_S), Image.LANCZOS)
        imgs[k].convert("RGB").save(os.path.join(out, f"robot_{k}.png"))
    sizes = (176, 98, 48, 32, 24)
    sheet = Image.new("RGBA", (1000, 3 * 210 + 20), (255, 255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.rectangle((500, 0, 1000, sheet.height), fill=(15, 15, 15, 255))
    lab = ImageFont.truetype("C:/Windows/Fonts/seguibl.ttf", 48)
    for i, (k, im) in enumerate(imgs.items()):
        y = 20 + i * 210
        for half, x0 in ((0, 10), (1, 510)):
            d.text((x0, y + 60), k, font=lab, fill=(20, 20, 20) if half == 0 else (255, 255, 255))
            x = x0 + 50
            for s in sizes:
                sheet.alpha_composite(circle(im, s), (x, y + (176 - s) // 2))
                x += s + 14
    sheet.convert("RGB").save(os.path.join(out, "preview.png"))


if __name__ == "__main__":
    main(sys.argv[1])
