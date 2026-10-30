"""pro-viral: find the outlier videos (far above their own channel's normal) and what they share.

    python outliers.py videos.csv [--min 3] [--today 2026-10-30]

videos.csv columns (header names are matched loosely):
  channel, title, views, published     published = a date (2026-09-14) or an age ("3 weeks ago")
Optional: duration.

For each channel, the median views is "normal". A video at --min times its channel median or more is an
outlier. Small channels' 50k hits count the same as big channels' 5M hits, which is the point: it measures
the idea, not the audience. Then it lists what the outlier titles have in common versus the rest.
"""
import csv, datetime as dt, re, statistics, sys
from collections import Counter

STOP = set("a an the to of in on for with and or is are be how i my you your this that it at by from we our what why "
           "when do does can will vs".split())


def col(head, *names):
    for i, h in enumerate(head):
        if any(n in h.lower() for n in names):
            return i
    return None


def views(v):
    v = v.strip().lower().replace(",", "").replace(" views", "")
    m = re.match(r"([\d.]+)\s*([kmb]?)", v)
    if not m:
        return None
    return float(m[1]) * {"": 1, "k": 1e3, "m": 1e6, "b": 1e9}[m[2]]


def age_days(v, today):
    v = v.strip().lower()
    try:
        return max(1, (today - dt.date.fromisoformat(v[:10])).days)
    except ValueError:
        pass
    m = re.search(r"(\d+)\s*(minute|hour|day|week|month|year)", v)
    if not m:
        return None
    return max(1, int(m[1]) * {"minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}[m[2]])


def traits(t):
    out = []
    if re.search(r"\d", t):
        out.append("has a number")
    if "?" in t:
        out.append("question")
    if re.search(r"\b(i|my|me)\b", t, re.I):
        out.append("first person (I/my)")
    if re.search(r"\b(you|your)\b", t, re.I):
        out.append("talks to 'you'")
    if re.search(r"\bhow to\b", t, re.I):
        out.append("'how to'")
    if re.search(r"\b(vs|versus|better than|instead of)\b", t, re.I):
        out.append("comparison")
    if re.search(r"\$|\bfree\b|\bmoney\b|\bpaid\b", t, re.I):
        out.append("money / free")
    if re.search(r"\b(stop|never|don'?t|mistake|wrong|worst)\b", t, re.I):
        out.append("warning / negative")
    out.append("short (<45 chars)" if len(t) < 45 else "long (60+ chars)" if len(t) > 60 else "medium length")
    return out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    k = float(a[a.index("--min") + 1]) if "--min" in a else 3.0
    today = dt.date.fromisoformat(a[a.index("--today") + 1]) if "--today" in a else dt.date.today()
    with open(a[0], encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    head = rows[0]
    ci, ti, vi, pi = col(head, "channel"), col(head, "title"), col(head, "view"), col(head, "publish", "date", "age", "upload")
    vids = []
    for r in rows[1:]:
        v = views(r[vi]) if vi is not None else None
        if not v:
            continue
        ch = r[ci] if ci is not None else "(one channel)"
        age = age_days(r[pi], today) if pi is not None else None
        vids.append({"ch": ch, "title": r[ti], "views": v, "age": age, "vpd": v / age if age else None})
    by = {}
    for x in vids:
        by.setdefault(x["ch"], []).append(x)
    outl, rest = [], []
    for ch, xs in by.items():
        if len(xs) < 3:
            print(f"note: {ch} has {len(xs)} videos; need 3+ for a fair median, skipped")
            continue
        med = statistics.median(x["views"] for x in xs)
        for x in xs:
            x["ratio"] = x["views"] / med
            (outl if x["ratio"] >= k else rest).append(x)
    outl.sort(key=lambda x: -x["ratio"])
    print(f"\n{len(outl)} outliers (>= {k:g}x their channel median) out of {len(outl) + len(rest)} videos:\n")
    for x in outl:
        vpd = f"{x['vpd']:,.0f}/day" if x["vpd"] else ""
        print(f"  {x['ratio']:5.1f}x  {x['views']:>12,.0f} views  {vpd:>12}  [{x['ch']}]  {x['title']}")
    if outl and rest:
        to, tr = Counter(t for x in outl for t in traits(x["title"])), Counter(t for x in rest for t in traits(x["title"]))
        print("\nWhat outlier titles do more often than the rest:")
        diffs = sorted(((to[t] / len(outl) - tr[t] / len(rest), t) for t in set(to) | set(tr)), reverse=True)
        for d, t in diffs[:5]:
            if d > 0.05:
                print(f"  {t:<24} {100 * to[t] / len(outl):3.0f}% of outliers vs {100 * tr[t] / len(rest):3.0f}% of the rest")
        wo = Counter(w for x in outl for w in set(re.findall(r"[a-z0-9$']+", x["title"].lower())) if w not in STOP)
        common = [w for w, n in wo.most_common(12) if n >= 2]
        if common:
            print(f"\nWords repeated across outliers: {', '.join(common)}")


if __name__ == "__main__":
    main()
