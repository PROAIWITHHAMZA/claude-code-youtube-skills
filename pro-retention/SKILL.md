---
name: pro-retention
description: Read a YouTube Studio audience-retention export and find exactly where viewers leave - intro hold at 30 seconds, the steepest drops matched to what was said, rewatch spikes, and the ending - with a marked chart. Use when the user shares retention data or asks why viewers stop watching.
---

# pro-retention: where viewers leave, and why

Script: `retention.py` in this folder (normally `~/.claude/skills/pro-retention/`). Needs `pip install pillow` for the chart.

## Get the data (the user does this; it's their Studio account)
YouTube Studio > Analytics > **Advanced mode** > select the video > metric **Audience retention** > Export > CSV.
Also get the video's captions (`.srt`), so drops can be matched to the words.

## Workflow
1. `python retention.py retention.csv --duration 6:30 --script captions.srt --chart retention.png`
2. Read the chart with the Read tool, then explain in plain words:
   - **Intro hold** under 50 % at 0:30: the hook or the first 30 seconds is the problem. Fix that first.
   - **Each cliff**: what was on screen and said there. Usual causes: a slow setup, a repeated point, a long
     static visual, an off-topic tangent, or a "that's it" moment that sounds like an ending.
   - **Rewatch bumps**: what people replayed. Make more of that.
3. Give **three concrete changes for the next video**, each tied to a timestamp in this one.

## Rules
- Compare against the video's own curve, not someone else's average.
- Don't over-read videos under ~1,000 views: the curve is noise.
