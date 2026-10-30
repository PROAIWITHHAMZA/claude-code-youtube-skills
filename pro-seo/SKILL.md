---
name: pro-seo
description: Write and check a YouTube description, tags and hashtags for search - keyword above the fold, chapters, hashtag limits, links, tag length and AI-disclosure reminders. Use when the user is preparing an upload, needs a description or tags, or asks why a video isn't found in search.
---

# pro-seo: an upload that can be found

Script: `seo_check.py` in this folder (normally `~/.claude/skills/pro-seo/`). It reuses /pro-chapters' parser.

## Workflow
1. **Find the target phrase**: what someone would type to find this video. Check YouTube's search suggestions
   (type the start of the phrase in the real YouTube search box). Pick one main phrase and 2–3 variants.
2. **Write the description:**
   - First 150 characters: the phrase plus what the viewer gets. This is all that shows before "...more".
   - 2–4 short paragraphs on what's covered, in plain words people search for.
   - Chapters (from /pro-chapters).
   - Resources and links mentioned in the video; credit anything you used or were inspired by.
   - A disclosure line if an AI voice or presenter is used.
   - 2–3 hashtags at the end.
3. **Tags**: the phrase, its variants, the main tool names, and the channel name. Under 500 characters total.
   Tags matter little; don't spend long on them.
4. `python seo_check.py description.txt --keyword "phrase" --title "Title" --tags tags.txt` and fix every `FIX`.
5. Give the user the final description, tags and a reminder of the upload checklist:
   captions file uploaded, chapters showing, "Altered or synthetic content" ticked if AI voice/host.

## Rules
- Never stuff the keyword. 2–4 natural mentions.
- More than 15 hashtags and YouTube ignores all of them.
- Don't use other creators' names or brands as tags to steal their traffic.
