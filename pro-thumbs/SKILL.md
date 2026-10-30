---
name: pro-thumbs
description: Design three YouTube thumbnail layouts from a headline and a photo, test each at real feed sizes (360, 168 and 120 px, dark and light mode), score readability with measured letter size and contrast, and pick the winner. Use when the user needs a thumbnail, wants to compare thumbnails, or asks why a thumbnail isn't working.
---

# pro-thumbs: thumbnails tested the way viewers see them

Most thumbnails are judged at full size on a big monitor. In suggested videos, right next to what people are watching, they are 168 px wide.
This skill designs three layouts and measures which one still reads when it's tiny.

Script: `thumbs.py` in this folder (normally `~/.claude/skills/pro-thumbs/`). Needs `pip install pillow`.

## Workflow
1. **Headline first.** 2–4 words, and they must not repeat the title. The title says what it is,
   the thumbnail says why it matters (a result, a number, a contrast). Run `/pro-title` if both exist.
2. **Subject photo.** A face with a clear emotion, or the result itself (a chart, an app screen).
   Ask the user for one, or use their channel host photo. Never use a real person's photo without permission.
3. Write `thumb.json` next to the photo:
   ```json
   {"headline": ["ZERO", "EDITING"], "image": "face.jpg", "badge": "FREE", "focus": 0.5}
   ```
   `focus` is where the subject's face sits horizontally (0 left … 1 right), so crops keep the face.
   `accent` sets the brand colour as `[r, g, b]` (default red).
4. `python thumbs.py thumb.json` writes `thumbs/thumb_A.png`, `thumb_B.png`, `thumb_C.png`, `winner.png` and
   `feed_test.png`.
5. **Look at `feed_test.png` with the Read tool.** The numbers are a guide, not a verdict. Check by eye:
   - Is the face cut badly (eyes or chin covered)?
   - Does the headline still read at 120 px?
   - Would it stand out next to a white YouTube page and a dark one?
6. If every score is under 70, change the input instead of polishing pixels: fewer words, a bigger face, a
   simpler photo. Re-run and compare.
7. Report the winner with its score and the reason it won, and show the user `feed_test.png`.

## The score (out of 100)
| part | points | measured as |
|---|---|---|
| text | 35 | headline letter height at 168 px wide (suggested-videos size); 12 px or more is full marks |
| contrast | 25 | WCAG contrast between the text colour and the pixels behind it; 7:1 or more is full marks |
| words | 20 | 3 words or fewer is full marks, 4 → 15, 5 → 8 |
| subject | 20 | share of the frame the photo fills; 30 % or more is full marks |

## Rules
- Thumbnail text must be true to the video. No fake "shocked" claims the video doesn't deliver.
- If the subject is an AI-generated person, the video needs YouTube's "Altered or synthetic content" disclosure.
- Upload at 1280×720, under 2 MB (export JPG if the PNG is bigger).
