---
name: pro-chapters
description: Create and validate YouTube chapters - propose chapter breaks from a captions file, write short titles, and check every rule YouTube enforces (0:00 first, 3+ chapters, 10s minimum, ascending). Use when the user needs chapters or timestamps, or their chapters aren't showing on YouTube.
---

# pro-chapters: chapters that actually show up

YouTube silently ignores the whole chapter list if one rule is broken. This skill checks every rule and
proposes breaks from what was actually said.

Script: `chapters.py` in this folder (normally `~/.claude/skills/pro-chapters/`). No installs.

## Workflow
**No chapters yet:**
1. Get captions: the `.srt` from /pro-video or /pro-edit, or YouTube Studio > Subtitles > download.
2. `python chapters.py propose captions.srt --n 6`: lists candidate breaks with the sentence that opens each.
3. Write a 2–5 word title for each: what the viewer gets, not "Part 2". Drop or merge breaks that are too close.

**Check (always, before upload):**
`python chapters.py check description.txt --duration 6:30` and fix every `FIX` line.

## Rules YouTube enforces
- The first timestamp is `0:00`.
- At least 3 chapters.
- Every chapter is 10 seconds or longer.
- Timestamps go up, one per line, at the start of the line.

## Good chapter titles
Searchable and specific ("Score your hook", not "Step 3"). Under ~40 characters. Chapters show in search
results, so each one is another way to be found.
