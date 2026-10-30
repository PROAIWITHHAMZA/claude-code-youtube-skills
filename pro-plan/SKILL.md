---
name: pro-plan
description: Build a weekly YouTube production plan that fits the hours the creator really has, warning when the cadence doesn't fit and proposing one that does. Use when the user asks how often to post, wants a content calendar, or feels behind on uploads.
---

# pro-plan: a schedule you can actually keep

Script: `plan.py` in this folder (normally `~/.claude/skills/pro-plan/`). No installs.

## Workflow
1. Ask for three things: **real hours per week**, **which days**, and the cadence they want
   (long videos and Shorts per week). Ask whether they use this pack (`--ai` timings) or edit by hand.
2. `python plan.py --hours 6 --days Mon,Wed,Sat --long 1 --shorts 2 --ai --start 2026-11-02`
3. If it says **DOESN'T FIT**, recommend the smaller cadence it proposes. Consistency beats volume:
   one video every two weeks for six months beats weekly for three weeks.
4. Add the topics: put the next video ideas (from /pro-gap, /pro-viral, /pro-comments) into the plan slots.
5. Offer the plan as a checklist the user can keep (a markdown file in their project).

## Defaults
Task timings are estimates. If the user knows their real times, edit `MANUAL` / `AI` at the top of `plan.py`.
Publish on the same weekday and hour every time.
