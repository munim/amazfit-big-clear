#!/usr/bin/env python3
"""Generate every sprite, edit-mode image and layout file for the face.

Geometry follows amazfit-face-round-v2.html (Oxanium, 36cqw time, four corner
data points, weather on top, date at the bottom). One build per resolution so
every sprite is rendered at native size and no resampling happens on device.

Usage: python3 tools/gen_assets.py
Needs: fontTools, Pillow, numpy, rsvg-convert (brew install librsvg).
"""
import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image
import io

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "tools" / "fonts" / "Oxanium-Regular.ttf"

# target key -> (screen width, zeus qualifier)
TARGETS = {"f466": (466, "w466-r"), "f480": (480, "w480-r")}

SAMPLE = {"kcal": 412, "hr": 72, "battery": 76, "steps": 8421, "goal": 10000,
          "temp": 18, "high": 22, "low": 14, "wx": "cloud",
          "hour": 10, "minute": 8, "weekday": 0, "month": 10, "day": 2}

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Zepp weather condition id -> icon name (ids from the Zepp watchface specification)
WEATHER_MAP = {
    0: "partly", 1: "rain", 2: "snow", 3: "sun", 4: "cloud", 5: "rain", 6: "snow",
    7: "rain", 8: "snow", 9: "snow", 10: "rain", 11: "fog", 12: "snow", 13: "fog",
    14: "fog", 15: "storm", 16: "snow", 17: "fog", 18: "rain", 19: "rain", 20: "storm",
    21: "rain", 22: "fog", 23: "fog", 24: "rain", 25: "cloud", 26: "partly", 27: "rain",
    28: "moon",
}

STEP_BAR_LEVELS = 20
BATTERY_LEVELS = 40  # 2.5% buckets, so the fill can round to the nearest quarter and warn at 20%
BATTERY_WARN_BELOW = 8  # buckets below 20%
STEPS_K_FROM = 10000


