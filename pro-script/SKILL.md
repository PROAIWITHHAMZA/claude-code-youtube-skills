---
name: pro-script
description: Write a YouTube script that holds attention, with chapters, an on-screen note for every line, five scored hooks, and real sources for every fact. Use when the user wants a video script, a hook, an outline, or to improve an existing script.
---

# pro-script: a script built to be watched, not read

Script: `hook_score.py` in this folder (normally `~/.claude/skills/pro-script/`). Pure Python, no installs.

## Before writing, get three things (ask only for what's missing)
1. **The gap**: who it's for and what the top videos on this topic miss (run /pro-gap if unknown).
2. **The proof**: what this video will *show* (real footage, a real result, real numbers).
3. **Length**: default 5–8 minutes. Roughly 150 spoken words per minute.

## Write
1. **Five hooks**, each 12–28 words, each a different type: a number with stakes, a mistake the viewer is
   making, a before/after result, a contrarian claim, a question the video answers. Save them as `hooks.txt`.
2. `python hook_score.py hooks.txt`: rewrite until the best one is 72+ (STRONG). Show the user the scores.
   A score is a guide; never keep a hook that promises something the video doesn't deliver.
3. **The script**, in this shape:
   - **0:00 hook** (the winner), then one line on what they'll have by the end. No "welcome back".
   - **Chapters**: 3–7, each opens with its own mini-hook and ends by pulling into the next one
     ("…but that only works if…").
   - **Every 20–40 seconds**: a change (new visual, a demo, a number, a question) so attention resets.
   - **Payoff** delivered where promised, then one line of CTA tied to the next video, not "smash like".
4. Under every spoken line, an `ON SCREEN:` note saying exactly what the viewer sees (footage, graphic type,
   text on screen). This is what /pro-video turns into scenes.
5. **Sources**: every number or claim gets a source line (publisher, date, link). If you can't find a real
   source, cut the claim. Never invent statistics or quotes.

## Output
`script.md` with: hooks + scores, chapters with timestamps estimated from word counts, the script with
ON SCREEN notes, and a sources list. Offer to hand it to /pro-video.

## Style
Short sentences. Spoken English, not essay English. "You" more than "I". Cut adverbs and warm-up phrases.
Read each line aloud in your head: if it needs a breath in the middle, split it.
