"""Final edit, look v2:  python3 compose_v2.py <episode_dir> <out.mp4>   (env FRAMES_DIR=frames_v2, END_T=<sec> for a sample cut)
v2 vs compose.py: colour grade (grade.py), 2-3 word phrase captions in the lower third with the spoken word
highlighted (subject stays visible mid-frame), badge with a live dot that pops on change, top progress bar,
motion smear on the punch-in.  Everything else (timing, SFX, music, zoom/shake/flash) is the same.

Inputs in <episode_dir>:
  frames/fNNNN.png   every 2nd frame of a 24 fps scene (scene second s == video second s)
  voice.wav, timing.json   from tts.py
  style.json (optional): {"badge": [[line_index, "TEXT"], ...] or {"label":"DEPTH","keys":[[line_index, number], ...], "unit":"m_km"},
                          "highlight": ["WORD", ...]}
Adds: impact zoom + shake on every line start, whoosh/boom SFX, 128 bpm music bed,
one-word pop captions (numbers + highlight words in yellow), badge pill at the top."""
import json, re, os, sys, glob, subprocess, random
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grade import grade
from PIL import Image, ImageDraw, ImageFont

ep, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Black.otf", 104)
FD = os.environ.get("FRAMES_DIR", "frames")
badge_font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Black.otf", 64)
random.seed(3)
lines = json.load(open(f"{ep}/timing.json"))
style = json.load(open(f"{ep}/style.json")) if os.path.exists(f"{ep}/style.json") else {}
HL = set(w.upper() for w in style.get("highlight", []))
frames = sorted(int(os.path.basename(p)[1:5]) for p in glob.glob(f"{ep}/{FD}/f*.png"))
LAST = frames[-1]
T = float(os.environ.get("END_T", lines[-1]["end"] + 0.7))
FULL_T = lines[-1]["end"] + 0.7
N = int(T * FPS)

words = []
for ln in lines:
    toks = [t for t in re.sub(r"\.\.\.", " ", ln["text"]).split() if t]
    wts = [len(re.sub(r"[^\w']", "", t)) + 2 for t in toks]
    tot, t, dur = sum(wts), ln["start"], ln["end"] - ln["start"]
    for tok, wt in zip(toks, wts):
        d = dur * wt / tot
        words.append((t, t + d, tok.strip(",.?!\"").upper()))
        t += d
# phrase chunks: max 3 words, break after punctuation -> [(start, end, [word indexes])]
chunks, wi = [], 0
for ln in lines:
    toks = [t for t in re.sub(r"\.\.\.", " ", ln["text"]).split() if t]
    grp = []
    for tok in toks:
        grp.append(wi); wi += 1
        if len(grp) == 3 or tok[-1] in ",.?!":
            chunks.append(grp); grp = []
    if grp:
        chunks.append(grp)
def chunk_at(ts):
    for ci, g in enumerate(chunks):
        a = words[g[0]][0]
        nxt = words[chunks[ci + 1][0]][0] if ci + 1 < len(chunks) else words[g[-1]][1] + 0.6
        if a <= ts < nxt:
            act = g[0]
            for j in g:
                if words[j][0] <= ts: act = j
            return g, act, ts - a, ts - words[act][0]
    return None, None, 0, 0
def word_at(ts):
    for i, (a, b, w) in enumerate(words):
        nb = words[i + 1][0] if i + 1 < len(words) else b + 0.6
        if a <= ts < max(b, min(nb, b + 0.3)):
            return w, ts - a
    return None, 0

def badge_text(t):
    b = style.get("badge")
    if not b:
        return None
    if isinstance(b, list):
        cur = None
        for li, txt in b:
            if t >= lines[li]["start"] - 0.05:
                cur = txt
        return cur
    keys = [(lines[li]["start"], v) for li, v in b["keys"]]
    if t < keys[0][0] - 0.05:
        return None
    prev, val = 0, keys[0][1]
    for i, (a, v) in enumerate(keys):
        if t >= a:
            k = 1 - (1 - min((t - a) / 0.6, 1)) ** 3
            prev = keys[i - 1][1] if i else 0
            val = prev + (v - prev) * k
    if b.get("unit") == "m_km":
        s = f"{int(round(val))} m" if val < 1000 else f"{val/1000:.1f} km".replace(".0 km", " km")
    else:
        s = f"{int(round(val)):,}{b.get('unit', '')}"
    return f"{b.get('label', '')}  {s}".strip()

hits = [l["start"] for l in lines]
def fx(t):
    z, sx, sy = 1.04 + 0.025 * np.sin(t * 0.9), 0.0, 0.0
    for h in hits:
        a = t - h
        if 0 <= a < 0.45:
            e = (1 - a / 0.45) ** 3
            z += 0.14 * e; sx += random.uniform(-1, 1) * 12 * e; sy += random.uniform(-1, 1) * 12 * e
    return z, sx, sy
