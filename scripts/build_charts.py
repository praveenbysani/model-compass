"""Build two offline interactive HTML charts directly from normalized CSVs."""
from __future__ import annotations

import argparse
import calendar
import html
import json
import math
from datetime import date, timedelta
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline.offline import get_plotlyjs

from normalize_data import ROOT, read_csv
from validate_data import validate


def quarter_ends(start: date, end: date) -> list[str]:
    return [day.isoformat() for year in range(start.year, end.year + 1)
            for month in [3, 6, 9, 12]
            if start <= (day := date(year, month, calendar.monthrange(year, month)[1])) <= end]


def price_paths(root: Path, settings: dict) -> dict[str, list[dict]]:
    """Combine actual quotes with carried-forward quarter-end/latest selections.

    Sampling adds drawing anchors, not new evidence. Every derived anchor retains
    its original price date and source. Only exact priced named releases get dots.
    """
    models = {r['model_id']: r for r in read_csv(root/'data/models.csv')}
    assignments = {r['model_id']: r['series_id'] for r in read_csv(root/'data/model-categories.csv')}
    prices = read_csv(root/'data/price-history.csv')
    cutoff = date.fromisoformat(settings['as_of'])
    quarters = quarter_ends(min(date.fromisoformat(r['price_date']) for r in prices), cutoff)
    paths = {}
    for series in settings['series']:
        quotes = sorted([r for r in prices if assignments.get(r['model_id']) == series['id']
                         and r['price_date'] <= settings['as_of']], key=lambda r: (r['price_date'], r['price_id']))
        if not quotes:
            raise ValueError(f'No priced evidence for configured series {series["id"]}')
        dates = [r['price_date'] for r in quotes]
        if len(set(dates)) != len(dates):
            raise ValueError(f'Multiple selected versions on one date: {series["id"]}; resolve the path explicitly.')
        selected = {r['price_date']: {**r, 'plot_date': r['price_date'], 'point_kind': 'source_quote'} for r in quotes}
        for day in [*quarters, settings['as_of']]:
            earlier = [r for r in quotes if r['price_date'] <= day]
            if earlier and day not in selected:
                selected[day] = {**earlier[-1], 'plot_date': day,
                    'point_kind': 'latest_selection' if day == settings['as_of'] else 'quarterly_selection'}
        for row in selected.values():
            model = models[row['model_id']]
            row.update(model_name=model['model_name'], context_window_tokens=model['context_window_tokens'],
                       context_definition=model['context_definition'], context_spec_date=model['context_spec_date'],
                       release_source_url=model['release_source_url'])
            row['release_marker'] = model['release_kind'] == 'named_release' and row['event_type'] == 'launch' and (
                row['plot_date'] == row['price_date'] == model['release_date'])
        paths[series['id']] = sorted(selected.values(), key=lambda r: r['plot_date'])
    return paths


def trace_for(series: dict, rows: list[dict], view: str) -> dict:
    color = series['category_color'] if view == 'category' else series['company_color']
    name = series['company'] + ' · ' + series['label'] if view == 'category' else series['label']
    hover = []
    for row in rows:
        event = 'Model release' if row['release_marker'] else 'Price observation / selection'
        text = f'<b>{html.escape(row["model_name"])}</b><br>{event}: {row["plot_date"]}'
        text += f'<br>${row["output_usd_per_million"]} / 1M output tokens'
        text += f'<br>Source quote date: {row["price_date"]}<br>{html.escape(row["pricing_conditions"])}'
        if row['note']:
            text += '<br>' + html.escape(row['note'])
        hover.append(text)
    return {'x': [r['plot_date'] for r in rows], 'y': [float(r['output_usd_per_million']) for r in rows],
        'name': name, 'mode': 'lines+markers', 'showlegend': True, 'legendgroup': series['id'],
        'line': {'color': color, 'width': 2.5, 'dash': series['dash']},
        'marker': {'color': color, 'symbol': series['symbol'], 'size': [8 if r['release_marker'] else 0 for r in rows]},
        'customdata': [[r['model_name'], r['price_date'], r['point_kind'], r['release_marker'],
                       r['release_source_url'], r['price_source_url']] for r in rows],
        'hovertext': hover, 'hovertemplate': '%{hovertext}<extra></extra>'}


