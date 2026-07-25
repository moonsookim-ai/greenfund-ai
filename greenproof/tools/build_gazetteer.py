#!/usr/bin/env python
"""Build the Korean region gazetteer for the emissions map.

Every si/gun/gu in the country, geocoded once at build time through OpenStreetMap
Nominatim (1 req/sec per usage policy, descriptive User-Agent). The output is a
static JSON the page ships with — no runtime geocoding, no API keys, and no
hand-typed coordinates that nobody has verified.

    python tools/build_gazetteer.py            # full build (~5 min, rate-limited)
    python tools/build_gazetteer.py --resume   # only fetch entries still missing
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "emissions" / "data" / "regions_kr.json"

# Official si/gun/gu list by province. Query strings use the full official
# prefix so that the many duplicate district names (중구, 서구, 남구 ...)
# resolve to the right city.
REGIONS: dict[str, list[str]] = {
    "서울특별시": ["종로구","중구","용산구","성동구","광진구","동대문구","중랑구","성북구","강북구","도봉구",
                "노원구","은평구","서대문구","마포구","양천구","강서구","구로구","금천구","영등포구","동작구",
                "관악구","서초구","강남구","송파구","강동구"],
    "부산광역시": ["중구","서구","동구","영도구","부산진구","동래구","남구","북구","해운대구","사하구",
                "금정구","강서구","연제구","수영구","사상구","기장군"],
    "대구광역시": ["중구","동구","서구","남구","북구","수성구","달서구","달성군","군위군"],
    "인천광역시": ["중구","동구","미추홀구","연수구","남동구","부평구","계양구","서구","강화군","옹진군"],
    "광주광역시": ["동구","서구","남구","북구","광산구"],
    "대전광역시": ["동구","중구","서구","유성구","대덕구"],
    "울산광역시": ["중구","남구","동구","북구","울주군"],
    "세종특별자치시": [""],
    "경기도": ["수원시","성남시","고양시","용인시","부천시","안산시","안양시","남양주시","화성시","평택시",
             "의정부시","시흥시","파주시","광명시","김포시","군포시","광주시","이천시","양주시","오산시",
             "구리시","안성시","포천시","의왕시","하남시","여주시","양평군","동두천시","과천시","가평군","연천군"],
    "강원특별자치도": ["춘천시","원주시","강릉시","동해시","태백시","속초시","삼척시","홍천군","횡성군","영월군",
                  "평창군","정선군","철원군","화천군","양구군","인제군","고성군","양양군"],
    "충청북도": ["청주시","충주시","제천시","보은군","옥천군","영동군","증평군","진천군","괴산군","음성군","단양군"],
    "충청남도": ["천안시","공주시","보령시","아산시","서산시","논산시","계룡시","당진시","금산군","부여군",
             "서천군","청양군","홍성군","예산군","태안군"],
    "전북특별자치도": ["전주시","군산시","익산시","정읍시","남원시","김제시","완주군","진안군","무주군","장수군",
                  "임실군","순창군","고창군","부안군"],
    "전라남도": ["목포시","여수시","순천시","나주시","광양시","담양군","곡성군","구례군","고흥군","보성군",
             "화순군","장흥군","강진군","해남군","영암군","무안군","함평군","영광군","장성군","완도군",
             "진도군","신안군"],
    "경상북도": ["포항시","경주시","김천시","안동시","구미시","영주시","영천시","상주시","문경시","경산시",
             "의성군","청송군","영양군","영덕군","청도군","고령군","성주군","칠곡군","예천군","봉화군",
             "울진군","울릉군"],
    "경상남도": ["창원시","진주시","통영시","사천시","김해시","밀양시","거제시","양산시","의령군","함안군",
             "창녕군","고성군","남해군","하동군","산청군","함양군","거창군","합천군"],
    "제주특별자치도": ["제주시","서귀포시"],
}

SIDO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
    "제주특별자치도": "제주",
}

UA = "greenproof-gazetteer/0.1 (Environmental Foundation module; contact via greenfund.ai.kr)"


def geocode(query: str):
    url = ("https://nominatim.openstreetmap.org/search?"
           + urllib.parse.urlencode({"q": query, "format": "json", "limit": 1,
                                     "countrycodes": "kr", "namedetails": 1,
                                     "accept-language": "ko"}))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        rows = json.load(r)
    if not rows:
        return None
    row = rows[0]
    nd = row.get("namedetails") or {}
    return {"lat": round(float(row["lat"]), 4), "lon": round(float(row["lon"]), 4),
            "en": nd.get("name:en") or ""}


def main():
    resume = "--resume" in sys.argv
    existing = {}
    if resume and OUT.exists():
        existing = {e["q"]: e for e in json.loads(OUT.read_text(encoding="utf-8"))["regions"]}

    entries, missed = [], []
    for sido, guns in REGIONS.items():
        short = SIDO_SHORT[sido]
        for gun in guns:
            q = f"{sido} {gun}".strip()
            label = f"{short} {gun}".strip() if gun else short
            if q in existing:
                entries.append(existing[q]);  continue
            g = geocode(q)
            time.sleep(1.1)  # Nominatim usage policy
            if not g:
                missed.append(q); print("  MISS", q); continue
            entries.append({"q": q, "ko": label, "sido": short, "gun": gun,
                            "en": g["en"], "lat": g["lat"], "lon": g["lon"]})
            print(f"  {label:12} {g['lat']:.4f},{g['lon']:.4f}  {g['en']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "OpenStreetMap Nominatim geocoding of official si/gun/gu names; © OpenStreetMap contributors",
        "count": len(entries), "regions": entries,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\n  {len(entries)} regions, {len(missed)} missed -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size/1024:.0f} KB)")
    if missed:
        print("  missed:", ", ".join(missed))


if __name__ == "__main__":
    main()
