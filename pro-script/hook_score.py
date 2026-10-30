"""pro-script hook scorer: rank opening hooks on six measurable signals.

    python hook_score.py hooks.txt          one hook per line (blank lines and # comments ignored)
    python hook_score.py "Hook one" "Hook two"

A hook is the first 1-2 sentences a viewer hears. Signals (0-100 each):
  concrete   numbers, money, time, named tools or places: proof this isn't generic
  stakes     what the viewer loses, wastes or gets wrong if they skip it
  gap        an open question or promise the video has to pay off
  viewer     talks to "you", not about the creator
  pace       12-28 words is the sweet spot for the opening; long hooks lose people
  clean      no warm-up filler ("hey guys", "in this video", "welcome back")
"""
import re, sys

WEIGHTS = {"concrete": 0.22, "stakes": 0.2, "gap": 0.2, "viewer": 0.13, "pace": 0.15, "clean": 0.1}
STAKES = r"\b(lose|losing|lost|waste|wasting|wasted|mistake|mistakes|wrong|stop|never|fail|failing|broke|costs?|" \
         r"paying|overpay|risk|behind|miss|missing|hurts?|killing|ruin|ban|banned|worse|slow|hours?)\b"
GAP = r"(\?|\bwhy\b|\bhow\b|\bwhat\b|\bhere'?s\b|\bthe one\b|\bsecret\b|\bnobody\b|\bmost people\b|\bactually\b|" \
      r"\bbut\b|\buntil\b|\binstead\b|\bturns out\b|\bthe real\b|\bby the end\b)"
FILLER = r"\b(hey guys|hi guys|welcome back|in this video|in today'?s video|today we('re| are) going to|" \
         r"before we (start|begin)|don'?t forget to subscribe|let'?s get started|so basically)\b"
CONCRETE = r"(\$\s?\d|\d+\s?(%|percent|k\b|x\b|minutes?|mins?|hours?|days?|seconds?|steps?|tools?|views?|dollars?)|\b\d{2,}\b)"


def score(h):
    low = h.lower()
    words = re.findall(r"[\w'$%]+", h)
    n = max(1, len(words))
    s = {}
    proper = len(re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-zA-Z]+", h))  # capitalised words mid-sentence: names, tools
    nums = len(re.findall(r"\d", h)) > 0
    s["concrete"] = min(100, 45 * len(re.findall(CONCRETE, low)) + 25 * nums + 15 * proper)
    s["stakes"] = min(100, 45 * len(re.findall(STAKES, low)))
    s["gap"] = min(100, 40 * len(re.findall(GAP, low)))
    you = len(re.findall(r"\b(you|your|you'?re|you'?ll|yourself)\b", low))
    me = len(re.findall(r"\b(i|me|my|i'?m|i'?ve)\b", low))
    s["viewer"] = min(100, 40 * you) - min(30, 10 * max(0, me - you))
    s["viewer"] = max(0, s["viewer"])
    s["pace"] = 100 if 12 <= n <= 28 else max(0, 100 - 8 * (12 - n)) if n < 12 else max(0, 100 - 6 * (n - 28))
    s["clean"] = 0 if re.search(FILLER, low) else 100
    total = round(sum(s[k] * w for k, w in WEIGHTS.items()))
    weakest = min(WEIGHTS, key=lambda k: s[k] * WEIGHTS[k] / max(WEIGHTS.values()) + s[k] / 1000)
    return total, s, weakest, n


TIPS = {
    "concrete": "add a real number, cost, time or tool name the video proves",
    "stakes": "say what the viewer loses or gets wrong without this",
    "gap": "open a question the video answers later (and make sure it does)",
    "viewer": "say 'you' and describe their problem, not your journey",
    "pace": "cut to 12-28 words; move detail to the second sentence",
    "clean": "delete the warm-up and start with the claim",
}


def verdict(t):
    return "STRONG" if t >= 72 else "WORKABLE" if t >= 55 else "WEAK"


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if len(args) == 1 and args[0].endswith(".txt"):
        with open(args[0], encoding="utf-8-sig") as fh:
            hooks = [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    else:
        hooks = args
    rows = sorted(((score(h), h) for h in hooks), key=lambda r: -r[0][0])
    for rank, ((total, s, weak, n), h) in enumerate(rows, 1):
        print(f"\n#{rank}  {total:3d}  {verdict(total):<8}  ({n} words)\n    {h}")
        print("    " + "  ".join(f"{k} {v}" for k, v in s.items()))
        if total < 85:
            print(f"    fix: {weak.upper()}: {TIPS[weak]}")


if __name__ == "__main__":
    main()
