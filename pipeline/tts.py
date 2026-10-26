"""Narration: python3 tts.py <episode_dir>
Reads <episode_dir>/script.json (list of lines), writes voice.wav + timing.json.
Kokoro model files are downloaded once to ~/kokoro (from GitHub releases)."""
import json, os, sys, subprocess
import numpy as np, soundfile as sf

ep = sys.argv[1]
speed = float(sys.argv[2]) if len(sys.argv) > 2 else 1.34
md = os.path.expanduser("~/kokoro")
os.makedirs(md, exist_ok=True)
base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
for f, name in (("kokoro.onnx", "kokoro-v1.0.onnx"), ("voices.bin", "voices-v1.0.bin")):
    if not os.path.exists(f"{md}/{f}"):
        subprocess.run(["curl", "-sSL", "-o", f"{md}/{f}", base + name], check=True)
from kokoro_onnx import Kokoro
k = Kokoro(f"{md}/kokoro.onnx", f"{md}/voices.bin")
lines = json.load(open(f"{ep}/script.json"))
out, timing, t, sr = [], [], 0.0, 24000
for l in lines:
    a, sr = k.create(l, voice="am_michael", speed=speed, lang="en-us")
    idx = np.where(np.abs(a) > 0.01)[0]
    a = a[max(idx[0] - 200, 0): idx[-1] + 800]
    gap = 0.12 if not l.endswith("...") else 0.3
    timing.append({"text": l, "start": t, "end": t + len(a) / sr})
    out += [a, np.zeros(int(gap * sr), dtype=a.dtype)]
    t += len(a) / sr + gap
sf.write(f"{ep}/voice.wav", np.concatenate(out), sr)
json.dump(timing, open(f"{ep}/timing.json", "w"), indent=1)
print(f"narration {t:.2f}s")
for x in timing:
    print(f"{x['start']:6.2f}  {x['text']}")
