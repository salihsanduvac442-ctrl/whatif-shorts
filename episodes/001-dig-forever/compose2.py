import json, re, subprocess, random, numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
FR = "/home/claude/whatif/frames"
OUT = "/home/claude/whatif/whatif_dig_25s.mp4"
font = ImageFont.truetype("/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf", 124)
badge_font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Black.otf", 64)
random.seed(3)

old = json.load(open("/home/claude/whatif/timing_v1.json"))
new = json.load(open("/home/claude/whatif/timing.json"))
T = new[-1]["end"] + 0.7
N = int(T * FPS)
OLD_END = 39.95
anchors_new = [0.0] + [l["start"] for l in new] + [new[-1]["end"] + 0.1, T]
anchors_old = [0.0] + [l["start"] for l in old] + [old[-1]["end"] + 0.1, OLD_END]
def old_t(t):
    return float(np.interp(t, anchors_new, anchors_old))

# depth badge values keyed on line starts (index -> metres)
depth_keys = [(0, 0), (new[2]["start"], 1), (new[3]["start"], 10), (new[5]["start"], 100),
              (new[6]["start"], 1000), (new[7]["start"], 12262), (new[9]["start"], 35000),
              (new[10]["start"], 70000), (T, 72000)]
def depth_at(t):
    for (a, da), (b, db) in zip(depth_keys, depth_keys[1:]):
        if a <= t < b:
            k = min((t - a) / 0.6, 1.0)          # quick count-up after each key
            k = 1 - (1 - k) ** 3
            prev = depth_keys[depth_keys.index((a, da)) - 1][1] if a > 0 else 0
            return prev + (da - prev) * k
    return depth_keys[-1][1]
def fmt_depth(m):
    if m < 1000:
        return f"{int(round(m))} m"
    return f"{m/1000:.1f} km".replace(".0 km", " km")

# ---- words ----
words = []
for ln in new:
    toks = [t for t in re.sub(r"\.\.\.", " ", ln["text"]).split() if t]
    wts = [len(re.sub(r"[^\w']", "", t)) + 2 for t in toks]
    tot = sum(wts); t = ln["start"]; dur = ln["end"] - ln["start"]
    for tok, wt in zip(toks, wts):
        d = dur * wt / tot
        words.append((t, t + d, tok.strip(",.?!").upper()))
        t += d
def word_at(ts):
    for i, (a, b, w) in enumerate(words):
        nb = words[i + 1][0] if i + 1 < len(words) else b + 0.6
        if a <= ts < max(b, min(nb, b + 0.3)):
            return w, ts - a
    return None, 0

# ---- impacts (line starts) ----
hits = [l["start"] for l in new]
def fx(t):
    zoom, sx, sy = 1.04 + 0.025 * np.sin(t * 0.9), 0.0, 0.0
    for h in hits:
        a = t - h
        if 0 <= a < 0.45:
            e = (1 - a / 0.45) ** 3
            zoom += 0.10 * e
            sx += random.uniform(-1, 1) * 9 * e
            sy += random.uniform(-1, 1) * 9 * e
    return zoom, sx, sy

src = {}
def raw(f):
    f = min(max(f, 0), 958)
    if f not in src:
        if len(src) > 6: src.clear()
        src[f] = Image.open(f"{FR}/f{f:04d}.png").convert("RGB")
    return src[f]
def frame_at_old(ot):
    x = ot * 24 / 2
    i = int(np.floor(x)); fr = x - i
    a, b = raw(i * 2), raw(i * 2 + 2)
    return Image.blend(a, b, fr) if fr > 0.02 else a

def caption(img, w, age):
    pop = min(age / 0.06, 1.0)
    scale = 0.7 + 0.3 * pop + 0.08 * np.sin(min(age / 0.14, 1) * np.pi)
    fnt = font.font_variant(size=int(124 * scale))
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), w, font=fnt, stroke_width=12)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x, y = (W - tw) / 2 - bb[0], H * 0.47 - th / 2 - bb[1]
    d.text((x + 5, y + 9), w, font=fnt, fill=(0, 0, 0), stroke_width=12, stroke_fill=(0, 0, 0))
    hl = (255, 214, 0) if any(c.isdigit() for c in w) or w in ("ONE", "TEN", "TWELVE", "HUNDRED", "KILOMETER", "KILOMETERS", "METER", "METERS", "MOLTEN", "TREASURE", "DINOSAUR", "FOSSILS", "ROOTS") else (255, 255, 255)
    d.text((x, y), w, font=fnt, fill=hl, stroke_width=12, stroke_fill=(10, 10, 10))