def panel_for(panel: dict, group: list[dict], paths: dict, settings: dict, view: str) -> dict:
    logarithmic = view == 'company'
    data = [trace_for(s, paths[s['id']], view) for s in group]
    owners, annotations = [], []
    selected_annotations = [a for a in settings['annotations'] if not a['endpoint']]
    selected_annotations += [{'series_id': s['id'], 'plot_date': settings['as_of'], 'endpoint': True}
                             for s in group if view == 'company' or s['id'] != 'openai-astra']
    for a in selected_annotations:
        indices = [i for i, s in enumerate(group) if s['id'] == a['series_id']]
        if not indices:
            continue
        owner = indices[0]
        row = next((r for r in paths[a['series_id']] if r['plot_date'] == a['plot_date']), None)
        if row is None:
            raise ValueError(f'Annotation has no plotted source: {a}')
        value = float(row['output_usd_per_million'])
        text = a.get('text')
        if a['endpoint']:
            qualifier = ' · introductory' if 'Introductory rate' in row['note'] else ''
            text = f'<b>{group[owner]["company"]} · {html.escape(row["model_name"])}</b><br>${value:g}{qualifier}'
        annotation = {'xref': 'x', 'yref': 'y', 'x': row['plot_date'],
            # Plotly log annotations use exponent coordinates; trace data stays in dollars.
            'y': math.log10(value) if logarithmic else value, 'text': text,
            'showarrow': True, 'arrowhead': 0, 'arrowwidth': .7, 'bgcolor': 'white',
            'arrowcolor': data[owner]['line']['color'], 'font': {'color': data[owner]['line']['color'], 'size': 14},
            'ax': 55 if a['endpoint'] else a.get('ax', 0), 'ay': 0 if a['endpoint'] else a.get('ay', -38)}
        if a['endpoint']:
            annotation['xanchor'] = 'left'
        annotations.append(annotation); owners.append(owner)
    first = min(date.fromisoformat(r['plot_date']) for rows in paths.values() for r in rows)
    cutoff = date.fromisoformat(settings['as_of'])
    ticks = [d for d in quarter_ends(first, cutoff) if d[5:7] in {'06', '12'}]
    if settings['as_of'] not in ticks:
        ticks.append(settings['as_of'])
    ticktext = [f'Q{(int(d[5:7])-1)//3+1} {d[:4]}' for d in ticks]
    ticktext[-1] = cutoff.strftime('%d %b %Y')
    yrange = settings['company_log_range'] if logarithmic else panel['range']
    yticks = settings['company_log_ticks'] if logarithmic else panel['ticks']
    layout = {'height': 650, 'margin': {'l': 100, 'r': 285, 't': 90, 'b': 70},
        'font': {'family': 'Arial', 'size': 15, 'color': '#242424'}, 'paper_bgcolor': 'white', 'plot_bgcolor': 'white',
        'annotations': annotations, 'showlegend': True, 'uirevision': panel['id'],
        'legend': {'orientation': 'h', 'x': 0, 'y': 1.17, 'xanchor': 'left', 'yanchor': 'top',
            'font': {'size': 15}, 'itemsizing': 'constant', 'itemclick': 'toggle', 'itemdoubleclick': 'toggleothers'},
        'xaxis': {'type': 'date', 'range': [(first-timedelta(days=22)).isoformat(), (cutoff+timedelta(days=61)).isoformat()],
            'domain': [0, 1], 'tickmode': 'array', 'tickvals': ticks, 'ticktext': ticktext, 'tickangle': 0,
            'tickfont': {'size': 14}, 'fixedrange': True, 'gridcolor': '#eff1f3', 'zeroline': False},
        'yaxis': {'type': 'log' if logarithmic else 'linear', 'range': yrange, 'domain': [0, 1],
            'tickmode': 'array', 'tickvals': yticks, 'ticktext': [f'${v:g}' for v in yticks],
            'tickfont': {'size': 14}, 'fixedrange': True, 'gridcolor': '#e6e9ed', 'zeroline': False,
            'title': {'text': 'USD / 1M output tokens', 'font': {'size': 14}, 'standoff': 18}}}
    go.Figure(data=data, layout=layout)
    return {**panel, 'base': {'data': data, 'layout': layout},
            'metadata': {'axes': ['y'], 'annotationOwners': owners}}


CSS = '''*{box-sizing:border-box}body{margin:0;background:white;color:#242424;font-family:Arial,sans-serif}
main{max-width:1440px;margin:auto;padding:36px 28px 44px}h1{font-size:34px;line-height:1.2;margin:0 0 40px}
.category{margin-bottom:60px}h2{font-size:29px;line-height:1.2;margin:0 0 6px}
.subtitle{font-size:18px;color:#62666b;line-height:1.4;margin:0 0 22px}
.take{background:#eef4fa;border:1px solid #dce7f1;color:#34495e;padding:20px 24px;margin-bottom:12px}
.take h3{font-size:20px;margin:0 0 8px}.take p{font-size:20px;line-height:1.45;margin:0}.take p+p{margin-top:14px}
.chart{width:100%;height:650px}.latest{display:flex;flex-wrap:wrap;gap:18px 30px;font-size:16px;line-height:1.5;padding:0 20px 10px 100px}
[hidden]{display:none!important}.notes{border-top:1px solid #e5e9ed;padding-top:24px;font-size:17px;line-height:1.5}
.notes h2{font-size:24px;margin-bottom:14px}.notes ul{margin:0;padding-left:22px}.notes li{margin-bottom:8px}
.sources{font-size:14px;color:#62666b;margin-top:20px}.sources summary{cursor:pointer}.sources a{color:#245cac;overflow-wrap:anywhere}
@media(max-width:600px){main{padding:24px 12px}h1{font-size:29px;margin-bottom:30px}h2{font-size:25px}.take{padding:18px}.latest{padding-left:80px}}'''


