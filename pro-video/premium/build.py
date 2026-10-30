"""Premium renderer: story.py + stage.html -> 1080p video, rendered frame by frame in headless Edge.

    python build.py <out_dir> [--stills 1.5,20,40] [--scenes] [--workers 3]

  --stills   render PNG frames at these times (seconds) and stop
  --scenes   render one PNG from the middle of every scene and stop

Pipeline: edge-tts voice per line with word timings -> timeline.json -> Edge renders each frame by calling
seek(t) in stage.html -> JPEG frames piped into ffmpeg -> sound design (whooshes, impacts, riser, shutter),
a synthesized music bed ducked under the voice -> final mp4, captions.srt, chapters, description.
"""
import asyncio, hashlib, json, math, os, pathlib, re, shutil, subprocess, sys, wave
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import edge_tts, imageio_ffmpeg

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import story  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS, SR = 30, 48000
VOICE, RATE = "en-US-AndrewNeural", "+4%"
WORK = pathlib.Path(os.environ["TEMP"]) / "prem"
TEMP = pathlib.Path(os.environ["TEMP"])
SRC = {  # real outputs from the skill runs
    "thumbA": TEMP / "pro-demo/thumbs/thumb_A.png", "thumbB": TEMP / "pro-demo/thumbs/thumb_B.png",
    "thumbC": TEMP / "pro-demo/thumbs/thumb_C.png", "thumbOld": TEMP / "pt-test/thumbs/thumb_C.png",
    "zaynPhoto": HERE.parent / "presenter/zayn_master.jpg", "zayn": HERE.parent / "presenter/clips/intro_hi.mp4",
    "search": TEMP / "pro-rec/search.mp4", "render": TEMP / "pro-rec/video.mp4",
}
RAW_TAKE = TEMP / "pro-demo/raw_take.mp4"
CUTS = [[0.0, 3.87, "retake"], [6.70, 8.38, "pause"]]  # from raw_take.cuts.txt


def ff(*a):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *map(str, a)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)


def duration(p):
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", subprocess.run([FF, "-hide_banner", "-i", str(p)], capture_output=True, text=True).stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def decode(p, sr=SR, ch=2):
    raw = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", str(p), "-f", "f32le", "-ac", str(ch), "-ar", str(sr), "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).copy()


# ---------------------------------------------------------------- voice with word timings

async def tts(text):
    key = hashlib.sha1(f"{VOICE}|{RATE}|{text}".encode()).hexdigest()[:14]
    mp3, js = WORK / "tts" / f"{key}.mp3", WORK / "tts" / f"{key}.json"
    if mp3.exists() and js.exists():
        return mp3, json.loads(js.read_text(encoding="utf-8"))
    mp3.parent.mkdir(parents=True, exist_ok=True)
    for n in range(6):
        try:
            words, audio = [], bytearray()
            async for c in edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary").stream():
                if c["type"] == "audio":
                    audio += c["data"]
                elif c["type"] == "WordBoundary":
                    words.append({"w": c["text"], "s": c["offset"] / 1e7, "e": (c["offset"] + c["duration"]) / 1e7})
            if not audio:
                raise RuntimeError("no audio")
            mp3.write_bytes(bytes(audio))
            break
        except Exception as e:  # the service drops the odd request
            if n == 5:
                raise
            print(f"    tts retry {n + 1}: {type(e).__name__}", flush=True)
            await asyncio.sleep(2 + 3 * n)
    # put the punctuation from the script back on the spoken words, for captions
    toks = text.split()
    j = 0
    for w in words:
        while j < len(toks) and re.sub(r"\W", "", toks[j]).lower() != re.sub(r"\W", "", w["w"]).lower():
            j += 1
        if j < len(toks):
            w["w"] = toks[j]
            j += 1
    js.write_text(json.dumps(words), encoding="utf-8")
    return mp3, words


LEAD = {"coldopen": .25, "title": .55, "rule": .45}
PAD = {"title": .75, "rule": 1.5, "coldopen": .9, "gap": .8, "wave": .9, "pairing": .6, "measure": .5}


