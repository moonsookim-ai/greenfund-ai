"""Greening detection.

The foundation does not yet hold the coordinates of its planting plots. Work
can start anyway. Sweeping the whole target region for ground that **was not
vegetated and now is** surfaces the places where planting actually happened.

Once coordinates arrive, this tool changes role. It stops finding plots and
starts checking them: does the boundary the partner supplied line up with the
greening the satellite saw?
"""
from __future__ import annotations

import numpy as np

from . import stac


def _blocks(arr: np.ndarray, k: int) -> np.ndarray:
    """Mean over k x k blocks. Suppresses per-pixel noise, keeps real patches."""
    h, w = arr.shape
    h2, w2 = h // k * k, w // k * k
    a = arr[:h2, :w2].reshape(h2 // k, k, w2 // k, k)
    return np.nanmean(a, axis=(1, 3))


def scan_region(bbox, baseline: tuple[str, str], recent: tuple[str, str],
                px_m: int = 20, block_m: int = 500, top: int = 12, log=print) -> dict:
    lon1, lat1, lon2, lat2 = bbox
    # Convert the lon/lat span to rough metres to choose a read size.
    span_x = abs(lon2 - lon1) * 111_320 * np.cos(np.radians((lat1 + lat2) / 2))
    span_y = abs(lat2 - lat1) * 110_540
    shape = (max(64, int(span_y / px_m)), max(64, int(span_x / px_m)))
    log(f"  read grid {shape[1]}x{shape[0]} (about {px_m} m/px)")

    log("  searching baseline scene")
    s0, d0 = stac.best_scene(bbox, *baseline, out_shape=shape, log=log)
    log("  searching recent scene")
    s1, d1 = stac.best_scene(bbox, *recent, out_shape=shape, log=log)
    if d0 is None or d1 is None:
        return {"error": "No readable scene found for the baseline or the recent window."}

    a0, a1 = d0["ndvi"], d1["ndvi"]
    n = min(a0.shape[0], a1.shape[0]), min(a0.shape[1], a1.shape[1])
    a0, a1 = a0[: n[0], : n[1]], a1[: n[0], : n[1]]

    # Planting signal: not vegetation before (<0.20), canopy now (>=0.35).
    with np.errstate(invalid="ignore"):
        newly = (a0 < 0.20) & (a1 >= 0.35)
    newly = np.where(np.isfinite(a0) & np.isfinite(a1), newly, np.nan).astype("float32")

    k = max(1, block_m // px_m)
    grid = _blocks(newly, k)
    gh, gw = grid.shape

    cells = []
    for r in range(gh):
        for c in range(gw):
            v = grid[r, c]
            if not np.isfinite(v) or v < 0.25:
                continue
            clon1 = lon1 + (lon2 - lon1) * (c * k) / n[1]
            clon2 = lon1 + (lon2 - lon1) * ((c + 1) * k) / n[1]
            clat2 = lat2 - (lat2 - lat1) * (r * k) / n[0]
            clat1 = lat2 - (lat2 - lat1) * ((r + 1) * k) / n[0]
            cells.append({
                "score": round(float(v), 3),
                "aoi": [round(clon1, 5), round(clat1, 5), round(clon2, 5), round(clat2, 5)],
            })

    cells.sort(key=lambda x: -x["score"])
    return {
        "baseline_scene": s0.item_id, "baseline_date": s0.dt[:10],
        "recent_scene": s1.item_id, "recent_date": s1.dt[:10],
        "newly_vegetated_frac": float(np.nanmean(newly)),
        "candidates": cells[:top],
    }
