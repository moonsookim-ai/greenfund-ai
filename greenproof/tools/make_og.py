"""공유 카드(og.png) 생성.

합성 그래픽을 쓰지 않는다. 실제 판독에 쓰인 위성 프레임을 그대로 좌우로 놓는다.
이 사업의 주장이 "우리가 본 것을 그대로 보여준다"이므로, 공유 카드부터 그래야 한다.

    python tools/make_og.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SITE = "dakope-demo"
W, H = 1200, 630

GOLD = (233, 179, 65)
GREEN = (61, 220, 132)
INK = (255, 255, 255)
MUTED = (185, 205, 193)


def font(size: int, bold=False):
    for name in (("malgunbd.ttf", "malgun.ttf") if bold else ("malgun.ttf",)):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def panel(path: Path, box_w: int, box_h: int) -> Image.Image:
    """프레임에서 하단 자막 띠를 떼고 구획 세로 전체가 들어오도록 담는다.

    10m 격자라 원본 화소 수가 적다. 확대하면 뭉개지므로 축소 방향으로만 맞춘다.
    """
    im = Image.open(path).convert("RGB")
    im = im.crop((0, 0, im.width, im.height - 62))
    scale = max(box_w / im.width, box_h / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    x = (im.width - box_w) // 2
    y = (im.height - box_h) // 2
    return im.crop((x, y, x + box_w, y + box_h))


def main():
    data = json.loads((ROOT / "web" / "data" / SITE / "report.json").read_text(encoding="utf-8"))
    raws = data["frames_raw"]
    d0, d1 = data["series"][0], data["series"][-1]

    img = Image.new("RGB", (W, H), (10, 16, 13))
    pw = 296          # 세로 패널 한 장의 폭
    for i, (name, s) in enumerate(((raws[0], d0), (raws[-1], d1))):
        img.paste(panel(ROOT / "web" / "data" / SITE / name, pw, H), (i * pw, 0))

    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([pw - 2, 0, pw + 2, H], fill=(255, 255, 255))

    # 각 패널 하단에 연도와 임관 피복
    for i, s in enumerate((d0, d1)):
        x0 = i * pw
        d.rectangle([x0, H - 74, x0 + pw, H], fill=(0, 0, 0, 170))
        d.text((x0 + 18, H - 64), str(s["year"]), font=font(28, True), fill=INK)
        d.text((x0 + 18, H - 30), f"임관 피복 {s['canopy_frac']*100:.0f}%",
               font=font(17), fill=GREEN if i else MUTED)

    # 오른쪽 본문
    tx = pw * 2 + 52
    d.text((tx, 92), "GREEN PROOF", font=font(21, True), fill=GREEN)
    d.text((tx + 162, 94), "환경재단 위성 검증소", font=font(17), fill=MUTED)
    d.text((tx, 152), "3년 전 심은 나무,", font=font(41, True), fill=INK)
    d.text((tx, 208), "지금 위성에서", font=font(41, True), fill=GOLD)
    d.text((tx, 262), "이렇게 보입니다", font=font(41, True), fill=GOLD)

    d.line([tx, 348, tx + 90, 348], fill=GREEN, width=3)
    for j, line in enumerate([
        "유럽 코페르니쿠스 Sentinel-2 위성이",
        f"{d0['date']} 부터 {d1['date']} 까지",
        "찍어 둔 것을 읽었습니다.",
    ]):
        d.text((tx, 374 + j * 30), line, font=font(19), fill=MUTED)

    d.text((tx, H - 62), "greenfund.ai.kr", font=font(19, True), fill=INK)
    d.text((tx, H - 34), "관측에 쓴 위성 장면을 전부 공개합니다", font=font(16), fill=MUTED)

    out = ROOT / "web" / "og.png"
    img.save(out, optimize=True)
    print(f"{out.relative_to(ROOT)}  {out.stat().st_size/1024:.0f} KB  {W}x{H}")


if __name__ == "__main__":
    main()
