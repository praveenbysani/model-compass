"""Normalize curated source records; never infer launch prices from later quotes."""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as stream:
        return [{key: value.strip() for key, value in row.items()}
                for row in csv.DictReader(stream)]


def canonical_name(name: str) -> str:
    # Cut/promotion labels describe price events, not new model identities.
    name = re.sub(r'\s+', ' ', name.strip())
    name = re.sub(r' (price cut|promotion)$', '', name)
    name = name.replace(' (December rate)', '')
    # Preserve these distinct snapshots rather than folding them into aliases.
    return name.replace('GPT-4o (Aug snapshot)', 'GPT-4o 2024-08-06').replace(
        'Sonnet 3.5 upgraded', 'Sonnet 3.5 2024-10-22')


def model_id(company: str, name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', canonical_name(name).lower()).strip('-')
    return re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-') + '/' + slug


def number(value: str) -> str:
    if not value:
        return ''
    amount = Decimal(value)
    if not amount.is_finite() or amount < 0:
        raise ValueError(f'Invalid nonnegative numeric value: {value}')
    return format(amount.normalize(), 'f')


def iso_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def csv_text(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def unique(rows: list[dict[str, str]], fields: tuple[str, ...]) -> list[dict[str, str]]:
    """Collapse identical duplicates and reject competing facts at the same key."""
    seen = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in seen and seen[key] != row:
            raise ValueError(f'Conflicting source records for {key}')
        seen[key] = row
    return list(seen.values())


def normalize(root: Path) -> dict[str, list[dict[str, str]]]:
    sources = root / 'data/sources'
    settings = json.loads((root / 'chart-settings.json').read_text(encoding='utf-8'))
    verified = iso_date(settings['as_of'])
    releases = unique(read_csv(sources / 'releases.csv'), ('provider', 'model'))
    quotes = unique(read_csv(sources / 'price-observations.csv'), ('provider', 'model', 'date'))
    contexts = unique(read_csv(sources / 'context-observations.csv'), ('company', 'model'))
    assignments = unique(read_csv(root / 'data/model-categories.csv'), ('model_id',))
    categories = {r['model_id']: r for r in assignments}

    catalogue = {}
    for release in releases:
        mid = model_id(release['provider'], release['model'])
        if mid in catalogue:
            raise ValueError(f'Model ID collision: {mid}')
        catalogue[mid] = {
            'model_id': mid, 'company': release['provider'], 'category': categories.get(mid, {}).get('category', ''),
            'family': release['family'], 'model_name': canonical_name(release['model']),
            'release_date': iso_date(release['date']), 'release_kind': 'named_release',
            'launch_input_usd_per_million': '', 'launch_output_usd_per_million': '',
            'launch_price_basis': '', 'context_window_tokens': '', 'context_definition': '',
            'context_spec_date': '', 'release_source_url': release['source'],
            'launch_price_source_url': '', 'context_source_url': '', 'verified_at': verified, 'notes': '',
        }

    history = []
    for quote in quotes:
        mid = model_id(quote['provider'], quote['model'])
        price_date = iso_date(quote['date'])
        if mid not in catalogue:
            if quote['event'] != 'snapshot':
                raise ValueError(f'Price quote has no documented model release: {mid}')
            catalogue[mid] = {
                'model_id': mid, 'company': quote['provider'], 'category': categories.get(mid, {}).get('category', ''),
                'family': quote['family'], 'model_name': canonical_name(quote['model']),
                'release_date': price_date, 'release_kind': 'dated_snapshot',
                'launch_input_usd_per_million': '', 'launch_output_usd_per_million': '',
                'launch_price_basis': '', 'context_window_tokens': '', 'context_definition': '',
                'context_spec_date': '', 'release_source_url': quote['price_source'],
                'launch_price_source_url': '', 'context_source_url': '', 'verified_at': verified,
                'notes': 'Dated snapshot; excluded from selected named-release marker counts.',
            }
        model = catalogue[mid]
        event = {'release': 'launch', 'cut': 'price_change', 'snapshot': 'snapshot',
                 'observation': 'observation'}[quote['event']]
        if 'promotion' in quote['model']:
            event = 'promotion'
        basis = 'derived_from_provider_discount' if 'recovered from the exact 80%' in quote['note'] else 'documented_quote'
        conditions = 'Standard text API, short-prompt base tier; excludes caching, batch, tools and enterprise discounts.'
        if mid == 'anthropic/haiku-5-5':
            conditions += ' Prompts up to 100000 input tokens; larger prompts have different rates.'
        if 'Introductory rate' in quote['note'] or 'promotional rate' in quote['note']:
            conditions += ' Promotional rate; see note for the documented schedule.'
        date_type = 'observation_date' if event == 'observation' else 'documented_event_date'
        if 'billing began' in quote['note']:
            date_type = 'announced_rate_date'
        record = {
            'price_id': mid + '@' + price_date, 'model_id': mid, 'api_provider': quote['provider'],
            'price_date': price_date, 'date_type': date_type,
            'input_usd_per_million': number(quote['input_usd_per_million']),
            'output_usd_per_million': number(quote['output_usd_per_million']),
            'event_type': event, 'price_basis': basis, 'pricing_conditions': conditions,
            'price_source_url': quote['price_source'], 'verified_at': verified,
            'source_model_name': quote['model'], 'note': quote['note'],
        }
        history.append(record)
        # An exact-date join is intentional. A later observation cannot fill a
        # missing launch quote, even if the price happens to be unchanged.
        if price_date == model['release_date'] and event in {'launch', 'snapshot'}:
            model.update(launch_input_usd_per_million=record['input_usd_per_million'],
                         launch_output_usd_per_million=record['output_usd_per_million'],
                         launch_price_basis=basis, launch_price_source_url=record['price_source_url'])

    for context in contexts:
        mid = model_id(context['company'], context['model'])
        if mid not in catalogue:
            raise ValueError(f'Context specification has no model: {mid}')
        catalogue[mid].update(context_window_tokens=number(context['context_window_tokens']),
            context_definition=context['context_definition'], context_spec_date=iso_date(context['spec_date']),
            context_source_url=context['source_url'])
        catalogue[mid]['notes'] = ' '.join(filter(None, [catalogue[mid]['notes'], context['note']]))

    for model in catalogue.values():
        missing = []
        if not model['launch_output_usd_per_million']:
            missing.append('Launch price unverified in the retained evidence.')
        if not model['context_window_tokens']:
            missing.append('Context capacity unverified in the exact-version sources checked.')
        model['notes'] = ' '.join(filter(None, [model['notes'], *missing]))
    history = unique(history, ('price_id',))
    return {'models.csv': sorted(catalogue.values(), key=lambda r: r['model_id']),
            'price-history.csv': sorted(history, key=lambda r: (r['api_provider'], r['price_date'], r['model_id']))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Repository root; defaults to this script’s parent.')
    parser.add_argument('--check', action='store_true', help='Check committed outputs without rewriting them.')
    args = parser.parse_args()
    outputs = normalize(args.root)
    for filename, rows in outputs.items():
        path, text = args.root / 'data' / filename, csv_text(rows)
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != text:
                raise SystemExit(f'{filename} is out of date; run normalize_data.py.')
        else:
            path.write_text(text, encoding='utf-8')
        print(f'{filename}: {len(rows)} records')


if __name__ == '__main__':
    main()
