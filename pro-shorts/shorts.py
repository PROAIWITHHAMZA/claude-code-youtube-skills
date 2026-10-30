"""pro-shorts: find the best YouTube Shorts inside a long video, and cut them to 9:16.

    python shorts.py <video> [--srt captions.srt] [--n 3] [--min 20] [--max 58] [--cut [--crop] [--x 0.5]] [--out DIR]

Without --srt the video is transcribed locally (pro-edit's transcriber, faster-whisper).
Every window of whole sentences between --min and --max seconds is scored:
  hook       the first sentence: a number, "you", a question, or a strong claim
  standalone does not open by pointing back ("and", "so", "this", "that", "it", "he"...)
  payoff     ends on a full stop with a result, number or clear instruction
  pace       2.2-3.4 words per second; slower drags on a phone
  length     30-50 s is the sweet spot
The best non-overlapping windows are printed. --cut renders each as 1080x1920: the whole frame over a blurred fill (good for screens and slides),
or with --crop a full-height crop (good for a face; --x picks the horizontal position) into <video>_shorts/. Shorts need their own title; YouTube adds auto-captions.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pro-edit"))
sys.path.insert(0, os.path.join(HERE, "..", "pro-chapters"))

BACKREF = re.compile(r"^(and|but|so|this|that|these|those|it|its|it's|he|she|they|then|also|because|which|plus)\b", re.I)
HOOK = re.compile(r"(\d|\?|\byou\b|\byour\b|\bnever\b|\bstop\b|\bmost\b|\bwrong\b|\bhere'?s\b|\bwhy\b|\bhow\b|\bsecret\b|\bmistake)", re.I)
PAYOFF = re.compile(r"(\d|\bthat'?s\b|\bso\b|\bresult|\bnow\b|\bjust\b|\btry\b|\bdo this\b|\bthe answer\b|\bworks?\b)", re.I)


def sentences_from_words(words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if w["w"].endswith((".", "?", "!")):
            out.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
            cur = []
    if cur:
        out.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
    return out


def sentences_from_srt(path):
    from chapters import read_srt
    return read_srt(path)


def score(win):
    first, last = win[0][2], win[-1][2]
    dur = win[-1][1] - win[0][0]
    words = sum(len(s[2].split()) for s in win)
    wps = words / max(dur, 1)
    lead = first.strip()
    early = re.search(r"\b(it|this|that|these|those|he|she|they)\b", " ".join(lead.split()[:5]), re.I)
    hook = (10 * ("?" in lead) + 8 * bool(re.search(r"\d", lead)) + 6 * bool(re.search(r"\byour?\b", lead, re.I)) +
            6 * bool(re.search(r"\b(never|stop|most|wrong|mistake|secret|why|how|here'?s)\b", lead, re.I)))
    s = {"hook": min(30, hook),
         "standalone": 0 if BACKREF.match(lead) else 10 if early else 20,
         "payoff": (10 if last.rstrip().endswith((".", "!")) else 0) + min(10, 5 * len(PAYOFF.findall(last))),
         "pace": 15 if 2.2 <= wps <= 3.4 else 8 if 1.8 <= wps <= 3.8 else 0,
         "length": 15 if 30 <= dur <= 50 else 9}
    return sum(s.values()), s, dur


def find(sents, n=3, lo=20, hi=58):
    cands = []
    for i in range(len(sents)):
        for j in range(i, len(sents)):
            dur = sents[j][1] - sents[i][0]
            if dur > hi:
                break
            if dur >= lo:
                total, parts, d = score(sents[i:j + 1])
                cands.append((total, sents[i][0], sents[j][1], parts, sents[i:j + 1]))
    picked = []
    for c in sorted(cands, key=lambda c: -c[0]):
        if all(c[2] <= p[1] or c[1] >= p[2] for p in picked):
            picked.append(c)
        if len(picked) >= n:
            break
    return sorted(picked, key=lambda c: c[1])


def cut(video, a, b, out, crop=False, x=0.5):
    import imageio_ffmpeg
    if crop:  # full-height centre crop: best for a face or one subject; x moves the crop window (0 left, 1 right)
        fc = f"[0:v]scale=-2:1920,crop=1080:1920:(iw-1080)*{x}:0,format=yuv420p[v]"
    else:
        fc = ("[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2,eq=brightness=-0.15[bg];"
          "[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2,format=yuv420p[v]")
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{a:.2f}", "-to", f"{b + 0.3:.2f}",
                        "-i", video, "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "20", "-c:a", "aac", "-b:a", "160k", out], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d
    video = os.path.abspath(a[0])
    srt = opt("--srt", None)
    if srt:
        sents = sentences_from_srt(srt)
    else:
        from cutlist import transcribe
        sents = sentences_from_words(transcribe(video))
    picks = find(sents, int(opt("--n", 3)), float(opt("--min", 20)), float(opt("--max", 58)))
    if not picks:
        sys.exit("no window of whole sentences fits the length limits; try --min 15")
    outdir = os.path.abspath(opt("--out", os.path.splitext(video)[0] + "_shorts"))
    for k, (total, s0, s1, parts, win) in enumerate(picks, 1):
        print(f"\nSHORT {k}   {mmss(s0)} - {mmss(s1)}  ({s1 - s0:.0f}s)   score {total}/100")
        print("   " + "  ".join(f"{n} {v}" for n, v in parts.items()))
        print(f"   opens: \"{win[0][2][:100]}\"")
        print(f"   ends:  \"{win[-1][2][-100:]}\"")
        if "--cut" in a:
            os.makedirs(outdir, exist_ok=True)
            out = os.path.join(outdir, f"short_{k}.mp4")
            cut(video, s0, s1, out, "--crop" in a, float(opt("--x", 0.5)))
            print(f"   -> {out}")


if __name__ == "__main__":
    main()
