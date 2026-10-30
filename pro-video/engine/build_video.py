"""Build "Stop Getting Generic Answers From AI: 7 Fixes" as a faceless video.

    python build_video.py <output_dir> <build_dir>

Per sentence: an AI voice line (edge-tts), a rendered visual and a separate caption layer (Pillow).
The visual gets a slow push-in, the caption is overlaid static, chapter openers fade in from black,
and prompt screens hold on silence so viewers can read or pause. Also writes the thumbnail, an .srt,
a description with real chapter timestamps, and prompts.md with every prompt in the video.
"""
import asyncio, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import edge_tts, imageio_ffmpeg

W, H = 1920, 1080
FPS = 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE, RATE = "en-US-AndrewNeural", "+2%"

BG, PANEL, PANEL2 = (13, 17, 30), (25, 31, 49), (37, 45, 66)
ACCENT, ACCENT_DK = (124, 92, 255), (50, 38, 108)
GREEN, GREEN_DK, RED, RED_DK, AMBER = (34, 197, 94), (16, 60, 38), (239, 68, 68), (70, 22, 26), (245, 158, 11)
WHITE, MUTED, DIM = (255, 255, 255), (148, 163, 184), (90, 100, 122)


def font(name, size):
    for n in (name, "segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + n, size)
        except OSError:
            pass
    return ImageFont.load_default()


REG = lambda s: font("segoeui.ttf", s)
BOLD = lambda s: font("segoeuib.ttf", s)
BLACK = lambda s: font("seguibl.ttf", s)
MONO = lambda s: font("consola.ttf", s)


def wrap(d, text, f, maxw):
    out = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= maxw:
                cur = t
            else:
                if cur:
                    out.append(cur)
                cur = w
        out.append(cur)
    return out


def center(d, y, text, f, fill=WHITE, maxw=1600, gap=1.18, **kw):
    lines = wrap(d, text, f, maxw)
    for i, ln in enumerate(lines):
        d.text(((W - d.textlength(ln, font=f)) / 2, y + i * f.size * gap), ln, font=f, fill=fill, **kw)
    return y + len(lines) * f.size * gap


def fit(d, text, maker, maxw, maxh, sizes, gap=1.3):
    """Largest font from `sizes` whose wrapped text fits the box."""
    for s in sizes:
        f = maker(s)
        lines = wrap(d, text, f, maxw)
        if len(lines) * s * gap <= maxh:
            return f, lines, s * gap
    f = maker(sizes[-1])
    return f, wrap(d, text, f, maxw), sizes[-1] * gap


def check(d, x, y, s, color=GREEN, w=12):
    d.line([(x, y + s * 0.55), (x + s * 0.38, y + s * 0.9), (x + s, y + s * 0.1)], fill=color, width=w, joint="curve")


def cross(d, x, y, s, color=RED, w=12):
    d.line([(x, y), (x + s, y + s)], fill=color, width=w)
    d.line([(x + s, y), (x, y + s)], fill=color, width=w)


def glow(img, box, color, radius=40, spread=20):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    ImageDraw.Draw(layer).rounded_rectangle((x0 - spread, y0 - spread, x1 + spread, y1 + spread),
                                            radius=radius + spread, fill=color + (150,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius)))


def bg_gradient():
    img = Image.new("RGBA", (W, H), BG + (255,))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse((-300, -400, 900, 500), fill=ACCENT + (40,))
    ld.ellipse((1300, 600, 2300, 1400), fill=(14, 165, 233, 26))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(160)))
    return img


# ---------- visuals (all drawn in the area above y=860; the caption lives below) ----------

def v_title(img, d, v):
    f = BLACK(v.get("size", 180))
    n = len(wrap(d, v["text"], f, 1600))
    y = center(d, 400 - n * f.size * 0.59, v["text"], f, fill=v.get("color", WHITE), stroke_width=6, stroke_fill=ACCENT_DK)
    if v.get("sub"):
        center(d, y + 30, v["sub"], BOLD(56), fill=MUTED)


def v_card(img, d, v):
    glow(img, (260, 170, 1660, 700), ACCENT, radius=60, spread=0)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((260, 170, 1660, 700), radius=40, fill=PANEL, outline=v.get("color", ACCENT), width=4)
    center(d, 230, v["kicker"], BOLD(44), fill=v.get("color", ACCENT))
    center(d, 330, v["text"], BOLD(76), maxw=1240)


def v_chapter(img, d, v):
    k = BLACK(130)
    label, total = f"FIX {v['n']}", "  / 7"
    if v["n"] == 0:
        label, total = "BONUS", ""
    w1, w2 = d.textlength(label, font=k), d.textlength(total, font=BLACK(90))
    x = (W - w1 - w2) / 2
    d.text((x, 170), label, font=k, fill=ACCENT)
    d.text((x + w1, 205), total, font=BLACK(90), fill=DIM)
    center(d, 380, v["text"], BLACK(104), maxw=1500)