def battery_fill(bucket):
    """Fill quarter (0, 25, 50, 75, 100) for a 2.5% bucket."""
    return int((2.5 * bucket + 12.5) // 25) * 25


def steps_text(n):
    """Steps as shown on the face: plain below 10000, then 10.4K (floored, never rounded up)."""
    if n < STEPS_K_FROM:
        return str(n)
    tenths = n // 100
    if tenths >= 1000:
        return "%dK" % (tenths // 10)
    return "%d.%dK" % (tenths // 10, tenths % 10)


# ───────────────────────── colour ─────────────────────────
def oklch(l, c, h):
    a = c * math.cos(math.radians(h))
    b = c * math.sin(math.radians(h))
    l_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (l - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = [
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    ]
    out = []
    for v in rgb:
        v = min(1.0, max(0.0, v))
        v = 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055
        out.append(round(v * 255))
    return "#%02x%02x%02x" % tuple(out)


FG = oklch(0.97, 0.004, 250)
DIM = oklch(0.66, 0.010, 250)
TRACK = oklch(0.26, 0.010, 250)
ACCENT = oklch(0.74, 0.15, 255)
WARN = oklch(0.80, 0.16, 75)
AOD_FG = oklch(0.78, 0.005, 250)
AOD_DIM = oklch(0.60, 0.008, 250)

# ───────────────────────── icons (24-unit grid, from the mockup) ─────────────────────────
ICON = {
    "steps": '<ellipse cx="8" cy="15.5" rx="2.9" ry="4.2"/><ellipse cx="16.5" cy="9.5" rx="2.9" ry="4.2"/>',
    "heart": '<path d="M12 19.5C12 19.5 4.5 15 4.5 9.2A3.9 3.9 0 0 1 12 7.4a3.9 3.9 0 0 1 7.5 1.8c0 5.8-7.5 10.3-7.5 10.3z"/>',
    "battery": '<rect x="2.5" y="7.5" width="16" height="9" rx="2"/><path d="M21.5 10.5v3"/>',
    "flame": '<path d="M12 3.2c.7 3 3.9 4.9 3.9 9.1a3.9 3.9 0 0 1-7.8 0c0-2 .9-3.4 2-4.5.1 1.4.7 2.3 1.6 2.7-.2-2.6.3-4.7.3-7.3z"/>',
    "cloud": '<path d="M7.5 18.5a4 4 0 0 1-.4-8 5.5 5.5 0 0 1 10.4-1.2 3.6 3.6 0 0 1 .5 9.2H7.5z"/>',
    "rain": '<path d="M7.5 15.5a4 4 0 0 1-.4-8 5.5 5.5 0 0 1 10.4-1.2 3.6 3.6 0 0 1 .5 9.2H7.5z"/><path d="M8.5 18.5l-.8 2.5M12.5 18.5l-.8 2.5M16.5 18.5l-.8 2.5"/>',
    "snow": '<path d="M7.5 15.5a4 4 0 0 1-.4-8 5.5 5.5 0 0 1 10.4-1.2 3.6 3.6 0 0 1 .5 9.2H7.5z"/><path d="M8 18.5v3M6.5 20h3M12 18.5v3M10.5 20h3M16 18.5v3M14.5 20h3"/>',
    "storm": '<path d="M7.5 15.5a4 4 0 0 1-.4-8 5.5 5.5 0 0 1 10.4-1.2 3.6 3.6 0 0 1 .5 9.2H7.5z"/><path d="M12.8 15.2 10.6 19h2.9l-2.2 3.8"/>',
    "fog": '<path d="M4 8h16M6.5 12h11M4 16h16M7.5 20h9"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M6.3 6.3l1.6 1.6M17.7 6.3l-1.6 1.6M17.7 17.7l-1.6-1.6M6.3 17.7l1.6-1.6"/>',
    "partly": '<circle cx="8.5" cy="8.5" r="2.9"/><path d="M8.5 2.6v1.3M2.6 8.5h1.3M4.4 4.4l.9.9M12.6 4.4l-.9.9"/><path d="M10.5 20h7.4a3.2 3.2 0 0 0 .2-6.4 4.6 4.6 0 0 0-8.5-1.1A3.2 3.2 0 0 0 10.5 20z"/>',
    "am": '<path d="M5.5 17a6.5 6.5 0 0 1 13 0"/><path d="M2.5 20.5h19M12 6.5v2M5.2 10.2l1.2 1.2M18.8 10.2l-1.2 1.2"/>',
    "pm": '<path d="M19.5 14.6A8 8 0 0 1 9.4 4.5a8 8 0 1 0 10.1 10.1z"/>',
    "up": '<path d="M12 19V5M5.5 11.5 12 5l6.5 6.5"/>',
    "down": '<path d="M12 5v14M5.5 12.5 12 19l6.5-6.5"/>',
}
ICON["moon"] = ICON["pm"]


# ───────────────────────── rendering helpers ─────────────────────────
def svg_png(svg, w, h):
    proc = subprocess.run(["rsvg-convert", "-f", "png", "-w", str(w), "-h", str(h)],
                          input=svg.encode(), capture_output=True, check=True)
    return Image.open(io.BytesIO(proc.stdout)).convert("RGBA")


def svg_doc(w, h, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>'
            % (w, h, w, h, body))


class Font:
    def __init__(self, path):
        self.ttf = TTFont(str(path))
        self.gs = self.ttf.getGlyphSet()
        self.cmap = self.ttf.getBestCmap()
        self.hmtx = self.ttf["hmtx"]
        self.upm = self.ttf["head"].unitsPerEm
        self._cache = {}

    def glyph(self, ch):
        if ch in self._cache:
            return self._cache[ch]
        name = self.cmap[ord(ch)]
        pen = SVGPathPen(self.gs)
        self.gs[name].draw(pen)
        bp = BoundsPen(self.gs)
        self.gs[name].draw(bp)
        res = {"d": pen.getCommands(), "adv": self.hmtx[name][0], "bounds": bp.bounds}
        self._cache[ch] = res
        return res

    def vrange(self, chars):
        ymax, ymin = 0, 0
        for ch in chars:
            b = self.glyph(ch)["bounds"]
            if b:
                ymax, ymin = max(ymax, b[3]), min(ymin, b[1])
        return ymax, ymin


FONT = Font(FONT_PATH)


class Sprite:
    def __init__(self, img, baseline):
        self.img = img
        self.baseline = baseline  # distance from canvas top to text baseline, px
        self.w, self.h = img.size


def text_sprite(text, size, fill, vchars, *, outline=0.0, tracking=0.0, cell_w=None,
                align="center", pad=1, trailing=0.0, bold=0.0, fixed_pad=None):
    """Render `text` with Oxanium outlines. size in px, tracking in px.
    All sprites that pass the same vchars/size/pad share one canvas height and baseline."""
    k = size / FONT.upm
    ymax, ymin = FONT.vrange(vchars)
    pad = pad + (math.ceil(outline / 2) if outline else 0) + (math.ceil(bold / 2) if bold else 0)
    if fixed_pad is not None:
        pad = fixed_pad
    h = math.ceil((ymax - ymin) * k + 2 * pad)
    baseline = pad + ymax * k
    x = 0.0
    items = []
    for ch in text:
        g = FONT.glyph(ch)
        items.append((x, g))
        x += g["adv"] * k + tracking
    natural = x
    w = cell_w if cell_w is not None else math.ceil(natural + trailing)
    off = {"left": 0.0, "center": (w - natural + tracking) / 2 if cell_w else 0.0,
           "right": w - natural + tracking}[align]
    body = []
    for gx, g in items:
        if not g["d"]:
            continue
        tr = 'translate(%.3f %.3f) scale(%.5f %.5f)' % (gx + off, baseline, k, -k)
        if outline:
            body.append('<path d="%s" transform="%s" fill="none" stroke="%s" stroke-width="%.4f" stroke-linejoin="round"/>'
                        % (g["d"], tr, fill, outline / k))
        elif bold:
            body.append('<path d="%s" transform="%s" fill="%s" stroke="%s" stroke-width="%.4f" stroke-linejoin="round"/>'
                        % (g["d"], tr, fill, fill, bold / k))
        else:
            body.append('<path d="%s" transform="%s" fill="%s"/>' % (g["d"], tr, fill))
    return Sprite(svg_png(svg_doc(w, h, "".join(body)), w, h), baseline)


def icon_sprite(name, size, color, stroke=1.6, extra=""):
    size = max(1, round(size))
    body = ('<g fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round" '
            'transform="scale(%.5f)">%s%s</g>' % (color, stroke, size / 24.0, ICON[name], extra))
    return Sprite(svg_png(svg_doc(size, size, body), size, size), 0)


def battery_icon_sprite(size, color, fill):
    extra = ""
    if fill:
        extra = '<rect x="4.3" y="9.3" width="%.2f" height="5.4" rx="0.8" fill="%s" stroke="none"/>' % (12.4 * fill / 100, color)
    return icon_sprite("battery", size, color, extra=extra)


def solid_sprite(w, h, rgba):
    return Sprite(Image.new("RGBA", (w, h), rgba), 0)


def rounded_rect_sprite(w, h, r, fill=None, stroke=None, sw=0):
    inset = sw / 2
    body = '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" fill="%s" stroke="%s" stroke-width="%.2f"/>' % (
        inset, inset, w - sw, h - sw, r, fill or "none", stroke or "none", sw)
    return Sprite(svg_png(svg_doc(w, h, body), w, h), 0)


def save(sprite, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    sprite.img.save(path, optimize=True)


# ───────────────────────── build one target ─────────────────────────
def build(target, W, qualifier):
    cq = W / 100.0
    s = W / 480.0
    out = ROOT / "assets" / ("%s.%s" % (target, qualifier))
    if out.exists():
        shutil.rmtree(out)
    img_dir = out / "images"
    files = {}  # name -> Sprite, name without extension

    def put(name, sprite):
        files[name] = sprite
        save(sprite, img_dir / (name + ".png"))
        return sprite

    digits = "0123456789"
    lay = {"W": W}

    # ── time ──
    tsize = 36 * cq
    tk = tsize / FONT.upm
    cell = math.ceil(FONT.glyph("0")["adv"] * tk)
    t_stroke = max(3.0, 0.7 * cq)  # extra weight of the solid digits / line width of the outline digits
    aod_w = max(2.0, 0.45 * cq)
    t_pad = 1 + math.ceil(t_stroke / 2)  # same canvas and baseline for every time sprite
    for d in digits:
        put("time/s%s" % d, text_sprite(d, tsize, FG, digits, cell_w=cell, bold=t_stroke, fixed_pad=t_pad))
        put("time/o%s" % d, text_sprite(d, tsize, FG, digits, cell_w=cell, outline=t_stroke, fixed_pad=t_pad))
        put("time/a%s" % d, text_sprite(d, tsize, AOD_FG, digits, cell_w=cell, outline=aod_w, fixed_pad=t_pad))
    tref = files["time/s0"]
    b1 = W / 2 - 0.13 * tsize
    b2 = b1 + 0.95 * tsize
    x0 = round(W / 2 - cell)
    lay["time"] = {
        "hx": x0, "hy": round(b1 - tref.baseline),
        "mx": x0, "my": round(b2 - tref.baseline),
        "cell": cell,
    }
    time_box_top = b1 - 0.69 * tsize
    time_box_bot = b2
    # AM / PM tag: icon above label, dim, right of the digits
    asz = 6.0 * cq
    lsz = 4.6 * cq
    gap = 0.8 * cq
    ltrack = 0.05 * lsz
    lh = math.ceil(1.1 * lsz)
    for tag, ic in (("AM", "am"), ("PM", "pm")):
        lbl = text_sprite(tag, lsz, DIM, "AMP", tracking=ltrack, pad=0)
        isp = icon_sprite(ic, asz, DIM)
        w = max(isp.w, lbl.w)
        h = isp.h + round(gap) + lh
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.alpha_composite(isp.img, ((w - isp.w) // 2, 0))
        base_y = isp.h + round(gap) + 0.84 * lsz
        canvas.alpha_composite(lbl.img, ((w - lbl.w) // 2, round(base_y - lbl.baseline)))
        put("time/%s" % tag.lower(), Sprite(canvas, 0))
    am = files["time/am"]
    pm = files["time/pm"]
    box_h = 1.9 * tsize
    t0 = W / 2 - 0.895 * tsize
    ay = round(t0 + 32.2 * cq - am.h / 2)
    ax = x0 + 2 * cell + round(1.2 * cq)
    lay["time"].update({"ax": ax, "ay": ay, "aw": max(am.w, pm.w), "ah": am.h})

    # ── corner value font (5.2cqw) ──
    vsize = 7.2 * cq
    vk = vsize / FONT.upm
    vcell = math.ceil(FONT.glyph("0")["adv"] * vk)
    vchars = digits + "%-K"
    for d in digits:
        put("val/%s" % d, text_sprite(d, vsize, FG, vchars, cell_w=vcell))
        put("val/a%s" % d, text_sprite(d, vsize, AOD_FG, vchars, cell_w=vcell))
    pct_cell = math.ceil(FONT.glyph("%")["adv"] * vk)
    put("val/pct", text_sprite("%", vsize, FG, vchars, cell_w=pct_cell))
    put("val/apct", text_sprite("%", vsize, AOD_FG, vchars, cell_w=pct_cell))
    put("val/inv", text_sprite("--", vsize, FG, vchars, tracking=0.04 * vsize))
    dot_cell = math.ceil(FONT.glyph(".")["adv"] * vk)
    k_cell = math.ceil(FONT.glyph("K")["adv"] * vk)
    put("val/dot", text_sprite(".", vsize, FG, vchars, cell_w=dot_cell))
    put("val/k", text_sprite("K", vsize, FG, vchars, cell_w=k_cell))
    vref = files["val/0"]

    isz_c = 7 * cq
    for name in ("flame", "heart", "steps"):
        put("icon/%s" % name, icon_sprite(name, isz_c, DIM))
    for fill in (0, 25, 50, 75, 100):
        put("icon/bat%d" % fill, battery_icon_sprite(isz_c, DIM, fill))
        put("icon/bata%d" % fill, battery_icon_sprite(isz_c, AOD_DIM, fill))
        if fill <= 25:
            put("icon/batw%d" % fill, battery_icon_sprite(isz_c, WARN, fill))

    def battery_name(pct, aod=False):
        b = min(BATTERY_LEVELS - 1, int(pct * BATTERY_LEVELS / 100))
        prefix = "bata" if aod else ("batw" if b < BATTERY_WARN_BELOW else "bat")
        return "icon/%s%d" % (prefix, battery_fill(b))

    bar_w = round(14 * cq)
    bar_h = max(3, round(4.5 * s))
    for i in range(STEP_BAR_LEVELS):
        fill_w = round(bar_w * i / (STEP_BAR_LEVELS - 1))
        body = '<rect width="%d" height="%d" rx="%.1f" fill="%s"/>' % (bar_w, bar_h, bar_h / 2, TRACK)
        if fill_w > 0:
            body += '<rect width="%d" height="%d" rx="%.1f" fill="%s"/>' % (max(fill_w, bar_h), bar_h, bar_h / 2, ACCENT)
        put("bar/%d" % i, Sprite(svg_png(svg_doc(bar_w, bar_h, body), bar_w, bar_h), 0))

    gap_c = 0.8 * cq  # icon-to-value gap
    line_v = 1.05 * vsize
    corners = {}
    for key, sx, sy, has_bar in (("cal", -1, -1, False), ("bat", 1, -1, False),
                                 ("hr", -1, 1, False), ("steps", 1, 1, True)):
        cx = W / 2 + sx * 33 * cq
        cy = W / 2 + sy * 17 * cq
        block_h = isz_c + gap_c + line_v + ((gap_c + bar_h) if has_bar else 0)
        top = cy - block_h / 2
        base = top + isz_c + gap_c + 0.815 * vsize
        vw = 6 * vcell
        c = {
            "cx": round(cx),
            "ix": round(cx - files["icon/flame"].w / 2), "iy": round(top),
            "vx": round(cx - vw / 2), "vy": round(base - vref.baseline), "vw": vw, "vh": vref.h,
        }
        if has_bar:
            c.update({"bx": round(cx - bar_w / 2),
                      "by": round(top + isz_c + gap_c + line_v + gap_c), "bw": bar_w, "bh": bar_h})
        corners[key] = c
    lay["corner"] = corners
    lay["stepsK"] = {"cell": vcell, "dot": dot_cell, "k": k_cell, "cx": corners["steps"]["cx"],
                     "y": corners["steps"]["vy"], "h": vref.h, "from": STEPS_K_FROM}

    # ── weather (top) ──
    wsize = 7.5 * cq
    wk = wsize / FONT.upm
    wcell = math.ceil(FONT.glyph("0")["adv"] * wk)
    wchars = digits + "°-"
    for d in digits:
        put("wx/t%s" % d, text_sprite(d, wsize, FG, wchars, cell_w=wcell))
    put("wx/deg", text_sprite("°", wsize, FG, wchars, cell_w=math.ceil(FONT.glyph("°")["adv"] * wk)))
    put("wx/neg", text_sprite("-", wsize, FG, wchars, cell_w=math.ceil(FONT.glyph("-")["adv"] * wk)))
    put("wx/inv", text_sprite("--", wsize, FG, wchars, tracking=0.04 * wsize))
    hsize = 4.8 * cq
    hk = hsize / FONT.upm
    hcell = math.ceil(FONT.glyph("0")["adv"] * hk)
    hchars = digits + "-"
    for d in digits:
        put("wx/h%s" % d, text_sprite(d, hsize, DIM, hchars, cell_w=hcell))
    put("wx/hneg", text_sprite("-", hsize, DIM, hchars, cell_w=math.ceil(FONT.glyph("-")["adv"] * hk)))
    put("wx/hinv", text_sprite("--", hsize, DIM, hchars, tracking=0.04 * hsize))
    wref = files["wx/t0"]
    href = files["wx/h0"]
    wicon = 6.5 * cq
    names = sorted(set(WEATHER_MAP.values()))
    for n in names:
        put("wx/i_%s" % n, icon_sprite(n, wicon, DIM))
    arrow = 4.2 * cq
    put("wx/up", icon_sprite("up", arrow, DIM))
    put("wx/down", icon_sprite("down", arrow, DIM))
    iw = files["wx/i_cloud"].w
    h1 = wsize
    h2 = hsize
    wgap = 0.5 * cq
    wblock = h1 + wgap + h2
    wtop = W / 2 - 38.5 * cq - wblock / 2
    nominal_t = 2 * wcell + math.ceil(FONT.glyph("°")["adv"] * wk)
    line1_w = iw + round(0.8 * cq) + nominal_t
    l1x = W / 2 - line1_w / 2
    tbase = wtop + 0.79 * wsize
    line2_top = wtop + h1 + wgap
    hbase = line2_top + 0.79 * hsize
    ar = files["wx/up"].w
    ig = round(0.4 * cq)
    group_w = ar + ig + 2 * hcell
    pair_gap = round(0.8 * cq)
    l2x = W / 2 - (2 * group_w + pair_gap) / 2
    lay["wx"] = {
        "ix": round(l1x), "iy": round(wtop + h1 / 2 - files["wx/i_cloud"].h / 2),
        "tx": round(l1x + iw + 0.8 * cq), "ty": round(tbase - wref.baseline), "tw": 5 * wcell, "th": wref.h,
        "uix": round(l2x), "uiy": round(line2_top + h2 / 2 - ar / 2),
        "ux": round(l2x + ar + ig), "uy": round(hbase - href.baseline), "uw": 3 * hcell, "uh": href.h,
        "dix": round(l2x + group_w + pair_gap), "diy": round(line2_top + h2 / 2 - ar / 2),
        "dx": round(l2x + group_w + pair_gap + ar + ig), "dy": round(hbase - href.baseline),
        "dw": 3 * hcell, "dh": href.h,
    }
    wx_top, wx_bot = wtop, wtop + wblock

    # ── date (bottom) ──
    dsize = 6.6 * cq
    dk = dsize / FONT.upm
    dtrack = 0.04 * dsize
    dchars = digits + "".join(WEEKDAYS) + "".join(MONTHS) + " "
    gap_d = round(FONT.glyph(" ")["adv"] * dk + dtrack)
    dcell = math.ceil(FONT.glyph("0")["adv"] * dk + dtrack)

    def word_w(word):
        return sum(FONT.glyph(c)["adv"] * dk + dtrack for c in word)

    wk_cell = math.ceil(max(word_w(w_) for w_ in WEEKDAYS)) + gap_d
    mo_cell = math.ceil(max(word_w(m_) for m_ in MONTHS))
    day_cell = 2 * dcell
    for tag, color in (("", FG), ("a", AOD_FG)):
        for i, wname in enumerate(WEEKDAYS):
            put("date/%swk%d" % (tag, i), text_sprite(wname, dsize, color, dchars, tracking=dtrack,
                                                    cell_w=wk_cell, align="left"))
        for i, mname in enumerate(MONTHS):
            put("date/%smo%d" % (tag, i), text_sprite(mname, dsize, color, dchars, tracking=dtrack,
                                                    cell_w=mo_cell, align="left"))
        for n in range(1, 32):
            put("date/%sday%d" % (tag, n), text_sprite(str(n), dsize, color, dchars, tracking=dtrack,
                                                      cell_w=day_cell, align="center"))
    dref = files["date/wk0"]
    d_top = W / 2 + 40 * cq - 0.6 * dsize
    d_base = d_top + 0.89 * dsize
    d_total = wk_cell + day_cell + gap_d + mo_cell
    dx0 = W / 2 - d_total / 2
    dy = round(d_base - dref.baseline)
    lay["date"] = {"wx": round(dx0), "dx": round(dx0 + wk_cell), "mx": round(dx0 + wk_cell + day_cell + gap_d),
                   "y": dy, "h": dref.h, "w": d_total}

    # ── masks for Do Not Disturb / sleep ──
    # (group boxes double as mask regions)
    def box(cx, cy, w, h):
        return {"x": round(cx - w / 2), "y": round(cy - h / 2), "w": round(w), "h": round(h)}

    time_h = (time_box_bot - time_box_top) + 16 * s
    groups = {
        "time": box(W / 2, (time_box_top + time_box_bot) / 2, 2 * cell, time_h),
        "wx": box(W / 2, (wx_top + wx_bot) / 2, 34 * cq, 14 * cq),
        "date": box(W / 2, W / 2 + 40 * cq, 44 * cq, 9.5 * cq),
        "cal": box(corners["cal"]["cx"] + 0.5 * cq, W / 2 - 16 * cq, 20 * cq, 20 * cq),
        "bat": box(corners["bat"]["cx"] - 0.5 * cq, W / 2 - 16 * cq, 20 * cq, 20 * cq),
        "hr": box(corners["hr"]["cx"] + 0.5 * cq, W / 2 + 16 * cq, 20 * cq, 20 * cq),
        "steps": box(corners["steps"]["cx"] - 0.5 * cq, W / 2 + 16 * cq, 20 * cq, 20 * cq),
    }
    tip_w, tip_h = round(124 * s), round(32 * s)
    for i, (name, g) in enumerate(groups.items()):
        g["id"] = 101 + i
        above = g["y"] > W * 0.55
        g["tx"] = round((g["w"] - tip_w) / 2)
        g["ty"] = -tip_h - 6 if above else g["h"] + 6
        g["name"] = name
    lay["groups"] = groups
    lay["tipW"] = tip_w
    lay["ampmMask"] = {"x": ax, "y": ay, "w": am.w, "h": am.h}

    for name, g in groups.items():
        alpha = 178 if name == "time" else 255
        put("mask/%s" % name, solid_sprite(g["w"], g["h"], (0, 0, 0, alpha)))
    put("mask/ampm", solid_sprite(am.w, am.h, (0, 0, 0, 178)))

    # ── edit mode assets ──
    for name, g in groups.items():
        r = 12 * s
        put("edit/sel_%s" % name, rounded_rect_sprite(g["w"], g["h"], r, stroke=FG, sw=max(2, round(2 * s))))
        put("edit/un_%s" % name, rounded_rect_sprite(g["w"], g["h"], r, stroke=TRACK, sw=max(2, round(2 * s))))
    put("edit/tips", rounded_rect_sprite(tip_w, tip_h, tip_h / 2, fill=TRACK))
    for nm, alpha in (("mask100", 1.0), ("mask70", 0.7)):
        mask = Image.new("RGBA", (W, W), (0, 0, 0, round(255 * alpha)))
        yy, xx = np.ogrid[:W, :W]
        inside = (xx + 0.5 - W / 2) ** 2 + (yy + 0.5 - W / 2) ** 2 <= (W / 2) ** 2
        arr = np.array(mask)
        arr[~inside] = (0, 0, 0, 0)
        put("edit/%s" % nm, Sprite(Image.fromarray(arr), 0))

    # ── weather condition level array is built in JS from names; export the mapping ──
    lay["weatherIcons"] = [WEATHER_MAP[i] for i in range(29)]
    lay["stepBarLevels"] = STEP_BAR_LEVELS
    lay["batteryIcons"] = [battery_name(i * 100 / BATTERY_LEVELS) for i in range(BATTERY_LEVELS)]
    lay["batteryIconsAod"] = [battery_name(i * 100 / BATTERY_LEVELS, True) for i in range(BATTERY_LEVELS)]

    # ── scene simulator (preview + edit previews) ──
    def scene(mode="active", style="solid", wx="full", date=True, corners_on=("cal", "bat", "hr", "steps"),
              hour24=False, steps=None):
        steps = SAMPLE["steps"] if steps is None else steps
        canvas = Image.new("RGBA", (W, W), (0, 0, 0, 255))

        def paste(name, x, y):
            im = files[name].img
            canvas.alpha_composite(im, (int(x), int(y)))

        def text_img(chars_names, x, y, w, align="center"):
            total = sum(files[n].w for n in chars_names)
            sx = x + (w - total) / 2 if align == "center" else x
            for n in chars_names:
                paste(n, sx, y)
                sx += files[n].w

        aod = mode == "aod"
        t = lay["time"]
        pre = "a" if aod else ("o" if style == "outline" else "s")
        hh = SAMPLE["hour"] if hour24 else (SAMPLE["hour"] % 12 or 12)
        hs = "%02d" % hh
        paste("time/%s%s" % (pre, hs[0]), t["hx"], t["hy"])
        paste("time/%s%s" % (pre, hs[1]), t["hx"] + cell, t["hy"])
        ms = "%02d" % SAMPLE["minute"]
        paste("time/%s%s" % (pre, ms[0]), t["mx"], t["my"])
        paste("time/%s%s" % (pre, ms[1]), t["mx"] + cell, t["my"])
        if not hour24:
            paste("time/am" if SAMPLE["hour"] < 12 else "time/pm", t["ax"], t["ay"])
        if date:
            d = lay["date"]
            p = "a" if aod else ""
            paste("date/%swk%d" % (p, SAMPLE["weekday"]), d["wx"], d["y"])
            paste("date/%sday%d" % (p, SAMPLE["day"]), d["dx"], d["y"])
            paste("date/%smo%d" % (p, SAMPLE["month"]), d["mx"], d["y"])
        if "bat" in corners_on:
            c = corners["bat"]
            paste(battery_name(SAMPLE["battery"], aod), c["ix"], c["iy"])
            pr = "a" if aod else ""
            text_img(["val/%s%s" % (pr, ch) for ch in str(SAMPLE["battery"])] + ["val/%spct" % pr],
                     c["vx"], c["vy"], c["vw"])
        if aod:
            return canvas
        if wx != "off":
            w_ = lay["wx"]
            paste("wx/i_%s" % SAMPLE["wx"], w_["ix"], w_["iy"])
            text_img(["wx/t%s" % ch for ch in str(SAMPLE["temp"])] + ["wx/deg"], w_["tx"], w_["ty"], 0, "left")
            if wx == "full":
                paste("wx/up", w_["uix"], w_["uiy"])
                text_img(["wx/h%s" % ch for ch in str(SAMPLE["high"])], w_["ux"], w_["uy"], 0, "left")
                paste("wx/down", w_["dix"], w_["diy"])
                text_img(["wx/h%s" % ch for ch in str(SAMPLE["low"])], w_["dx"], w_["dy"], 0, "left")
        for key, icon, val in (("cal", "flame", SAMPLE["kcal"]), ("hr", "heart", SAMPLE["hr"]),
                               ("steps", "steps", steps)):
            if key not in corners_on:
                continue
            c = corners[key]
            paste("icon/%s" % icon, c["ix"], c["iy"])
            glyph = {".": "dot", "K": "k"}
            text_img(["val/%s" % glyph.get(ch, ch) for ch in (steps_text(val) if key == "steps" else str(val))],
                     c["vx"], c["vy"], c["vw"])
            if key == "steps":
                lvl = round(min(1, steps / SAMPLE["goal"]) * (STEP_BAR_LEVELS - 1))
                paste("bar/%d" % lvl, c["bx"], c["by"])
        if "bat" in corners_on:
            pass
        if mode == "dnd":
            for name, g in groups.items():
                paste("mask/%s" % name, g["x"], g["y"])
            paste("mask/ampm", t["ax"], t["ay"])
        return canvas

    def circular(im):
        arr = np.array(im.convert("RGBA"))
        yy, xx = np.ogrid[:W, :W]
        inside = (xx + 0.5 - W / 2) ** 2 + (yy + 0.5 - W / 2) ** 2 <= (W / 2) ** 2
        arr[~inside] = (0, 0, 0, 255)
        return Image.fromarray(arr)

    # option previews: crop the group box from a scene showing only that option
    def crop(im, g):
        return im.crop((g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"]))

    def off_preview(g):
        lbl = text_sprite("OFF", 6.6 * cq, DIM, "OFF", tracking=0.08 * 6.6 * cq)
        base = Image.new("RGBA", (g["w"], g["h"]), (0, 0, 0, 255))
        base.alpha_composite(lbl.img, ((g["w"] - lbl.w) // 2, (g["h"] - lbl.h) // 2))
        return Sprite(base, 0)

    def show_only(**kw):
        return scene(**kw)

    for style in ("solid", "outline"):
        put("edit/pv_time_%s" % style, Sprite(crop(scene(style=style, wx="off", date=False, corners_on=()), groups["time"]), 0))
    put("edit/pv_wx_full", Sprite(crop(scene(wx="full", date=False, corners_on=()), groups["wx"]), 0))
    put("edit/pv_wx_temp", Sprite(crop(scene(wx="temp", date=False, corners_on=()), groups["wx"]), 0))
    put("edit/pv_date_on", Sprite(crop(scene(wx="off", date=True, corners_on=()), groups["date"]), 0))
    for key in ("cal", "bat", "hr", "steps"):
        put("edit/pv_%s_on" % key, Sprite(crop(scene(wx="off", date=False, corners_on=(key,)), groups[key]), 0))
    for name in ("wx", "date", "cal", "bat", "hr", "steps"):
        put("edit/pv_%s_off" % name, off_preview(groups[name]))

    # store preview + app icon
    put_prev = circular(scene(mode="active"))
    put_prev.save(out / "preview.png")
    Image.open(out / "preview.png")
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    put_prev.save(docs / ("preview-active-%d.png" % W))
    circular(scene(mode="aod", style="outline")).save(docs / ("preview-aod-%d.png" % W))
    circular(scene(mode="dnd")).save(docs / ("preview-sleep-%d.png" % W))
    circular(scene(mode="active", style="outline", hour24=True)).save(docs / ("preview-outline-24h-%d.png" % W))
    circular(scene(mode="active", steps=10473)).save(docs / ("preview-steps-10k-%d.png" % W))

    # layout module consumed by watchface/index.js via zosLoader
    lay_path = ROOT / "watchface" / ("index.%s.layout.js" % qualifier)
    lay_path.parent.mkdir(exist_ok=True)
    lay_path.write_text("// Generated by tools/gen_assets.py. Do not edit.\nexport const layout = %s\n"
                        % json.dumps(lay, indent=1))
    n_files = len(files)
    print("%s %dpx: %d sprites, time cell %d, date %dpx wide" % (target, W, n_files, cell, d_total))


if __name__ == "__main__":
    for tgt, (w_, q_) in TARGETS.items():
        build(tgt, w_, q_)
