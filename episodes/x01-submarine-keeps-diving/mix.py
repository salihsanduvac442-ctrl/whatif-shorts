# score + foley + voice -> out/mix.wav  (narrator in front, effects barely audible)
import json, os, sys, numpy as np, soundfile as sf, soxr
HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.environ.get('LIB', os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(LIB, 'core', 'audio'))
from sfx import SR, t_, env_exp, lp, hp, bp, noise, brown, compress, limit, add, thump, creak, whoosh, rumble
EV = json.load(open(os.path.join(HERE, 'events.json'))); DUR = EV['dur']
src = open(os.path.join(HERE, 'timeline.js')).read(); LINES = json.loads(src[src.index('['):src.index('];') + 1])
T = {l['id']: l for l in LINES}
N = int(DUR * SR) + SR
music = np.zeros((N, 2)); fx = np.zeros((N, 2)); vox = np.zeros((N, 2))
rng = np.random.default_rng(7)
mtof = lambda m: 440 * 2 ** ((m - 69) / 12)
def marimba(m, v=1.0, d=1.2):
    f = mtof(m); tt = t_(d)
    x = np.sin(2 * np.pi * f * tt) * np.exp(-tt / .45) + .35 * np.sin(2 * np.pi * f * 3.93 * tt) * np.exp(-tt / .06) + .12 * np.sin(2 * np.pi * f * 9.2 * tt) * np.exp(-tt / .02)
    a = np.minimum(1, tt / .003); return x * a * v
def pluck(m, v=1.0, d=.5):
    f = mtof(m); tt = t_(d); x = np.zeros_like(tt)
    for h in range(1, 7): x += np.sin(2 * np.pi * f * h * tt) / h ** 1.3 * np.exp(-tt * (5 + h * 2.5))
    return x * np.minimum(1, tt / .002) * v
def bass(m, v=1.0, d=.45):
    f = mtof(m); tt = t_(d)
    x = np.sin(2 * np.pi * f * tt) + .35 * np.sin(4 * np.pi * f * tt) + .15 * np.sin(6 * np.pi * f * tt)
    return x * np.exp(-tt / .25) * np.minimum(1, tt / .005) * v
BEAT = .42
HOOK = 1.25 - .3   # music starts on the impact
CH = [[62, 65, 69, 74], [58, 62, 65, 70], [65, 69, 72, 77], [60, 64, 67, 72]]   # Dm Bb F C
BS = [38, 34, 41, 36]
t_floor0, t_cut = T['l08']['t0'] + .3, T['l10']['t0']; t_drill = t_cut + .6; t_end = T['l12']['t0']
# arpeggio layer (surface -> floor): eighths, instruments drop out with depth
bright = np.zeros((N, 2)); dull = np.zeros((N, 2))
t = HOOK + .3; i = 0
while t < t_floor0 - .2:
    bar = int((t - HOOK - .3) / (BEAT * 4)) % 4; step = i % 8; m = CH[bar][[0, 1, 2, 3, 2, 1, 2, 3][step]]
    dep = (t - HOOK) / (t_floor0 - HOOK)
    if dep < .45: add(bright, marimba(m + 12, .32), t, 1, -.3 + .6 * (step % 2))
    if step % 2 == 0: add(dull, bp(noise(.06), 3000, 9000) * np.exp(-t_(.06) / .015) * .25, t, 1, .4)   # shaker drive
    else: add(bright, pluck(m, .34), t, 1, -.3 + .6 * (step % 2))
    if step % 4 == 0: add(dull, bass(BS[bar], .55, .9), t, 1, 0)
    if dep > .6 and step % 2 == 1: add(dull, bass(BS[bar] + 12, .25, .25), t, 1, 0)
    t += BEAT / 2; i += 1
# intro: two marimba chords under the title
for k, m in enumerate(CH[0]): add(bright, marimba(m + 12, .4, 2.0), HOOK + .3 + k * .05, 1, -.4 + k * .25)
# cold open: driving low pulse under the flash-forward