def chat_frame(img, d, box, title="Any AI chat  ·  ChatGPT  ·  Claude  ·  Gemini"):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=28, fill=PANEL)
    d.rounded_rectangle((x0, y0, x1, y0 + 64), radius=28, fill=PANEL2)
    d.rectangle((x0, y0 + 36, x1, y0 + 64), fill=PANEL2)
    for i, c in enumerate(((239, 68, 68), (245, 158, 11), (34, 197, 94))):
        d.ellipse((x0 + 26 + i * 34, y0 + 22, x0 + 46 + i * 34, y0 + 42), fill=c)
    d.text((x0 + 150, y0 + 14), title, font=BOLD(30), fill=MUTED)


def bubble(d, box, text, fill, maker=MONO, sizes=(54, 50, 46, 42, 39, 36, 33, 30), color=WHITE, label=None, label_col=MUTED):
    x0, y0, x1, y1 = box
    pad = 30
    top = y0 + (52 if label else 0)
    f, lines, lh = fit(d, text, maker, x1 - x0 - 2 * pad, y1 - top - 2 * pad, sizes)
    h = len(lines) * lh + 2 * pad + (52 if label else 0)
    d.rounded_rectangle((x0, y0, x1, y0 + h), radius=24, fill=fill)
    if label:
        d.text((x0 + pad, y0 + 18), label, font=BOLD(28), fill=label_col)
    for i, ln in enumerate(lines):
        d.text((x0 + pad, top + pad + i * lh), ln, font=f, fill=color)
    return y0 + h


def v_chat(img, d, v):
    chat_frame(img, d, (150, 60, 1770, 850), v.get("app", "Any AI chat  ·  ChatGPT  ·  Claude  ·  Gemini"))
    tag = "PROMPT  ·  copy it from the description"
    d.text((1740 - d.textlength(tag, font=BOLD(28)), 76), tag, font=BOLD(28), fill=GREEN)
    bottom = 830 if not v.get("reply") else 640
    y = bubble(d, (300, 150, 1730, bottom), v["prompt"], ACCENT_DK, label="YOU", label_col=(190, 175, 255))
    if v.get("reply"):
        bubble(d, (190, y + 24, 1500, 830), v["reply"], PANEL2, maker=REG, sizes=(44, 40, 36, 32), color=MUTED, label="AI")


def v_compare(img, d, v):
    for x, w, head, col, dk, text in ((80, 560, "BEFORE", RED, RED_DK, v["before"]),
                                      (680, 1160, "AFTER", GREEN, GREEN_DK, v["after"])):
        d.rounded_rectangle((x, 70, x + w, 850), radius=30, fill=PANEL, outline=col, width=5)
        d.text((x + 40, 100), head, font=BLACK(56), fill=col)
        bubble(d, (x + 40, 200, x + w - 40, 820), text, dk, sizes=(48, 44, 41, 38, 35, 32, 29))


def v_formula(img, d, v):
    parts = [("CONTEXT", "Who you are,\nwho it's for"), ("TASK", "What you want,\nand WHY"),
             ("RULES", "Length, tone,\nwhat to avoid"), ("FORMAT", "Bullets, table,\nemail...")]
    center(d, 120, "The 4-part brief", BOLD(64))
    hi = v.get("highlight")
    for i, (h, sub) in enumerate(parts):
        x = 150 + i * 415
        on = hi is None or hi == i
        if hi == i:
            glow(img, (x, 260, x + 375, 700), ACCENT, radius=50, spread=4)
            d = ImageDraw.Draw(img)
        d.rounded_rectangle((x, 260, x + 375, 700), radius=32, fill=ACCENT_DK if hi == i else PANEL,
                            outline=ACCENT if on else PANEL2, width=4)
        d.ellipse((x + 147, 300, x + 227, 380), fill=ACCENT if on else PANEL2)
        n = BLACK(48)
        d.text((x + 187 - d.textlength(str(i + 1), font=n) / 2, 306), str(i + 1), font=n, fill=WHITE)
        hf = BLACK(52)
        d.text((x + (375 - d.textlength(h, font=hf)) / 2, 420), h, font=hf, fill=WHITE if on else DIM)
        for j, ln in enumerate(sub.split("\n")):
            sf = BOLD(36)
            d.text((x + (375 - d.textlength(ln, font=sf)) / 2, 520 + j * 48), ln, font=sf, fill=MUTED if on else DIM)


def v_stat(img, d, v):
    f = BLACK(300)
    w = d.textlength(v["big"], font=f)
    d.text(((W - w) / 2, 60), v["big"], font=f, fill=v.get("color", RED))
    y = center(d, 470, v["line"], BOLD(60), maxw=1500)
    center(d, y + 30, v["source"], REG(38), fill=MUTED, maxw=1500)