def flash(t):
    """Short white flash on every other line start (dynamic transition)."""
    for i, h in enumerate(hits[1:], 1):
        a = t - h
        if i % 2 == 0 and 0 <= a < 0.12:
            return 0.35 * (1 - a / 0.12)
    return 0.0

cache = {}
def raw(f):
    f = min(max(f, 0), LAST)
    f -= f % 2
    if f not in cache:
        if len(cache) > 6: cache.clear()
        cache[f] = Image.open(f"{ep}/{FD}/f{f:04d}.png").convert("RGB")
    return cache[f]
def scene_frame(t):
    x = t * 24 / 2
    i = int(np.floor(x)); fr = x - i
    a, b = raw(i * 2), raw(i * 2 + 2)
    return Image.blend(a, b, fr) if fr > 0.02 else a

def caption(img, w, age):
    pop = min(age / 0.06, 1.0)
    s = 0.7 + 0.3 * pop + 0.08 * np.sin(min(age / 0.14, 1) * np.pi)
    fnt = font.font_variant(size=int(124 * s))
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), w, font=fnt, stroke_width=12)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    if tw > W - 80:
        fnt = font.font_variant(size=int(124 * s * (W - 80) / tw)); bb = d.textbbox((0, 0), w, font=fnt, stroke_width=12)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x, y = (W - tw) / 2 - bb[0], H * 0.47 - th / 2 - bb[1]
    d.text((x + 5, y + 9), w, font=fnt, fill=(0, 0, 0), stroke_width=12, stroke_fill=(0, 0, 0))
    col = (255, 214, 0) if (any(c.isdigit() for c in w) or w in HL) else (255, 255, 255)
    d.text((x, y), w, font=fnt, fill=col, stroke_width=12, stroke_fill=(10, 10, 10))

NUMW = set("ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE TWENTY THIRTY FORTY FIFTY HUNDRED THOUSAND MILLION BILLION TRILLION".split())
def caption2(img, g, act, age, wage):
    pop = min(age / 0.08, 1.0)
    s = 0.82 + 0.18 * pop + 0.06 * np.sin(min(age / 0.16, 1) * np.pi)
    toks = [words[j][2] for j in g]
    d = ImageDraw.Draw(img, "RGBA")
    size = int(104 * s)
    def layout(size):
        f_n = font.font_variant(size=size); f_a = font.font_variant(size=int(size * 1.14))
        ws = []
        for j, w in zip(g, toks):
            f = f_a if j == act else f_n
            bb = d.textbbox((0, 0), w, font=f, stroke_width=10)
            ws.append((w, j, f, bb))
        gap = size * 0.28
        tw = sum(b[2] - b[0] for *_, b in ws) + gap * (len(ws) - 1)
        return ws, gap, tw
    ws, gap, tw = layout(size)
    if tw > W - 90:
        size = int(size * (W - 90) / tw); ws, gap, tw = layout(size)
    x = (W - tw) / 2; yc = H * 0.665
    for w, j, f, bb in ws:
        ww, hh = bb[2] - bb[0], bb[3] - bb[1]
        y = yc - hh / 2 - bb[1]
        key = any(c.isdigit() for c in w) or w in HL or w in NUMW
        if j == act:
            pad = 18; k = 1.0
            d.rounded_rectangle((x - pad, yc - hh / 2 - pad * 0.8, x + ww + pad, yc + hh / 2 + pad * 0.8),
                                radius=22, fill=(255, 214, 0, int(235 * k)) if key else (124, 58, 237, int(235 * k)))
            col = (20, 20, 20) if key else (255, 255, 255)
            d.text((x, y), w, font=f, fill=col, stroke_width=0)
        else:
            d.text((x + 4, y + 7), w, font=f, fill=(0, 0, 0, 160), stroke_width=10, stroke_fill=(0, 0, 0, 160))
            d.text((x, y), w, font=f, fill=(255, 214, 0) if key else (255, 255, 255), stroke_width=10, stroke_fill=(12, 12, 12))
        x += ww + gap

_last_badge = [None, 0.0]
def badge2(img, t):
    txt = badge_text(t)
    if not txt:
        return
    if txt != _last_badge[0]:
        _last_badge[0], _last_badge[1] = txt, t
    age = t - _last_badge[1]
    s = 1.0 + 0.18 * max(0, 1 - age / 0.25) ** 2
    bf = badge_font.font_variant(size=int(56 * s))
    d = ImageDraw.Draw(img, "RGBA")
    bb = d.textbbox((0, 0), txt, font=bf)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    dot = int(22 * s); padx = 34
    full = dot + 18 + tw
    x0, y0 = (W - full) / 2 - padx, 250
    d.rounded_rectangle((x0, y0, x0 + full + 2 * padx, y0 + th + 44), radius=40, fill=(10, 10, 20, 185),
                        outline=(255, 255, 255, 60), width=3)
    on = 0.55 + 0.45 * np.cos(t * 2 * np.pi * 1.2)
    cy = y0 + (th + 44) / 2
    d.ellipse((x0 + padx, cy - dot / 2, x0 + padx + dot, cy + dot / 2), fill=(255, 60, 60, int(255 * on)))
    d.text((x0 + padx + dot + 18 - bb[0], y0 + 22 - bb[1]), txt, font=bf, fill=(255, 255, 255))

