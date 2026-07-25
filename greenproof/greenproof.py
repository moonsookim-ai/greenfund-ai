#!/usr/bin/env python
"""그린프루프 위성 검증소.

사용법
  python greenproof.py scan   --region dakope        후보 구획 탐색
  python greenproof.py verify --site dakope-demo     구획 검증 + 프레임 생성
  python greenproof.py list                          설정 확인

산출물은 web/data/ 에 떨어지고 web/index.html 이 그대로 읽는다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gp import analysis, render, scan, stac  # noqa: E402

CONFIG = ROOT / "config" / "sites.json"
WEB_DATA = ROOT / "web" / "data"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def log(msg=""):
    print(msg, flush=True)


# --------------------------------------------------------------------------- scan
def cmd_scan(args):
    cfg = load_config()
    region = cfg["regions"][args.region]
    log(f"■ 녹화 신호 탐색: {region['label']}")
    log(f"  범위 {region['bbox']}")

    res = scan.scan_region(
        region["bbox"],
        baseline=(f"{args.baseline}-12-01", f"{args.baseline + 1}-03-31"),
        recent=(f"{args.recent - 1}-12-01", f"{args.recent}-03-31"),
        log=log,
    )
    if "error" in res:
        log("  " + res["error"])
        return 1

    log(f"\n  기준 {res['baseline_date']} / 현재 {res['recent_date']}")
    log(f"  지역 전체 신규 식생 비율 {res['newly_vegetated_frac']:.1%}\n")
    log("  순위  신규식생비율  구획 좌표(경도1, 위도1, 경도2, 위도2)")
    for i, c in enumerate(res["candidates"], 1):
        log(f"  {i:>3}   {c['score']:>10.1%}  {c['aoi']}")

    out = ROOT / "out" / f"scan_{args.region}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n  저장 {out.relative_to(ROOT)}")
    return 0


# ------------------------------------------------------------------------- verify
def cmd_verify(args):
    cfg = load_config()
    site = dict(cfg["sites"][args.site])
    obs = cfg["observation"]
    coef = cfg["carbon_coefficient"]

    if args.aoi:
        site["aoi"] = [float(x) for x in args.aoi.split(",")]
        site["coords_status"] = "ad-hoc"
    bbox = site["aoi"]
    area_ha = analysis.aoi_area_ha(bbox)
    log(f"■ 구획 검증: {site['label']}")
    log(f"  관측 면적 {area_ha:.1f} ha · 좌표 상태 {site['coords_status']}")

    series, frames, raws = [], [], []
    aspect = None
    for year in obs["years"]:
        start, end = f"{year - 1}-12-01", f"{year}-03-31"
        log(f"  {year} 건기 장면 탐색")
        sc, data = stac.best_scene(bbox, start, end, log=log)
        if sc is None:
            log(f"    {year}: 판독 가능한 장면 없음")
            continue

        st = analysis.canopy_stats(data["ndvi"], area_ha)
        st.update(
            year=year, date=sc.dt[:10], scene=sc.item_id,
            cloud_scene=round(sc.cloud, 2),
            cloud_aoi=round(data["cloud_frac"], 3),
            t_years=year - site["planted_year"],
        )
        series.append(st)
        log(f"    {sc.dt[:10]}  임관 {st['canopy_frac']:.1%}  NDVI 평균 {st['ndvi_mean']:.3f}")

        rgb = render.read_rgb(sc.scenes, bbox, out_shape=data["ndvi"].shape)
        if rgb is not None:
            px_m = (area_ha * 10_000) ** 0.5 / max(data["ndvi"].shape)
            aspect = round(rgb.shape[1] / rgb.shape[0], 4)
            common = dict(label=f"{sc.dt[:10]}   임관 피복 {st['canopy_frac']:.0%}", scale_m_per_px=px_m)
            frames.append((str(year), render.make_frame(
                rgb, data["ndvi"], overlay=True,
                sub=f"Sentinel-2 · {sc.item_id[:24]} · 초록 음영 = 임관 판정 화소", **common)))
            raws.append((str(year), render.make_frame(
                rgb, None, overlay=False,
                sub=f"Sentinel-2 · {sc.item_id[:24]} · 위성 원본 실사", **common)))

    if len(series) < 2:
        log("  판독된 시점이 2개 미만이다. 기간을 넓히거나 구름 조건을 완화할 것.")
        return 1

    # 상록성 검사: 마지막 관측 연도의 우기 장면과 대조한다.
    last_year = series[-1]["year"]
    log(f"  {last_year} 우기 대조 (상록성 검사)")
    wet_obs, wet_data = stac.best_scene(
        bbox, f"{last_year - 1}-08-01", f"{last_year - 1}-11-30",
        max_cloud_aoi=0.35, log=log)
    if wet_obs is None:
        wet_obs, wet_data = stac.best_scene(
            bbox, f"{last_year}-07-01", f"{last_year}-11-30", max_cloud_aoi=0.45, log=log)
    if wet_data is not None:
        wet = analysis.canopy_stats(wet_data["ndvi"], area_ha)
        ever = analysis.evergreen_test(series[-1]["canopy_frac"], wet["canopy_frac"])
        ever["wet_date"] = wet_obs.dt[:10]
        ever["wet_canopy_frac"] = wet["canopy_frac"]
        ever["dry_canopy_frac"] = series[-1]["canopy_frac"]
        log(f"    {wet_obs.dt[:10]} 우기 임관 {wet['canopy_frac']:.1%} → {ever['flag']}")
    else:
        ever = {"ratio": None, "flag": "미실시", "note": "우기에 판독 가능한 장면을 찾지 못했다."}
        log("    우기 장면 없음. 상록성 검사 미실시.")

    first, last = series[0], series[-1]
    planted_ha = site.get("planted_ha") or area_ha
    est = analysis.establishment(first, last, planted_ha)
    years_elapsed = max(0.5, last["year"] - site["planted_year"])
    car = analysis.carbon(est.get("gain_ha", 0), years_elapsed, coef)
    tr = analysis.trend(series)
    label, note = analysis.verdict(est, tr, last, site.get("role", "subject"))

    outdir = WEB_DATA / args.site
    names = render.write_frames(frames, outdir)
    raw_names = render.write_frames(raws, outdir, prefix="raw_")
    made_mp4 = render.make_video(outdir, raw_names, outdir / "timelapse.mp4")

    report = {
        "site": args.site,
        "label": site["label"],
        "partner": site.get("partner"),
        "coords_status": site["coords_status"],
        "role": site.get("role", "subject"),
        "aoi": bbox,
        "area_ha": round(area_ha, 2),
        "planted_year": site["planted_year"],
        "planted_ha": site.get("planted_ha"),
        "planted_trees": site.get("planted_trees"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "series": series,
        "frames": names,
        "frames_raw": raw_names,
        "frame_aspect": aspect,
        "video": "timelapse.mp4" if made_mp4 else None,
        "establishment": est,
        "carbon": car,
        "carbon_coefficient": coef,
        "trend": tr,
        "evergreen": ever,
        "verdict": {"label": label, "note": note},
        "method": {
            "source": "Copernicus Sentinel-2 L2A (AWS Open Data, 무료 공개)",
            "index": "NDVI = (B08 − B04) / (B08 + B04)",
            "canopy_threshold": analysis.NDVI_CANOPY,
            "threshold_range": [analysis.NDVI_CANOPY_LOW, analysis.NDVI_CANOPY_HIGH],
            "cloud_mask": "SCL 장면분류에서 구름·그림자·결측 화소 제외",
            "season": obs["season_note"],
            "limits": [
                "10m 격자보다 작은 어린 묘목은 잡히지 않는다. 초기 정착률은 하한으로 읽어야 한다.",
                "조위에 따라 갯벌 노출 면적이 달라져 NDVI 가 흔들린다. 같은 건기 장면끼리만 비교했다.",
                "흡수 탄소는 임관 면적에서 역산한 추정치다. 현장 실측을 대체하지 않는다.",
                "좌표가 확정되기 전 결과는 후보 구획에 대한 것이다.",
            ],
        },
    }

    out = outdir / "report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    index = WEB_DATA / "index.json"
    sites = json.loads(index.read_text(encoding="utf-8")) if index.exists() else {"sites": []}
    sites["sites"] = [s for s in sites["sites"] if s["id"] != args.site] + [
        {"id": args.site, "label": site["label"], "coords_status": site["coords_status"]}
    ]
    sites["generated_at"] = report["generated_at"]
    index.write_text(json.dumps(sites, ensure_ascii=False, indent=2), encoding="utf-8")

    log("")
    log(f"  판정        {label} · {note}")
    log(f"  임관 면적   {first['canopy_ha']:.2f} ha ({first['year']}) → {last['canopy_ha']:.2f} ha ({last['year']})")
    if est:
        log(f"  증가        {est['gain_ha']:+.2f} ha  (범위 {est['gain_ha_lo']:+.2f} ~ {est['gain_ha_hi']:+.2f})")
        log(f"  정착 추정률 {est['rate']:.0%}  (범위 {est['rate_lo']:.0%} ~ {est['rate_hi']:.0%}, 하한 해석)")
    log(f"  흡수 추정   {car['tco2']:.0f} tCO2  (범위 {car['tco2_lo']:.0f} ~ {car['tco2_hi']:.0f}, 계수 잠정)")
    if tr:
        log(f"  추세        연 {tr['slope_pp_per_year']:+.2f}%P  (R² {tr['r2']:.2f}, n={tr['n']})")
    log(f"  상록성      {ever['flag']}" + (f" (우기/건기 {ever['ratio']:.2f})" if ever.get("ratio") else ""))
    log(f"  프레임 {len(names)}장, mp4 {'생성' if made_mp4 else '미생성(ffmpeg 없음, 뷰어는 정상)'}")
    log(f"  저장 {out.relative_to(ROOT)}")
    return 0


def cmd_list(args):
    cfg = load_config()
    log("■ 지역")
    for k, v in cfg["regions"].items():
        log(f"  {k:<14} {v['label']}  {v['bbox']}")
    log("■ 구획")
    for k, v in cfg["sites"].items():
        log(f"  {k:<14} {v['label']}  좌표 {v['coords_status']}  식재 {v['planted_year']}")
    c = cfg["carbon_coefficient"]
    log(f"■ 탄소 계수  {c['low']}~{c['high']} {c['unit']} (기준 {c['mid']}) · 상태 {c['status']}")
    return 0


def main():
    p = argparse.ArgumentParser(description="그린프루프 위성 검증소")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="지역에서 녹화 신호 상위 구획 탐색")
    s.add_argument("--region", default="dakope")
    s.add_argument("--baseline", type=int, default=2022, help="기준 건기의 시작 연도")
    s.add_argument("--recent", type=int, default=2026, help="현재 건기의 종료 연도")
    s.set_defaults(func=cmd_scan)

    v = sub.add_parser("verify", help="구획 검증 및 프레임 생성")
    v.add_argument("--site", default="dakope-demo")
    v.add_argument("--no-overlay", action="store_true", help="임관 음영 없이 원본 위성 실사만")
    v.add_argument("--aoi", help="설정 대신 임시 좌표로 검증: lon1,lat1,lon2,lat2")
    v.set_defaults(func=cmd_verify)

    l = sub.add_parser("list", help="설정 확인")
    l.set_defaults(func=cmd_list)

    args = p.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
