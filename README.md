# ModelCompass

**Open data for comparing AI model pricing, performance and quality.**

Picking an AI model involves more than finding the cheapest token price. ModelCompass
brings together sourced data and reproducible tools to make those comparisons easier.

This first release covers selected models from OpenAI, Anthropic and Google: release
history, input/output prices and documented context capacities. Benchmarks, quality
signals and practical performance are next.

**Data as of 10 October 2026.** This is a curated historical snapshot; automated
refreshes and alerts are planned.

## Explore

- [Pricing by category — linear scale](charts/category-linear.html)
- [Pricing by company — logarithmic scale](charts/company-log.html)

Download either HTML file and open it in a browser. The charts include their data
and Plotly runtime, so they work offline. Click a legend item to hide/show a family;
double-click to isolate it. Filtering rescales that panel and updates its labels.
The date window stays fixed. “My take” boxes are the author's interpretation.

For web links in a LinkedIn post, enable GitHub Pages for the repository's main
branch and root folder. The included `index.html` links to both charts. See
[GitHub's setup guide](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Use the data

| File | Contents |
| --- | --- |
| [models.csv](data/models.csv) | 72 model/version records: 70 selected named releases and two dated snapshots; launch prices and context metadata |
| [price-history.csv](data/price-history.csv) | 77 sourced price events/observations; later cuts remain separate from launch prices |
| [model-categories.csv](data/model-categories.csv) | Editable intended-use categories and the selected comparison paths |
| [sources/](data/sources/) | Curated source records for releases, prices and context specifications |

Prices are **USD per 1M standard text tokens**, using short-prompt base tiers.
Context capacities are in tokens, with the provider's definition recorded. Dates
use `YYYY-MM-DD`. Blank values mean unknown or unverified, not zero.

Launch prices are available for 66 of the 72 records, including the two snapshots.
Context capacities are sourced for 67 records. The six launch-price gaps and five
context gaps are listed in [METHODOLOGY.md](METHODOLOGY.md). One historical o3 quote
is explicitly labelled as derived from a provider-stated discount.

The charts show 12 selected family paths, 175 drawing anchors and **61 verified
named-release markers**. Quarter-end/latest anchors carry forward a documented
quote; they are not additional source observations or releases. Both charts use
the same underlying records. The o-series branch remains in the CSVs but is
excluded from these charts.

See [METHODOLOGY.md](METHODOLOGY.md) for field definitions and comparison rules.

## Reproduce

Requires **Python 3.10+**. Run from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/normalize_data.py
python scripts/validate_data.py
python scripts/build_charts.py
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.
No API key or network connection is needed after dependencies are installed.

`normalize_data.py` standardizes identities, dates and numeric units, checks
duplicates, joins release/price evidence and preserves missing values.
`validate_data.py` checks references, provenance, dates and prices, and reports
coverage gaps. `build_charts.py` regenerates both HTML files and the landing page.
The small JavaScript helper handles responsive labels and legend filtering.

To check whether committed CSVs match their sources without rewriting them:

```bash
python scripts/normalize_data.py --check
```

Presentation choices, category descriptions and commentary live in
`chart-settings.json`, separate from the factual CSVs. Source collection is
currently manual; these scripts reproduce normalization and chart generation.

## Contribute

Corrections, missing historical quotes, additional models and reproducible
evaluations are welcome. Open an issue or pull request with the source URL,
relevant date, exact model version and any pricing/evaluation conditions.

For data changes, edit the appropriate CSV in `data/sources/`. Add or revise the
model's category assignment when needed, then run the three scripts above.
Include regenerated CSVs and charts with your pull request. Category changes and
commentary changes should be identified as judgement rather than provider facts.

## Roadmap

- [ ] Expand historical coverage, specifications and hosting providers.
- [ ] Add open-weight models, separating hosted API prices from self-hosting costs.
- [ ] Add benchmarks with exact model versions, evaluation settings and provenance.
- [ ] Add task-specific quality/reliability signals and human evaluations.
- [ ] Add latency, throughput and operational-performance measurements.
- [ ] Introduce reviewed weekly refreshes, then daily checks where useful.
- [ ] Add configurable alerts for releases, price changes and new evaluation results.

Future datasets will join through `model_id`. Developer and API hosting provider
remain separate, and provider-reported results will be distinguished from
independent evaluations. There is no benchmark leaderboard or composite quality
score in this release.

## Licence

Code: [MIT](LICENSE). Dataset compilation: [CC BY 4.0](DATA_LICENSE.md).
Provider evidence remains linked and attributed. Embedded Plotly.js notices are
documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
