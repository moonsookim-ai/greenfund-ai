#!/usr/bin/env python
"""GreenProof satellite verification.

    python greenproof.py scan   --region dakope       find candidate plots
    python greenproof.py verify --site dakope-demo    verify a plot, render frames
    python greenproof.py list                         show configuration

Output lands in web/data/ and web/index.html reads it as is.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gp import analysis, i18n, render, scan, stac  # noqa: E402

CONFIG = ROOT / "config" / "sites.json"
WEB_DATA = ROOT / "web" / "data"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def log(msg=""):
    print(msg, flush=True)


def en(payload: dict, key: str) -> str:
    return payload["en"][key]


# --------------------------------------------------------------------------- scan
def cmd_scan(args):
    cfg = load_config()
    region = cfg["regions"][args.region]
    log(f"# Greening scan: {region['label']['en']}")
    log(f"  bounds {region['bbox']}")

    res = scan.scan_region(
        region["bbox"],
        baseline=(f"{args.baseline}-12-01", f"{args.baseline + 1}-03-31"),
        recent=(f"{args.recent - 1}-12-01", f"{args.recent}-03-31"),
        log=log,
    )
    if "error" in res:
        log("  " + res["error"])
        return 1

    log(f"\n  baseline {res['baseline_date']} / recent {res['recent_date']}")
    log(f"  newly vegetated across the region: {res['newly_vegetated_frac']:.1%}\n")
    log("  rank  newly vegetated  plot bounds (lon1, lat1, lon2, lat2)")
    for i, c in enumerate(res["candidates"], 1):
        log(f"  {i:>3}   {c['score']:>13.1%}  {c['aoi']}")

    out = ROOT / "out" / f"scan_{args.region}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n  saved {out.relative_to(ROOT)}")
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
    log(f"# Plot verification: {site['label']['en']}")
    log(f"  observed area {area_ha:.1f} ha, coordinates {site['coords_status']}")

    series, frames, raws = [], [], []
    aspect = None
    for year in obs["years"]:
        start, end = f"{year - 1}-12-01", f"{year}-03-31"
        log(f"  searching {year} dry-season scene")
        sc, data = stac.best_scene(bbox, start, end, log=log)
        if sc is None:
            log(f"    {year}: no readable scene")
            continue

        st = analysis.canopy_stats(data["ndvi"], area_ha)
        st.update(
            year=year, date=sc.dt[:10], scene=sc.item_id,
            cloud_scene=round(sc.cloud, 2),
            cloud_aoi=round(data["cloud_frac"], 3),
            t_years=year - site["planted_year"],
        )
        series.append(st)
        log(f"    {sc.dt[:10]}  canopy {st['canopy_frac']:.1%}  mean NDVI {st['ndvi_mean']:.3f}")

        rgb = render.read_rgb(sc.scenes, bbox, out_shape=data["ndvi"].shape)
        if rgb is not None:
            px_m = (area_ha * 10_000) ** 0.5 / max(data["ndvi"].shape)
            aspect = round(rgb.shape[1] / rgb.shape[0], 4)
            common = dict(label=f"{sc.dt[:10]}   Canopy {st['canopy_frac']:.0%}", scale_m_per_px=px_m)
            frames.append((str(year), render.make_frame(
                rgb, data["ndvi"], overlay=True,
                sub=f"Sentinel-2 · {sc.item_id[:24]} · green = pixels classified as canopy", **common)))
            raws.append((str(year), render.make_frame(
                rgb, None, overlay=False,
                sub=f"Sentinel-2 · {sc.item_id[:24]} · unmodified satellite view", **common)))

    if len(series) < 2:
        log("  fewer than two readable dates. Widen the window or relax the cloud limit.")
        return 1

    # Evergreen test against a wet-season scene from the final year.
    last_year = series[-1]["year"]
    log(f"  cross-checking {last_year} wet season (evergreen test)")
    wet_obs, wet_data = stac.best_scene(
        bbox, f"{last_year - 1}-08-01", f"{last_year - 1}-11-30", max_cloud_aoi=0.35, log=log)
    if wet_obs is None:
        wet_obs, wet_data = stac.best_scene(
            bbox, f"{last_year}-07-01", f"{last_year}-11-30", max_cloud_aoi=0.45, log=log)
    if wet_data is not None:
        wet = analysis.canopy_stats(wet_data["ndvi"], area_ha)
        code, ratio = analysis.evergreen_code(series[-1]["canopy_frac"], wet["canopy_frac"])
        ever = i18n.pack(i18n.EVERGREEN, code)
        ever.update(ratio=ratio, wet_date=wet_obs.dt[:10],
                    wet_canopy_frac=wet["canopy_frac"], dry_canopy_frac=series[-1]["canopy_frac"])
        log(f"    {wet_obs.dt[:10]} wet-season canopy {wet['canopy_frac']:.1%} -> {en(ever, 'label')}")
    else:
        ever = i18n.pack(i18n.EVERGREEN, "not_run")
        ever["ratio"] = None
        log("    no wet-season scene, evergreen test skipped")

    first, last = series[0], series[-1]
    planted_ha = site.get("planted_ha") or area_ha
    est = analysis.establishment(first, last, planted_ha)
    years_elapsed = max(0.5, last["year"] - site["planted_year"])
    car = analysis.carbon(est.get("gain_ha", 0), years_elapsed, coef)
    tr = analysis.trend(series)
    verdict = i18n.pack(i18n.VERDICT,
                        analysis.verdict_code(est, tr, last, site.get("role", "subject")))

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
        "verdict": verdict,
        "method": {
            "canopy_threshold": analysis.NDVI_CANOPY,
            "threshold_range": [analysis.NDVI_CANOPY_LOW, analysis.NDVI_CANOPY_HIGH],
            **i18n.METHOD,
        },
    }

    out = outdir / "report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    index = WEB_DATA / "index.json"
    sites = json.loads(index.read_text(encoding="utf-8")) if index.exists() else {"sites": []}
    sites["sites"] = [s for s in sites["sites"] if s["id"] != args.site] + [
        {"id": args.site, "label": site["label"], "coords_status": site["coords_status"]}
    ]
    sites["sites"].sort(key=lambda s: s["id"])
    sites["generated_at"] = report["generated_at"]
    index.write_text(json.dumps(sites, ensure_ascii=False, indent=2), encoding="utf-8")

    log("")
    log(f"  verdict      {en(verdict, 'label')} · {en(verdict, 'note')}")
    log(f"  canopy       {first['canopy_ha']:.2f} ha ({first['year']}) -> {last['canopy_ha']:.2f} ha ({last['year']})")
    if est:
        log(f"  gain         {est['gain_ha']:+.2f} ha  (range {est['gain_ha_lo']:+.2f} to {est['gain_ha_hi']:+.2f})")
        log(f"  establishment {est['rate']:.0%}  (range {est['rate_lo']:.0%} to {est['rate_hi']:.0%}, lower bound)")
    log(f"  carbon       {car['tco2']:.0f} tCO2  (range {car['tco2_lo']:.0f} to {car['tco2_hi']:.0f}, provisional coefficient)")
    if tr:
        log(f"  trend        {tr['slope_pp_per_year']:+.2f} pp/year  (R2 {tr['r2']:.2f}, n={tr['n']})")
    log(f"  evergreen    {en(ever, 'label')}" + (f" (wet/dry {ever['ratio']:.2f})" if ever.get("ratio") else ""))
    log(f"  {len(names)} frames, mp4 {'written' if made_mp4 else 'skipped (no ffmpeg; viewer unaffected)'}")
    log(f"  saved {out.relative_to(ROOT)}")
    return 0


def cmd_list(args):
    cfg = load_config()
    log("# Regions")
    for k, v in cfg["regions"].items():
        log(f"  {k:<20} {v['label']['en']}  {v['bbox']}")
    log("# Plots")
    for k, v in cfg["sites"].items():
        log(f"  {k:<20} {v['label']['en']}  coords={v['coords_status']}  planted={v['planted_year']}")
    c = cfg["carbon_coefficient"]
    log(f"# Carbon coefficient  {c['low']}-{c['high']} {c['unit']} (mid {c['mid']}), status {c['status']}")
    return 0


def main():
    p = argparse.ArgumentParser(description="GreenProof satellite verification")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="find the strongest greening signals in a region")
    s.add_argument("--region", default="dakope")
    s.add_argument("--baseline", type=int, default=2022, help="start year of the baseline dry season")
    s.add_argument("--recent", type=int, default=2026, help="end year of the recent dry season")
    s.set_defaults(func=cmd_scan)

    v = sub.add_parser("verify", help="verify a plot and render frames")
    v.add_argument("--site", default="dakope-demo")
    v.add_argument("--no-overlay", action="store_true", help="satellite view only, no canopy shading")
    v.add_argument("--aoi", help="override the configured bounds: lon1,lat1,lon2,lat2")
    v.set_defaults(func=cmd_verify)

    l = sub.add_parser("list", help="show configuration")
    l.set_defaults(func=cmd_list)

    args = p.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
