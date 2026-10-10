"""Check integrity, provenance and missingness before building public charts."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from normalize_data import ROOT, normalize, read_csv


def validate(root: Path) -> dict:
    settings = json.loads((root/'chart-settings.json').read_text(encoding='utf-8'))
    cutoff = date.fromisoformat(settings['as_of'])
    models = read_csv(root/'data/models.csv')
    prices = read_csv(root/'data/price-history.csv')
    assignments = read_csv(root/'data/model-categories.csv')
    by_id = {r['model_id']: r for r in models}
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def valid_url(value):
        parsed = urlparse(value)
        return parsed.scheme in {'https', 'http'} and bool(parsed.netloc)

    def valid_date(value):
        try:
            return date.fromisoformat(value) <= cutoff
        except ValueError:
            return False

    def numeric(value, positive=False, integer=False):
        try:
            parsed = Decimal(value)
            return parsed.is_finite() and (parsed > 0 if positive else parsed >= 0) and (
                not integer or parsed == parsed.to_integral_value())
        except Exception:
            return False

    for rows, key in [(models, 'model_id'), (prices, 'price_id'), (assignments, 'model_id')]:
        require(len({r[key] for r in rows}) == len(rows), f'Duplicate {key}')
    series = {s['id']: s for s in settings['series']}
    category_names = {c['title'] for c in settings['categories']}
    for assignment in assignments:
        mid = assignment['model_id']
        require(mid in by_id, f'Category references unknown model: {mid}')
        require(assignment['category'] in category_names, f'Unknown category: {mid}')
        if assignment['series_id']:
            s = series.get(assignment['series_id'])
            require(s is not None, f'Unknown chart series: {mid}')
            if s and mid in by_id:
                require(s['company'] == by_id[mid]['company'], f'Provider/series mismatch: {mid}')
                require(s['category'] == assignment['category'], f'Category/series mismatch: {mid}')

    for model in models:
        mid = model['model_id']
        require(valid_date(model['release_date']), f'Invalid/future release date: {mid}')
        require(valid_date(model['verified_at']), f'Invalid verification date: {mid}')
        require(valid_url(model['release_source_url']), f'Missing release source: {mid}')
        require(model['release_kind'] in {'named_release', 'dated_snapshot'}, f'Invalid release kind: {mid}')
        incoming, outgoing = model['launch_input_usd_per_million'], model['launch_output_usd_per_million']
        require(bool(incoming) == bool(outgoing), f'Partially filled launch quote: {mid}')
        if outgoing:
            require(numeric(incoming) and numeric(outgoing, positive=True), f'Invalid launch quote: {mid}')
            require(valid_url(model['launch_price_source_url']), f'Missing launch-price source: {mid}')
            exact = [p for p in prices if p['model_id'] == mid and p['price_date'] == model['release_date']
                     and p['event_type'] in {'launch', 'snapshot'}]
            require(len(exact) == 1, f'Launch quote lacks an exact-date match: {mid}')
            if len(exact) == 1:
                require((incoming, outgoing) == (exact[0]['input_usd_per_million'], exact[0]['output_usd_per_million']),
                        f'Launch-price join changed a rate: {mid}')
        context = model['context_window_tokens']
        if context:
            require(numeric(context, positive=True, integer=True), f'Invalid context capacity: {mid}')
            require(valid_url(model['context_source_url']) and valid_date(model['context_spec_date']),
                    f'Missing context provenance: {mid}')
            require(model['context_definition'] in {'provider_context_window', 'provider_input_token_limit'},
                    f'Missing context definition: {mid}')

    for price in prices:
        pid, mid = price['price_id'], price['model_id']
        require(mid in by_id, f'Price references unknown model: {pid}')
        require(valid_date(price['price_date']) and valid_date(price['verified_at']), f'Invalid price date: {pid}')
        require(numeric(price['input_usd_per_million']) and numeric(price['output_usd_per_million'], positive=True),
                f'Invalid price rate: {pid}')
        require(valid_url(price['price_source_url']), f'Missing price source: {pid}')
        require(price['event_type'] in {'launch', 'price_change', 'promotion', 'snapshot', 'observation'},
                f'Unknown price event: {pid}')
        require(price['date_type'] in {'documented_event_date', 'observation_date', 'announced_rate_date'},
                f'Unknown date type: {pid}')
        require(price['price_basis'] in {'documented_quote', 'derived_from_provider_discount'}, f'Unknown price basis: {pid}')
        if mid in by_id:
            require(price['price_date'] >= by_id[mid]['release_date'], f'Price precedes model release: {pid}')

    # Regeneration equality also catches accidental manual edits to derived data.
    for name, expected in normalize(root).items():
        require(read_csv(root/'data'/name) == expected, f'{name} differs from normalized source records')
    if errors:
        raise ValueError('\n'.join(errors))
    return {'models': len(models), 'named_releases': sum(r['release_kind'] == 'named_release' for r in models),
            'price_observations': len(prices), 'context_values': sum(bool(r['context_window_tokens']) for r in models),
            'missing_launch_prices': [r['model_id'] for r in models if not r['launch_output_usd_per_million']],
            'missing_context_values': [r['model_id'] for r in models if not r['context_window_tokens']],
            'price_basis': dict(Counter(r['price_basis'] for r in prices))}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(validate(args.root), indent=2))
