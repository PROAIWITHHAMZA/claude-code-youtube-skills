"""pro-chapters: validate YouTube chapters, or propose chapter breaks from a captions file.

    python chapters.py check description.txt [--duration 6:30]
    python chapters.py propose captions.srt [--n 6]

check:   YouTube only shows chapters when ALL of these hold: the first timestamp is 0:00, there are at least
         3 chapters, each one is at least 10 seconds long, and timestamps go up. Also warns about long titles
         and timestamps past the end of the video.
propose: finds likely topic changes (pauses + words like "step", "next", "now", "first", "finally") and
         prints candidate breaks with the sentence that opens each one, so the titles can be written from them.
"""
import re, sys

TS = re.compile(r"^\s*(?:(\d+):)?(\d{1,2}):(\d{2})\s*[-–—:|]?\s*(.+?)\s*$")
CUE = re.compile(r"\b(step \w+|next|now|first|second|third|finally|last|let'?s|here'?s|number \w+|part \w+|okay so|so now|"
                 r"the (first|second|third|next|last|final))\b", re.I)


def secs(t):
    p = [int(x) for x in t.split(":")]
    return sum(v * 60 ** i for i, v in enumerate(reversed(p)))


def fmt(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def parse(text):
    out = []
    for line in text.splitlines():
        m = TS.match(line)
        if m:
            h, mi, s, title = m.groups()
            out.append(((int(h or 0) * 3600) + int(mi) * 60 + int(s), title, line.strip()))
    return out


def check(path, duration=None):
    with open(path, encoding="utf-8-sig") as fh:
        ch = parse(fh.read())
    errs, warns = [], []
    if not ch:
        print("FIX  no chapter lines found (format: 0:00 Title, one per line)")
        return 1
    if ch[0][0] != 0:
        errs.append(f"first chapter must start at 0:00 (found {fmt(ch[0][0])})")
    if len(ch) < 3:
        errs.append(f"need at least 3 chapters (found {len(ch)})")
    for (a, ta, _), (b, tb, _) in zip(ch, ch[1:]):
        if b <= a:
            errs.append(f"timestamps must go up: {fmt(a)} then {fmt(b)}")
        elif b - a < 10:
            errs.append(f"\"{ta}\" is {b - a}s long; every chapter needs 10s or more")
    if duration:
        end = secs(duration)
        if ch[-1][0] >= end:
            errs.append(f"last chapter {fmt(ch[-1][0])} starts after the video ends ({duration})")
        elif end - ch[-1][0] < 10:
            errs.append(f"last chapter is only {end - ch[-1][0]}s long")
    for s, t, _ in ch:
        if len(t) > 40:
            warns.append(f"\"{t}\" is {len(t)} chars; chapter titles read best under ~40")
    for s, t, line in ch:
        print(f"   {line}")
    for e in errs:
        print(f"FIX  {e}")
    for w in warns:
        print(f"warn {w}")
    print("OK   YouTube will show these chapters" if not errs else f"\n{len(errs)} problem(s): YouTube will NOT show chapters until fixed")
    return 1 if errs else 0


def read_srt(path):
    with open(path, encoding="utf-8-sig") as fh:
        blocks = re.split(r"\n\s*\n", fh.read().strip())
    out = []
    for b in blocks:
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", b)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        e = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = " ".join(l for l in b.splitlines()[1:] if "-->" not in l).strip()
        out.append((a, e, text))
    return out


def propose(path, n=6):
    segs = read_srt(path)
    if not segs:
        sys.exit("no captions found")
    total = segs[-1][1]
    cands = []
    for i, (a, e, text) in enumerate(segs):
        if i == 0:
            continue
        pause = a - segs[i - 1][1]
        cue = CUE.search(text[:40])
        strong = cue and re.match(r"(step|number|part|the (first|second|third|next|last|final)|first|second|third|finally)", cue.group(0), re.I)
        cands.append((pause * 1.5 + (4.0 if strong else 2.0 if cue else 0), a, text))
    min_gap = max(20, total / (n * 2.5))
    picked = [(0.0, segs[0][2])]
    for sc, a, text in sorted(cands, reverse=True):
        if len(picked) >= n:
            break
        if all(abs(a - p) >= min_gap for p, _ in picked) and total - a >= 15:
            picked.append((a, text))
    picked.sort()
    print(f"Candidate chapters ({fmt(total)} video). Write a 2-5 word title for each, then run `check`:\n")
    for a, text in picked:
        print(f"   {fmt(a)}  <title>    opens with: \"{text[:80]}\"")


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    if a[0] == "check":
        sys.exit(check(a[1], a[a.index("--duration") + 1] if "--duration" in a else None))
    propose(a[1], int(a[a.index("--n") + 1]) if "--n" in a else 6)


if __name__ == "__main__":
    main()
