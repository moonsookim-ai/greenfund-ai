# GreenProof

**Live: https://greenfund.ai.kr**

Satellite verification for reforestation. It answers one question about a
planting project: *are the trees actually alive?*

Environmental NGOs can say "we planted X trees." Almost none can show that the
trees survived. GreenProof closes that gap. It reads free Copernicus Sentinel-2
satellite imagery for a plot, measures how the tree canopy changed over years,
and publishes canopy cover, establishment rate and sequestered carbon — each
with an error range, and with every satellite scene it used disclosed so anyone
can repeat the calculation.

This repository is the working prototype behind the **satellite verification**
component of an AI programme proposed to a Korean environmental foundation.

## What is here

| Path | What it is |
|---|---|
| [`greenproof/`](greenproof/) | The pipeline and the public web viewer. See its [README](greenproof/README.md). |

## What it does, in one run

Working on a mangrove planting area in Dakope, Bangladesh, with no plot
coordinates supplied yet:

- **Find** — sweep the region for ground that was not vegetated and now is, and
  surface the strongest greening as candidate plots.
- **Verify** — read the plot across several dry-season dates. On the demo plot,
  canopy cover rose from 5% (2022) to 84% (2026); +39.1 ha, trend +21.7 pp/year.
- **Doubt itself** — an evergreen cross-check compares the wet season, so a
  greening paddy is never counted as forest. It also runs a mature-forest
  control to confirm the classification rules return the value expected.
- **Show** — a supporter opens a link and watches their own plot change over
  three years, over the satellite imagery, with the raw scene ids on the page.

## Principles

- **Every estimate is a range.** A single number looks precise and cannot be
  audited.
- **Not answering beats answering wrong.** In environmental data one
  exaggeration undoes years of trust.
- **The record is reproducible.** Every scene used is disclosed; the method and
  its limits ship with the output.

## Cost

Zero. Sentinel-2 imagery is a free public mirror on AWS Open Data, read by HTTP
range request so only the plot rectangle is fetched — a few megabytes for a
plot's whole time series.

## Data and licensing

Contains modified Copernicus Sentinel data, processed for canopy analysis. The
carbon coefficient is provisional and must be fixed by a review panel before any
figure is quoted as settled. See `greenproof/README.md` for the method and its
limits.