def progress(img, t):
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, 0, W, 10), fill=(255, 255, 255, 50))
    d.rectangle((0, 0, int(W * min(t / FULL_T, 1)), 10), fill=(255, 214, 0, 230))

def badge(img, t):
    txt = badge_text(t)
    if not txt:
        return
    d = ImageDraw.Draw(img, "RGBA")
    bb = d.textbbox((0, 0), txt, font=badge_font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x0, y0 = (W - tw) / 2 - 40, 250
    d.rounded_rectangle((x0, y0, x0 + tw + 80, y0 + th + 50), radius=40, fill=(0, 0, 0, 170))
    d.text((x0 + 40 - bb[0], y0 + 25 - bb[1]), txt, font=badge_font, fill=(255, 255, 255))

# ---- audio ----
sr = 48000
voice, vsr = sf.read(f"{ep}/voice.wav")
voice = np.interp(np.arange(0, len(voice) * sr / vsr) * vsr / sr, np.arange(len(voice)), voice)
t = np.arange(int(T * sr)) / sr
rise = np.clip(t / T, 0, 1)
pad = sum(a * np.sin(2 * np.pi * f0 * t) for f0, a in [(65.4, .5), (98, .35), (130.8, .25), (155.6, .2)])
music = 0.05 * pad * (0.7 + 0.3 * rise)
beat = 60 / 128
n = int(0.22 * sr); tt = np.arange(n) / sr
kick = np.sin(2 * np.pi * 50 * np.exp(-tt * 9) * tt * 3) * np.exp(-tt * 16)
hn = int(0.05 * sr); hat = np.random.default_rng(1).normal(0, 1, hn) * np.exp(-np.arange(hn) / sr * 70)
for k in range(int(T / beat)):
    s = int(k * beat * sr); seg = music[s:s + n]; seg += 0.16 * kick[:len(seg)] * (0.5 + 0.5 * rise[s])
    s2 = int((k + 0.5) * beat * sr); seg2 = music[s2:s2 + hn]; seg2 += 0.025 * hat[:len(seg2)]
rng = np.random.default_rng(5); wn = int(0.35 * sr)
whoosh = np.convolve(rng.normal(0, 1, wn), np.ones(40) / 40, mode="same") * np.sin(np.linspace(0, np.pi, wn)) ** 2
bn = int(0.5 * sr); boom = np.sin(2 * np.pi * 42 * np.arange(bn) / sr) * np.exp(-np.arange(bn) / sr * 7)
for h in hits[1:]:
    s = int(max(h - 0.2, 0) * sr); seg = music[s:s + wn]; seg += 0.25 * whoosh[:len(seg)]
    s = int(h * sr); seg = music[s:s + bn]; seg += 0.35 * boom[:len(seg)]
music *= np.clip(t / 0.3, 0, 1) * np.clip((T - t) / 0.8, 0, 1)
mix = music.copy(); mix[:len(voice)] += voice[:len(mix)]
mix /= max(1.0, np.abs(mix).max() / 0.95)
sf.write(f"{ep}/mix.wav", mix.astype(np.float32), sr)

cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
       "-i", f"{ep}/mix.wav", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
prev_img = None
for f in range(N):
    tn = f / FPS
    base = scene_frame(tn)
    z, sx, sy = fx(tn)
    bw, bh = base.size; cw, ch = bw / z, bh / z
    cx = min(max(bw / 2 + sx * bw / W, cw / 2), bw - cw / 2)
    cy = min(max(bh / 2 + sy * bh / H, ch / 2), bh - ch / 2)
    img = base.resize((W, H), Image.LANCZOS, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    if z > 1.12 and prev_img is not None:               # motion smear on the punch-in
        img = Image.blend(img, prev_img, 0.35)
    prev_img = img
    img = grade(img)
    fl = flash(tn)
    if fl > 0:
        img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), fl)
    badge2(img, tn)
    g, act, age, wage = chunk_at(tn)
    if g:
        caption2(img, g, act, age, wage)
    progress(img, tn)
    p.stdin.write(img.tobytes())
p.stdin.close(); p.wait()
print("WROTE", OUT, round(T, 2))
