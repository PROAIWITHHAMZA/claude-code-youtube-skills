---
name: pro-viral
description: Find outlier YouTube videos that performed far above their own channel's normal views (not just big channels) and what their titles share, so the user can learn which ideas the audience wants. Use when the user asks what's working in a niche, wants video ideas backed by data, or wants to study competitors.
---

# pro-viral: ideas the audience already voted for

Big channels get big views for anything. An outlier is a video that did **3x or more its own channel's
median**. That measures the idea, not the audience size.

Script: `outliers.py` in this folder (normally `~/.claude/skills/pro-viral/`). Reuses nothing; no installs.

## Workflow
1. **Collect real data.** Pick 5–10 channels in the niche, including small ones. For each, open their
   Videos tab (the built-in browser or Chrome) and record the last 15–30 videos as CSV:
   `channel,title,views,published` (published can be "3 weeks ago"). Never invent rows.
2. `python outliers.py videos.csv --min 3`
3. Open the top outliers and look at the thumbnail, the first 30 seconds and the top comments.
   Note what they promise.
4. Report:
   - the outliers, with their ratio
   - the shared traits the script found
   - **3 video ideas** for the user's channel, each one an outlier's *idea* made with the user's own angle
     and proof. Never a copy of the title or thumbnail.

## Rules
- Learn from the idea; never copy titles, thumbnails or scripts.
- Fewer than 3 videos from a channel gives no fair median; the script skips it.
