# Methodology

## Scope and evidence

This is a selected historical comparison of first-party text API offerings from
OpenAI, Anthropic and Google, checked as of **10 October 2026**. It is not a full
model catalogue, a live price feed or a claim that every historical endpoint is
still available. Paid public previews are included where explicitly named.

The three source CSVs contain manually curated facts and source URLs, not scraped
copies of provider pages. Normalization is reproducible; original collection and
source interpretation involve review. Current model documentation is not used to
backfill unknown historical launch prices.

## Identity and dates

`model_id` is a stable project identifier, not necessarily an API endpoint ID.
It combines the developer and normalized model/version name. A price-cut or
promotion suffix is an event label and is removed from model identity. The
August 2024 GPT-4o snapshot and October 2024 Sonnet 3.5 update keep distinct IDs.
Renames and selected family succession do not establish retirement or equivalence.

`release_date` is the documented date in the selected release inventory; API
availability takes precedence over an earlier product announcement where known.
`release_kind` distinguishes `named_release` from `dated_snapshot`. Prices join
to launch metadata only when the date and exact model/version match.

`price_date` is the source event/observation date. `date_type` identifies a
documented event, an observation or an announced rate. These are not universally
asserted billing-effective dates: Gemini 1.5 Flash-8B's rate was announced on
3 October 2024, with billing starting 14 October. The source note preserves this.

## Prices and context

Rates are USD per 1M standard text tokens for short-prompt base tiers. They do not
adjust for caching, batch processing, tools, regional premiums or enterprise
discounts. Output rates can include billed reasoning tokens; equal rates do not
imply equal total task costs or equal quality. Some source records are promotional;
their conditions remain in the data rather than being assumed permanent.

Haiku 5.5's retained base quote applies to prompts up to 100,000 input tokens.
Its context capacity is larger, but larger prompts have a different price tier.
Other providers also apply length-dependent pricing; a context limit does not
mean the quoted base rate applies throughout that window.

`price_basis` distinguishes documented quotes from calculations. The o3 launch
quote of $10 input/$40 output is reconstructed from the provider's stated 80%
reduction to $2/$8: `new_rate / (1 - 0.80)`. It is retained with its source and
calculation label, not presented as a directly recovered launch quotation.

Context values are specifications verified on `context_spec_date`, **not launch
specifications**. `provider_context_window` follows the provider's window
definition; Google's `provider_input_token_limit` records its maximum input
capacity, not an invented combined input/output total. Default documented Claude
windows exclude opt-in beta extensions. A documented capacity does not establish
that an endpoint remains available, or that it reliably uses all that context.

## Categories and chart construction

Categories reflect intended workloads, not equivalent capability, quality or
fixed price bands. `model-categories.csv` stores editable analytical assignments;
`models.csv` includes the category as a generated convenience column. A blank
`series_id` keeps a model in the catalogue but out of the selected chart paths.

The category chart orders Complex/Professional, Efficient/General-Purpose,
Fast/High-Volume and Most Demanding. That order is editorial, not a measured
popularity ranking. It uses category-specific linear dollar ranges. Most
Demanding starts at $20; the other panels start at zero. Initial company panels
share a logarithmic range; equally spaced ticks represent multiplicative changes.

Both charts reconstruct the same 175 anchors from the 77 source quotes and
quarter-end/latest selection. Each selection carries the last documented quote
within its configured family path. It does not imply a newly observed rate,
an average price, the cheapest model, or that an older endpoint stayed available.
Lines connect anchors; they do not establish unobserved intra-period price paths.

Dots appear only on selected named releases with exact-date launch quotes. Same-
model cuts, promotions, snapshots and carried-forward quarterly anchors are not
release markers. Four unpriced launches on the plotted paths are unmarked. The
o-series branch is retained in the datasets but excluded from these 12 paths.
Named GPT Pro variants and Astra remain separate offers.

Legend filtering hides owned annotations and rescales only the affected panel;
the date window stays fixed. Narrow layouts move endpoint labels below the plot,
and suppress historical labels when no clear placement is available. All points
remain accessible through hover. “My take” boxes are opinions and conditional
forecasts, authored for the initial snapshot; they do not automatically update
when data or legend selection changes.

## Known gaps

Launch prices are unverified for Haiku 3.5, Gemini 1.5 Flash, Gemini 1.5 Pro,
Gemini 3.6 Flash, o1-preview and o1-pro. Later/current observations are not
substituted for missing launch quotes. The first four belong to plotted paths.

Exact-version context capacities remain unverified for Gemini 1.5 Flash,
Gemini 1.5 Flash-8B, Gemini 1.5 Pro, GPT-4o 2024-08-06 and Sonnet 3.5 2024-10-22.
The contemporary official Gemini 1.5 model-page routes did not yield token-limit
text in the checks performed. This does not establish that those specifications
never existed. Values stay blank pending historical/exact-version evidence.

## Field dictionary

### `models.csv`

| Field | Definition |
| --- | --- |
| `model_id`, `company`, `family`, `model_name` | Project identity, developer and descriptive names |
| `category` | Generated convenience join from the separate assignment table |
| `release_date`, `release_kind` | Documented release/version date and inventory type |
| `launch_input_usd_per_million`, `launch_output_usd_per_million` | Exact-date launch/version quotes; blank when unverified |
| `launch_price_basis` | Documented quote or provider-discount calculation |
| `context_window_tokens`, `context_definition`, `context_spec_date` | Dated capacity and its provider-specific meaning |
| `release_source_url`, `launch_price_source_url`, `context_source_url` | Field-specific provenance |
| `verified_at`, `notes` | Snapshot review date, scope and missingness |

### `price-history.csv`

| Field | Definition |
| --- | --- |
| `price_id`, `model_id`, `api_provider` | Quote identifier, model join and billing provider |
| `price_date`, `date_type` | Source event/observation date and its meaning |
| `input_usd_per_million`, `output_usd_per_million` | Numeric standard text-token rates |
| `event_type` | Launch, price change, promotion, snapshot or observation |
| `price_basis`, `pricing_conditions` | Evidence type and applicable pricing scope |
| `price_source_url`, `verified_at` | Provenance and snapshot review date |
| `source_model_name`, `note` | Original label and retained evidence qualifications |

### Future comparison data

Benchmarks will record benchmark/version, score and direction, evaluator, exact
model version, evaluation date, source and relevant configuration, including tools,
reasoning effort and quantization. Provider-reported and independent results will
remain distinct. Quality evidence should include task, population/sample size and
conditions where available. Popularity/adoption signals are not quality scores.
Hosted open-weight rates must identify the API provider; self-hosting costs will
need separate hardware, utilization and workload assumptions.
