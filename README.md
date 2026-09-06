# GREEN PROOF · AI환경연구소

**Live: https://greenfund.ai.kr**
**환경재단이 운영하는 AI환경연구소 GREEN PROOF**
연구책임자 김문수 교수 · <mskim@ceobizschool.kr>

이 사이트는 환경재단 홈페이지의 [재단소개 → AI환경연구소](https://greenfund.org/about/ai-environment-institute) 메뉴에도 연결되어 있습니다.

The site brings together satellite verification, an emissions map, and the
[Nepal situation room](https://greenfund.ai.kr/nepal/). The Nepal public evidence
register and Model A were researched, designed, visualised and implemented with
**GPT-6 Astra**. Read the [model definitions and limitations](docs/nepal-model-a.md).

Satellite verification for reforestation. It answers one question about a
planting project: *are the trees actually alive?*

Environmental NGOs can say "we planted X trees." Almost none can show that the
trees survived. GreenProof closes that gap. It reads free Copernicus Sentinel-2
satellite imagery for a plot, measures how the tree canopy changed over years,
and publishes canopy cover, establishment rate and sequestered carbon — each
with an error range, and with every satellite scene it used disclosed so anyone
can repeat the calculation.

The following sections describe the original **satellite verification** pipeline
within GREEN PROOF, the AI Environmental Research Institute operated by the
Environmental Foundation.

## What is here

| Path | What it is |
|---|---|
| [`greenproof/`](greenproof/) | The pipeline and the public web viewer. See its [README](greenproof/README.md). |

Three live modules share the site:

- **Satellite verification** (`/`) — reforestation read from Sentinel-2, the
  section above.
- **Emissions near you** (`/emissions/`) — type where you live and see the
  largest greenhouse-gas emitters around you, ranked, from open Climate TRACE
  facility data (1,204 Korean facilities, 587 Mt CO₂e). A local radar of nearby
  emitters plus a ranked list, bilingual, self-contained. Built by
  `greenproof/tools/build_emissions.py`. Farms and forests are excluded on
  purpose — they arrive as diffuse grid cells, not facilities — and the page
  says so. The framing is information, not accusation.
- **네팔상황실 / Nepal situation room** (`/nepal/`) — source-backed evidence for
  the August–September 2026 flood and a WASH aid-priority scenario calculator.
  Missing public inputs stay null; no unsupported official ranking is published.
  Includes sensitivity to policy weights, input/result export, and source notes.
  Research lead: 김문수 교수. Built with GPT-6 Astra.

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
