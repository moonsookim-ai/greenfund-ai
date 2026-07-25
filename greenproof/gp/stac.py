"""Scene discovery and windowed reads of Sentinel-2 imagery.

The source is the Sentinel-2 L2A cloud-optimised GeoTIFF mirror on AWS Open
Data. No API key, and no whole-file downloads: an HTTP range request pulls
only the rectangle covering the area of interest. For a 60 ha plot that is a
few hundred kilobytes per band.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import date

# Stop GDAL from listing the remote directory. Leaving this on makes every
# remote read several times slower.
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

# Usable values of the SCL scene-classification band:
# 4 vegetation, 5 bare soil, 6 water, 7 unclassified.
# Everything else is cloud, shadow or no data.
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
    """Scenes covering the AOI, ordered by scene-level cloud cover."""
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
    """Read only the AOI rectangle from a COG. out_shape reads a decimated overview."""
    with rasterio.open("/vsicurl/" + href) as src:
        b = transform_bounds("EPSG:4326", src.crs, *bbox)
        win = from_bounds(*b, transform=src.transform)
        kw = {"window": win, "boundless": True, "fill_value": 0}
        if out_shape:
            kw["out_shape"] = out_shape
        arr = src.read(1, **kw)
        return arr, src.crs


def _mosaic(scenes: list[Scene], key: str, bbox, out_shape):
    """Mosaic neighbouring tiles from the same day.

    When an AOI straddles a tile boundary, reading one tile returns half a
    frame of no-data. Sentinel-2 captures adjacent tiles in the same orbital
    pass, so stitching them introduces no time mismatch.
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
    """Build NDVI and a validity mask from every scene captured on one date.

    Returns dict(ndvi, valid, scl, nodata_frac, cloud_frac), or None if unreadable.
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
    """One day of observation, possibly spanning several tiles."""
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
    """Pick one observation date inside the window that truly covers the AOI.

    Scene-level cloud cover is only a hint: tile-edge no-data and cloud sitting
    over this particular plot only show up once the rectangle is actually read.
    So candidates are read and tested in order.
    """
    for obs in group_by_day(search(bbox, start, end))[:tries]:
        data = read_day(obs.scenes, bbox, out_shape)
        if data is None:
            continue
        if data["nodata_frac"] > max_nodata or data["cloud_frac"] > max_cloud_aoi:
            log(f"    skip {obs.day} ({len(obs.scenes)} tile) no-data {data['nodata_frac']:.0%} cloud {data['cloud_frac']:.0%}")
            continue
        return obs, data
    return None, None
