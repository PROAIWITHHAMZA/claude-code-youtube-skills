"""pro-audit: a channel audit that ends in ONE fix, not a list of twenty.

    python audit.py channel.csv [--today 2026-10-30]

channel.csv: one row per video. Columns matched loosely:
  title, views, published (date or "3 weeks ago")      required
  duration (m:ss), likes, comments, ctr (%), avd (m:ss or %)   optional, used when present
YouTube Studio > Content lets you export this; Claude can also read it from the channel's Videos tab.

Checks, in priority order. The first one that fails is THE fix:
  1 consistency  long gaps between uploads (median gap, longest gap, last upload)
  2 packaging    CTR under 4 % (if given), or titles far from the channel's own best performers
  3 retention    average view duration under 35 % of length (if given)
  4 direction    the last 5 videos vs the channel median: growing, flat or falling
  5 focus        views spread: are a few topics carrying the channel?
"""
import csv, datetime as dt, re, statistics, sys
from collections import Counter

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "pro-viral"))
from outliers import views as parse_views, age_days, col, STOP  # noqa: E402


def secs(v):
    v = (v or "").strip()
    if not v:
        return None
    if ":" in v:
        p = [float(x) for x in v.split(":")]
        return sum(x * 60 ** i for i, x in enumerate(reversed(p)))
    try:
        return float(v.rstrip("%s"))
    except ValueError:
        return None


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    today = dt.date.fromisoformat(a[a.index("--today") + 1]) if "--today" in a else dt.date.today()
    with open(a[0], encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    h = rows[0]
    ti, vi, pi = col(h, "title"), col(h, "view"), col(h, "publish", "date", "age", "upload")
    di, ci, ai = col(h, "duration", "length"), col(h, "ctr", "click"), col(h, "avd", "average view", "avg")
    vids = []
    for r in rows[1:]:
        v = parse_views(r[vi])
        age = age_days(r[pi], today)
        if v is None or age is None:
            continue
        vids.append({"title": r[ti], "views": v, "age": age, "dur": secs(r[di]) if di is not None else None,
                     "ctr": secs(r[ci]) if ci is not None else None, "avd": r[ai] if ai is not None else None})
    if len(vids) < 3:
        sys.exit("need at least 3 videos")
    vids.sort(key=lambda x: x["age"])  # newest first
    med = statistics.median(x["views"] for x in vids)
    findings = []
    ages = [x["age"] for x in vids]
    gaps = [b - a_ for a_, b in zip(ages, ages[1:])]
    mg = statistics.median(gaps) if gaps else 0
    last = ages[0]
    cons_bad = last > max(21, 2 * mg) or (gaps and max(gaps) > 45)
    findings.append(("consistency", cons_bad,
                     f"last upload {last} days ago; median gap {mg:.0f} days; longest gap {max(gaps) if gaps else 0} days",
                     f"Publish on a fixed day every {7 if mg <= 10 else 14} days for the next 8 weeks, with no gaps. "
                     "Plan it with /pro-plan so the cadence fits your hours."))
    ctrs = [x["ctr"] for x in vids if x["ctr"] is not None]
    if ctrs:
        mc = statistics.median(ctrs)
        findings.append(("packaging", mc < 4, f"median CTR {mc:.1f}%",
                         "Thumbnails and titles are the bottleneck. Re-test the next three with /pro-thumbs and /pro-title, "
                         "and swap the thumbnail on your two most-shown, lowest-CTR videos."))
    else:
        top = sorted(vids, key=lambda x: -x["views"])[:3]
        tl = statistics.median(len(x["title"]) for x in top)
        al = statistics.median(len(x["title"]) for x in vids)
        findings.append(("packaging", abs(tl - al) > 15, f"best videos' titles ~{tl:.0f} chars vs channel ~{al:.0f} chars",
                         "Your best titles have a different shape from the rest. Write the next titles like your top three."))
    avds = []
    for x in vids:
        if x["avd"] and x["dur"]:
            s = x["avd"].strip()
            avds.append(float(s.rstrip("%")) if s.endswith("%") else 100 * (secs(s) or 0) / x["dur"])
    if avds:
        ma = statistics.median(avds)
        findings.append(("retention", ma < 35, f"median view duration {ma:.0f}% of length",
                         "Viewers leave early. Run /pro-retention on your most-viewed video and fix the first 30 seconds of the next one."))
    recent = statistics.median(x["views"] for x in vids[:5])
    trend = recent / med
    findings.append(("direction", trend < 0.7, f"last 5 videos at {trend:.2f}x the channel median ({recent:,.0f} vs {med:,.0f})",
                     "Recent topics are under-performing. Run /pro-viral on your own channel and /pro-gap on your best topic, "
                     "and make the next video in that lane."))
    words = Counter(w for x in vids for w in set(re.findall(r"[a-z0-9']+", x["title"].lower())) if w not in STOP and len(w) > 2)
    winners = Counter(w for x in vids if x["views"] >= 2 * med for w in set(re.findall(r"[a-z0-9']+", x["title"].lower())) if w not in STOP and len(w) > 2)
    lane = [w for w, n in winners.most_common(5) if n >= 2]
    findings.append(("focus", False, f"words in your 2x+ videos: {', '.join(lane) or 'no repeated theme yet'}", ""))
    print(f"Channel: {len(vids)} videos, median {med:,.0f} views\n")
    fix = next((f for f in findings if f[1]), None)
    for name, bad, detail, _ in findings:
        print(f"  {'FIX ' if bad else 'ok  '} {name:<12} {detail}")
    print("\nTHE ONE FIX:")
    print(f"  {fix[0].upper()}: {fix[3]}" if fix else
          "  Nothing is broken. Double down: more videos in your best lane (" + (", ".join(lane) or "see /pro-viral") + ").")
    best = sorted(vids, key=lambda x: -x["views"])[:3]
    print("\nYour top 3:")
    for x in best:
        print(f"  {x['views']:>10,.0f}  {x['title']}")


if __name__ == "__main__":
    main()
