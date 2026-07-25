"""Canopy classification and impact estimation.

One rule governs this module: **every estimate ships as a range.**
A single number looks precise and cannot be audited.
"""
from __future__ import annotations

import math

import numpy as np

# Canopy threshold. This is where mangrove separates from mudflat and water.
NDVI_CANOPY = 0.30
# Uncertainty of the threshold itself. Sweeping it between these bounds
# produces the upper and lower area estimates.
NDVI_CANOPY_LOW = 0.25
NDVI_CANOPY_HIGH = 0.35


def aoi_area_ha(bbox) -> float:
    """Real-world area of a lon/lat box, in hectares, corrected for latitude."""
    lon1, lat1, lon2, lat2 = bbox
    lat_m = (lat1 + lat2) / 2
    dx = abs(lon2 - lon1) * 111_320 * math.cos(math.radians(lat_m))
    dy = abs(lat2 - lat1) * 110_540
    return dx * dy / 10_000


def canopy_stats(ndvi: np.ndarray, area_ha: float) -> dict:
    """Canopy cover statistics for a single observation date."""
    valid = np.isfinite(ndvi)
    n = int(valid.sum())
    if n == 0:
        return {"valid_frac": 0.0}

    v = ndvi[valid]
    frac = float((v >= NDVI_CANOPY).mean())
    frac_lo = float((v >= NDVI_CANOPY_HIGH).mean())
    frac_hi = float((v >= NDVI_CANOPY_LOW).mean())

    return {
        "valid_frac": n / ndvi.size,
        "ndvi_mean": float(np.nanmean(v)),
        "ndvi_p90": float(np.nanpercentile(v, 90)),
        "canopy_frac": frac,
        "canopy_frac_lo": frac_lo,
        "canopy_frac_hi": frac_hi,
        "canopy_ha": frac * area_ha,
        "canopy_ha_lo": frac_lo * area_ha,
        "canopy_ha_hi": frac_hi * area_ha,
    }


def establishment(first: dict, last: dict, planted_ha: float) -> dict:
    """Estimated establishment rate.

    Canopy gained since the baseline, divided by the planted area.
    Young seedlings do not register on a 10 m grid, so this figure is a
    **lower bound**, never an upper one.
    """
    if not planted_ha:
        return {}
    gain = last["canopy_ha"] - first["canopy_ha"]
    gain_lo = last["canopy_ha_lo"] - first["canopy_ha_hi"]
    gain_hi = last["canopy_ha_hi"] - first["canopy_ha_lo"]
    return {
        "gain_ha": gain,
        "gain_ha_lo": gain_lo,
        "gain_ha_hi": gain_hi,
        "rate": max(0.0, gain / planted_ha),
        "rate_lo": max(0.0, gain_lo / planted_ha),
        "rate_hi": max(0.0, gain_hi / planted_ha),
    }


def carbon(gain_ha: float, years: float, coef: dict) -> dict:
    """Estimated sequestered carbon, in tonnes of CO2.

    The coefficient comes from config. Until the foundation's review panel
    fixes it, the output always travels with its source and its range.
    """
    if gain_ha <= 0 or years <= 0:
        return {"tco2": 0.0, "tco2_lo": 0.0, "tco2_hi": 0.0}
    # Canopy does not grow linearly. Halving the effective years keeps the
    # estimate conservative rather than flattering.
    eff_years = years / 2
    return {
        "tco2": gain_ha * coef["mid"] * eff_years,
        "tco2_lo": gain_ha * coef["low"] * eff_years,
        "tco2_hi": gain_ha * coef["high"] * eff_years,
        "eff_years": eff_years,
    }


def trend(series: list[dict]) -> dict:
    """Annual trend in canopy cover: linear slope in percentage points per year."""
    pts = [(s["t_years"], s["canopy_frac"]) for s in series if s.get("canopy_frac") is not None]
    if len(pts) < 3:
        return {}
    x = np.array([p[0] for p in pts])
    y = np.array([p[1] for p in pts]) * 100
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {
        "slope_pp_per_year": float(slope),
        "r2": 1 - ss_res / ss_tot if ss_tot > 0 else 0.0,
        "n": len(pts),
    }


def evergreen_code(dry_frac: float, wet_frac: float) -> tuple[str, float | None]:
    """Evergreen test. Separates mangrove from a seasonal crop.

    Mangrove is evergreen: it holds canopy in the dry season and the wet one.
    Rice is green in one season and flooded or bare in the other. Vegetation
    indices cannot tell one green from another, so without this test a
    greening paddy would be counted as a planted forest.
    """
    if dry_frac <= 0.05:
        return "undetermined", None
    ratio = wet_frac / dry_frac
    if ratio >= 0.75:
        return "evergreen", ratio
    if ratio >= 0.45:
        return "partial", ratio
    return "seasonal_crop", ratio


def verdict_code(est: dict, tr: dict, last: dict | None = None, role: str = "subject") -> str:
    """Overall verdict. Decisive where the evidence allows, silent where it does not."""
    rate = est.get("rate", 0)
    slope = tr.get("slope_pp_per_year", 0)

    if role == "control":
        # A control plot is supposed to stay put. An odd reading here means
        # the rules are wrong, not that the forest changed.
        cover = (last or {}).get("canopy_frac", 0)
        return "control_ok" if cover >= 0.90 and abs(slope) < 2.0 else "control_anomaly"

    if rate >= 0.7 and slope > 0:
        return "established"
    if rate >= 0.35 and slope > 0:
        return "growing"
    if slope > 0.5:
        return "early"
    if slope < -0.5:
        return "declining"
    return "inconclusive"
