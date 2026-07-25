"""식생 판정과 임팩트 추정.

원칙은 하나다. **추정치는 반드시 범위로 낸다.**
단일 숫자는 정확해 보이지만 검증받을 수 없다.
"""
from __future__ import annotations

import math

import numpy as np

# 맹그로브 임관 판정 임계값. 갯벌·수면과 갈라지는 지점이다.
NDVI_CANOPY = 0.30
# 임계값 자체의 불확실성. 판정을 0.25~0.35 로 흔들어 면적의 폭을 만든다.
NDVI_CANOPY_LOW = 0.25
NDVI_CANOPY_HIGH = 0.35


def aoi_area_ha(bbox) -> float:
    """경위도 사각형의 실제 면적(ha). 위도 보정을 넣는다."""
    lon1, lat1, lon2, lat2 = bbox
    lat_m = (lat1 + lat2) / 2
    dx = abs(lon2 - lon1) * 111_320 * math.cos(math.radians(lat_m))
    dy = abs(lat2 - lat1) * 110_540
    return dx * dy / 10_000


def canopy_stats(ndvi: np.ndarray, area_ha: float) -> dict:
    """한 시점의 임관 피복 통계."""
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
    """정착 추정률.

    조성 전 대비 늘어난 임관 면적을 식재 면적으로 나눈다.
    어린 묘목은 10m 격자에서 잡히지 않으므로 이 값은 **하한**으로 읽어야 한다.
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
    """흡수 탄소 추정(tCO2).

    계수는 config 에서 온다. 재단 검증위원회가 확정하기 전까지는 잠정값이며,
    산출 결과에는 계수의 출처와 범위를 항상 함께 싣는다.
    """
    if gain_ha <= 0 or years <= 0:
        return {"tco2": 0.0, "tco2_lo": 0.0, "tco2_hi": 0.0}
    # 임관은 선형으로 자라지 않는다. 평균 유효 기간을 절반으로 잡아 보수적으로 센다.
    eff_years = years / 2
    return {
        "tco2": gain_ha * coef["mid"] * eff_years,
        "tco2_lo": gain_ha * coef["low"] * eff_years,
        "tco2_hi": gain_ha * coef["high"] * eff_years,
        "eff_years": eff_years,
    }


def trend(series: list[dict]) -> dict:
    """임관 피복률의 연간 추세(선형 회귀 기울기, %P/년)."""
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


def evergreen_test(dry_frac: float, wet_frac: float) -> dict:
    """상록성 검사. 맹그로브인지, 계절 작물인지 가른다.

    맹그로브는 상록수라 건기와 우기 모두 임관을 유지한다.
    벼는 한쪽 계절에만 푸르고 다른 계절엔 물에 잠기거나 맨땅이 된다.
    위성 지수만으로는 초록이 다 같은 초록이므로, 이 검사가 없으면
    논을 맹그로브로 세는 사고가 난다.
    """
    if dry_frac <= 0.05:
        return {"ratio": None, "flag": "판정 불가", "note": "임관이 너무 작아 계절 비교가 무의미하다."}
    ratio = wet_frac / dry_frac
    if ratio >= 0.75:
        return {"ratio": ratio, "flag": "상록 정합",
                "note": "건기와 우기 모두 임관을 유지한다. 맹그로브를 포함한 상록 식생과 정합한다."}
    if ratio >= 0.45:
        return {"ratio": ratio, "flag": "부분 낙엽",
                "note": "계절 변동이 있다. 혼재 식생이거나 조위 영향일 수 있어 현장 확인이 필요하다."}
    return {"ratio": ratio, "flag": "계절 작물 의심",
            "note": "한 계절에만 푸르다. 조림이 아니라 경작지일 가능성을 배제할 수 없다."}


def verdict(est: dict, tr: dict, last: dict | None = None, role: str = "subject") -> tuple[str, str]:
    """판정 문구. 단정하되 근거 없는 단정은 하지 않는다."""
    rate = est.get("rate", 0)
    slope = tr.get("slope_pp_per_year", 0)

    if role == "control":
        # 대조군은 변하지 않는 것이 정답이다. 여기서 이상값이 나오면 규칙을 의심한다.
        cover = (last or {}).get("canopy_frac", 0)
        if cover >= 0.90 and abs(slope) < 2.0:
            return "대조 정상", "성숙림이 예상대로 높고 평탄하게 읽혔다. 판독 규칙이 정상 작동한다."
        return "대조 이상", "성숙림에서 예상 밖의 값이 나왔다. 판독 규칙을 먼저 점검할 것."

    if rate >= 0.7 and slope > 0:
        return "정착", "식재 구획의 임관이 안정적으로 확대되고 있다."
    if rate >= 0.35 and slope > 0:
        return "성장", "임관이 확대 중이나 아직 완전 피복에 이르지 않았다."
    if slope > 0.5:
        return "초기", "증가 추세는 뚜렷하나 위성 격자에 잡히는 임관은 아직 작다."
    if slope < -0.5:
        return "감소", "임관이 줄고 있다. 현장 확인이 필요하다."
    return "관찰 필요", "유의한 변화를 확정하기 어렵다. 관측 기간을 늘려야 한다."
