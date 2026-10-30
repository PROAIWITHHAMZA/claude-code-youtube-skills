---
name: pro-shorts
description: Find the best YouTube Shorts inside a long video (scored on hook, standalone opening, payoff, pace and length) and cut them to vertical 9:16. Use when the user wants Shorts, clips or vertical videos from an existing video.
---

# pro-shorts: Shorts that work on their own

A good Short is not a random 40 seconds. It opens with a hook, makes sense without the long video, and
ends on a payoff. This skill scores every window of whole sentences and picks the best ones that don't overlap.

Script: `shorts.py` in this folder (normally `~/.claude/skills/pro-shorts/`). It uses /pro-edit's transcriber
and /pro-chapters' caption reader, so install the whole pack together.

## Workflow
1. `python shorts.py video.mp4 --srt captions.srt --n 5` (or leave out `--srt` to transcribe locally).
2. Read the candidates. Reject any that need context from earlier in the video, even if it scored well.
3. Cut the winners:
   - screens, slides or footage: `--cut` (the whole frame over a blurred fill)
   - a face: `--cut --crop --x 0.5` (full-height crop; `--x` moves it to keep the face centred)
   - `--out DIR` sets where the clips go.
4. Grab a frame from each clip with ffmpeg and look at it. Is the subject in frame? Is the text readable on a phone?
5. Write a title for each Short (under 40 characters, the hook in words) and show them with the clips.

## Scoring (out of 100)
hook 30 (question, number, "you", a strong claim) · standalone 20 (doesn't open with "and/so/this/it") ·
payoff 20 (ends a full sentence on a result or instruction) · pace 15 (2.2–3.4 words/s) · length 15 (30–50 s best).
