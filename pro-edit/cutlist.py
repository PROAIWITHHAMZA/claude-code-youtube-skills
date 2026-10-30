"""pro-edit: turn a raw talking recording into a cut list (dead air, filler words, retakes) and render it.

    python cutlist.py <video_or_audio> [--pause 0.7] [--model base.en] [--render] [--keep-fillers]

Transcribes locally with faster-whisper (word timestamps, CPU, free), then marks:
  pause    silence between words longer than --pause seconds (keeps 0.2 s either side so cuts breathe)
  filler   um, uh, erm, hmm (and "you know" / "I mean" when they stand alone between pauses)
  retake   a phrase of 3+ words said again within 10 s: the first, abandoned attempt is cut

Writes next to the input:
  <name>.words.json     every word with start/end (reused on the next run, so re-runs are instant)
  <name>.captions.srt   captions for the ORIGINAL timing
  <name>.cuts.txt       human-readable cut list with the reason and text for every cut
  <name>.edited.mp4     with --render: the video with every cut applied (re-encoded, frame-accurate)
"""
import json, os, re, subprocess, sys

FILLERS = {"um", "uh", "erm", "er", "hmm", "mm", "uhm", "ah"}
SOFT_FILLERS = [("you", "know"), ("i", "mean")]


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def transcribe(path, model="base.en"):
    """Word-level transcript as [{"w", "s", "e"}]. Cached next to the media file."""
    cache = os.path.splitext(path)[0] + ".words.json"
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        with open(cache, encoding="utf-8") as fh:
            return json.load(fh)
    import numpy as np
    from faster_whisper import WhisperModel
    # decode with ffmpeg ourselves: avoids PyAV version problems and handles any container
    raw = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(audio, word_timestamps=True, vad_filter=False,
                           initial_prompt="Um, uh, so, like, you know, I mean, hmm.")  # keeps fillers in the text
    words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words]
    with open(cache, "w", encoding="utf-8") as fh:
        json.dump(words, fh)
    return words


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def find_cuts(words, pause=0.7, keep_fillers=False):
    cuts = []
    for a, b in zip(words, words[1:]):
        gap = b["s"] - a["e"]
        if gap > pause:
            cuts.append((a["e"] + 0.2, b["s"] - 0.2, "pause", f"{gap:.1f}s silence"))
    if not keep_fillers:
        for i, w in enumerate(words):
            if norm(w["w"]) in FILLERS:
                cuts.append((w["s"] - 0.03, w["e"] + 0.03, "filler", w["w"]))
        for i in range(len(words) - 1):
            pair = (norm(words[i]["w"]), norm(words[i + 1]["w"]))
            if pair in SOFT_FILLERS:
                before = words[i]["s"] - (words[i - 1]["e"] if i else 0)
                after = (words[i + 2]["s"] if i + 2 < len(words) else 1e9) - words[i + 1]["e"]
                if before > 0.25 and after > 0.25:  # only when it stands alone, not "do you know how"
                    cuts.append((words[i]["s"] - 0.03, words[i + 1]["e"] + 0.03, "filler", "you know" if pair[0] == "you" else "I mean"))
    toks = [norm(w["w"]) for w in words]
    i = 0
    while i < len(words) - 3:
        found = False
        for n in (6, 5, 4, 3):
            if i + n > len(words):
                continue
            phrase = toks[i:i + n]
            for j in range(i + 1, min(len(words) - n + 1, i + 40)):
                if words[j]["s"] - words[i]["s"] > 10:
                    break
                if toks[j:j + n] == phrase:
                    # the earlier attempt (from i up to the restart at j) is the retake
                    cuts.append((words[i]["s"] - 0.05, words[j]["s"] - 0.05, "retake",
                                 " ".join(w["w"] for w in words[i:j])))
                    i, found = j, True
                    break
            if found:
                break
        if not found:
            i += 1
    cuts = sorted((max(0.0, a), b, k, t) for a, b, k, t in cuts if b - a > 0.08)
    merged = []
    for c in cuts:
        if merged and c[0] <= merged[-1][1] + 0.05:
            p = merged[-1]
            merged[-1] = (p[0], max(p[1], c[1]), p[2] if p[2] == c[2] else p[2] + "+" + c[2], p[3] + " | " + c[3])
        else:
            merged.append(c)
    return merged


