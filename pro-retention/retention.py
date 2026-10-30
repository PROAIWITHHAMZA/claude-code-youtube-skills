"""pro-retention: find exactly where viewers leave, from a YouTube Studio audience-retention export.

    python retention.py retention.csv --duration 6:30 [--script captions.srt] [--chart out.png]

Export: YouTube Studio > Analytics > Advanced mode > pick the video > Audience retention > Export (CSV).
The script finds the position column (percent, seconds or m:ss) and the retention column itself.

Reports
  intro hold   share still watching at 30 s (under 50 % means the hook is the problem, not the content)
  cliffs       the 5 steepest drops per 10 s of video, with what was said there (if --script is given)
  rewatches    bumps where retention rises: moments people replay (make more of these)
  ending       how many reach the last 10 %
--chart draws the curve with every cliff marked, for the video or the report.
"""
import csv, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pro-chapters"))


def tsec(v):
    v = v.strip()
    if ":" in v:
        p = [float(x) for x in v.split(":")]
        return sum(x * 60 ** i for i, x in enumerate(reversed(p)))
    return float(v.rstrip("%s"))


def load(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    head = [h.lower() for h in rows[0]]
    pos = next(i for i, h in enumerate(head) if re.search(r"position|time|moment|elapsed", h))
    ret = next(i for i, h in enumerate(head) if re.search(r"absolute|audience retention|retention|watching", h) and i != pos)
    pct = "%" in head[pos] or "percent" in head[pos] or "ratio" in head[pos]
    pts = []
    for r in rows[1:]:
        try:
            x, y = tsec(r[pos]), float(r[ret].rstrip("%"))
        except (ValueError, IndexError):
            continue
        pts.append((x, y))
    if pts and max(y for _, y in pts) <= 1.5:  # ratios 0..1 -> percent
        pts = [(x, y * 100) for x, y in pts]
    return pts, pct


def at(pts, t):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= t <= x1:
            return y0 + (y1 - y0) * (t - x0) / max(1e-9, x1 - x0)
    return pts[-1][1] if t > pts[-1][0] else pts[0][1]


def fmt(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def said(segs, t):
    if not segs:
        return ""
    best = min(segs, key=lambda s: 0 if s[0] <= t <= s[1] else min(abs(s[0] - t), abs(s[1] - t)))
    return best[2][:90]


def main():
    a = sys.argv[1:]
    if not a or "--duration" not in a:
        sys.exit(__doc__)
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    dur = tsec(opt("--duration"))
    pts, pct = load(a[0])
    if pct or max(x for x, _ in pts) <= 100.5 and dur > 101:
        pts = [(x / 100 * dur, y) for x, y in pts]
    pts.sort()
    segs = []
    if opt("--script"):
        from chapters import read_srt
        segs = read_srt(opt("--script"))
    hold30 = at(pts, 30)
    print(f"Intro hold: {hold30:.0f}% still watching at 0:30" +
          ("  <- the hook is losing people; fix the first 30 s before anything else" if hold30 < 50 else
           "  (healthy)" if hold30 >= 65 else "  (average)"))
    win = 10.0
    drops, bumps = [], []
    t = 30.0 if dur > 60 else 0.0
    while t + win <= dur - win:
        d = at(pts, t) - at(pts, t + win)
        (drops if d > 0 else bumps).append((d, t))
        t += win / 2
    drops.sort(reverse=True)
    cliffs = []
    for d, t in drops:
        if all(abs(t - c) >= 20 for _, c in cliffs):
            cliffs.append((d, t))
        if len(cliffs) == 5:
            break
    norm = sorted(d for d, _ in drops)[len(drops) // 2] if drops else 0
    print(f"\nSteepest drops after the intro (typical 10 s drop here: {norm:.1f} points):")
    for d, t in cliffs:
        print(f"  {fmt(t)}-{fmt(t + win)}  -{d:.1f} pts  ({d / max(norm, 0.1):.1f}x normal)" + (f"   \"{said(segs, t + win / 2)}\"" if segs else ""))
    rises = sorted(((-d, t) for d, t in bumps if -d > 0.5), reverse=True)[:3]
    if rises:
        print("\nRewatch bumps (people went back to see this again):")
        for d, t in rises:
            print(f"  {fmt(t)}  +{d:.1f} pts" + (f"   \"{said(segs, t + win / 2)}\"" if segs else ""))
    end = at(pts, dur * 0.9)
    print(f"\nEnding: {end:.0f}% reach the last 10%.")
    if opt("--chart"):
        from PIL import Image, ImageDraw, ImageFont
        W_, H_, L, B = 1600, 700, 90, 70
        img = Image.new("RGB", (W_, H_), (12, 12, 15))
        d = ImageDraw.Draw(img)
        try:
            f = ImageFont.truetype("segoeuib.ttf", 26)
        except OSError:
            f = ImageFont.load_default()
        top = max(110, max(y for _, y in pts))
        X = lambda x: L + (W_ - L - 40) * x / dur
        Y = lambda y: 40 + (H_ - B - 40) * (1 - y / top)
        for g in range(0, int(top) + 1, 25):
            d.line([(L, Y(g)), (W_ - 40, Y(g))], fill=(40, 40, 48))
            d.text((20, Y(g) - 14), f"{g}%", font=f, fill=(150, 150, 160))
        for d_, t in cliffs:
            d.rectangle((X(t), 40, X(t + win), H_ - B), fill=(70, 14, 22))
            d.text((X(t), H_ - B + 10), fmt(t), font=f, fill=(255, 90, 90))
        d.line([(X(x), Y(y)) for x, y in pts], fill=(239, 35, 50), width=5)
        img.save(opt("--chart"))
        print(f"chart: {opt('--chart')}")


if __name__ == "__main__":
    main()
