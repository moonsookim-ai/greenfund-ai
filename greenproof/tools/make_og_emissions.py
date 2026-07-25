"""Social card for the emissions map (web/emissions/og.png).

Same rule as the main card: no synthetic artwork. The left panel is the real
dataset — every one of the 1,200+ facilities plotted at its true coordinates,
sized by emissions — which draws an unmistakable outline of Korea. The right
panel is the national top-5, from the same file the page ships.

    python tools/make_og_emissions.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "web" / "emissions" / "data" / "emissions_kr.json"
OUT = ROOT / "web" / "emissions" / "og.png"
W, H = 1200, 630

INK = (255, 255, 255)
MUTED = (185, 205, 193)
GREEN = (61, 220, 132)
GOLD = (233, 179, 65)
BG = (10, 16, 13)
COL = {"power": (227, 103, 90), "mfg": (217, 139, 58), "fossil": (138, 110, 240),
       "waste": (58, 157, 217), "transp": (224, 177, 58), "bldg": (90, 176, 106)}


def font(size: int, bold=False):
    for name in (("malgunbd.ttf", "malgun.ttf") if bold else ("malgun.ttf",)):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    fac = d["facilities"]

    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img, "RGBA")

    # ---- left: the country, drawn by its emitters -----------------------
    # Korea mainland bbox; the panel is tall, which suits the peninsula.
    lon1, lon2 = 125.8, 129.8
    lat1, lat2 = 33.9, 38.4
    px_area = (40, 30, 560, H - 55)
    ax0, ay0, ax1, ay1 = px_area
    kx = (ax1 - ax0) / (lon2 - lon1)
    ky = (ay1 - ay0) / (lat2 - lat1)
    k = min(kx, ky)  # uniform scale, no squash

    maxe = fac[0]["e"]
    for f in sorted(fac, key=lambda x: x["e"]):          # big ones drawn last
        if not (lon1 <= f["lon"] <= lon2 and lat1 <= f["lat"] <= lat2):
            continue
        x = ax0 + (f["lon"] - lon1) * k
        y = ay1 - (f["lat"] - lat1) * k
        r = 1.5 + 13 * math.sqrt(f["e"] / maxe)
        c = COL.get(f["s"], GREEN)
        a = 150 if f["e"] < maxe * 0.05 else 220
        dr.ellipse([x - r, y - r, x + r, y + r], fill=(*c, a))

    dr.text((40, H - 42), "1,204 facilities · every dot is real, at its true location",
            font=font(15), fill=MUTED)

    # ---- right: headline + national top 5 -------------------------------
    tx = 620
    dr.text((tx, 56), "GREEN PROOF", font=font(21, True), fill=GREEN)
    dr.text((tx + 162, 58), "Environmental Foundation", font=font(16), fill=MUTED)
    dr.text((tx, 108), "What emits the most", font=font(38, True), fill=INK)
    dr.text((tx, 156), "around you?", font=font(38, True), fill=GOLD)
    dr.text((tx, 216), "Type your district. See the biggest emitters", font=font(18), fill=MUTED)
    dr.text((tx, 244), "near you, ranked - from open Climate TRACE data.", font=font(18), fill=MUTED)

    dr.line([tx, 292, tx + 90, 292], fill=GREEN, width=3)
    dr.text((tx, 306), "Korea's five largest single emitters", font=font(15, True), fill=MUTED)

    y = 340
    for i, f in enumerate(fac[:5], 1):
        mt = f["e"] / 1e6
        c = COL.get(f["s"], GREEN)
        dr.ellipse([tx, y + 6, tx + 12, y + 18], fill=c)
        name = f["n"] if len(f["n"]) <= 34 else f["n"][:33] + "…"
        dr.text((tx + 24, y), f"{i}. {name}", font=font(18), fill=INK)
        wtxt = f"{mt:.1f} Mt"
        dr.text((W - 46 - dr.textlength(wtxt, font=font(18, True)), y), wtxt,
                font=font(18, True), fill=GOLD)
        y += 38

    dr.text((tx, H - 62), "greenfund.ai.kr/emissions", font=font(19, True), fill=INK)
    dr.text((tx, H - 34), "Climate change has an address", font=font(16), fill=MUTED)

    img.save(OUT, optimize=True)
    print(f"{OUT.relative_to(ROOT)}  {OUT.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
