# GreenProof satellite verification

**Live: https://greenfund.ai.kr**

The working implementation of the satellite-verification component. It verifies a
planting plot against free Copernicus Sentinel-2 imagery and produces the public
web viewer where a supporter watches their own plot change over years.
**Nothing is captured on demand — it reads what the satellite already recorded.**

---

## What runs today

The whole pipeline runs on real data. Figures below are from a run on
2026-07-25.

**Find (`scan`)** — the foundation does not hold plot coordinates yet, so this
sweeps ~25×25 km around Dakope, Khulna, Bangladesh on a 20 m grid for ground that
was not vegetated in 2023 and is canopy in 2026. Four candidate cells; the top
two are adjacent and merge into a 50 ha plot.

**Verify (`verify`)** — five dry-season dates for that plot:

| Observed | Canopy cover | Mean NDVI |
|---|---|---|
| 2022-03-10 | 5.4% | 0.115 |
| 2023-01-09 | 16.0% | 0.167 |
| 2023-12-30 | 23.5% | 0.136 |
| 2025-03-29 | 77.1% | 0.512 |
| 2026-03-04 | 83.6% | 0.590 |

Canopy area 2.72 → 41.82 ha, gain +39.10 ha (range 34.72–42.34), trend
+21.7 pp/year (R² 0.89), sequestered carbon 369 tCO₂ (range 235–528).

**Control** — reading the mature Sundarbans mangrove forest with the same rules
returns canopy 99.9%, +0.04 ha over five years, evergreen 1.00. Exactly as
expected: it shows the classification rules work.

**Evergreen test** — the candidate plot's wet-season canopy was 0.54× its dry
season, so the verdict is "partly deciduous, field verification required." The
system does not assert this plot is mangrove. That restraint is the point.
Vegetation indices cannot tell one green from another; without this test a
greening paddy would be reported as a planted forest.

---

## Install and run

```bash
pip install rasterio numpy pillow
```

```bash
python greenproof.py list                        # show configuration
python greenproof.py scan --region dakope         # find candidate plots
python greenproof.py verify --site dakope-demo    # verify a plot, render frames
python greenproof.py verify --site dakope-demo --aoi 89.454,22.666,89.459,22.675
```

Serve `web/` statically for the viewer. A supporter link is `?plot=<id>`.

```bash
python -m http.server 4810 --directory web
```

The viewer has a language toggle (English / Korean); the pipeline writes verdict
codes and every code carries both renderings, so the record is translatable
without re-running the analysis.

---

## Output

```
web/data/<id>/report.json      the ledger: scenes, figures, method, limits
web/data/<id>/NN_YYYY.jpg       frames with the canopy classification overlaid
web/data/<id>/raw_NN_YYYY.jpg   the unmodified satellite frames
web/data/<id>/timelapse.mp4     press cut (when ffmpeg is present)
web/og.png                      social card, built from the real frames
out/scan_<region>.json          scan results
```

---

## How it reads

**Source** Copernicus Sentinel-2 L2A, the free AWS Open Data mirror. No API key.
No whole-file downloads: an HTTP range request pulls only the plot rectangle.

**Index** NDVI = (B08 − B04) / (B08 + B04). Canopy threshold 0.30; the range
estimate sweeps 0.25–0.35 to bracket the area.

**Cloud handling** Cloud, shadow and no-data pixels are removed with the SCL
scene-classification band. Scene-level cloud cover is only a hint, so the plot is
read and re-measured for cloud sitting over it.

**Season** Dry season only (Dec–Mar). The monsoon brings cloud, and high tides
distort readings over tidal flats.

**Tile mosaic** When a plot straddles a tile boundary, adjacent tiles from the
same orbital pass are stitched — same capture time, no mismatch.

**Evergreen test** Cross-checks a wet-season scene. Mangrove holds canopy in both
seasons; rice does not.

---

## Limits (shipped with every output)

- Seedlings smaller than the 10 m grid are invisible; early establishment is a
  lower bound.
- Tide level changes exposed flat area and moves NDVI; only same-season scenes
  are compared.
- Sequestered carbon is inferred from canopy area and does not replace field
  measurement.
- The carbon coefficient (4.0–9.0 tCO₂/ha/yr) is **provisional**; do not quote it
  as settled until a review panel fixes it. Change it in `config/sites.json`.
- Until coordinates are confirmed, results describe a candidate plot.

---

## When coordinates arrive

This tool changes role: from finding plots to checking them. Set the real
boundary as `aoi` in `config/sites.json`, set `coords_status` to `confirmed`,
fill `planted_ha` and `planted_trees`, and re-run `verify`. Then check whether the
supplied boundary and the greening the satellite saw actually overlap. All the
partner needs to send is the plot boundary — GeoJSON, or a list of corner
lon/lat.

---

## Field notes (measured, kept for whoever runs this next)

- **Tile-edge no-data** Dakope sits on the 45QYE / 45QYF tile boundary. Reading
  one tile returns 80–90% no-data. Same-day mosaicking is required.
- **Cloud 0% yet 90% no-data** The STAC `eo:cloud_cover` is a whole-tile figure,
  irrelevant to the plot. Read the rectangle and re-measure.
- **Remote-read speed** Without `GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR`, remote
  reads are several times slower. Set in `gp/stac.py`.
- **Green is not green** NDVI cannot separate paddy from mangrove. Without the
  evergreen test, a greening crop reads as afforestation.
- **A verifier needs a control** If the mature forest does not return the
  expected value, suspect the rules before the forest.

---

## Ocean intro

The landing page opens on a full-screen procedural ocean — a self-contained
WebGL2 shader (`web/ocean.js`), no libraries or assets: a raymarched heightfield
of choppy multi-octave swell, an analytic sky shared by the dome and the water
reflection, Fresnel, sun glitter, subsurface crest scatter, foam and horizon
haze, closed with ACES tone mapping. WebGL2 rather than WebGPU on purpose: the
whole point of the site is that anyone can see the proof, and WebGPU still fails
on many browsers. It pauses off-screen and on hidden tabs, caps device pixel
ratio, and renders a single static frame under `prefers-reduced-motion`.
