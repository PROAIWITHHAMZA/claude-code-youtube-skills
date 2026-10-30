"""pro-comments: sort YouTube comments into what needs a reply first.

    python triage.py comments.txt|comments.csv [--out triage.md]

Input: a text file with one comment per line, or a CSV with a column named like "comment"/"text"
(and optionally "author", "likes"). YouTube Studio > Comments lets you copy them; Claude can also
collect them from the watch page.

Buckets, in reply order:
  question    someone is stuck or asking how: answer these first, they become FAQ and video ideas
  request     "make a video on...": the free topic research
  criticism   disagreement or a correction: check it, thank them, fix it if they are right
  praise      short thanks: a heart is enough, reply to the detailed ones
  spam        links, "check my channel", crypto/WhatsApp/Telegram: hide, never reply
  other
Writes a markdown file with every comment numbered, so replies can be drafted against the numbers.
"""
import csv, re, sys

RULES = [
    ("spam", r"(https?://|www\.|t\.me/|wa\.me|whatsapp|telegram|crypto|bitcoin|forex|invest(ment)? with|"
             r"check (out )?my channel|sub(scribe)? to me|sub4sub|dm me|\+\d{7,})"),
    ("request", r"(make a video|next video|please (do|make|cover)|can you (do|make|cover)|tutorial on|video on|part 2|"
                r"would love (a|to see)|do one on)"),
    ("question", r"(\?|^(how|what|why|where|when|which|can|could|does|do|is|are|will|should)\b|\bhow (do|can|did)\b|"
                 r"\bi('m| am) stuck\b|\bdoesn'?t work\b|\bnot working\b|\berror\b|\bhelp\b)"),
    ("criticism", r"(\bwrong\b|\bactually\b|\bmisleading\b|\bclickbait\b|\bnot true\b|\bdisagree\b|\bbut\b.*\bdoesn'?t\b|"
                  r"\bfake\b|\btoo (fast|slow|long|basic)\b|\bboring\b|\bwaste\b|\bmistake\b)"),
    ("praise", r"(thank|thanks|great|amazing|awesome|love|helpful|best|perfect|brilliant|nice|underrated|gem)"),
]
ORDER = ["question", "request", "criticism", "praise", "other", "spam"]


def classify(text):
    t = text.lower().strip()
    for name, rx in RULES:
        if re.search(rx, t):
            return name
    return "other"


def load(path):
    if path.lower().endswith(".csv"):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        key = next(k for k in rows[0] if re.search(r"comment|text|body|content", k, re.I))
        auth = next((k for k in rows[0] if re.search(r"author|user|name", k, re.I)), None)
        likes = next((k for k in rows[0] if re.search(r"like", k, re.I)), None)
        return [(r[key], r.get(auth, "") if auth else "", int(r.get(likes) or 0) if likes else 0) for r in rows if r[key].strip()]
    with open(path, encoding="utf-8-sig") as fh:
        return [(l.strip(), "", 0) for l in fh if l.strip()]


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    out = a[a.index("--out") + 1] if "--out" in a else None
    items = load(a[0])
    groups = {k: [] for k in ORDER}
    for n, (text, author, likes) in enumerate(items, 1):
        groups[classify(text)].append((n, text, author, likes))
    lines = [f"# Comment triage: {len(items)} comments\n"]
    for k in ORDER:
        g = sorted(groups[k], key=lambda x: -x[3])
        if not g:
            continue
        lines.append(f"\n## {k.upper()} ({len(g)})\n")
        for n, text, author, likes in g:
            meta = " · ".join(x for x in (author, f"{likes} likes" if likes else "") if x)
            lines.append(f"- **#{n}** {text}" + (f"  _({meta})_" if meta else ""))
    md = "\n".join(lines) + "\n"
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(md)
    print(md if not out else f"wrote {out}")
    print("  " + "  ".join(f"{k} {len(groups[k])}" for k in ORDER))


if __name__ == "__main__":
    main()
