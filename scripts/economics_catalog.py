#!/usr/bin/env python3
"""Build the Economics catalogue without deriving permanent IDs from current ranks.

The registry owns identity and statements; rankings.csv owns the mutable order.
This module deliberately does not depend on the full-site builder.
"""

import csv
import json
from pathlib import Path
import re


BASE_DIR = Path(__file__).resolve().parents[1]
REGISTRY_PATH = Path('lists/economics/problems.json')
RANKINGS_PATH = Path('lists/economics/rankings.csv')
STATEMENTS_PATH = Path('attacks/open_problems/economics/statements')
PUBLIC_STATEMENTS_PATH = Path('docs/data/economics/statements')
STATEMENT_START = '% BEGIN ECONOMICS STATEMENT\n'
STATEMENT_END = '% END ECONOMICS STATEMENT'
ID_RE = re.compile(r'[A-Z][0-9]{2}-[1-9][0-9]*')


def load_registry(base_dir=BASE_DIR):
    base_dir = Path(base_dir)
    registry = json.loads((base_dir / REGISTRY_PATH).read_text(encoding='utf-8'))
    if registry.get('schema_version') != 1 or not isinstance(registry.get('problems'), list):
        raise ValueError('Unsupported Economics registry format')
    records = registry['problems']
    if not records or registry.get('problem_count') != len(records):
        raise ValueError('Economics registry count does not match its records')
    seen = set()
    source_keys = set()
    initial_ranks = []
    for record in records:
        problem_id = record.get('id', '')
        initial_rank = record.get('initial_rank')
        if (not isinstance(problem_id, str) or not ID_RE.fullmatch(problem_id)
                or type(initial_rank) is not int or initial_rank < 1
                or problem_id != f"{record.get('jel_code')}-{initial_rank}"):
            raise ValueError(f'Invalid permanent Economics identity: {problem_id!r}')
        if problem_id in seen:
            raise ValueError(f'Duplicate permanent Economics identity: {problem_id}')
        seen.add(problem_id)
        initial_ranks.append(initial_rank)
        key = (record.get('source_id'), record.get('title'), record.get('jel_code'))
        if key in source_keys:
            raise ValueError(f'Duplicate Economics source identity: {key}')
        source_keys.add(key)
        if not all(isinstance(record.get(field), str) and record[field].strip()
                   for field in ('title', 'jel_code', 'source_id')):
            raise ValueError(f'Missing Economics metadata for {problem_id}')
        expected_file = str(STATEMENTS_PATH / f'{problem_id}.tex')
        if record.get('statement_file') != expected_file:
            raise ValueError(f'Invalid statement path for {problem_id}')
    validate_rank_values(initial_ranks, len(records))
    for record in records:
        aliases = record.get('reference_aliases', {})
        if not isinstance(aliases, dict) or any(
                not re.fullmatch(r'problem:OP-\d{4}', key) or target not in seen
                for key, target in aliases.items()):
            raise ValueError(f"Invalid verified reference alias for {record['id']}")
    return registry


def validate_rank_values(ranks, count):
    if any(type(rank) is not int or rank < 1 for rank in ranks):
        raise ValueError('New rank must be a positive integer')
    if len(ranks) != count:
        raise ValueError(f'Ranking coverage must contain all {count} problems')
    if len(set(ranks)) != count:
        raise ValueError('New rank values must be unique')
    if set(ranks) != set(range(1, count + 1)):
        raise ValueError(f'New rank values must be contiguous from 1 to {count}')


def normalize_title(value):
    """Normalize harmless Unicode and whitespace differences, never wording."""
    import unicodedata
    return ' '.join(unicodedata.normalize('NFKC', value).split())


