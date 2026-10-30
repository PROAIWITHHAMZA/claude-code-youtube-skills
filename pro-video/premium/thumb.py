"""Render the premium thumbnail variants from thumb.html and a feed-size test sheet.

    python thumb.py <out_dir>
"""
import os, pathlib, shutil, sys
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path(os.environ["TEMP"]) / "prem"
out = pathlib.Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
shutil.copy2(HERE / "thumb.html", WORK / "thumb.html")
names = sys.argv[2].split(",") if len(sys.argv) > 2 else ["1", "2"]
with sync_playwright() as pw:
    br = pw.chromium.launch(channel="msedge", headless=True)
    pg = br.new_page(viewport={"width": 1280, "height": 720})
    for v in names:
        pg.goto((WORK / "thumb.html").as_uri() + f"?v={v}")
        pg.wait_for_timeout(600)
        pg.screenshot(path=str(out / f"thumb_v{v}.png"))
    br.close()
f = ImageFont.truetype("segoeuib.ttf", 26)
sheet = Image.new("RGB", (1500, 300 * len(names) + 40), (255, 255, 255))
d = ImageDraw.Draw(sheet)
d.rectangle((0, 0, 750, sheet.height), fill=(15, 15, 15))
for i, v in enumerate(names):
    im = Image.open(out / f"thumb_v{v}.png").convert("RGB")
    for x0 in (20, 770):
        x = x0
        for w in (360, 168, 120):
            sheet.paste(im.resize((w, w * 9 // 16), Image.LANCZOS), (x, 30 + i * 300))
            x += w + 18
        d.text((x0, 240 + i * 300), f"variant {v}", font=f, fill=(150, 150, 150))
sheet.save(out / "thumb_feed_test.png")
print("wrote", out)
