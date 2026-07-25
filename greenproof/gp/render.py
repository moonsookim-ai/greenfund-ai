"""Frame rendering: the canopy classification drawn over true-colour imagery.

This does not produce a video. It writes still frames and lets the viewer
stitch them, so a supporter can stop on any single date and look at it.
Evidence you can pause beats evidence that only plays.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from .analysis import NDVI_CANOPY

OUT_W = 720


def read_rgb(scenes, bbox, out_shape=None) -> np.ndarray | None:
    """Read true-colour imagery, mosaicking neighbouring tiles from the same day."""
    out = None
    for sc in scenes:
        href = sc.assets.get("visual", {}).get("href")
        if not href:
            continue
        try:
            with rasterio.open("/vsicurl/" + href) as src:
                b = transform_bounds("EPSG:4326", src.crs, *bbox)
                win = from_bounds(*b, transform=src.transform)
                kw = {"window": win, "boundless": True, "fill_value": 0}
                if out_shape:
                    kw["out_shape"] = (3, *out_shape)
                arr = np.transpose(src.read((1, 2, 3), **kw), (1, 2, 0)).astype("uint8")
        except Exception:
            continue
        if out is None:
            out = arr
        else:
            h, w = min(out.shape[0], arr.shape[0]), min(out.shape[1], arr.shape[1])
            out = out[:h, :w]
            gap = out.sum(axis=2) == 0
            out[gap] = arr[:h, :w][gap]
    return out


def _font(size: int):
    for name in ("malgun.ttf", "malgunbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _stretch(rgb: np.ndarray) -> np.ndarray:
    """Mudflat is dark and water is darker. Without a stretch you see nothing."""
    out = np.zeros_like(rgb, dtype="float32")
    for c in range(3):
        band = rgb[:, :, c].astype("float32")
        lo, hi = np.percentile(band[band > 0], (2, 98)) if (band > 0).any() else (0, 255)
        if hi <= lo:
            hi = lo + 1
        out[:, :, c] = np.clip((band - lo) / (hi - lo), 0, 1) * 255
    return out.astype("uint8")


def make_frame(rgb: np.ndarray, ndvi: np.ndarray, label: str, sub: str,
               overlay: bool = True, scale_m_per_px: float | None = None) -> Image.Image:
    img = Image.fromarray(_stretch(rgb)).convert("RGB")
    scale = OUT_W / img.width
    img = img.resize((OUT_W, max(1, int(img.height * scale))), Image.LANCZOS)

    if overlay and ndvi is not None:
        mask = np.isfinite(ndvi) & (ndvi >= NDVI_CANOPY)
        m = Image.fromarray((mask * 255).astype("uint8")).resize(img.size, Image.NEAREST)
        tint = Image.new("RGB", img.size, (46, 204, 113))
        img = Image.composite(Image.blend(img, tint, 0.35), img, m)

    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, img.height - 62, img.width, img.height], fill=(0, 0, 0, 150))
    d.text((16, img.height - 54), label, font=_font(26), fill=(255, 255, 255))
    d.text((16, img.height - 24), sub, font=_font(15), fill=(200, 220, 210))

    if scale_m_per_px:
        bar_px = int(500 / (scale_m_per_px / scale))
        if 20 < bar_px < img.width // 2:
            x0, y0 = img.width - bar_px - 20, img.height - 76
            d.line([x0, y0, x0 + bar_px, y0], fill=(255, 255, 255), width=3)
            d.text((x0, y0 - 20), "500 m", font=_font(13), fill=(255, 255, 255))
    return img


def write_frames(frames: list[tuple[str, Image.Image]], outdir: Path, prefix: str = "") -> list[str]:
    outdir.mkdir(parents=True, exist_ok=True)
    names = []
    for i, (key, img) in enumerate(frames):
        name = f"{prefix}{i:02d}_{key}.jpg"
        img.save(outdir / name, quality=88, optimize=True)
        names.append(name)
    return names


def make_video(outdir: Path, names: list[str], out: Path, seconds: float = 15.0) -> bool:
    """An mp4 for press use. Optional: the viewer runs on the frames regardless."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        for p in Path.home().glob("AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe"):
            ffmpeg = str(p)
            break
    if not ffmpeg or not names:
        return False
    fps = max(1.0, len(names) / seconds)
    lst = outdir / "_frames.txt"
    lst.write_text("".join(f"file '{n}'\nduration {1/fps:.3f}\n" for n in names) + f"file '{names[-1]}'\n",
                   encoding="utf-8")
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
           "-vf", "scale=720:-2:flags=lanczos,format=yuv420p", "-r", "30", str(out)]
    try:
        subprocess.run(cmd, check=True, cwd=str(outdir), timeout=300)
        return out.exists()
    except Exception:
        return False
