---
name: pro-title
description: Write and check YouTube titles as a pair with the thumbnail text - length and truncation, keyword position, specificity, overlap with the thumbnail, and hype. Use when the user needs a title, has several title options, or asks whether a title and thumbnail work together.
---

# pro-title: title and thumbnail as one package

The title and the thumbnail are read together in under a second. The title says **what** it is
(searchable, specific). The thumbnail says **why it matters** (2–4 words, a feeling or result). If they say
the same thing, half the package is wasted.

Script: `title_check.py` in this folder (normally `~/.claude/skills/pro-title/`). No installs.

## Workflow
1. Find the **search phrase** people actually type (YouTube's search suggestions, or /pro-gap).
2. Write **8 titles**, mixing shapes: result ("I…"), how-to with a number, mistake/warning, comparison,
   question. Keep the phrase in the first 40 characters. Save them as `titles.txt`.
3. `python title_check.py titles.txt --keyword "phrase" --thumb "THUMB TEXT"`: ranks them all.
4. Fix every `FIX` line, then show the user the top 3 with scores and one sentence on why each works.
5. If the thumbnail text repeats the title, rewrite the thumbnail text instead of the title.

## Rules
- Specific beats clever: numbers, tool names, a real result.
- Never promise what the video doesn't show. Misleading titles get punished in satisfaction metrics.
- One ALL-CAPS word at most. No "insane", "shocking", "you won't believe".
- 40–60 characters reads in full almost everywhere.
