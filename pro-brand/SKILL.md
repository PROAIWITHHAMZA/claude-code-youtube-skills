---
name: pro-brand
description: Make and check YouTube channel branding - an 800x800 profile picture previewed at real circle sizes, a 2560x1440 banner with content kept inside the area every device shows, and a check that marks the TV/desktop/tablet/mobile crops on any banner. Use when the user needs a profile picture, a banner, or asks why their banner is cut off.
---

# pro-brand: branding that survives every screen

Script: `brand.py` in this folder (normally `~/.claude/skills/pro-brand/`). Needs `pip install pillow`.

## Profile picture
1. Get a photo or logo from the user (or one they made with an image tool).
2. `python brand.py profile photo.jpg --box x,y,size --ring 239,35,50 --out brand`
   (`--box` is the square to keep; leave it out to auto-centre).
3. Read `profile_preview.png`: it shows the picture at 176 → 24 px on light and dark. If the face or logo is
   unreadable at 32 px, crop tighter or simplify.

## Banner
1. Agree on one line (what the channel does for the viewer), an optional sub-line (topics or upload day),
   the brand colour, and optional art (logo or mascot, PNG with transparency).
2. `python brand.py banner --title "Make AI work for you." --sub "New video every Tuesday" --image mascot.png --out brand`
3. Read `banner_areas.png`: the green box is all a phone shows. Everything important must be inside it.

## Check an existing banner
`python brand.py check banner.png`: marks the device areas and warns when detail sits outside the safe area.

## Rules
- Banner: 2560×1440, under 6 MB. Profile: 800×800, shown as a circle.
- Don't use logos, characters or photos the user doesn't own or have rights to.
