"""pro-title: check a YouTube title and its thumbnail text as a pair.

    python title_check.py "Title" [--thumb "THUMB TEXT"] [--keyword "search phrase"]
    python title_check.py titles.txt [--thumb ...] [--keyword ...]     one title per line, ranked

Checks (score out of 100):
  length     40-60 characters shows in full almost everywhere; past ~70 gets cut in search and on mobile
  keyword    the search phrase appears, ideally in the first 40 characters
  specific   a number, a named tool or a concrete result
  pair       the thumbnail adds new words instead of repeating the title
  thumb      thumbnail text of 4 words or fewer
  honest     no vague hype words that the video can't back up, at most one ALL-CAPS word
"""
import re, sys

STOP = set("a an the to of in on for with and or is are be how i my you your this that it its at by from we our "
           "what why when do does can will".split())
HYPE = ["insane", "shocking", "you won't believe", "unbelievable", "mind-blowing", "mind blowing", "crazy", "secret trick",
        "gone wrong", "100% guaranteed", "destroyed", "exposed", "must watch", "omg"]


def words(s):
    return [w for w in re.findall(r"[a-z0-9$%']+", s.lower()) if w not in STOP]


def check(title, thumb=None, keyword=None):
    out, pts = [], 0
    n = len(title)
    if 40 <= n <= 60:
        pts += 25
        out.append(f"ok    length {n} chars")
    elif n <= 70:
        pts += 17
        out.append(f"warn  length {n} chars: fine on desktop, may cut on mobile after: \"{title[:60]}…\"")
    elif n < 40:
        pts += 15
        out.append(f"warn  length {n} chars: room to add a result or number")
    else:
        pts += 5
        out.append(f"FIX   length {n} chars: search shows about \"{title[:68]}…\"")
    if keyword:
        i = title.lower().find(keyword.lower())
        if 0 <= i <= 40:
            pts += 20
            out.append(f"ok    keyword \"{keyword}\" at character {i}")
        elif i > 40:
            pts += 12
            out.append(f"warn  keyword \"{keyword}\" appears late (character {i}); move it forward")
        else:
            out.append(f"FIX   keyword \"{keyword}\" missing")
    else:
        pts += 12
        out.append("info  no --keyword given; add the phrase people search for")
    spec = bool(re.search(r"\d", title)) + bool(re.search(r"\b[A-Z][a-z]+[A-Z]?\w*\b", title[1:]))
    pts += 20 if spec else 6
    out.append("ok    specific (number or named tool)" if spec else "FIX   nothing concrete: add a number, tool or result")
    if thumb:
        shared = sorted(set(words(title)) & set(words(thumb)))
        tw = len(thumb.split())
        if len(shared) <= 1:
            pts += 15
            out.append(f"ok    thumbnail adds new words (shared: {', '.join(shared) or 'none'})")
        else:
            pts += 4
            out.append(f"FIX   thumbnail repeats the title: {', '.join(shared)}. Make it say why it matters, not what it is")
        pts += 10 if tw <= 4 else 5 if tw <= 6 else 0
        out.append(f"{'ok  ' if tw <= 4 else 'FIX '}  thumbnail text {tw} words" + ("" if tw <= 4 else ": cut to 4 or fewer"))
    else:
        pts += 15
        out.append("info  no --thumb given; pair check skipped")
    hype = [h for h in HYPE if h in title.lower()]
    caps = [w for w in re.findall(r"\b[A-Z]{3,}\b", title) if w not in ("AI", "API", "SEO", "CEO", "USA", "GPU", "CPU", "PDF", "CSV", "UK")]
    if hype or len(caps) > 1:
        out.append(f"FIX   hype: {', '.join(hype + caps)}. Viewers and YouTube punish titles the video can't back up")
    else:
        pts += 10
        out.append("ok    no hype words")
    return min(100, pts), out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    thumb, kw = opt("--thumb"), opt("--keyword")
    first = a[0]
    if first.endswith(".txt"):
        with open(first, encoding="utf-8-sig") as fh:
            titles = [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    else:
        titles = [first]
    res = sorted(((check(t, thumb, kw), t) for t in titles), key=lambda r: -r[0][0])
    for (s, lines), t in res:
        print(f"\n{s:3d}/100  {t}" + (f"   +  thumb: {thumb}" if thumb else ""))
        for l in lines:
            print("   " + l)


if __name__ == "__main__":
    main()