def read_ranking_csv(path, records, allow_source_ids=False):
    """Return fixed-ID -> current rank after complete, unambiguous validation.

    Permanent IDs are preferred. Legacy OP IDs need title and JEL when an ID
    was reused by the source; no row is silently resolved by current rank.
    """
    by_id = {record['id']: record for record in records}
    by_source = {}
    for record in records:
        by_source.setdefault(record['source_id'], []).append(record)
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        if 'Problem ID' not in headers or 'New rank' not in headers:
            raise ValueError('Ranking CSV requires Problem ID and New rank columns')
        rows = list(reader)
    result = {}
    for row_number, row in enumerate(rows, 2):
        identifier = (row.get('Problem ID') or '').strip()
        title = (row.get('Problem title') or '').strip()
        jel = (row.get('JEL code') or '').strip()
        if identifier in by_id:
            record = by_id[identifier]
        elif allow_source_ids and identifier in by_source:
            candidates = by_source[identifier]
            if title:
                candidates = [record for record in candidates
                              if normalize_title(record['title']) == normalize_title(title)]
            if jel:
                candidates = [record for record in candidates if record['jel_code'] == jel]
            if len(candidates) != 1:
                raise ValueError(f'Row {row_number}: ambiguous source Problem ID {identifier}; '
                                 'use its permanent ID or matching Problem title and JEL code')
            record = candidates[0]
        else:
            raise ValueError(f'Row {row_number}: unknown Problem ID {identifier!r}')
        problem_id = record['id']
        if title and normalize_title(title) != normalize_title(record['title']):
            raise ValueError(f'Row {row_number}: title mismatch for {problem_id}')
        if jel and jel != record['jel_code']:
            raise ValueError(f'Row {row_number}: JEL code mismatch for {problem_id}')
        value = (row.get('New rank') or '').strip()
        if not re.fullmatch(r'[1-9][0-9]*', value):
            raise ValueError(f'Row {row_number}: New rank must be a positive integer')
        if problem_id in result:
            raise ValueError(f'Row {row_number}: duplicate Problem ID {problem_id}')
        result[problem_id] = int(value)
    missing = sorted(set(by_id) - set(result))
    if missing:
        raise ValueError('Ranking coverage is incomplete; missing: ' + ', '.join(missing))
    validate_rank_values(list(result.values()), len(records))
    return result


def ranking_csv_text(records, rankings):
    import io
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['Problem ID', 'New rank', 'Problem title', 'JEL code'])
    for record in sorted(records, key=lambda record: rankings[record['id']]):
        writer.writerow([record['id'], rankings[record['id']], record['title'], record['jel_code']])
    return stream.getvalue()


def extract_statement(content):
    if content.count(STATEMENT_START) != 1 or content.count(STATEMENT_END) != 1:
        raise ValueError('Statement file must contain one Economics statement boundary pair')
    body = content.split(STATEMENT_START, 1)[1].split(STATEMENT_END, 1)[0].strip()
    if not body or not re.search(r'\\subsection\*?\s*\{', body):
        raise ValueError('Economics statement has no substantive subsection')
    if re.search(r'\\label\{difficulty-rank:', body) or '\\ProblemClassification' in body:
        raise ValueError('Economics statement contains obsolete classification/rank metadata')
    return body


def build_economics_data(base_dir=BASE_DIR):
    """Return window.ECONOMICS_DATA records (read-only; works offline)."""
    base_dir = Path(base_dir)
    registry = load_registry(base_dir)
    records = registry['problems']
    rankings = read_ranking_csv(base_dir / RANKINGS_PATH, records)
    data = {}
    for record in sorted(records, key=lambda record: rankings[record['id']]):
        problem_id = record['id']
        statement_path = base_dir / record['statement_file']
        content = statement_path.read_text(encoding='utf-8')
        body = extract_statement(content)
        data[problem_id] = {
            'id': problem_id,
            'title': record['title'],
            'jel_code': record['jel_code'],
            'rank': rankings[problem_id],
            'source_id': record['source_id'],
            'source_catalog': record.get('source_catalog'),
            'source_original_id': record.get('source_original_id'),
            'source_metadata': record.get('source_metadata', {}),
            'source_labels': record.get('source_labels', []),
            'reference_aliases': record.get('reference_aliases', {}),
            'definition_tex': body,
            'definitionFile': record['statement_file'],
            'definition_file': record['statement_file'],
            'statement_url': f'data/economics/statements/{problem_id}.tex',
            'entry_kind': 'statement_only',
            'attacks': [],
        }
    return data


def generate_economics_data(base_dir=BASE_DIR, data_dir=None):
    """Validate, then write embedded JS data and local downloadable TeX copies.

    root build_site.py calls this function with no arguments. The optional
    paths make isolated tests and preview packages straightforward.
    """
    base_dir = Path(base_dir)
    data_dir = Path(data_dir) if data_dir is not None else base_dir / 'docs/data'
    data = build_economics_data(base_dir)
    serialized = json.dumps(data, ensure_ascii=False, indent=2).replace('</', '<\\/')
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / 'economics_data.js').write_text(
        '// Generated from fixed Economics identities and mutable rankings.\n'
        'window.ECONOMICS_DATA = ' + serialized + ';\n', encoding='utf-8')
    download_dir = data_dir / 'economics/statements'
    download_dir.mkdir(parents=True, exist_ok=True)
    for problem_id, record in data.items():
        (download_dir / f'{problem_id}.tex').write_bytes(
            (base_dir / record['definitionFile']).read_bytes())
    return data


if __name__ == '__main__':
    catalogue = generate_economics_data()
    print(f'Generated {len(catalogue)} Economics statements')
