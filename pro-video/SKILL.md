---
name: pro-video
description: Render a complete 1080p YouTube video (voice, motion graphics, real screen footage, captions, chapters, music) from a JSON scene spec, with free tools only. Use when the user wants to turn a script into a finished video, re-render a video after edits, or asks for a faceless/explainer video.
---

# pro-video: script in, finished video out

You turn a script into `spec.json`, run `render.py`, watch the result, and fix it. Everything runs on the
user's machine with free tools: edge-tts (voice), Pillow (frames), ffmpeg (video, via imageio-ffmpeg).

The engine is in the same folder as this file (normally `~/.claude/skills/pro-video/`):
- `render.py`: the renderer. `python render.py spec.json [--check] [--stills] [--out DIR]`
- `example.json`: a working spec that uses every scene type. Copy it as a starting point.
- `engine/`: drawing code, robot host, music bed, captions.

## Setup (first run only)
```
pip install edge-tts pillow imageio-ffmpeg
```
Windows fonts (Segoe UI, Consolas) are used. On macOS/Linux, text falls back to Arial or the default font.

## Workflow
1. **Get the script.** If the user has none, write it (or use /pro-script). One spoken sentence per line, 6–25 words.
2. **Pick a visual for every line.** Change the visual every 3–6 seconds. Never show the same type twice in a row
   unless it's a sequence (steps). Put the strongest visual first: the opening 5 seconds decide retention.
3. **Write `spec.json`** next to the user's project (format below). Paths are relative to the spec file.
4. `python render.py spec.json --check`: fix every problem it lists.
5. `python render.py spec.json --stills`: look at every PNG in `output/stills/` with the Read tool. Fix text that
   overflows, overlaps or is too small to read on a phone (under ~32 px at 1080p).
6. `python render.py spec.json`: renders. Only changed lines re-render on later runs (content-hash cache).
7. Pull 3–4 frames from the mp4 with ffmpeg and look at them. Report the length, chapters and anything weak.
   Never claim it's good without looking.

## Spec format
(The `//` notes explain fields; real JSON can't contain them, so leave them out.)
```json
{
  "title": "My video", "file": "my-video.mp4",
  "voice": "en-US-AndrewNeural", "rate": "+2%",
  "host": "robot",                     // "robot" = talking robot in the corner, "none" = no host
  "music_volume": 0.11,                // 0 = no music
  "presenter": {"photo": "host.jpg", "name": "ZAYN", "role": "AI host"},   // optional
  "recordings": "recordings",          // optional folder searched for footage files
  "description": "Summary...\n\n{chapters}\n\n#tags",   // {chapters} is replaced with real timestamps
  "chapters": [
    {"title": "Intro", "pill": null, "lines": [
      {"say": "Words the voice speaks.", "hold": 0.3, "visual": {"type": "kinetic", "lines": ["BIG TEXT", ["RED TEXT", "hot"]]}}
    ]},
    {"title": "Step 1", "pill": 1, "lines": [ ... ]}
  ]
}
```
`pill` numbers the chapter dots in the top-right corner (null = no dot). `hold` adds silent seconds after the
line, for prompts people need to read. Colors: `white`, `red`, `hot`, `green`, `amber`, `muted`, or `[r,g,b]`.

## Scene types
| type | keys | use it for |
|---|---|---|
| `kinetic` | `lines` (text or [text, color]), `size`, `top`, `sub` | hooks, punchlines; words pop in |
| `step` | `n`, `text`, `of` | chapter openers |
| `prompt` | `text`, `title`, `tag` | a prompt typing itself out |
| `list` | `heading`, `items` (text or [text, ok]) | checklists; ticks animate |
| `bars` | `heading`, `groups` [{name, values, color}], `weak`, `strong` | scores, before/after numbers |
| `pipeline` | `heading`, `nodes` [[label, sub]] | a process, 3–6 steps |
| `grid` | `heading`, `tiles` [[name, sub]], `cols`, `highlight` | maps of many items (a skill pack, a toolset) |
| `table` | `heading`, `columns`, `rows` (text / true / false cells), `ours` | "how we're different" comparisons |
| `compare` | `heading`, `left`, `right`, `left_title`, `right_title` | before / after, wrong / right |
| `stat` | `value`, `label`, `prefix`, `suffix`, `decimals`, `source`, `color` | one number that matters; always give `source` for facts |
| `terminal` | `lines`, `title`, `size` | command output; `$`/`>` lines red, `done`/`✓` green, `!` amber |
| `card` | `kicker`, `text`, `color` | honest notes, warnings, the one takeaway |
| `thumbs` | `heading`, `images` (3), `winner` | thumbnails shrinking to feed size |
| `image` | `src`, `label`, `fill` | a screenshot with a push-in |
| `footage` | `rec`, `crop` [w,h,x,y], `start`, `len`, `label` | real screen recordings (time-fitted to the line) |
| `host` | `name`, `role`, `photo` | presenter photo card with a name strip |
| `hostclip` | `src`, `segments` [[start, end, caption]] | a real talking-presenter clip in its own voice |

## Rules
- Real footage beats graphics. Record with /pro-record and crop out names, emails, paths and other sessions.
- Every number on screen needs a real source. Never invent stats.
- An AI presenter or AI voice must be disclosed (description line + YouTube's "Altered or synthetic content" box).
- Never crop, blur or cover another service's watermark.

## Premium mode (cinematic motion graphics)
`premium/` renders scenes as HTML in headless Microsoft Edge, frame by frame: real 3D camera moves, glass panels,
light sweeps, particles, film grain, word-by-word captions from the voice's own word timings, synthesized sound
design (whooshes, impacts, riser) and a music bed ducked under the voice.
- Setup once: `pip install playwright numpy` (it drives the Edge already on Windows; no browser download).
- `premium/story.py` holds the scenes and their real numbers; `premium/stage.html` holds 17 animated scene types
  (coldopen, zayn, promise, title, sidebar, measure, carousel, rule, pairing, radar, gap, wave, orbit, render, notes,
  cta, outro); `SRC` at the top of `premium/build.py` lists the footage and images for the video.
- `python premium/build.py OUT --scenes` renders one still per scene to check, then `python premium/build.py OUT` renders.
- Use it when the user asks for premium or cinematic work. Copy story.py, write new scenes and data, and keep the
  same rule: every number on screen comes from a real run or a real source.
