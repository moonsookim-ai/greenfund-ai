#!/usr/bin/env python
"""Build the Korean emissions dataset for the "emissions near you" map.

Source: Climate TRACE (climatetrace.org), an open coalition that estimates
greenhouse-gas emissions for individual facilities worldwide from satellites,
sensors and AI. Its API is public and needs no key.

We keep the point sources a citizen would recognise as "an emitter near me"
— power stations, steel and cement works, refineries, landfills, airports and
ports, and city-level building totals. We deliberately drop agriculture and
forestry-and-land-use: those come as thousands of diffuse grid cells, not
facilities, and would bury the map. That choice is disclosed on the page.

    python tools/build_emissions.py
"""
from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "emissions" / "data"
API = "https://api.climatetrace.org/v6"

# sector slug -> (short code, EN label, KO label)
SECTORS = {
    "power":                  ("power",  "Power",           "발전"),
    "manufacturing":          ("mfg",    "Manufacturing",   "제조 (철강·시멘트 등)"),
    "fossil-fuel-operations": ("fossil", "Oil & gas",       "정유·석유가스"),
    "waste":                  ("waste",  "Waste",           "폐기물"),
    "transportation":         ("transp", "Transport hubs",  "수송 거점 (공항·항만)"),
    "buildings":              ("bldg",   "Buildings (city)","건물 (도시 합계)"),
}


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "greenproof/0.1", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def main():
    facilities = []
    per_sector = {}
    for slug, (code, en, ko) in SECTORS.items():
        d = get(f"{API}/assets?countries=KOR&sectors={slug}&limit=1000")
        kept = 0
        for a in d.get("assets", []):
            es = (a.get("EmissionsSummary") or [{}])[0]
            e = es.get("EmissionsQuantity")
            geom = (a.get("Centroid") or {}).get("Geometry")
            if not e or e <= 0 or not geom:
                continue
            owners = a.get("Owners") or []
            facilities.append({
                "id": a["Id"],
                "n": a.get("Name") or "Unknown",
                "s": code,
                "t": a.get("AssetType") or "",
                "lon": round(float(geom[0]), 4),
                "lat": round(float(geom[1]), 4),
                "e": int(round(e)),                       # tonnes CO2e (100yr)
                "o": (owners[0].get("CompanyName") if owners else "") or "",
            })
            kept += 1
        per_sector[code] = kept
        print(f"  {slug:24} kept {kept}")

    facilities.sort(key=lambda f: -f["e"])
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": date.today().isoformat(),
        "source": "Climate TRACE (climatetrace.org), open facility-level emissions",
        "gas": "co2e_100yr, tonnes",
        "note_excluded": "Agriculture and forestry-and-land-use are excluded: they are diffuse grid cells, not facilities.",
        "sectors": {code: {"en": en, "ko": ko} for slug, (code, en, ko) in SECTORS.items()},
        "count": len(facilities),
        "total_tco2e": sum(f["e"] for f in facilities),
        "facilities": facilities,
    }
    out = OUT / "emissions_kr.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    mt = payload["total_tco2e"] / 1e6
    print(f"\n  {len(facilities)} facilities, {mt:,.0f} Mt CO2e total")
    print(f"  top: {facilities[0]['n']} {facilities[0]['e']/1e6:.1f} Mt")
    print(f"  saved {out.relative_to(ROOT)}  ({out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