async def timeline():
    scenes, t, voice = [], 0.0, []
    for s in story.SCENES:
        sc = {k: v for k, v in s.items() if k not in ("lines",)}
        sc["start"], sc["lines"] = t, []
        if s["kind"] == "zayn":
            d = duration(SRC["zayn"])
            sc["lines"] = [{"s": a, "e": b, "words": [{"w": w, "s": a + (b - a) * i / len(seg.split()), "e": a + (b - a) * (i + 1) / len(seg.split())}
                                                      for i, w in enumerate(seg.split())]} for a, b, seg in s["segments"]]
            sc["dur"] = d + .1
            voice.append((t, SRC["zayn"]))
        else:
            lt = LEAD.get(s["kind"], .4)
            for text in s["lines"]:
                mp3, words = await tts(text)
                d = duration(mp3)
                sc["lines"].append({"s": lt, "e": lt + (words[-1]["e"] if words else d), "words": words, "text": text})
                voice.append((t + lt, mp3))
                lt += d + .3
            sc["dur"] = lt - .3 + s.get("pad", PAD.get(s["kind"], .45))
        t += sc["dur"]
        scenes.append(sc)
        print(f"  {sc['kind']:<9} {sc['start']:6.2f}s +{sc['dur']:5.2f}s", flush=True)
    return scenes, t, voice


def cue(sc, i, key):
    l = sc["lines"][min(i, len(sc["lines"]) - 1)]
    for w in l["words"]:
        if re.sub(r"[^a-z0-9.\-']", "", w["w"].lower()).startswith(key):
            return sc["start"] + l["s"] + w["s"]
    return sc["start"] + l["s"]


# ---------------------------------------------------------------- assets

def assets():
    a = WORK / "assets"
    a.mkdir(parents=True, exist_ok=True)
    out = {}
    for k, p in SRC.items():
        dst = a / (k + p.suffix)
        if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
            shutil.copy2(p, dst)
        out[k] = "assets/" + dst.name
    # real waveform of the test take, plus its transcript and cut list from pro-edit
    s = decode(RAW_TAKE, 16000, 1)[:, 0]
    n = 230
    peaks = [float(np.sqrt(np.mean(c ** 2))) if len(c) else 0.0 for c in np.array_split(s, n)]
    m = max(peaks) or 1
    words = json.loads((TEMP / "pro-demo/raw_take.words.json").read_text(encoding="utf-8"))
    out["wave"] = {"peaks": [round(p / m, 3) for p in peaks], "dur": round(len(s) / 16000, 2), "cuts": CUTS,
                   "words": [{"w": w["w"], "s": w["s"]} for w in words]}
    return out


# ---------------------------------------------------------------- sound design

def env(n, a, r):
    e = np.ones(n)
    ai, ri = int(a * SR), int(r * SR)
    if ai:
        e[:ai] = np.linspace(0, 1, ai)
    if ri:
        e[-ri:] *= np.linspace(1, 0, ri) ** 2
    return e


def bandnoise(n, lo, hi, rnd):
    x = rnd.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() or 1)


def sfx(rnd):
    out = {}
    n = int(.7 * SR)  # whoosh: noise sweeping up then down, panned left to right
    t = np.linspace(0, 1, n)
    w = np.zeros(n)
    for k in range(14):
        seg = slice(k * n // 14, (k + 1) * n // 14)
        c = 400 + 3800 * math.sin(math.pi * (k + .5) / 14)
        w[seg] = bandnoise(n, c * .6, c * 1.4, rnd)[seg]
    w *= np.sin(np.pi * t) ** 2 * .5
    out["whoosh"] = np.stack([w * (1 - t * .6), w * (.4 + t * .6)], 1)
    n = int(1.6 * SR)  # impact: falling sub + noise burst
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (52 * t - 14 * t * t)) * np.exp(-t * 2.6)
    hit = bandnoise(n, 80, 2500, rnd) * np.exp(-t * 18) * .5
    b = (sub + hit) * .8
    out["boom"] = np.stack([b, b], 1)
    n = int(1.4 * SR)  # riser
    t = np.arange(n) / SR
    r = (bandnoise(n, 1500, 9000, rnd) * .35 + np.sin(2 * np.pi * (200 * t + 300 * t * t)) * .15) * (t / 1.4) ** 2.2
    out["riser"] = np.stack([r, r], 1)
    n = int(.25 * SR)  # shutter: two clicks
    s = np.zeros(n)
    for o in (0, int(.09 * SR)):
        k = int(.03 * SR)
        s[o:o + k] += bandnoise(k, 2000, 8000, rnd) * np.exp(-np.arange(k) / SR * 120)
    out["shutter"] = np.stack([s * .6, s * .6], 1)
    n = int(.35 * SR)  # stamp: short punchy thud
    t = np.arange(n) / SR
    p = (np.sin(2 * np.pi * 110 * t) * np.exp(-t * 14) + bandnoise(n, 300, 3000, rnd) * np.exp(-t * 40) * .6) * .8
    out["stamp"] = np.stack([p, p], 1)
    n = int(.12 * SR)  # tick for counters / reveals
    t = np.arange(n) / SR
    k_ = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 60) * .25
    out["tick"] = np.stack([k_, k_], 1)
    return out


