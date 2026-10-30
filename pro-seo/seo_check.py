"""pro-seo: check a YouTube description (and tags) before upload.

    python seo_check.py description.txt --keyword "search phrase" [--title "Title"] [--tags tags.txt]

Checks
  above the fold  the first ~150 characters (all that shows before "...more") include the keyword and say
                  what the viewer gets
  length          at least ~200 characters of real text; hard limit 5000
  chapters        a valid chapter list (0:00 first, 3+, 10s+ each)
  hashtags        YouTube ignores every hashtag if there are more than 15; the first 3 show above the title
  links           links present (resources, related video); flags shortened links that look like spam
  keyword         appears in the title and 2-3 times in the description, not stuffed
  tags            combined length under 500 characters
  disclosure      if the text mentions AI voice/host/avatar, reminds you to tick "Altered or synthetic content"
"""
import os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pro-chapters"))
try:
    from chapters import parse as parse_chapters
except ImportError:  # pro-chapters not installed next to this skill
    parse_chapters = None


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    with open(a[0], encoding="utf-8-sig") as fh:
        desc = fh.read()
    kw, title, tags = opt("--keyword"), opt("--title"), opt("--tags")
    res = []
    add = lambda lvl, msg: res.append((lvl, msg))
    fold = desc.strip()[:150]
    if kw:
        add("ok" if kw.lower() in fold.lower() else "FIX", f"above the fold: keyword {'found' if kw.lower() in fold.lower() else 'missing'} in the first 150 chars")
        n = desc.lower().count(kw.lower())
        add("ok" if 1 <= n <= 4 else "warn", f"keyword appears {n}x in the description" + (" (stuffing: keep to 2-4)" if n > 4 else ""))
        if title:
            add("ok" if kw.lower() in title.lower() else "FIX", f"keyword {'in' if kw.lower() in title.lower() else 'NOT in'} the title")
    else:
        add("info", "no --keyword: pass the phrase people actually search for")
    add("info", f"first 150 chars: \"{fold}\"")
    plain = re.sub(r"https?://\S+|#\w+|^\s*\d+:\d+.*$", "", desc, flags=re.M)
    nchar = len(desc)
    if nchar > 5000:
        add("FIX", f"{nchar} chars: YouTube's limit is 5000")
    elif len(plain.strip()) < 200:
        add("warn", f"only {len(plain.strip())} chars of real text: add 2-3 sentences on what the video covers")
    else:
        add("ok", f"{nchar} chars")
    if parse_chapters:
        ch = parse_chapters(desc)
        if not ch:
            add("warn", "no chapters: they add search entry points and help retention")
        else:
            bad = ch[0][0] != 0 or len(ch) < 3 or any(b[0] - a_[0] < 10 for a_, b in zip(ch, ch[1:]))
            add("FIX" if bad else "ok", f"{len(ch)} chapters" + (": invalid, run /pro-chapters check" if bad else ""))
    tagsin = re.findall(r"(?<!\w)#\w+", desc)
    if len(tagsin) > 15:
        add("FIX", f"{len(tagsin)} hashtags: over 15 and YouTube ignores all of them")
    else:
        add("ok" if tagsin else "warn", f"{len(tagsin)} hashtags" + (f"; the first 3 shown above the title: {' '.join(tagsin[:3])}" if tagsin else ": add 2-3"))
    links = re.findall(r"https?://\S+", desc)
    short = [l for l in links if re.search(r"bit\.ly|tinyurl|t\.co/|cutt\.ly|shorturl", l)]
    add("ok" if links else "info", f"{len(links)} links")
    if short:
        add("warn", f"shortened links look like spam to viewers and filters: {', '.join(short)}")
    if re.search(r"\b(ai[- ](voice|host|avatar|generated|presenter)|synthetic|text-to-speech|tts)\b", desc, re.I):
        add("info", "mentions AI voice/host: tick 'Altered or synthetic content' in YouTube Studio when uploading")
    if tags:
        with open(tags, encoding="utf-8-sig") as fh:
            tl = [t.strip() for t in re.split(r"[,\n]", fh.read()) if t.strip()]
        total = sum(len(t) for t in tl) + 2 * max(0, len(tl) - 1)
        add("FIX" if total > 500 else "ok", f"{len(tl)} tags, {total}/500 chars")
    for lvl, msg in res:
        print(f"{lvl:<5} {msg}")
    fixes = sum(1 for l, _ in res if l == "FIX")
    print(f"\n{'READY' if not fixes else f'{fixes} thing(s) to fix before upload'}")


if __name__ == "__main__":
    main()
