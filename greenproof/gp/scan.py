"""녹화 신호 탐색.

재단은 지금 구획 좌표를 가지고 있지 않다. 그래도 시작할 수 있다.
대상 지역 전체를 훑어 **비식생이었다가 식생이 된 곳**을 찾으면
조림이 실제로 일어난 자리가 후보로 떠오른다.

좌표가 도착하면 이 도구는 검증 도구로 바뀐다.
재단이 받은 좌표와 위성이 본 녹화 지점이 겹치는지 대조하는 데 쓴다.
"""
from __future__ import annotations

import numpy as np

from . import stac


def _blocks(arr: np.ndarray, k: int) -> np.ndarray:
    """k×k 블록 평균. 격자 잡음을 눌러 실제 덩어리만 남긴다."""
    h, w = arr.shape
    h2, w2 = h // k * k, w // k * k
    a = arr[:h2, :w2].reshape(h2 // k, k, w2 // k, k)
    return np.nanmean(a, axis=(1, 3))


def scan_region(bbox, baseline: tuple[str, str], recent: tuple[str, str],
                px_m: int = 20, block_m: int = 500, top: int = 12, log=print) -> dict:
    lon1, lat1, lon2, lat2 = bbox
    # 경위도 폭을 대략 미터로 환산해 읽을 크기를 정한다.
    span_x = abs(lon2 - lon1) * 111_320 * np.cos(np.radians((lat1 + lat2) / 2))
    span_y = abs(lat2 - lat1) * 110_540
    shape = (max(64, int(span_y / px_m)), max(64, int(span_x / px_m)))
    log(f"  판독 격자 {shape[1]}x{shape[0]} (약 {px_m}m/px)")

    log("  기준 시점 장면 탐색")
    s0, d0 = stac.best_scene(bbox, *baseline, out_shape=shape, log=log)
    log("  현재 시점 장면 탐색")
    s1, d1 = stac.best_scene(bbox, *recent, out_shape=shape, log=log)
    if d0 is None or d1 is None:
        return {"error": "기준 또는 현재 시점에서 판독 가능한 장면을 찾지 못했다."}

    a0, a1 = d0["ndvi"], d1["ndvi"]
    n = min(a0.shape[0], a1.shape[0]), min(a0.shape[1], a1.shape[1])
    a0, a1 = a0[: n[0], : n[1]], a1[: n[0], : n[1]]

    # 조림 신호: 예전엔 식생이 아니었고(<0.20) 지금은 임관이다(>=0.35).
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
