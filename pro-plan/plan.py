"""pro-plan: a weekly YouTube plan that fits the hours you actually have.

    python plan.py --hours 8 [--days Mon,Wed,Sat] [--long 1] [--shorts 2] [--start 2026-11-02] [--ai]

--hours   real hours per week for the channel
--days    the days you can work (hours are split evenly across them)
--long    long videos per week you'd like; --shorts the same for Shorts
--ai      use the Claude Code timings (script, voice, visuals and render are mostly automated)

Each task has an hour estimate. If the week doesn't fit, the plan says so and proposes the cadence that
does (for example one long video every two weeks), instead of a schedule that quietly fails by Thursday.
Order inside a video is fixed: research -> script -> record -> edit -> thumbnail/title -> publish.
"""
import datetime as dt, sys

MANUAL = {"long": [("Find the gap (research)", 1.5), ("Script + hook", 2.5), ("Record", 2.0), ("Edit", 5.0),
                   ("Thumbnail + title", 1.0), ("Description, chapters, upload", 0.5)],
          "short": [("Pick the moment", 0.25), ("Cut + vertical edit", 0.75), ("Title + upload", 0.25)]}
AI = {"long": [("Find the gap (/pro-gap)", 0.75), ("Script + hook (/pro-script)", 1.0), ("Record real footage (/pro-record)", 1.0),
               ("Render + review (/pro-video)", 1.5), ("Thumbnail + title (/pro-thumbs, /pro-title)", 0.5),
               ("SEO + chapters + upload (/pro-seo)", 0.5)],
      "short": [("Find Shorts (/pro-shorts)", 0.25), ("Review the cut + title", 0.25), ("Upload", 0.1)]}
WEEKLY = [("Reply to comments (/pro-comments)", 0.5), ("Check last video's retention (/pro-retention)", 0.25)]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def main():
    a = sys.argv[1:]
    if "--hours" not in a:
        sys.exit(__doc__)
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d
    hours = float(opt("--hours", 8))
    days = opt("--days", "Mon,Tue,Wed,Thu,Fri").split(",")
    nlong, nshort = int(opt("--long", 1)), int(opt("--shorts", 2))
    tasks = AI if "--ai" in a else MANUAL
    start = dt.date.fromisoformat(opt("--start", str(dt.date.today() + dt.timedelta(days=(7 - dt.date.today().weekday()) % 7))))
    need_long = sum(h for _, h in tasks["long"])
    need_short = sum(h for _, h in tasks["short"])
    need_week = sum(h for _, h in WEEKLY)
    need = need_long * nlong + need_short * nshort + need_week
    print(f"Needed: {need:.1f} h/week  ({nlong} long x {need_long:.1f} h, {nshort} shorts x {need_short:.1f} h, upkeep {need_week:.1f} h)")
    print(f"You have: {hours:.1f} h/week on {', '.join(days)}  ({'Claude Code timings' if '--ai' in a else 'manual timings'})")
    if need > hours:
        spare = hours - need_week - need_short * nshort
        weeks = need_long / spare if spare > 0 else None
        print(f"\nDOESN'T FIT: {need - hours:.1f} h short.")
        if weeks and weeks <= 4:
            print(f"Fits instead: 1 long video every {max(2, round(weeks + 0.49))} weeks + {nshort} shorts/week, "
                  f"or drop to {max(0, int((hours - need_week - need_long) / need_short))} shorts with 1 long/week.")
        else:
            print("Fits instead: Shorts only for now, or add hours. A consistent smaller cadence beats an ambitious one you miss.")
        print("Below, the full queue is laid out on your days: it runs into next week, which is that slower cadence in practice.\n")
    queue = []
    for v in range(nlong):
        queue += [(f"Long {v + 1}: {t}", h) for t, h in tasks["long"]]
    for s in range(nshort):
        queue += [(f"Short {s + 1}: {t}", h) for t, h in tasks["short"]]
    queue += WEEKLY
    per_day = hours / len(days)
    week, day_i, left, cal = 0, 0, per_day, {}
    for name, h in queue:
        rem = h
        while rem > 1e-6:
            if left <= 1e-6:
                day_i += 1
                if day_i >= len(days):
                    day_i, week = 0, week + 1
                left = per_day
            take = min(rem, left)
            d = start + dt.timedelta(weeks=week, days=DAYS.index(days[day_i]))
            cal.setdefault(d, []).append((name, take))
            rem -= take
            left -= take
    for d in sorted(cal):
        print(f"{d:%a %d %b}  ({sum(h for _, h in cal[d]):.1f} h)")
        for name, h in cal[d]:
            print(f"   {h:4.2f} h  {name}")
    print("\nPublish rule: same weekday and hour every time, so the audience learns when to expect you.")


if __name__ == "__main__":
    main()
