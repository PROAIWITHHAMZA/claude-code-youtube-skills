"""pro-gap: turn real YouTube search results into a gap report.

    python gap.py results.json [--flag paid,course,$] [--out gap.md] [--today 2026-10-30]

results.json: the search results as Claude collected them from the real YouTube results page:
  {"query": "make youtube video with claude code",
   "results": [{"title": "...", "channel": "...", "views": "1.1M", "age": "3 months ago", "duration": "18:42"}, ...]}

Measures
  demand      total and median views, views per day (fresh demand vs old demand)
  freshness   how old the top results are: big but old videos = demand with stale supply (the best gap)
  crowding    how many top results are under 3 months old
  angles      the words and promises the titles repeat (what everyone already says)
  flags       how many titles hit --flag words (e.g. paid tools, hype, "$/month"): the angle to be different on
The report ends with the questions that decide the gap; Claude answers them from the pages it read.
"""
import json, re, statistics, sys, datetime as dt
from collections import Counter
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pro-viral"))
from outliers import views as parse_views, age_days, STOP  # noqa: E402


def mins(d):
    if not d:
        return None
    p = [int(x) for x in re.findall(r"\d+", d)]
    return sum(x * 60 ** i for i, x in enumerate(reversed(p))) / 60 if p else None


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    today = dt.date.fromisoformat(opt("--today")) if opt("--today") else dt.date.today()
    with open(a[0], encoding="utf-8-sig") as fh:
        data = json.load(fh)
    res = []
    for r in data["results"]:
        v, ag = parse_views(str(r.get("views", ""))), age_days(str(r.get("age", "")), today)
        if v is None:
            continue
        res.append(dict(r, v=v, days=ag, vpd=v / ag if ag else None, mins=mins(r.get("duration"))))
    if not res:
        sys.exit("no usable results (need views on each)")
    L = [f"# Gap report: \"{data.get('query', '')}\"\n", f"{len(res)} real results, collected {today}\n",
         "| # | views | age | views/day | length | channel | title |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(res, 1):
        L.append(f"| {i} | {r['v']:,.0f} | {r.get('age', '')} | {r['vpd']:,.0f} | {r.get('duration', '')} | {r.get('channel', '')} | {r['title']} |"
                 if r["vpd"] else f"| {i} | {r['v']:,.0f} | {r.get('age', '')} | - | {r.get('duration', '')} | {r.get('channel', '')} | {r['title']} |")
    vs = [r["v"] for r in res]
    ds = [r["days"] for r in res if r["days"]]
    fresh = [r for r in res if r["days"] and r["days"] <= 90]
    stale_big = [r for r in res if r["days"] and r["days"] >= 365 and r["v"] >= statistics.median(vs)]
    L += ["\n## Signals\n",
          f"- **Demand:** {sum(vs):,.0f} views across the top {len(res)}; median {statistics.median(vs):,.0f}.",
          f"- **Freshness:** median age {statistics.median(ds) / 30:.0f} months." if ds else "- **Freshness:** unknown (no ages).",
          f"- **Crowding:** {len(fresh)} of {len(res)} are under 3 months old" +
          (" (crowded: you need a clearly different angle)." if len(fresh) >= len(res) / 2 else " (room to be the fresh answer)."),
          f"- **Stale but big:** {len(stale_big)} results are a year+ old with above-median views" +
          (": demand with old supply. Strong gap signal." if stale_big else ".")]
    lens = [r["mins"] for r in res if r["mins"]]
    if lens:
        L.append(f"- **Length:** median {statistics.median(lens):.0f} min (range {min(lens):.0f}-{max(lens):.0f}).")
    words = Counter(w for r in res for w in set(re.findall(r"[a-z0-9$']+", r["title"].lower())) if w not in STOP and len(w) > 2)
    L.append(f"- **Angles everyone uses:** {', '.join(f'{w} ({n})' for w, n in words.most_common(10) if n >= 2) or 'no repeated words'}.")
    if opt("--flag"):
        flags = [f.strip().lower() for f in opt("--flag").split(",") if f.strip()]
        hit = [r for r in res if any(f in (r["title"] + " " + r.get("note", "")).lower() for f in flags)]
        L.append(f"- **Flagged ({', '.join(flags)}):** {len(hit)} of {len(res)} titles/notes" +
                 (f": {'; '.join(r['title'][:50] for r in hit[:4])}" if hit else "."))
    L += ["\n## Decide the gap (answer from the videos you actually opened)\n",
          "1. What does every top video promise, and what do the top comments say it failed to deliver?",
          "2. Which viewer is left out (beginner, no budget, non-US, a specific tool or job)?",
          "3. What can this channel *show* (real footage, real numbers) that the others only *say*?",
          "4. One-line gap: \"High demand for ___, but every top video ___. Ours ___.\""]
    md = "\n".join(L) + "\n"
    if opt("--out"):
        with open(opt("--out"), "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"wrote {opt('--out')}")
    print(md)


if __name__ == "__main__":
    main()