def badge(img, t):
    if t < new[2]["start"] - 0.05:
        return
    txt = "DEPTH  " + fmt_depth(depth_at(t))
    d = ImageDraw.Draw(img, "RGBA")
    bb = d.textbbox((0, 0), txt, font=badge_font)
    tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    x0 = (W - tw) / 2 - 40; y0 = 250
    d.rounded_rectangle((x0, y0, x0 + tw + 80, y0 + th + 50), radius=40, fill=(0, 0, 0, 170))
    d.text((x0 + 40 - bb[0], y0 + 25 - bb[1]), txt, font=badge_font, fill=(255, 255, 255))

# ---- audio: voice + punchier music + impact/whoosh sfx ----
sr = 48000
voice, vsr = sf.read("/home/claude/whatif/voice.wav")
voice = np.interp(np.arange(0, len(voice) * sr / vsr) * vsr / sr, np.arange(len(voice)), voice)
t = np.arange(int(T * sr)) / sr
rise = np.clip(t / T, 0, 1)
pad = sum(a * np.sin(2 * np.pi * f0 * t) for f0, a in [(65.4, .5), (98, .35), (130.8, .25), (155.6, .2)])
bpm = 128; beat_len = 60 / bpm
music = 0.05 * pad * (0.7 + 0.3 * rise)
n = int(0.22 * sr); tt = np.arange(n) / sr
kick = np.sin(2 * np.pi * 50 * np.exp(-tt * 9) * tt * 3) * np.exp(-tt * 16)
hat_n = int(0.05 * sr); hat = np.random.default_rng(1).normal(0, 1, hat_n) * np.exp(-np.arange(hat_n) / sr * 70)
for k in range(int(T / beat_len)):
    s = int(k * beat_len * sr)
    seg = music[s:s + n]; seg += 0.16 * kick[:len(seg)] * (0.5 + 0.5 * rise[s])
    s2 = int((k + 0.5) * beat_len * sr); seg2 = music[s2:s2 + hat_n]; seg2 += 0.025 * hat[:len(seg2)]
rng = np.random.default_rng(5)
wn = int(0.35 * sr)
noise = rng.normal(0, 1, wn)
whoosh = np.convolve(noise, np.ones(40) / 40, mode="same") * np.sin(np.linspace(0, np.pi, wn)) ** 2
boom = np.sin(2 * np.pi * 42 * np.arange(int(0.5 * sr)) / sr) * np.exp(-np.arange(int(0.5 * sr)) / sr * 7)
for h in hits[1:]:
    s = int((h - 0.2) * sr); seg = music[s:s + wn]; seg += 0.25 * whoosh[:len(seg)]
    s = int(h * sr); seg = music[s:s + len(boom)]; seg += 0.35 * boom[:len(seg)]
music *= np.clip(t / 0.3, 0, 1) * np.clip((T - t) / 0.8, 0, 1)
mix = music.copy(); mix[:len(voice)] += voice[:len(mix)]
mix /= max(1.0, np.abs(mix).max() / 0.95)
sf.write("/home/claude/whatif/mix25.wav", mix.astype(np.float32), sr)

cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
       "-i", "/home/claude/whatif/mix25.wav", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
for f in range(N):
    tnow = f / FPS
    base = frame_at_old(old_t(tnow))
    z, sx, sy = fx(tnow)
    bw, bh = base.size
    cw, ch = bw / z, bh / z
    cx, cy = bw / 2 + sx * bw / W, bh / 2 + sy * bh / H
    cx = min(max(cx, cw / 2), bw - cw / 2); cy = min(max(cy, ch / 2), bh - ch / 2)
    img = base.resize((W, H), Image.LANCZOS, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    badge(img, tnow)
    w, age = word_at(tnow)
    if w:
        caption(img, w, age)
    p.stdin.write(img.tobytes())
p.stdin.close(); p.wait()
print("WROTE", OUT, round(T, 2))