# low-pass closing with depth: crossfade 3 filtered copies
tt = np.arange(N) / SR
w = np.clip((tt - HOOK) / (t_floor0 - HOOK), 0, 1)
B = [np.stack([lp(bright[:, c], f) for c in range(2)], 1) for f in (9000, 2200, 700)]
wa = np.clip(1 - w * 2, 0, 1); wc = np.clip(w * 2 - 1, 0, 1); wb = 1 - wa - wc
music += B[0] * wa[:, None] + B[1] * wb[:, None] + B[2] * wc[:, None] + dull
# drone underneath the whole dive, deepening
dr = np.zeros(N)
for f, g in ((36.7, .5), (55, .25), (73.4, .12)): dr += np.sin(2 * np.pi * f * tt + g) * g
dr *= np.clip((tt - HOOK) / 6, 0, 1) * (1 - np.clip((tt - t_floor0) / .6, 0, 1) * .7) * .22
music += np.stack([dr, dr], 1)
# drill section: pulse returns, faster (sixteenths), low
t = t_drill; i = 0
while t < t_end:
    bar = int((t - t_drill) / (BEAT * 4)) % 2; add(music, bass([38, 37][bar], .5 if i % 4 == 0 else .28, .2), t, 1, 0)
    if i % 4 == 2: add(music, pluck(62 + [0, 3, 5, 7][(i // 4) % 4], .22, .3), t, 1, .3)
    t += BEAT / 4; i += 1
# ending: one note per milestone as the column is revealed, then the open question
for k in range(10): add(music, marimba([62, 65, 69, 72, 74, 77, 79, 81, 84, 86][k], .3, 1.6), t_end + 1.2 + k * .16, 1, -.5 + k * .1)
add(music, marimba(76, .35, 3.0), DUR - 1.6, 1, 0); add(music, marimba(71, .25, 3.0), DUR - 1.6, 1, .2)
# ---- foley (quiet) ----
def ping():
    tt = t_(1.4); return np.sin(2 * np.pi * 1320 * tt) * np.exp(-tt / .35) * .5
def splash():
    x = bp(noise(1.0), 300, 4000) * np.exp(-t_(1.0) / .25); return x * .5
for e in EV['ev']:
    ty, at = e['type'], e['t']
    if ty == 'splash': add(fx, splash(), at, .5)
    elif ty == 'ping': add(fx, ping(), at, .22, .2)
    elif ty == 'fall':
        d = e['d']; n = int(d * SR); f = 1400 * np.exp(np.linspace(0, np.log(.35), n)); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.linspace(.1, .6, n)
        x = x + bp(noise(d), 500, 5000)[:n] * np.linspace(0, .6, n); add(fx, x, at, .5)
    elif ty == 'bigsplash':
        d = 1.6; x = bp(noise(d), 200, 6000) * np.exp(-t_(d) / .35) + lp(noise(d), 300) * np.exp(-t_(d) / .25) * 2
        add(fx, x / np.abs(x).max(), at, 1.6); add(fx, thump(1.0, 50), at, 1.4)
        add(fx, lp(noise(1.2), 900) * np.exp(-t_(1.2) / .5) * .8, at + .3, .6)
    elif ty == 'slam': add(fx, thump(1.0, 90), at, .55); add(fx, bp(noise(.08), 1500, 7000) * np.exp(-t_(.08) / .02), at, .25)
    elif ty == 'hit': add(fx, thump(1.0, 60), at, .45); add(fx, ping(), at, .12, .2)
    elif ty == 'rewind':
        d = .45; f = 200 * np.exp(np.linspace(np.log(1), np.log(12), int(d * SR))); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * .3 + bp(noise(d), 800, 6000) * .5
        add(fx, x * np.linspace(.2, 1, len(x)), at, .6); add(fx, whoosh(.5, 1.0), at, .5)
    elif ty == 'thud': add(fx, thump(1.0, 55), at, .7)
    elif ty == 'creak': add(fx, creak(1.0), at, .25, -.3)
    elif ty == 'cut': add(fx, bp(noise(.5), 1500, 5000) * np.exp(-t_(.5) / .2) * .3, at, .3)
    elif ty == 'crack': add(fx, thump(1.0, 80), at, .6); add(fx, bp(noise(.4), 400, 3000) * np.exp(-t_(.4) / .08), at, .3)
    elif ty == 'drill':
        d = e['d']; x = lp(brown(d), 600) * (1 + .4 * np.sin(2 * np.pi * 23 * t_(d))); x = x / (np.abs(x).max() + 1e-9)
        x *= np.minimum(1, t_(d) / .2) * np.minimum(1, (d - t_(d)) / .5); add(fx, x, at, .18)
    elif ty == 'whoosh': add(fx, whoosh(1.2, 1.0), at, .25)
# ambience: soft surf at the surface, low hum below
amb = lp(brown(DUR + 1), 900); amb = amb / (np.abs(amb).max() + 1e-9)
amb_env = np.where((tt < HOOK + 1.2) & (tt > HOOK), .25, .08 * np.clip(1 - (tt - t_floor0) / 1.0, .2, 1)); fx += np.stack([amb[:N] * amb_env, amb[:N] * amb_env], 1) * .5
# ---- voice ----
for l in LINES:
    x, sr = sf.read(os.path.join(HERE, 'voices', l['id'] + '.wav'))
    if x.ndim > 1: x = x.mean(1)
    x = soxr.resample(x, sr, SR); x = hp(x, 80)
    add(vox, x, l['t0'], 1.0)
v = vox[:, 0]; v = compress(v / (np.abs(v).max() + 1e-9) * .9, thr=.18, ratio=4.0); vox = np.stack([v, v], 1)
rms = lambda a: np.sqrt(np.mean(a[np.abs(a) > 1e-4] ** 2)) if np.any(np.abs(a) > 1e-4) else 1e-9
music *= (rms(vox) / rms(music)) * 10 ** (-13 / 20)       # music ~13 dB under the voice
fx *= (rms(vox) / max(rms(fx), 1e-9)) * 10 ** (-15 / 20)
# duck music under speech
spk = np.zeros(N)
for l in LINES: spk[int(l['t0'] * SR):int(l['t1'] * SR)] = 1
k = int(.15 * SR); spk = np.convolve(spk, np.ones(k) / k, 'same'); music *= (1 - .45 * spk)[:, None]
mix = vox + music + fx
mix = mix / (np.abs(mix).max() + 1e-9) * .9
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
sf.write(os.path.join(HERE, 'out', 'mix.wav'), mix[:int(DUR * SR)].astype(np.float32), SR, subtype='PCM_24')
print('mix ok', DUR)