def ts(t, srt=False):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s % 1) * 1000):03d}" if srt else f"{m}:{s:05.2f}" if not h else f"{h}:{m:02d}:{s:05.2f}"


def write_srt(words, path, max_words=8):
    out, chunk = [], []
    for w in words:
        chunk.append(w)
        if len(chunk) >= max_words or w["w"].endswith((".", "?", "!")):
            out.append(chunk)
            chunk = []
    if chunk:
        out.append(chunk)
    with open(path, "w", encoding="utf-8") as fh:
        for n, c in enumerate(out, 1):
            fh.write(f"{n}\n{ts(c[0]['s'], True)} --> {ts(c[-1]['e'], True)}\n{' '.join(w['w'] for w in c)}\n\n")


def duration(path):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def render(path, keeps, out):
    has_video = "Video:" in subprocess.run([ffmpeg(), "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    parts, fc = [], ""
    for k, (a, b) in enumerate(keeps):
        if has_video:
            fc += f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{k}];"
        fc += f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={max(0, b - a - 0.02):.3f}:d=0.02[a{k}];"
        parts.append(f"[v{k}][a{k}]" if has_video else f"[a{k}]")
    fc += "".join(parts) + f"concat=n={len(keeps)}:v={1 if has_video else 0}:a=1" + ("[v][a]" if has_video else "[a]")
    script = out + ".filter.txt"
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(fc)
    args = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", path, "-filter_complex_script", script]
    args += (["-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p"]
             if has_video else ["-map", "[a]"]) + ["-c:a", "aac", "-b:a", "192k", out]
    r = subprocess.run(args, capture_output=True, text=True)
    os.remove(script)
    if r.returncode:
        sys.exit(r.stderr)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    path = os.path.abspath(a[0])
    pause = float(a[a.index("--pause") + 1]) if "--pause" in a else 0.7
    model = a[a.index("--model") + 1] if "--model" in a else "base.en"
    words = transcribe(path, model)
    if not words:
        sys.exit("no speech found")
    stem = os.path.splitext(path)[0]
    write_srt(words, stem + ".captions.srt")
    cuts = find_cuts(words, pause, "--keep-fillers" in a)
    total = duration(path)
    keeps, t = [], 0.0
    for c0, c1, _, _ in cuts:
        if c0 - t > 0.05:
            keeps.append((t, c0))
        t = max(t, c1)
    if total - t > 0.05:
        keeps.append((t, total))
    removed = total - sum(b - a_ for a_, b in keeps)
    counts = {}
    for c in cuts:
        for k in c[2].split("+"):
            counts[k] = counts.get(k, 0) + 1
    with open(stem + ".cuts.txt", "w", encoding="utf-8") as fh:
        fh.write(f"{len(cuts)} cuts, {removed:.1f}s removed of {total:.1f}s ({100 * removed / total:.0f}%)\n\n")
        for c0, c1, kind, text in cuts:
            fh.write(f"{ts(c0)} - {ts(c1)}  {kind:<13} {text[:90]}\n")
    print(f"  {len(words)} words, {len(cuts)} cuts ({', '.join(f'{v} {k}' for k, v in counts.items()) or 'none'})")
    print(f"  removes {removed:.1f}s of {total:.1f}s ({100 * removed / total:.0f}%)  ->  {total - removed:.1f}s")
    print(f"  cut list: {stem}.cuts.txt\n  captions: {stem}.captions.srt")
    if "--render" in a:
        out = stem + ".edited.mp4"
        render(path, keeps, out)
        print(f"  edited:   {out} ({duration(out):.1f}s)")


if __name__ == "__main__":
    main()