def music(total, rnd):
    """Dark, modern bed: 92 bpm, Am-F-C-G pads, sub pulse, soft kick and hats. Built in numpy."""
    bpm = 92
    beat = 60 / bpm
    n = int((total + 2) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    chords = [(57, 60, 64, 69), (53, 57, 60, 65), (48, 55, 60, 64), (55, 59, 62, 67)]
    roots = [33, 29, 36, 31]
    bar = 4 * beat
    for k in range(int(total / bar) + 2):
        ci = k % 4
        a, b = int(k * bar * SR), min(n, int((k + 1) * bar * SR + .8 * SR))
        if a >= n:
            break
        tt = np.arange(b - a) / SR
        e = np.minimum(1, tt / .9) * np.minimum(1, np.maximum(0, (bar + .8 - tt) / .9))
        for j, m in enumerate(chords[ci]):
            f = hz(m)
            v = (np.sin(2 * np.pi * f * tt) + .3 * np.sin(2 * np.pi * 2 * f * tt + .3) + .12 * np.sin(2 * np.pi * 3 * f * tt)) * .045 * e
            pan = .5 + (j - 1.5) * .18
            out[a:b, 0] += v * (1 - pan)
            out[a:b, 1] += v * pan
        for q in range(8):  # sub pulse on eighths
            s0 = a + int(q * beat / 2 * SR)
            ln = int(beat / 2 * SR * .9)
            if s0 + ln > n:
                break
            st = np.arange(ln) / SR
            sb = np.sin(2 * np.pi * hz(roots[ci]) * st) * np.exp(-st * 5) * (.16 if q % 2 == 0 else .09)
            out[s0:s0 + ln] += sb[:, None]
    for i in range(int(total / beat) + 2):  # kick on 1 and 3, hats on off-beats
        s0 = int(i * beat * SR)
        if s0 >= n:
            break
        if i % 2 == 0:
            ln = min(int(.32 * SR), n - s0)
            st = np.arange(ln) / SR
            kk = np.sin(2 * np.pi * (58 * st - 30 * st * st)) * np.exp(-st * 9) * .32
            out[s0:s0 + ln] += kk[:, None]
        h0 = s0 + int(beat / 2 * SR)
        ln = min(int(.05 * SR), max(0, n - h0))
        if ln:
            hh = rnd.standard_normal(ln) * np.exp(-np.arange(ln) / SR * 90) * .035
            out[h0:h0 + ln, 0] += hh * .7
            out[h0:h0 + ln, 1] += hh
    fade = int(2 * SR)
    out[:fade] *= np.linspace(0, 1, fade)[:, None]
    end = int(total * SR)
    out[max(0, end - 3 * SR):end] *= np.linspace(1, 0, min(end, 3 * SR))[:, None]
    return out[:end]


def mix(scenes, total, voice, path):
    rnd = np.random.default_rng(5)
    n = int(total * SR) + SR
    vo = np.zeros((n, 2))
    for t, p in voice:
        a = decode(p)
        i = int(t * SR)
        vo[i:i + len(a)] += a[: max(0, n - i)]
    fx = np.zeros((n, 2))
    S = sfx(rnd)

    def put(name, t, gain=1.0):
        i = max(0, int(t * SR))
        a = S[name][: max(0, n - i)] * gain
        fx[i:i + len(a)] += a

    for k, sc in enumerate(scenes):
        st = sc["start"]
        if k and sc["kind"] not in ("zayn",):
            put("whoosh", st - .2, .55)
        if sc["kind"] == "title":
            put("boom", st + .1, .9)
        if sc["kind"] == "rule":
            put("shutter", st + sc["lines"][0]["e"] + .12, .9)
        if sc["kind"] == "coldopen":
            t5 = cue(sc, 1, "5")
            put("riser", t5 - 1.4, .7)
            put("boom", t5 - .05, 1.0)
            for i in range(3):
                put("tick", st + sc["lines"][1]["s"] + .15 + i * .32, .9)
        if sc["kind"] == "measure":
            put("stamp", st + sc["lines"][1]["s"] + .25, 1.0)
        if sc["kind"] == "gap":
            for i in range(6):
                put("tick", st + sc["lines"][1]["s"] + .3 + i * .45, .8)
            put("boom", st + sc["lines"][2]["s"] - .1, .7)
        if sc["kind"] == "pairing":
            put("tick", cue(sc, 1, "100"), 1.2)
        if sc["kind"] == "carousel":
            put("stamp", cue(sc, 0, "winner"), .6)
        if sc["kind"] == "render":
            put("boom", cue(sc, 0, "this") - .1, .6)
    m = music(total, rnd)
    m = np.vstack([m, np.zeros((n - len(m), 2))])[:n]
    # duck the music under the voice (smoothed envelope)
    lvl = np.abs(vo).max(1)
    k = int(.25 * SR)
    sm = np.convolve(lvl, np.ones(k) / k, "same")
    duck = 1 - .62 * np.clip(sm / (sm.max() * .25 + 1e-9), 0, 1)
    out = vo * 1.0 + fx * .8 + m * duck[:, None] * .9
    out /= max(1.0, np.abs(out).max() / .97)
    pcm = (out * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- frames

def render_range(args):
    a, b, out = args
    from playwright.sync_api import sync_playwright
    p = subprocess.Popen([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-vcodec", "mjpeg", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)],
                         stdin=subprocess.PIPE)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        pg = br.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto((WORK / "stage.html").as_uri())
        pg.evaluate("window.ready")
        for f in range(a, b):
            pg.evaluate("t => seek(t)", f / FPS)
            p.stdin.write(pg.screenshot(type="jpeg", quality=92))
            if (f - a) % 300 == 0:
                print(f"    frames {a}-{b}: {f - a}/{b - a}", flush=True)
        br.close()
    p.stdin.close()
    p.wait()
    return str(out)


def stills(times, out):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="msedge", headless=True)
        pg = br.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto((WORK / "stage.html").as_uri())
        pg.evaluate("window.ready")
        for t in times:
            pg.evaluate("t => seek(t)", t)
            p = out / f"still_{t:07.2f}.png"
            pg.screenshot(path=str(p))
            print("  ", p, flush=True)
        br.close()


def srt_ts(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t % 1 * 1000):03d}"


def main():
    a = sys.argv[1:]
    out = pathlib.Path(a[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    scenes, total, voice = asyncio.run(timeline())
    tl = {"scenes": scenes, "total": total, "assets": assets()}
    (WORK / "timeline.js").write_text("window.TL = " + json.dumps(tl) + ";", encoding="utf-8")
    shutil.copy2(HERE / "stage.html", WORK / "stage.html")
    print(f"  total {total:.1f}s, {len(scenes)} scenes", flush=True)
    if "--stills" in a:
        stills([float(x) for x in a[a.index("--stills") + 1].split(",")], out / "stills")
        return
    if "--scenes" in a:
        stills([round(s["start"] + s["dur"] * .72, 2) for s in scenes], out / "stills")
        return
    wav = WORK / "mix.wav"
    mix(scenes, total, voice, wav)
    nf = int(total * FPS)
    k = int(a[a.index("--workers") + 1]) if "--workers" in a else 3
    cuts = [round(nf * i / k) for i in range(k + 1)]
    jobs = [(cuts[i], cuts[i + 1], WORK / f"seg_{i}.mp4") for i in range(k)]
    with ProcessPoolExecutor(k) as ex:
        segs = list(ex.map(render_range, jobs))
    lst = WORK / "segs.txt"
    lst.write_text("".join(f"file '{s}'\n".replace("\\", "/") for s in segs), encoding="utf-8")
    final = out / "5-youtube-mistakes.mp4"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
       "-shortest", "-movflags", "+faststart", final)
    caps, n = [], 0
    for sc in scenes:
        for l in sc["lines"]:
            ws = l["words"]
            for i in range(0, len(ws), 7):
                ch = ws[i:i + 7]
                n += 1
                caps.append(f"{n}\n{srt_ts(sc['start'] + l['s'] + ch[0]['s'])} --> {srt_ts(sc['start'] + l['s'] + ch[-1]['e'])}\n{' '.join(w['w'] for w in ch)}\n")
    (out / "captions.srt").write_text("\n".join(caps), encoding="utf-8")
    print(f"\n  done: {final}  ({duration(final):.1f}s)")


if __name__ == "__main__":
    main()
