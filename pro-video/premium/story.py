"""The showcase video as data: every scene, what is said, and the real numbers each scene shows.

Every number here comes from a real run of the pro-* skills (Oct 29-30, 2026):
  thumbnails  pro-thumbs on "IT EDITS ITSELF": A 81 (13.6 px, 2.9:1), B 87 (14.4 px, 4.2:1), C 90 (12.5 px, 4.7:1)
  pairing     pro-title: thumb "16 SKILLS RUN MY CHANNEL" = 84 (repeats 4 words), "IT EDITS ITSELF" = 100
  hooks       pro-script: "Hey guys, welcome back..." 24, first draft 51, this video's opening 82
  gap         real YouTube results for "make youtube video with claude code", 6 results, 2,626,000 views
  edit        pro-edit on a 14.1 s test take: retake + filler 0:00-3.87, pause 6.70-8.38, 8.5 s left (39 % cut)
"""

TITLE = "5 YouTube Mistakes I Measured With 16 Claude Code Skills"

MISTAKES = [
    "Judging your thumbnail at full size",
    "Repeating your title in the thumbnail",
    "Warming up before the hook",
    "Chasing popular, not badly served",
    "Cutting silence, keeping retakes",
]

HOOKS = {  # pro-script signal scores, in the order of the radar axes
    "axes": ["CONCRETE", "STAKES", "OPEN QUESTION", "TALKS TO YOU", "PACE", "NO WARM-UP"],
    "list": [
        {"text": "Hey guys, welcome back, in this video I'll show you some AI tips.", "score": 24, "v": [15, 0, 0, 40, 100, 0]},
        {"text": "I built 16 Claude Code skills that run my YouTube channel, and you can copy every one.", "score": 51,
         "v": [100, 0, 0, 30, 100, 100]},
        {"text": "Why do your videos stall? I measured my own with 16 Claude Code skills and found 5 mistakes you're probably making too.",
         "score": 82, "v": [100, 45, 80, 80, 100, 100]},
    ],
}

SEARCH = {  # real results, collected Oct 29, 2026
    "query": "make youtube video with claude code",
    "rows": [
        {"title": "Claude Code (Free Plan) + YouTube = $77,000/Month", "views": 1100000, "label": "1.1M", "tag": "PAID TOOLS"},
        {"title": "How to Use Claude to Grow Your YouTube Channel", "views": 746000, "label": "746K", "tag": "NO VIDEO MADE"},
        {"title": "How to Create Insane Motion Graphics With Claude", "views": 345000, "label": "345K", "tag": "HYPE"},
        {"title": "Build ANY Faceless YouTube Channel with Claude", "views": 180000, "label": "180K", "tag": "PAID TOOLS"},
        {"title": "Claude Opus 5.5 Edited This ENTIRE Video In 5 Minutes", "views": 179000, "label": "179K", "tag": "OWN FOOTAGE"},
        {"title": "Watch Me Make a Faceless YouTube Video With Claude Code", "views": 76000, "label": "76K", "tag": "PAID TOOLS"},
    ],
}

SKILLS = [("pro-gap", "Find"), ("pro-viral", "Find"), ("pro-audit", "Find"), ("pro-plan", "Find"),
          ("pro-script", "Make"), ("pro-record", "Make"), ("pro-edit", "Make"), ("pro-video", "Make"),
          ("pro-shorts", "Make"), ("pro-title", "Package"), ("pro-thumbs", "Package"), ("pro-seo", "Package"),
          ("pro-chapters", "Package"), ("pro-brand", "Package"), ("pro-retention", "Grow"), ("pro-comments", "Grow")]
USED = ["pro-thumbs", "pro-title", "pro-script", "pro-gap", "pro-edit"]


def rule(n, items, say):
    return {"kind": "rule", "pill": n, "lines": [say], "data": {"items": items}, "captions": False}


