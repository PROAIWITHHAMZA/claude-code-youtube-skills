---
name: pro-record
description: Record real screen footage for videos on Windows - a web page in a clean Edge InPrivate window or one app window - with scripted scrolling and typing, crop and blur boxes for privacy, and a black-screen check. Use when the user needs real footage, a screen recording, or a demo clip for a video.
---

# pro-record: real footage, nothing private in it

Real footage is what separates a real tutorial from a slideshow. This records it without leaking anything.

Script: `record.ps1` in this folder (normally `~/.claude/skills/pro-record/`). Windows only.
Needs `pip install imageio-ffmpeg pillow` and Microsoft Edge (for `-Url`).

## Before recording (tell the user)
- **Keep the screen awake and unlocked.** A locked or sleeping screen records black. The script checks for this.
- Close or hide anything private: notifications, chat apps, email.
- Recording opens a window on their screen for the length of the recording. Ask before starting.

## Record
Run with `powershell -ExecutionPolicy Bypass -File record.ps1 ...`
- **A web page** (fresh InPrivate window, no account, no history; closes itself afterwards):
  `-Url "https://www.youtube.com/results?search_query=claude+code" -Out search.mp4 -Seconds 20 -Steps "wait:5;keys:{DOWN 6};wait:3;keys:{DOWN 6}"`
- **One app window** (only that window's area is captured):
  `-Window "Visual Studio Code" -Out build.mp4 -Seconds 30`
- **Steps**: `wait:<s>`, `keys:<SendKeys>` (e.g. `{ENTER}`, `^l` for Ctrl+L, `{DOWN 6}`), `type:<text>`, separated by `;`.

## Privacy pass
- `-Crop "w:h:x:y"` keeps only the useful area (in physical pixels; check one frame first).
- `-Blur "x:y:w:h,x:y:w:h"` blurs boxes: names, emails, file paths, other tabs, account avatars.
- **Always extract one frame and look at it** before using the footage:
  `ffmpeg -ss 3 -i out.mp4 -frames:v 1 check.png`. Blur anything personal, then record again or re-run the pass.

## Rules
- Never record sign-in pages, passwords, payment details or private messages.
- Never record other people's content to republish it. Short clips of search results for commentary are fine.
- Hand the clips to /pro-video as `footage` scenes.
