---
name: pro-edit
description: Automatically edit a raw talking recording - transcribe it locally, find dead air, filler words (um, uh) and abandoned retakes, write a reviewable cut list and captions, and render the edited video. Use when the user has a raw recording, a voiceover, or a talking-head take to clean up.
---

# pro-edit: the rough cut, done for you

Script: `cutlist.py` in this folder (normally `~/.claude/skills/pro-edit/`).
Setup once: `pip install faster-whisper imageio-ffmpeg numpy` (runs on CPU; the first run downloads a ~150 MB model).

## Workflow
1. `python cutlist.py raw.mp4`: transcribes (cached as `raw.words.json`), then writes:
   - `raw.cuts.txt`: every cut with its time, type and the words removed
   - `raw.captions.srt`: captions for the original timing
2. **Read `raw.cuts.txt` and review it with the user.** Retake detection keeps the *last* attempt of a
   repeated phrase. Flag any cut that removes words the speaker meant to keep.
3. Tune if needed:
   - `--pause 1.0` for a calmer pace (default 0.7 s; 0.5 for a fast, punchy edit)
   - `--keep-fillers` if the speaker's natural "um" should stay
   - `--model small.en` for accents or noisy audio (slower, more accurate)
4. `python cutlist.py raw.mp4 --render` writes `raw.edited.mp4` (frame-accurate, with tiny audio fades
   at every cut, so there are no clicks).
5. Check: run `cutlist.py` on the edited file. It should find few or no cuts. Report the time saved.

## Notes
- Captions for the edited video: run `cutlist.py raw.edited.mp4` and use its `.captions.srt`.
- Long files: about 1x real time on a laptop CPU for `base.en`.
- Nothing is uploaded anywhere; transcription is local.
