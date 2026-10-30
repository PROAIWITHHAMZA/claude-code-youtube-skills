# pro-* skills for Claude Code: run a YouTube channel with real work

**Created by Hamza Tahir**

16 Claude Code skills that do the work, not just write about it: they render videos, test thumbnails at feed size,
record real footage, edit raw takes and read your analytics. Every script runs locally with free tools.

| Skill | What it does |
|---|---|
| **Find the idea** | |
| `/pro-gap` | Reads the real YouTube results for a topic and reports the gap: demand, freshness, crowding, repeated angles |
| `/pro-viral` | Finds outliers (3x+ their own channel's median) and what their titles share |
| `/pro-audit` | Scores your channel's levers and ends with ONE fix |
| `/pro-plan` | A weekly plan that fits your real hours, and warns when it doesn't |
| **Make it** | |
| `/pro-script` | Script with chapters, ON SCREEN notes, sources, and 5 hooks scored on 6 signals |
| `/pro-record` | Real screen footage (InPrivate browser or one window), with crop and blur for privacy |
| `/pro-edit` | Transcribes a raw take locally and cuts dead air, filler words and retakes |
| `/pro-video` | JSON spec in, finished 1080p video out: voice, motion graphics, footage, captions, music |
| `/pro-shorts` | Finds the Shorts inside a long video and cuts them to 9:16 |
| **Package it** | |
| `/pro-title` | Checks the title and the thumbnail text as one pair |
| `/pro-thumbs` | 3 thumbnail layouts, tested at 360/168/120 px, scored on measured letter size and contrast |
| `/pro-seo` | Description, tags and hashtags checked against YouTube's limits |
| `/pro-chapters` | Proposes chapters from captions and checks YouTube's chapter rules |
| `/pro-brand` | Profile picture at real circle sizes, and a banner checked against every device crop |
| **Grow it** | |
| `/pro-retention` | Studio retention export → intro hold, the steepest drops with what was said there, rewatches |
| `/pro-comments` | Triage comments (questions first, spam out) and draft replies in your voice |

## Install
1. Install Python 3.10+.
2. Copy every `pro-*` folder into `~/.claude/skills/` (Windows: `C:\Users\<you>\.claude\skills\`),
   or run `install.ps1` (Windows) from this folder.
3. Run `pip install edge-tts pillow imageio-ffmpeg faster-whisper numpy`.
4. Start a new Claude Code session and type `/pro-` to see them.

Keep the folders side by side: a few skills share helpers (`pro-seo` uses `pro-chapters`, `pro-shorts` uses
`pro-edit`, `pro-audit` and `pro-gap` use `pro-viral`).

Premium mode of `/pro-video` (cinematic HTML scenes rendered in Edge) also needs `pip install playwright`.

## Credit
Inspired by the open-source [youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) pack by
Jake Schincariol (MIT). The pro-* skills here are written from scratch by Hamza Tahir.

## Honest notes
- Claude Code needs a paid Claude plan. Every tool these skills use is free.
- `/pro-record` is Windows-only. Fonts look best on Windows (Segoe UI); other systems fall back to Arial or DejaVu.
- Scores are measured heuristics to compare options, not predictions of views.
- If you use an AI voice or an AI presenter, tick YouTube's "Altered or synthetic content" box.