SCENES = [
    {"kind": "coldopen", "lines": ["Why do your videos stall?",
                                   "I measured my own with 16 Claude Code skills, and found 5 mistakes you're probably making too."]},
    {"kind": "zayn", "src": "zayn_hi.mp4", "segments": [[0.0, 2.58, "Hi, I'm Zayn, the AI host of this channel."]]},
    {"kind": "promise", "lines": ["Stay to the end, and you can fix all five today. With the skills, or without them."],
     "data": {"mistakes": MISTAKES}},

    {"kind": "title", "pill": 1, "lines": ["Mistake one. Judging your thumbnail at full size."], "data": {"n": 1}, "captions": False},
    {"kind": "sidebar", "pill": 1, "lines": ["Nobody sees it big. In suggested videos, right next to what someone is watching, your thumbnail is just 168 pixels wide."]},
    {"kind": "measure", "pill": 1, "lines": ["So the skill measures it at that size. My first layout had big letters, but red on red, under three to one contrast.",
                                             "At 168 pixels, it falls apart."]},
    {"kind": "carousel", "pill": 1, "lines": ["It designs three layouts and scores every one. The winner, 90 out of 100, still reads at 120 pixels."]},
    rule(1, ["4 words or fewer", "Letters 12 px tall at feed size", "Strong contrast, never red on red"],
         "The rule: four words or fewer, letters at least twelve pixels tall at feed size, and strong contrast."),

    {"kind": "title", "pill": 2, "lines": ["Mistake two. Repeating your title in the thumbnail."], "data": {"n": 2}, "captions": False},
    {"kind": "pairing", "pill": 2, "lines": ["Viewers read both in under a second. My first thumbnail said: 16 skills, run my channel. The title already said that. 84.",
                                             "Same title, new thumbnail words: it edits itself. 100."]},
    rule(2, ["Title: what it is", "Thumbnail: why it matters", "Zero repeated words"],
         "The title says what it is. The thumbnail says why it matters."),

    {"kind": "title", "pill": 3, "lines": ["Mistake three. Warming up before the hook."], "data": {"n": 3}, "captions": False},
    {"kind": "radar", "pill": 3, "lines": ["The skill scores your first sentence on six signals: something concrete, the stakes, an open question, talking to you, pace, and no warm-up.",
                                           "Hey guys, welcome back, scores 24.",
                                           "My first hook for this video scored 51. The one you heard at the start: 82."]},
    rule(3, ["Start with the claim", "A number, a cost, or a question", "No “hey guys”"],
         "Start with the claim. A number, a cost, or a question."),

    {"kind": "title", "pill": 4, "lines": ["Mistake four. Chasing what's popular, instead of what's badly served."], "data": {"n": 4}, "captions": False},
    {"kind": "gap", "pill": 4, "lines": ["I searched: make a YouTube video with Claude Code. The top six had 2.6 million views.",
                                         "But four of the six lean on paid tools or hype. None of them showed the whole job done with free tools.",
                                         "That gap became this channel."]},
    rule(4, ["High demand", "Weak or paid answers", "= your next video"],
         "Look for high demand, and answers that leave people wanting more."),

    {"kind": "title", "pill": 5, "lines": ["Mistake five. Cutting the silence, but keeping the retakes."], "data": {"n": 5}, "captions": False},
    {"kind": "wave", "pill": 5, "lines": ["Silence is easy to cut. Retakes are what make a video feel amateur: you start a sentence, stop, and say it again.",
                                          "The skill transcribes it on your own laptop, finds the abandoned attempt, and keeps the clean one.",
                                          "Thirty-nine percent of this take, gone automatically."]},
    rule(5, ["Keep the last take", "Cut pauses over 0.7 s", "Then cut the ums"],
         "Keep the last take. Cut pauses longer than seven tenths of a second."),

    {"kind": "orbit", "lines": ["Those are five of the 16 skills.",
                                "The others find outlier videos, plan your week around your real hours, write chapters YouTube accepts, cut Shorts, read your retention, and sort your comments."]},
    {"kind": "render", "lines": ["And one of them renders whole videos from a single script file. This video was made the same way."]},
    {"kind": "notes", "lines": ["Two honest notes. Claude Code needs a paid plan, but every tool the skills use is free.",
                                "And the scores compare options. They don't predict views."]},
    {"kind": "cta", "lines": ["Want all 16? Comment: skills, and I'll send you the link.",
                              "I wrote them from scratch, inspired by an open source pack that's linked in the description."]},
    {"kind": "outro", "lines": ["I'm Zayn. Next video, we build a real AI agent in n8n. See you there."], "pad": 1.6},
]

for s in SCENES:
    s["data"] = dict(s.get("data", {}), mistakes=MISTAKES, hooks=HOOKS, search=SEARCH, skills=SKILLS, used=USED)