def v_quote(img, d, v):
    d.text((200, 40), "\u201C", font=BLACK(300), fill=ACCENT)
    y = center(d, 250, v["text"], BOLD(70), maxw=1400)
    center(d, y + 40, "— " + v["who"], REG(42), fill=MUTED)


def v_steps(img, d, v):
    center(d, 90, v["heading"], BOLD(60))
    hi = v.get("highlight")
    n = len(v["steps"])
    rh = min(130, 640 // n)
    for i, s in enumerate(v["steps"]):
        y = 210 + i * rh
        on = hi is None or hi == i
        d.rounded_rectangle((260, y, 1660, y + rh - 22), radius=24, fill=ACCENT_DK if hi == i else PANEL,
                            outline=ACCENT if hi == i else None, width=4)
        cy = y + (rh - 22) / 2
        d.ellipse((290, cy - 32, 354, cy + 32), fill=ACCENT if on else PANEL2)
        nf = BLACK(38)
        d.text((322 - d.textlength(str(i + 1), font=nf) / 2, cy - 26), str(i + 1), font=nf, fill=WHITE)
        f, lines, lh = fit(d, s, BOLD, 1240, rh - 40, (52, 48, 44, 40, 36), gap=1.2)
        ty = cy - len(lines) * lh / 2
        for j, ln in enumerate(lines):
            d.text((390, ty + j * lh), ln, font=f, fill=WHITE if on else DIM)


def v_modes(img, d, v):
    center(d, 110, "Built-in learning modes", BOLD(60))
    for i, (tool, mode) in enumerate((("ChatGPT", "Study and learn"), ("Claude", "Learning style"), ("Gemini", "Guided Learning"))):
        x = 165 + i * 545
        d.rounded_rectangle((x, 250, x + 500, 650), radius=36, fill=PANEL, outline=ACCENT, width=4)
        tf, mf = BLACK(66), BOLD(46)
        d.text((x + (500 - d.textlength(tool, font=tf)) / 2, 320), tool, font=tf, fill=WHITE)
        d.text((x + (500 - d.textlength(mode, font=mf)) / 2, 470), mode, font=mf, fill=(190, 175, 255))
    center(d, 710, "Menu names move around. The prompt works anywhere.", BOLD(42), fill=MUTED)


def v_warning(img, d, v):
    d.rounded_rectangle((260, 150, 1660, 760), radius=40, fill=PANEL, outline=AMBER, width=5)
    d.polygon([(960, 200), (900, 310), (1020, 310)], fill=AMBER)
    d.text((948, 222), "!", font=BLACK(70), fill=PANEL)
    center(d, 350, v["head"], BLACK(76), fill=AMBER)
    center(d, 470, v["text"], BOLD(52), maxw=1240)


def v_table(img, d, v):
    d.rounded_rectangle((140, 90, 1780, 840), radius=36, fill=PANEL)
    cols = v["cols"]
    xs = [200, 860, 1340]
    for x, h in zip(xs, cols):
        d.text((x, 120), h, font=BOLD(40), fill=ACCENT)
    d.line([(180, 190), (1740, 190)], fill=PANEL2, width=4)
    for i, row in enumerate(v["rows"]):
        y = 225 + i * 120
        for x, cell in zip(xs, row):
            col = AMBER if cell.startswith("no ") else WHITE
            d.text((x, y), cell, font=BOLD(46) if x == 200 else REG(46), fill=col)
    if v.get("note"):
        center(d, 770, v["note"], BOLD(38), fill=MUTED)


def v_recap(img, d, v):
    center(d, 70, "7 fixes for generic AI answers", BOLD(60))
    items = ["Write a brief, not a search", "Let it interview you", "Show examples", "Read with NotebookLM",
             "Make it prove every claim", "Meetings -> action items", "Make it teach, not tell"]
    for i, t in enumerate(items):
        col, row = i // 4, i % 4
        x, y = 170 + col * 820, 200 + row * 150
        d.rounded_rectangle((x, y, x + 760, y + 120), radius=24, fill=PANEL)
        d.ellipse((x + 24, y + 24, x + 96, y + 96), fill=ACCENT)
        nf = BLACK(42)
        d.text((x + 60 - d.textlength(str(i + 1), font=nf) / 2, y + 28), str(i + 1), font=nf, fill=WHITE)
        d.text((x + 124, y + 32), t, font=BOLD(44), fill=WHITE)
    if v.get("cta"):
        d.rounded_rectangle((990, 650, 1750, 770), radius=24, fill=ACCENT_DK, outline=ACCENT, width=4)
        d.text((1030, 680), "Comment the one you tried", font=BOLD(44), fill=WHITE)


VISUALS = {"title": v_title, "card": v_card, "chapter": v_chapter, "chat": v_chat, "compare": v_compare,
           "formula": v_formula, "stat": v_stat, "quote": v_quote, "steps": v_steps, "modes": v_modes,
           "warning": v_warning, "table": v_table, "recap": v_recap}


def render_visual(v, chapter, path):
    img = bg_gradient()
    d = ImageDraw.Draw(img)
    VISUALS[v["type"]](img, d, v)
    img.convert("RGB").save(path)


def render_caption(text, chapter, progress, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cf = BOLD(44)
    lines = wrap(d, text, cf, 1640)
    lh = 56
    top = 1045 - len(lines) * lh - 28
    d.rounded_rectangle((100, top, 1820, 1055), radius=24, fill=(0, 0, 0, 185))
    for i, ln in enumerate(lines):
        d.text(((W - d.textlength(ln, font=cf)) / 2, top + 12 + i * lh), ln, font=cf, fill=WHITE)
    d.rectangle((0, 0, int(W * progress), 7), fill=ACCENT)
    # chapter pills, top right
    if chapter:
        for i in range(1, 8):
            x = 1500 + (i - 1) * 54
            on = i == chapter
            d.rounded_rectangle((x, 22, x + 44, 62), radius=12, fill=ACCENT if on else (40, 48, 70, 200))
            nf = BOLD(26)
            d.text((x + 22 - d.textlength(str(i), font=nf) / 2, 26), str(i), font=nf, fill=WHITE if on else MUTED)
    img.save(path)


def thumbnail(path):
    img = Image.new("RGBA", (1280, 720), (8, 11, 24, 255))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse((560, 260, 1400, 820), fill=GREEN + (70,))
    ld.ellipse((620, -120, 1340, 300), fill=RED + (55,))
    ld.ellipse((-200, 60, 620, 700), fill=ACCENT + (60,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(110)))
    d = ImageDraw.Draw(img)
    # the bad prompt: readable, with a red X badge instead of a strike-through
    d.rounded_rectangle((640, 52, 1205, 205), radius=30, fill=(64, 26, 30), outline=RED, width=6)
    d.text((675, 98), "write an email", font=MONO(56), fill=(235, 215, 218))
    d.ellipse((1160, 22, 1250, 112), fill=RED, outline=(8, 11, 24), width=6)
    cross(d, 1185, 47, 40, color=WHITE, w=11)
    # the good prompt: real words, bright green, filling the right half
    d.rounded_rectangle((610, 245, 1250, 680), radius=34, fill=(14, 62, 38), outline=(74, 222, 128), width=7)
    rows = (("Context:", "my team"), ("Task:", "delay, why"), ("Rules:", "120 words"), ("Format:", "short email"))
    for i, (k, val) in enumerate(rows):
        y = 280 + i * 92
        d.text((645, y), k, font=MONO(46), fill=(134, 239, 172))
        d.text((645 + d.textlength(k + " ", font=MONO(46)), y), val, font=MONO(46), fill=WHITE)
    d.ellipse((1160, 600, 1260, 700), fill=GREEN, outline=(8, 11, 24), width=6)
    check(d, 1182, 625, 54, color=WHITE, w=12)
    f = BLACK(156)
    for i, word in enumerate(("COPY", "THESE")):
        d.text((34, 140 + i * 185), word, font=f, fill=WHITE, stroke_width=11, stroke_fill=(0, 0, 0))
    d.rounded_rectangle((40, 545, 540, 571), radius=8, fill=(250, 204, 21))
    img.convert("RGB").save(path)


# ---------- the script ----------

P_BEFORE = "Write an email about the project delay."
P_AFTER = ("Context: I run a 5-person design team. This goes to a client who has been patient but is frustrated.\n"
           "Task: Tell them launch moves from March 3 to March 17 because our payment provider failed a security review.\n"
           "Rules: Under 120 words. Take responsibility once, no excuses. Offer one concrete thing to make up for it.\n"
           "Format: Subject line, then the email.")
P_INTERVIEW = ("I want to write [what you're writing] for [who it's for].\n"
               "Before you write anything, interview me.\n"
               "Ask one question at a time and wait for my answer.\n"
               "Stop when you have enough to write something only I could have written.\n"
               "Then show me an outline before the full draft.")
P_EXAMPLES = ("Here are 3 things I've written that worked well:\n"
              "<example>[paste #1]</example>\n<example>[paste #2]</example>\n<example>[paste #3]</example>\n"
              "Study the tone, sentence length and structure.\n"
              "Write a new one about [topic] in the same style.\n"
              "Then list the patterns you copied.")
P_BRIEFING = ("Create a briefing for someone with 5 minutes.\n"
              "1. The 5 most important points, with the evidence for each.\n"
              "2. Where the sources disagree.\n"
              "3. What's missing or unclear.\n"
              "Cite every point.")
P_VERIFY = ("Go through your last answer claim by claim.\n"
            "For each claim, quote the exact sentence from the source that supports it, with the link.\n"
            "If you can't find one, mark it UNSUPPORTED.\n"
            "Don't add any new claims.")
P_MEETING = ("Here is a meeting transcript. Give me:\n"
             "1. Decisions that were made.\n"
             "2. Action items as a table: task, owner, deadline. Write \"no owner\" or \"no deadline\" if none was agreed.\n"
             "3. Open questions.\n"
             "4. A follow-up email to everyone, under 150 words.\n"
             "Only use what's in the transcript.\n\n[paste transcript]")
P_TUTOR = ("Teach me [topic]. I already know [what you know]. My goal is [goal].\n"
           "Don't give me the answers. Ask one question at a time, let me try, then correct me.\n"
           "Every 5 questions, quiz me on what I got wrong earlier.")

PROMPTS = [("Fix 1 - The 4-part brief (example)", P_AFTER), ("Fix 2 - Interview me first", P_INTERVIEW),
           ("Fix 3 - Show examples", P_EXAMPLES), ("Fix 4 - NotebookLM briefing", P_BRIEFING),
           ("Fix 5 - Verification pass", P_VERIFY), ("Fix 6 - Meeting to action items", P_MEETING),
           ("Fix 7 - Tutor mode", P_TUTOR)]

GENERIC_REPLY = ("Dear Client, I hope this email finds you well. Unfortunately, due to unforeseen circumstances, "
                 "the project has been delayed. We apologize for any inconvenience...")
FORMULA_STEPS = None


def ch(n, text):
    return {"type": "chapter", "n": n, "text": text}


# (chapter title for description, chapter pill number, [(visual, spoken line, extra hold seconds)])
SCENES = [
    ("Why your AI answers are generic", None, [
        ({"type": "title", "text": "GENERIC?", "sub": "Same model. Different results."}, "Why do you still get generic answers from AI?", 0),
        ({"type": "chat", "prompt": P_BEFORE, "reply": GENERIC_REPLY},
         "Nobody shows you the seven workflows that stop you wasting it.", 0.5),
        ({"type": "card", "kicker": "IN THIS VIDEO", "text": "7 fixes. The exact prompt for each."},
         "So here they are. Seven fixes, each with the exact prompt on screen. Every prompt is also in the description, ready to copy.", 0),
        ({"type": "card", "kicker": "IN THIS VIDEO", "text": "7 fixes. The exact prompt for each."},
         "We'll start with the one that fixes almost every bad answer.", 0),
    ]),
    ("Fix 1: Write a brief, not a search", 1, [
        (ch(1, "Write a brief, not a search"), "Fix one. Stop typing to AI like it's Google.", 0),
        ({"type": "quote", "text": "Think of Claude as a brilliant but new employee who lacks context on your norms and workflows.",
          "who": "Anthropic's prompting guide"},
         "Anthropic's own prompting guide says to treat the AI like a brilliant but new employee, who lacks context on your norms and workflows.", 0.5),
        ({"type": "chat", "prompt": P_BEFORE, "reply": GENERIC_REPLY},
         "Give a new employee one line, like write an email about the delay, and you get the most average email possible. AI does exactly the same.", 0),
        ({"type": "formula"}, "So give it what a good manager would. Every useful brief has four parts.", 0),
        ({"type": "formula", "highlight": 0}, "Context. Who you are, and who this is for.", 0),
        ({"type": "formula", "highlight": 1}, "Task. What you want, and why it matters. The why changes the answer more than most people expect.", 0),
        ({"type": "formula", "highlight": 2}, "Rules. The length, the tone, and what to avoid.", 0),
        ({"type": "formula", "highlight": 3}, "Format. Bullets, a table, or an email with a subject line.", 0),
        ({"type": "compare", "before": P_BEFORE, "after": P_AFTER},
         "Here's the same request, before and after. Pause here if you want to read it.", 3.0),
        ({"type": "compare", "before": P_BEFORE, "after": P_AFTER},
         "Same model, same free plan. The only thing that changed is what you told it.", 1.0),
        ({"type": "quote", "text": "Show your prompt to a colleague with minimal context. If they'd be confused, Claude will be too.",
          "who": "Anthropic's prompting guide, paraphrased"},
         "And here's a quick test from the same guide. Show your prompt to a colleague with no context. If they'd be confused, the AI will be too.", 0.5),
    ]),
    ("Fix 2: Let it interview you", 2, [
        (ch(2, "Let it interview you"), "Fix two. When you don't know what to put in the brief, make the AI ask for it.", 0),
        ({"type": "chat", "prompt": P_INTERVIEW}, "Paste this, and swap in what you're writing and who it's for.", 3.5),
        ({"type": "chat", "prompt": P_INTERVIEW},
         "The key words are one question at a time. Without them, you get a wall of ten questions, and you answer none of them properly.", 0.5),
        ({"type": "chat", "prompt": P_INTERVIEW},
         "If it starts asking several at once anyway, just reply: one at a time.", 0),
        ({"type": "title", "text": "ONLY YOU", "sub": "Your numbers. Your story. Your opinion.", "size": 200},
         "By the end, it has the details only you know. Your numbers, your story, your opinion. That's what makes the draft sound like you, and not like everyone else.", 0),
    ]),
    ("Fix 3: Show examples, don't describe", 3, [
        (ch(3, "Show examples, don't describe"), "Fix three. Show, don't describe.", 0),
        ({"type": "compare", "before": "Make it punchy and engaging.", "after": "Here are 3 posts I wrote. Copy their tone and structure."},
         "Telling an AI to make it punchy is vague. Everyone's idea of punchy is different. Showing it what you mean is precise.", 0.5),
        ({"type": "quote", "text": "Examples are one of the most reliable ways to steer Claude's output format, tone, and structure.",
          "who": "Anthropic's prompting guide"},
         "Anthropic's guide calls examples one of the most reliable ways to steer format, tone and structure, and suggests three to five of them.", 0.5),
        ({"type": "chat", "prompt": P_EXAMPLES}, "Here's the prompt. Paste your own best work where the brackets are.", 3.5),
        ({"type": "chat", "prompt": P_EXAMPLES},
         "Wrapping each sample in example tags helps the AI tell your samples apart from your instructions.", 0),
        ({"type": "chat", "prompt": P_EXAMPLES},
         "And the last line matters. Asking which patterns it copied lets you check it learned the right thing, before you trust the draft.", 0.5),
    ]),
    ("Fix 4: Read 50 pages in 5 minutes", 4, [
        (ch(4, "Read 50 pages in 5 minutes"), "Fix four. Stop reading everything yourself.", 0),
        ({"type": "steps", "heading": "Google NotebookLM", "steps": [
            "Go to notebooklm.google.com", "Create a new notebook",
            "Add sources: PDFs, Docs, Slides, websites, YouTube links", "Ask questions: answers cite YOUR sources"]},
         "Google's NotebookLM answers from the documents you give it, not from the whole internet.", 0),
        ({"type": "steps", "heading": "Google NotebookLM", "highlight": 2, "steps": [
            "Go to notebooklm.google.com", "Create a new notebook",
            "Add sources: PDFs, Docs, Slides, websites, YouTube links", "Ask questions: answers cite YOUR sources"]},
         "Go to notebooklm dot google dot com, create a notebook, and add your sources. PDFs, Google Docs, Slides, websites, even YouTube links.", 0),
        ({"type": "card", "kicker": "FREE PLAN (per Google's help page)", "text": "Up to 100 notebooks · 50 sources each", "color": GREEN},
         "On the free plan, Google's help page lists up to one hundred notebooks, with fifty sources in each.", 0),
        ({"type": "chat", "prompt": P_BRIEFING, "app": "NotebookLM  ·  chat"},
         "Then ask for a briefing, not a summary. A summary shrinks the document. A briefing tells you what matters and where it's weak.", 3.0),
        ({"type": "steps", "heading": "Then check and go deeper", "highlight": 0, "steps": [
            "Click a citation number: it jumps to the exact passage", "Studio > Audio Overview: listen on a walk",
            "Studio > Flashcards & quizzes: test yourself"]},
         "Every point comes with a citation number. Click it, and it jumps to the exact passage, so you can check any claim in seconds.", 0),
        ({"type": "steps", "heading": "Then check and go deeper", "highlight": 1, "steps": [
            "Click a citation number: it jumps to the exact passage", "Studio > Audio Overview: listen on a walk",
            "Studio > Flashcards & quizzes: test yourself"]},
         "Then open the Studio panel. Audio Overview turns your sources into a podcast-style conversation you can listen to on a walk.", 0),
        ({"type": "steps", "heading": "Then check and go deeper", "highlight": 2, "steps": [
            "Click a citation number: it jumps to the exact passage", "Studio > Audio Overview: listen on a walk",
            "Studio > Flashcards & quizzes: test yourself"]},
         "And the same panel can turn your material into flashcards and quizzes, which is how you actually remember it.", 0),
    ]),
    ("Fix 5: Make it prove every claim", 5, [
        (ch(5, "Make it prove every claim"), "Fix five. Never trust a citation you haven't clicked.", 0),
        ({"type": "stat", "big": "1,600", "line": "queries · 8 AI search tools tested", "color": ACCENT,
          "source": "Tow Center for Digital Journalism, Columbia Journalism Review · March 2025"},
         "In March twenty twenty-five, Columbia Journalism Review's Tow Center tested eight AI search tools, on sixteen hundred queries.", 0),
        ({"type": "stat", "big": "60%+", "line": "of answers were wrong",
          "source": "Tow Center for Digital Journalism, Columbia Journalism Review · March 2025"},
         "Together, they got more than sixty percent of the answers wrong.", 0.5),
        ({"type": "stat", "big": "37%", "line": "wrong, even for the best performer (Perplexity)", "color": AMBER,
          "source": "Some paid versions had higher error rates than their free versions"},
         "Even the best performer, Perplexity, was wrong thirty-seven percent of the time. And some paid versions had higher error rates than the free ones.", 0),
        ({"type": "chat", "prompt": P_VERIFY}, "So after any research answer, run a verification pass. Paste this straight after the answer.", 3.0),
        ({"type": "chat", "prompt": P_VERIFY},
         "Anything marked unsupported gets cut, or checked by hand.", 0),
        ({"type": "steps", "heading": "The 3-link rule", "steps": [
            "Open 3 of the links yourself", "Does the page actually say that?",
            "One miss = the whole answer is a draft, not a fact"]},
         "Then open three of the links yourself. If even one doesn't say what the AI claimed, treat the whole answer as a draft, not a fact.", 0),
    ]),
    ("Fix 6: Meetings to action items, free", 6, [
        (ch(6, "Turn meetings into action items"), "Fix six. Turn any meeting into action items, for free.", 0),
        ({"type": "steps", "heading": "Free transcript, no extra app", "highlight": 0, "steps": [
            "Ask everyone before you record", "iPhone (iOS 18+): Voice Memos shows a transcript",
            "Pixel: the Recorder app transcribes on the device", "Copy the transcript into any AI chat"]},
         "Record it with your phone, and ask everyone first.", 0),
        ({"type": "steps", "heading": "Free transcript, no extra app", "highlight": 1, "steps": [
            "Ask everyone before you record", "iPhone (iOS 18+): Voice Memos shows a transcript",
            "Pixel: the Recorder app transcribes on the device", "Copy the transcript into any AI chat"]},
         "On an iPhone with iOS eighteen or later, Voice Memos shows a transcript of your recording.", 0),
        ({"type": "steps", "heading": "Free transcript, no extra app", "highlight": 2, "steps": [
            "Ask everyone before you record", "iPhone (iOS 18+): Voice Memos shows a transcript",
            "Pixel: the Recorder app transcribes on the device", "Copy the transcript into any AI chat"]},
         "On a Google Pixel, the Recorder app transcribes on the device.", 0),
        ({"type": "chat", "prompt": P_MEETING}, "Copy the transcript, and paste it into any AI chat with this prompt.", 3.5),
        ({"type": "table", "cols": ["TASK", "OWNER", "DEADLINE"],
          "rows": [["Send revised quote", "Sara", "Friday"], ["Book venue walkthrough", "no owner", "no deadline"],
                   ["Update the budget sheet", "Omar", "no deadline"]],
          "note": "Example output. The gaps are the point."},
         "Two lines do the heavy lifting. Only use what's in the transcript stops it inventing deadlines nobody agreed to.", 0),
        ({"type": "table", "cols": ["TASK", "OWNER", "DEADLINE"],
          "rows": [["Send revised quote", "Sara", "Friday"], ["Book venue walkthrough", "no owner", "no deadline"],
                   ["Update the budget sheet", "Omar", "no deadline"]],
          "note": "Example output. The gaps are the point."},
         "And no owner forces the gaps into the open, which is exactly where projects slip.", 0.5),
        ({"type": "warning", "head": "Check before you paste", "text": "Free consumer plans can handle your data differently from business plans. Check your company's policy."},
         "One warning. Before pasting a work meeting into a free AI tool, check your company's policy. Free consumer plans can handle your data differently from business plans, and some use chats for training unless you opt out.", 0),
    ]),
    ("Fix 7: Make AI teach, not tell", 7, [
        (ch(7, "Make AI teach, not tell"), "Fix seven. Learn anything, without the AI doing it for you.", 0),
        ({"type": "modes"},
         "ChatGPT, Claude and Gemini each have a learning mode. Look for Study and learn in ChatGPT, the Learning style in Claude, and Guided Learning in Gemini.", 0),
        ({"type": "modes"}, "Instead of handing over answers, they ask you questions.", 0),
        ({"type": "chat", "prompt": P_TUTOR},
         "Menu names move around, so if you can't find the mode, this prompt does the same job in any chat.", 3.0),
        ({"type": "chat", "prompt": P_TUTOR},
         "Trying first and getting corrected feels slower in the moment. But it's the difference between reading about something and actually knowing it.", 0.5),
    ]),
    ("Bonus: Set it up once", None, [
        (ch(0, "Stop retyping your context"), "One bonus.", 0),
        ({"type": "steps", "heading": "Save your context once", "steps": [
            "ChatGPT or Claude: create a Project", "Gemini: create a Gem",
            "Add your brief, your examples, your rules", "Every chat inside starts already knowing them"]},
         "Put your brief, your examples, and your rules into a Project in ChatGPT or Claude, or a Gem in Gemini. Every chat inside starts already knowing them. Check which of these your plan includes.", 0),
    ]),
    ("Which one to try first", None, [
        ({"type": "recap"}, "That's seven fixes.", 0),
        ({"type": "recap"}, "Don't try all seven this week. Pick the one that matches a task you're doing tomorrow, and copy its prompt from the description.", 1.0),
        ({"type": "recap", "cta": True}, "Then comment which one you tried, and what changed. The most useful replies become the next video.", 1.5),
    ]),
]


def ff(*args):
    r = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)


def duration(path):
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def ts(t, srt=False):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    if srt:
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    return f"{h}:{m:02d}:{int(s):02d}" if h else f"{m}:{int(s):02d}"


async def speak(text, path, tries=6):
    # reuse a line from an earlier run; the TTS service drops the odd request, so retry with backoff
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    for n in range(tries):
        try:
            await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)
            return
        except Exception as e:
            if n == tries - 1:
                raise
            print(f"    tts retry {n + 1}: {type(e).__name__}", flush=True)
            await asyncio.sleep(2 + n * 3)