def page_html(root: Path, title: str, panels: list[dict], settings: dict, paths: dict) -> str:
    sections = []
    for panel in panels:
        take = ''
        if panel.get('take'):
            take = '<aside class="take"><h3>My take</h3>' + ''.join('<p>'+html.escape(t)+'</p>' for t in panel['take']) + '</aside>'
        summaries = []
        for i, t in enumerate(panel['base']['data']):
            row = paths[t['legendgroup']][-1]
            qualifier = ' · introductory' if 'Introductory rate' in row['note'] else ''
            summaries.append(f'<span data-family="{i}" style="color:{t["line"]["color"]}"><strong>{html.escape(row["api_provider"]+" · "+row["model_name"])}</strong><br>${float(row["output_usd_per_million"]):g}{qualifier}</span>')
        sections.append(f'<section class="category" aria-labelledby="heading-{panel["id"]}"><h2 id="heading-{panel["id"]}">{html.escape(panel["title"])}</h2><p class="subtitle">{html.escape(panel["subtitle"])}</p>{take}<div class="chart" id="chart-{panel["id"]}" aria-label="{html.escape(panel["title"])} output-price history"></div><div class="latest" id="latest-{panel["id"]}" hidden>{"".join(summaries)}</div></section>')
    urls = sorted({r[key] for rows in paths.values() for r in rows for key in ['price_source_url', 'release_source_url'] if r[key]})
    sources = ''.join(f'<li><a href="{html.escape(u, quote=True)}">{html.escape(u)}</a></li>' for u in urls)
    note_list = ''.join('<li>'+html.escape(n)+'</li>' for n in settings['notes'])
    cutoff = date.fromisoformat(settings['as_of']).strftime('%d %B %Y')
    payload = json.dumps({'panels': panels}, ensure_ascii=False).replace('</', '<\\/')
    controller = (root/'scripts/chart_interactions.js').read_text(encoding='utf-8')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{CSS}</style></head><body><main><h1>{html.escape(title)}</h1>{''.join(sections)}<section class="notes"><h2>Notes</h2><ul>{note_list}</ul><p>Data as of <strong>{cutoff}</strong>.</p><details class="sources"><summary>Sources</summary><ul>{sources}</ul></details></section></main><script>{get_plotlyjs()}</script><script>{controller}</script><script>const MODEL_COMPASS={payload};ModelCompass.mount(MODEL_COMPASS);</script></body></html>'''


def build(root: Path) -> dict:
    validate(root)
    settings = json.loads((root/'chart-settings.json').read_text(encoding='utf-8'))
    paths = price_paths(root, settings)
    category = [panel_for(c, [s for s in settings['series'] if s['category'] == c['title']], paths, settings, 'category')
                for c in settings['categories']]
    company = [panel_for({'id': name.lower(), 'title': name if name != 'Google' else 'Google · Gemini',
                        'subtitle': 'Shared logarithmic scale · selected family versions'},
                        [s for s in settings['series'] if s['company'] == name], paths, settings, 'company')
               for name in dict.fromkeys(s['company'] for s in settings['series'])]
    (root/'charts').mkdir(exist_ok=True)
    (root/'charts/category-linear.html').write_text(page_html(root, settings['category_title'], category, settings, paths), encoding='utf-8')
    (root/'charts/company-log.html').write_text(page_html(root, settings['company_title'], company, settings, paths), encoding='utf-8')
    (root/'index.html').write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ModelCompass</title><style>body{{font:18px/1.6 Arial,sans-serif;color:#242424;max-width:800px;margin:64px auto;padding:0 24px}}a{{color:#245cac}}h1{{line-height:1.2}}</style></head><body><h1>ModelCompass</h1><p>Open data for comparing AI model pricing, performance and quality.</p><p>This first release covers selected model releases and historical API prices, as of {date.fromisoformat(settings['as_of']).strftime('%d %B %Y')}.</p><ul><li><a href="charts/category-linear.html">Pricing by category · linear scale</a></li><li><a href="charts/company-log.html">Pricing by company · logarithmic scale</a></li><li><a href="data/models.csv">Model catalogue CSV</a></li><li><a href="data/price-history.csv">Price history CSV</a></li></ul><p>Benchmarks, quality signals, open-weight coverage, scheduled refreshes and alerts are planned.</p></body></html>''', encoding='utf-8')
    return {'curve_points': sum(len(r) for r in paths.values()),
            'release_markers': sum(r['release_marker'] for rows in paths.values() for r in rows),
            'category_panels': category, 'company_panels': company}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    result = build(args.root)
    print(json.dumps({k: result[k] for k in ['curve_points', 'release_markers']}))
