"""Sentinel-2 장면 검색과 창(window) 단위 판독.

원천은 AWS Open Data 의 Sentinel-2 L2A COG 이다. 인증 키가 필요 없고
파일 전체를 받지 않는다. HTTP 범위 요청으로 관심영역(AOI)에 해당하는
사각형만 잘라 읽는다. 60ha 한 구획이면 한 밴드당 수백 KB 수준이다.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import date

# GDAL 이 디렉터리 목록을 훑지 않도록 막는다. 이걸 켜두면 원격 읽기가 몇 배 느려진다.
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("GDAL_HTTP_MULTIPLEX", "YES")
os.environ.setdefault("VSI_CACHE", "TRUE")
os.environ.setdefault("VSI_CACHE_SIZE", "50000000")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.warp import transform_bounds  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402

STAC_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"

# SCL(장면 분류) 코드 가운데 판독에 쓸 수 있는 값.
# 4 식생, 5 나지, 6 수면, 7 미분류. 나머지는 구름·그림자·결측이다.
SCL_CLEAR = (4, 5, 6, 7)
SCL_NODATA = 0


@dataclass
class Scene:
    item_id: str
    dt: str
    cloud: float
    assets: dict

    @property
    def day(self) -> date:
        return date.fromisoformat(self.dt[:10])


def search(bbox, start: str, end: str, max_cloud: float = 30.0, limit: int = 40) -> list[Scene]:
    """AOI 를 덮는 장면 목록을 구름량 오름차순으로 돌려준다."""
    body = {
        "collections": [COLLECTION],
        "bbox": list(bbox),
        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
        "limit": limit,
    }
    req = urllib.request.Request(
        STAC_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "greenproof/0.1"},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        payload = json.load(resp)

    scenes = [
        Scene(f["id"], f["properties"]["datetime"], float(f["properties"].get("eo:cloud_cover", 100)), f["assets"])
        for f in payload.get("features", [])
    ]
    scenes.sort(key=lambda s: s.cloud)
    return scenes


def _read(href: str, bbox, out_shape=None):
    """COG 에서 AOI 사각형만 잘라 읽는다. out_shape 를 주면 오버뷰로 축소해 읽는다."""
    with rasterio.open("/vsicurl/" + href) as src:
        b = transform_bounds("EPSG:4326", src.crs, *bbox)
        win = from_bounds(*b, transform=src.transform)
        kw = {"window": win, "boundless": True, "fill_value": 0}
        if out_shape:
            kw["out_shape"] = out_shape
        arr = src.read(1, **kw)
        return arr, src.crs


def _mosaic(scenes: list[Scene], key: str, bbox, out_shape):
    """같은 날 인접 타일을 이어 붙인다.

    AOI 가 타일 경계에 걸치면 한 타일만 읽어서는 절반이 결측으로 나온다.
    Sentinel-2 는 같은 궤도 통과에서 인접 타일을 같은 시각에 찍으므로
    이어 붙여도 시점 불일치가 없다.
    """
    out = None
    for sc in scenes:
        href = sc.assets.get(key, {}).get("href")
        if not href:
            continue
        try:
            arr, _ = _read(href, bbox, out_shape)
        except Exception:
            continue
        if out is None:
            out = arr
        else:
            h = min(out.shape[0], arr.shape[0])
            w = min(out.shape[1], arr.shape[1])
            out = out[:h, :w]
            gap = out == 0
            out[gap] = arr[:h, :w][gap]
    return out


def read_day(scenes: list[Scene], bbox, out_shape=None):
    """같은 날짜의 장면들에서 NDVI 와 유효 마스크를 만든다.

    반환: dict(ndvi, valid, scl, nodata_frac, cloud_frac) 또는 None(판독 불가).
    """
    red = _mosaic(scenes, "red", bbox, out_shape)
    nir = _mosaic(scenes, "nir", bbox, out_shape)
    scl = _mosaic(scenes, "scl", bbox, out_shape)
    if red is None or nir is None or scl is None or red.size == 0:
        return None

    h = min(red.shape[0], nir.shape[0], scl.shape[0])
    w = min(red.shape[1], nir.shape[1], scl.shape[1])
    red, nir, scl = red[:h, :w], nir[:h, :w], scl[:h, :w]

    scl = scl.astype("uint8")
    nodata = scl == SCL_NODATA
    clear = np.isin(scl, SCL_CLEAR) & ~nodata

    nodata_frac = float(nodata.mean())
    cloud_frac = float((~clear & ~nodata).mean()) if (~nodata).any() else 1.0

    red = red.astype("float32")
    nir = nir.astype("float32")
    denom = nir + red
    ndvi = np.where(denom > 0, (nir - red) / np.where(denom == 0, 1, denom), np.nan)
    ndvi = np.where(clear, ndvi, np.nan)

    return {
        "ndvi": ndvi.astype("float32"),
        "valid": clear,
        "scl": scl,
        "nodata_frac": nodata_frac,
        "cloud_frac": cloud_frac,
    }


@dataclass
class DayObs:
    """한 날짜의 관측. 타일이 여러 장일 수 있다."""
    day: str
    scenes: list

    @property
    def item_id(self) -> str:
        return " + ".join(s.item_id for s in self.scenes)

    @property
    def cloud(self) -> float:
        return sum(s.cloud for s in self.scenes) / len(self.scenes)

    @property
    def dt(self) -> str:
        return self.scenes[0].dt


def group_by_day(scenes: list[Scene]) -> list[DayObs]:
    days: dict[str, list[Scene]] = {}
    for s in scenes:
        days.setdefault(s.dt[:10], []).append(s)
    obs = [DayObs(d, v) for d, v in days.items()]
    obs.sort(key=lambda o: o.cloud)
    return obs


def best_scene(bbox, start: str, end: str, out_shape=None, max_nodata=0.10, max_cloud_aoi=0.15,
               tries: int = 8, log=print):
    """기간 안에서 AOI 를 실제로 덮고 구름이 적은 관측일 하나를 고른다.

    장면 단위 구름량은 참고값일 뿐이다. 타일 가장자리 결측과 AOI 국지 구름은
    실제로 잘라 읽어 봐야 알 수 있으므로, 후보를 순서대로 검사한다.
    """
    for obs in group_by_day(search(bbox, start, end))[:tries]:
        data = read_day(obs.scenes, bbox, out_shape)
        if data is None:
            continue
        if data["nodata_frac"] > max_nodata or data["cloud_frac"] > max_cloud_aoi:
            log(f"    건너뜀 {obs.day} (타일 {len(obs.scenes)}) 결측 {data['nodata_frac']:.0%} 구름 {data['cloud_frac']:.0%}")
            continue
        return obs, data
    return None, None
