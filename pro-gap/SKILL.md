---
name: pro-gap
description: Research a topic on the real YouTube search results page (views, age, length, what each top video actually does) and report the content gap - high demand that nobody serves well - as a one-line angle for a new video. Use when the user is choosing a video topic or asks what to make next.
---

# pro-gap: find what nobody covers well, before writing anything

Script: `gap.py` in this folder (normally `~/.claude/skills/pro-gap/`). Reuses /pro-viral's parsers.

## Workflow
1. **Search for real.** Open `https://www.youtube.com/results?search_query=<phrase>` in the built-in browser
   (or Chrome if the user prefers) and read the page text. Use the phrase a viewer would type.
   Try 2–3 variants of the phrase.
2. **Record the top 8–10 results** exactly as shown: title, channel, views, age, duration. Open the top 3–4
   videos and note in `note` what they actually do (which tools, paid or free, what's missing, what the top
   comments complain about). Save as `results.json`:
   ```json
   {"query": "...", "results": [{"title": "...", "channel": "...", "views": "1.1M", "age": "4 months ago",
                                 "duration": "18:42", "note": "uses paid ElevenLabs; no real result shown"}]}
   ```
3. `python gap.py results.json --flag "paid,$,insane" --out gap.md`. Put words that mark the angle you
   want to be different on into `--flag`.
4. Answer the four "decide the gap" questions at the end of the report, from what you actually saw.
5. Give the user **one line**: "High demand for ___, but every top video ___. Ours ___." plus 3 title ideas
   (check them with /pro-title).

## Rules
- Only real results from the real page, with the date collected. Never estimate views.
- The gap must be something the user can actually deliver and *show*.
