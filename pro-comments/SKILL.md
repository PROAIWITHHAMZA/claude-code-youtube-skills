---
name: pro-comments
description: Triage YouTube comments into questions, requests, criticism, praise and spam, then draft replies in the creator's voice for review and turn repeated questions into video ideas. Use when the user shares comments or wants help replying to their audience.
---

# pro-comments: reply to the right people first

Script: `triage.py` in this folder (normally `~/.claude/skills/pro-comments/`). No installs.

## Workflow
1. **Get the comments.** The user pastes or exports them (YouTube Studio > Comments), or Claude reads them
   from the watch page. Save them one per line in `comments.txt`, or as a CSV with a `comment` column.
2. `python triage.py comments.txt --out triage.md`
3. Fix any obvious wrong bucket by reading, then **draft replies** in order:
   - **question**: answer it fully in 1–3 sentences. If the video already answers it, give the timestamp.
   - **request**: thank them and say honestly whether it's planned. Collect these as video ideas.
   - **criticism**: check whether they're right. If right: thank them, correct it, pin the correction.
     If wrong: one calm, factual line. Never argue.
   - **praise**: reply only to the specific ones, and say something specific back.
   - **spam**: no reply. List them so the user can hide them.
4. Show the drafts as a numbered list matching the comment numbers. **The user posts replies themselves**:
   never post on their behalf without explicit approval for each reply.
5. Finish with "**Video ideas from comments**": questions or requests that came up two or more times.

## Voice
Write like the creator talks: short, warm, direct, no corporate phrases ("Thank you for your feedback!").
If `voice.md` exists in the user's project, follow it. If not, ask for 3 replies they've written before and match them.
