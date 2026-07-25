"""Bilingual strings for verdicts, tests and methodology notes.

The pipeline never writes a sentence into the report. It writes a *code*, and
every code carries both an English and a Korean rendering. The viewer picks the
language; the numbers stay identical in both. This keeps the published record
translatable without ever re-running the analysis.
"""
from __future__ import annotations

LANGS = ("en", "ko")


def pack(table: dict, code: str) -> dict:
    """Turn a code into the report payload: the code plus every rendering."""
    entry = table[code]
    return {"code": code, **{lang: entry[lang] for lang in LANGS}}


VERDICT = {
    "established": {
        "en": {"label": "Established",
               "note": "Canopy over the planted area is expanding steadily."},
        "ko": {"label": "정착",
               "note": "식재 구획의 임관이 안정적으로 확대되고 있다."},
    },
    "growing": {
        "en": {"label": "Growing",
               "note": "Canopy is expanding but has not reached full closure."},
        "ko": {"label": "성장",
               "note": "임관이 확대 중이나 아직 완전 피복에 이르지 않았다."},
    },
    "early": {
        "en": {"label": "Early stage",
               "note": "The upward trend is clear, but the canopy visible at 10 m resolution is still small."},
        "ko": {"label": "초기",
               "note": "증가 추세는 뚜렷하나 위성 격자에 잡히는 임관은 아직 작다."},
    },
    "declining": {
        "en": {"label": "Declining",
               "note": "Canopy is shrinking. Field verification is required."},
        "ko": {"label": "감소",
               "note": "임관이 줄고 있다. 현장 확인이 필요하다."},
    },
    "inconclusive": {
        "en": {"label": "Inconclusive",
               "note": "No significant change can be confirmed. The observation window must be extended."},
        "ko": {"label": "관찰 필요",
               "note": "유의한 변화를 확정하기 어렵다. 관측 기간을 늘려야 한다."},
    },
    "control_ok": {
        "en": {"label": "Control nominal",
               "note": "The mature forest reads high and flat, as expected. The classification rules are working."},
        "ko": {"label": "대조 정상",
               "note": "성숙림이 예상대로 높고 평탄하게 읽혔다. 판독 규칙이 정상 작동한다."},
    },
    "control_anomaly": {
        "en": {"label": "Control anomaly",
               "note": "The mature forest returned an unexpected value. Check the classification rules first."},
        "ko": {"label": "대조 이상",
               "note": "성숙림에서 예상 밖의 값이 나왔다. 판독 규칙을 먼저 점검할 것."},
    },
}

EVERGREEN = {
    "evergreen": {
        "en": {"label": "Evergreen consistent",
               "note": "Canopy holds through both the dry and the wet season, consistent with mangrove and other evergreen cover."},
        "ko": {"label": "상록 정합",
               "note": "건기와 우기 모두 임관을 유지한다. 맹그로브를 포함한 상록 식생과 정합한다."},
    },
    "partial": {
        "en": {"label": "Partly deciduous",
               "note": "Seasonal variation is present. This may be mixed vegetation or a tidal effect, and needs field verification."},
        "ko": {"label": "부분 낙엽",
               "note": "계절 변동이 있다. 혼재 식생이거나 조위 영향일 수 있어 현장 확인이 필요하다."},
    },
    "seasonal_crop": {
        "en": {"label": "Possible seasonal crop",
               "note": "Green in one season only. Cropland cannot be ruled out, so this is not counted as afforestation."},
        "ko": {"label": "계절 작물 의심",
               "note": "한 계절에만 푸르다. 조림이 아니라 경작지일 가능성을 배제할 수 없다."},
    },
    "undetermined": {
        "en": {"label": "Not determinable",
               "note": "The canopy is too small for a seasonal comparison to mean anything."},
        "ko": {"label": "판정 불가",
               "note": "임관이 너무 작아 계절 비교가 무의미하다."},
    },
    "not_run": {
        "en": {"label": "Not run",
               "note": "No readable wet-season scene was found."},
        "ko": {"label": "미실시",
               "note": "우기에 판독 가능한 장면을 찾지 못했다."},
    },
}

METHOD = {
    "en": {
        "source": "Copernicus Sentinel-2 L2A, via the AWS Open Data public mirror",
        "index": "NDVI = (B08 - B04) / (B08 + B04)",
        "cloud_mask": "Cloud, shadow and no-data pixels removed using the SCL scene classification band",
        "season": "Dry season only (December to March). The monsoon brings cloud, and high tides distort readings over tidal flats.",
        "limits": [
            "Seedlings smaller than the 10 m grid are invisible. Early establishment rates must be read as a lower bound.",
            "Tide level changes how much flat is exposed, which moves NDVI. Only same-season scenes are compared.",
            "Sequestered carbon is inferred from canopy area. It does not replace field measurement.",
            "Until coordinates are confirmed, results describe a candidate plot.",
        ],
    },
    "ko": {
        "source": "Copernicus Sentinel-2 L2A (AWS Open Data 공개본)",
        "index": "NDVI = (B08 − B04) / (B08 + B04)",
        "cloud_mask": "SCL 장면분류에서 구름·그림자·결측 화소 제외",
        "season": "건기(12~3월)만 쓴다. 우기는 구름이 덮고 조위가 높아 갯벌 판독이 흔들린다.",
        "limits": [
            "10m 격자보다 작은 어린 묘목은 잡히지 않는다. 초기 정착률은 하한으로 읽어야 한다.",
            "조위에 따라 갯벌 노출 면적이 달라져 NDVI 가 흔들린다. 같은 건기 장면끼리만 비교했다.",
            "흡수 탄소는 임관 면적에서 역산한 추정치다. 현장 실측을 대체하지 않는다.",
            "좌표가 확정되기 전 결과는 후보 구획에 대한 것이다.",
        ],
    },
}
