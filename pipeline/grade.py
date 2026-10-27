"""Colour grade for look v2 (used by compose_v2.py): bloom on bright lights, punchier contrast and
saturation, a gentle teal-shadow / warm-highlight split, vignette and fine grain."""
import numpy as np
from PIL import Image, ImageFilter

_vig = {}
def _vignette(w, h):
    if (w, h) not in _vig:
        y, x = np.mgrid[0:h, 0:w]
        r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
        _vig[(w, h)] = (1 - 0.38 * np.clip((r - 0.35) / 0.65, 0, 1) ** 1.6)[..., None].astype(np.float32)
    return _vig[(w, h)]

_rng = np.random.default_rng(7)
def grade(img):
    w, h = img.size
    small = img.resize((w // 4, h // 4), Image.BILINEAR)
    a = np.asarray(small, dtype=np.float32) / 255
    mx = a.max(axis=2)
    hi = np.clip((mx - 0.97) / 0.03, 0, 1)[..., None] * a            # only near-clipped lights (lamps, windows, glow)
    b1 = Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    b2 = Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18))
    bloom = (np.asarray(b1.resize((w, h), Image.BILINEAR), np.float32) * 0.16 +
             np.asarray(b2.resize((w, h), Image.BILINEAR), np.float32) * 0.22) / 255

    x = np.asarray(img, dtype=np.float32) / 255
    x = x + bloom * (1 - x * 0.5)                                         # screen-ish add
    l = x @ np.array([0.299, 0.587, 0.114], np.float32)
    x = l[..., None] + (x - l[..., None]) * 1.18                          # saturation +18 %
    x = 0.5 + (x - 0.5) * 1.10                                            # contrast +10 %
    sh = np.clip(1 - l * 2.2, 0, 1)[..., None]                            # shadows -> a touch teal
    hl = np.clip((l - 0.6) * 2.5, 0, 1)[..., None]                        # highlights -> a touch warm
    x = x + sh * np.array([-0.02, 0.01, 0.035], np.float32) + hl * np.array([0.03, 0.012, -0.02], np.float32)
    x = x * _vignette(w, h)
    x = x + _rng.normal(0, 0.012, (h, w, 1)).astype(np.float32)          # fine grain
    return Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8))
