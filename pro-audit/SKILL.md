---
name: pro-audit
description: Audit a YouTube channel from its video list and Studio numbers - consistency, packaging (CTR), retention, direction and focus - and end with the ONE fix that matters most right now. Use when the user asks what's wrong with their channel, why growth stalled, or what to improve first.
---

# pro-audit: one fix, not twenty

Most audits give a long list nobody acts on. This one checks the levers in order of impact and stops at
the first broken one.

Script: `audit.py` in this folder (normally `~/.claude/skills/pro-audit/`). Reuses /pro-viral's parsers.

## Workflow
1. **Get the data.** Best: YouTube Studio > Content (or Analytics > Advanced mode > Content), exported with
   title, views, published date, duration, impressions CTR and average view duration. If there's no Studio access,
   read the public Videos tab (title, views, age only); the CTR and retention checks are then skipped.
2. `python audit.py channel.csv`
3. Present:
   - the scorecard (one line per lever)
   - **THE ONE FIX**, as a concrete action for the next 2–4 weeks
   - which skill in this pack does that work (/pro-plan, /pro-thumbs, /pro-retention, /pro-gap…)
4. Don't pile on. Mention the other failing levers as "after this".

## Order of levers
consistency → packaging (CTR) → retention → direction (recent vs median) → focus (which topics win)