def make_clip(vis, cap, audio, hold, fade, out):
    dur = duration(audio) + 0.35 + hold
    frames = int(dur * FPS) + 1
    # slow push-in on the visual only, so the caption stays rock steady
    zoom = (f"[0:v]scale=2880:-1,zoompan=z='1+0.035*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={W}x{H}:fps={FPS}[bg];[bg][1:v]overlay=0:0")
    if fade:
        zoom += ",fade=t=in:st=0:d=0.35"
    zoom += "[v]"
    ff("-i", vis, "-loop", "1", "-framerate", str(FPS), "-i", cap, "-i", audio,
       "-filter_complex", zoom + f";[2:a]apad=pad_dur={0.35 + hold}[a]",
       "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out)


async def main(out, build):
    os.makedirs(out, exist_ok=True)
    os.makedirs(build, exist_ok=True)
    lines = [(si, pill, v, text, hold, j == 0)
             for si, (_, pill, items) in enumerate(SCENES) for j, (v, text, hold) in enumerate(items)]
    clips, t, chapters, srt = [], 0.0, [], []
    for i, (si, pill, v, text, hold, first) in enumerate(lines):
        base = os.path.join(build, f"{i:03d}")
        a, vis, cap, mp4 = base + ".mp3", base + "_v.png", base + "_c.png", base + ".mp4"
        await speak(text, a)
        render_visual(v, pill, vis)
        render_caption(text, pill, (i + 1) / len(lines), cap)
        make_clip(vis, cap, a, hold, first, mp4)
        if first:
            chapters.append((si, t))
        dur = duration(mp4)
        srt.append(f"{i + 1}\n{ts(t, True)} --> {ts(t + dur - 0.3 - hold, True)}\n{text}\n")
        t += dur
        clips.append(mp4)
        print(f"  [{i + 1:2d}/{len(lines)}] {dur:5.2f}s  {text[:60]}", flush=True)
    lst = os.path.join(build, "list.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        fh.writelines(f"file '{c.replace(os.sep, '/')}'\n" for c in clips)
    final = os.path.join(out, "stop-getting-generic-answers-from-ai.mp4")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", final)
    thumbnail(os.path.join(out, "thumbnail.png"))
    with open(os.path.join(out, "captions.srt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(srt))
    chap = "\n".join(f"{ts(st)} {SCENES[si][0]}" for si, st in chapters)
    prompts = "\n\n".join(f"{name}\n{p}" for name, p in PROMPTS)
    with open(os.path.join(out, "description.txt"), "w", encoding="utf-8") as fh:
        fh.write("Generic AI answers aren't the model's fault. Here are 7 fixes, with the exact prompt for each. "
                 "All of them work on free plans of ChatGPT, Claude or Gemini.\n\n"
                 + chap + "\n\n---- THE PROMPTS (copy these) ----\n\n" + prompts +
                 "\n\n---- SOURCES ----\n"
                 "Anthropic prompting guide: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices\n"
                 "Tow Center / CJR, 'AI Search Has a Citation Problem' (Mar 2025): https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php\n"
                 "NotebookLM: https://notebooklm.google.com\n")
    with open(os.path.join(out, "prompts.md"), "w", encoding="utf-8") as fh:
        fh.write("# The 7 prompts\n\n" + "\n\n".join(f"## {name}\n\n```\n{p}\n```" for name, p in PROMPTS) + "\n")
    print(f"\n  done: {final}  ({ts(duration(final))})\n\n{chap}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
