#!/usr/bin/env python3
"""Build the Economics catalogue without deriving permanent IDs from current ranks.

The registry owns identity and statements; rankings.csv owns the mutable order.
The standalone catalogue command also builds model/version research attempts.
"""

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit


BASE_DIR = Path(__file__).resolve().parents[1]
REGISTRY_PATH = Path('lists/economics/problems.json')
RANKINGS_PATH = Path('lists/economics/rankings.csv')
JEL_CODES_PATH = Path('lists/economics/jel_codes.json')
STATEMENTS_PATH = Path('attacks/open_problems/economics/statements')
PUBLIC_STATEMENTS_PATH = Path('docs/data/economics/statements')
ATTEMPTS_PATH = Path('attacks/open_problems/economics')
PUBLIC_ATTEMPTS_PATH = Path('docs/data/economics/attempts')
HUMAN_CONTRIBUTIONS_PATH = Path('lists/economics/human_contributions.json')
STATEMENT_START = '% BEGIN ECONOMICS STATEMENT\n'
STATEMENT_END = '% END ECONOMICS STATEMENT'
ID_RE = re.compile(r'[A-Z][0-9]{2}-[1-9][0-9]*')
MODEL_LABELS = {
    'gpt_6_astra_pro': 'GPT 6 Astra Pro',
    'gpt6_astra_ultra': 'GPT 6 Astra Ultra',
    'gpt_6_astra_ultra': 'GPT 6 Astra Ultra',
    'opus_5.5_high': 'Claude Opus 5.5 High',
}


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


def load_economics_human_contributions(base_dir, records):
    """Validate attribution and immutable originals separately from LLM claims."""
    base_dir = Path(base_dir)
    manifest_path = base_dir / HUMAN_CONTRIBUTIONS_PATH
    if not manifest_path.exists():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or not isinstance(manifest.get('contributions'), list):
        raise ValueError('Unsupported Economics human contribution manifest')
    registered = {record['id'] for record in records}
    result = {}
    for entry in manifest['contributions']:
        if not isinstance(entry, dict):
            raise ValueError('Invalid Economics human contribution record')
        identifier, filename = entry.get('problem_id'), entry.get('filename')
        if (identifier not in registered or not isinstance(filename, str)
                or not re.fullmatch(re.escape(identifier) + r'(?:_v(?:[2-9]|[1-9][0-9]+))?\.tex', filename)
                or filename in result):
            raise ValueError('Invalid or duplicate Economics human contribution identity')
        for key in ('author', 'submitted_by', 'scope', 'ai_use', 'verification'):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError(f'Missing human contribution {key}: {filename}')
        posted = entry.get('first_posted')
        if not isinstance(posted, str) or date.fromisoformat(posted).isoformat() != posted:
            raise ValueError(f'Invalid human contribution date: {filename}')
        if entry.get('review_status') != 'submitted':
            raise ValueError('Human contribution imports must remain submitted')
        for key in ('submission_url', 'original_source'):
            url = urlsplit(entry.get(key, ''))
            if url.scheme != 'https' or url.netloc != 'github.com' or url.username or url.password:
                raise ValueError(f'Invalid human contribution {key}: {filename}')
        if not re.fullmatch(r'/mehmetmars7/Erdosproblems-llm-hunter/pull/[1-9][0-9]*',
                            urlsplit(entry['submission_url']).path):
            raise ValueError(f'Invalid human contribution submission URL: {filename}')
        if not re.fullmatch(r'/[\w.-]+/[\w.-]+/tree/[0-9a-f]{40}',
                            urlsplit(entry['original_source']).path):
            raise ValueError(f'Human contribution source must be commit-pinned: {filename}')
        path = base_dir / ATTEMPTS_PATH / 'Human_Contribution' / filename
        if (path.is_symlink() or not path.resolve().is_relative_to(base_dir.resolve())
                or not path.is_file()):
            raise ValueError(f'Missing or unsafe human contribution file: {filename}')
        digest = entry.get('tex_sha256', '')
        if (not re.fullmatch(r'[0-9a-f]{64}', digest)
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError(f'Human contribution checksum mismatch: {filename}')
        result[filename] = entry
    return result


def load_economics_attempts(base_dir, records):
    """Join model/version writeups by permanent ID, never legacy OP ID or rank."""
    base_dir = Path(base_dir)
    by_id = {record['id']: record for record in records}
    attempts = {problem_id: [] for problem_id in by_id}
    human_contributions = load_economics_human_contributions(base_dir, records)
    filename = re.compile(r'([A-Z][0-9]{2}-[1-9][0-9]*)(?:_v([1-9][0-9]*))?\.tex')
    for directory in sorted((base_dir / ATTEMPTS_PATH).glob('*')):
        if not directory.is_dir() or directory.name in {'statements', 'definitions'}:
            continue
        for path in sorted(directory.glob('*.tex')):
            match = filename.fullmatch(path.name)
            if not match or (match[2] is not None and int(match[2]) < 2):
                raise ValueError(f'Invalid Economics attempt filename: {path.name}')
            problem_id, version = match[1], int(match[2] or 1)
            if problem_id not in by_id:
                raise ValueError(f'Unknown Economics attempt ID: {problem_id}')
            content = path.read_text(encoding='utf-8')
            human = human_contributions.get(path.name) if directory.name == 'Human_Contribution' else None
            if directory.name == 'Human_Contribution':
                if human is None:
                    raise ValueError(f'Unregistered Economics human contribution: {path.name}')
                metadata = by_id[problem_id]
                status, posted = 'unresolved', human['first_posted']
            else:
                header = re.findall(r'^% ECONOMICS_PROBLEM: (.+)$', content, re.M)
                if len(header) != 1:
                    raise ValueError(f'Missing or repeated Economics attempt identity: {path.name}')
                metadata = json.loads(header[0])
                for field in ('id', 'title', 'jel_code', 'source_id'):
                    if metadata.get(field) != by_id[problem_id][field]:
                        raise ValueError(f'Economics attempt {field} mismatch: {path.name}')
                statuses = re.findall(r'^% ATTEMPT_STATUS: (.+)$', content, re.M)
                if len(statuses) != 1 or statuses[0] not in {'unresolved', 'partial', 'solved'}:
                    raise ValueError(f'Missing or invalid Economics ATTEMPT_STATUS: {path.name}')
                dates = re.findall(r'^% FIRST_POSTED: (.+)$', content, re.M)
                if len(dates) != 1 or date.fromisoformat(dates[0]).isoformat() != dates[0]:
                    raise ValueError(f'Missing or invalid Economics FIRST_POSTED: {path.name}')
                status, posted = statuses[0], dates[0]
            if content.count(r'\begin{document}') != 1 or content.count(r'\end{document}') != 1:
                raise ValueError(f'Expected one complete Economics attempt: {path.name}')
            preamble, body = content.split(r'\begin{document}', 1)
            body, trailing = body.split(r'\end{document}', 1)
            if trailing.strip() or not body.strip():
                raise ValueError(f'Invalid Economics attempt document: {path.name}')
            # Reuse the site's existing read-only parser and document-local notation
            # expansion. The late import avoids the builder's catalogue import cycle.
            if str(BASE_DIR) not in sys.path:
                sys.path.insert(0, str(BASE_DIR))
            from build_site import (expand_tex_notation, parse_attack,
                                    replace_tex_command, tex_notation_macros)
            titles = []
            replace_tex_command(preamble, 'title', 1, lambda title: titles.append(title) or '')
            if titles:
                # PDF title spacing and font sizes must not become display math
                # or raw commands inside the website's section heading.
                titles[0] = re.sub(r'\\\\(?:\[[^\]]*\])?', ' ', titles[0])
                titles[0] = re.sub(r'\\(?:large|Large|LARGE|huge|Huge|small|normalsize)\b', '', titles[0])
                titles[0] = ' '.join(titles[0].split())
            body = body.replace(r'\maketitle', r'\section*{' + titles[0] + '}' if titles else '')
            body = re.sub(r'\\(?:tableofcontents|appendix|clearpage)\b', '', body)
            body = body.replace(r'\begin{abstract}', r'\subsection*{Abstract}').replace(r'\end{abstract}', '')
            body = re.sub(r'\\(?:begingroup|endgroup)\b', '', body)
            body = replace_tex_command(body, 'vspace', 1, lambda *args: '')
            body = replace_tex_command(body, 'setlength', 2, lambda *args: '')
            body = replace_tex_command(body, 'addcontentsline', 3, lambda *args: '')
            body = expand_tex_notation(body, tex_notation_macros(preamble, {}))
            attack = parse_attack('% ATTEMPT_STATUS: ' + status + '\n' + body.strip(),
                                  (human['author'] + ' (human contribution)') if human else
                                  MODEL_LABELS.get(directory.name, directory.name.replace('_', ' ')),
                                  posted,
                                  metadata_content=content)
            # A full solution claim implies full completion even when the
            # manuscript has no numeric estimate or states a lower one.
            if attack['status'] == 'solved':
                attack['completion'] = 100
            attack.update(version=version, entry_kind='research_attempt',
                          file_path=path.relative_to(base_dir).as_posix(),
                          download_url=(PUBLIC_ATTEMPTS_PATH / directory.name / path.name)
                          .relative_to('docs').as_posix())
            if human:
                attack.update(entry_kind='human_contribution', status='unresolved',
                              author=human['author'], review_status='submitted',
                              submission_url=human['submission_url'],
                              contribution_scope=human['scope'], ai_use=human['ai_use'],
                              verification=human['verification'])
                attack.pop('completion', None)
            attempts[problem_id].append(attack)
    for records in attempts.values():
        records.sort(key=lambda attack: (attack['model'], attack['version']))
    return attempts


def build_economics_data(base_dir=BASE_DIR):
    """Return window.ECONOMICS_DATA records (read-only; works offline)."""
    base_dir = Path(base_dir)
    registry = load_registry(base_dir)
    records = registry['problems']
    rankings = read_ranking_csv(base_dir / RANKINGS_PATH, records)
    attempts = load_economics_attempts(base_dir, records)
    data = {}
    for record in sorted(records, key=lambda record: rankings[record['id']]):
        problem_id = record['id']
        statement_path = base_dir / record['statement_file']
        content = statement_path.read_text(encoding='utf-8')
        body = extract_statement(content)
        llm_attempts = [attack for attack in attempts[problem_id]
                        if attack.get('entry_kind') != 'human_contribution']
        data[problem_id] = {
            'id': problem_id,
            'title': record['title'],
            'jel_code': record['jel_code'],
            'domain_label': 'Game theory' if record.get('source_catalog') == 'Game theory' else 'Economics',
            'status': 'open',
            'llm_status': ('solved' if any(attack['status'] == 'solved' for attack in llm_attempts)
                           else 'unresolved' if llm_attempts else 'none'),
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
            'attacks': attempts[problem_id],
        }
        # As with resolved Erdos records, full resolution takes precedence
        # over numeric estimates. Here it is explicitly an LLM claim; retain
        # the source-catalogue status separately from the displayed status.
        if data[problem_id]['llm_status'] == 'solved':
            data[problem_id].update(source_status='open', status='solved',
                                    status_source='llm_claim', completion=100,
                                    completion_source='llm_claim')
            continue
        # Unresolved attempts use the highest stated estimate across models
        # and versions, leaving absent estimates unset.
        completions = [attack['completion'] for attack in llm_attempts
                       if type(attack.get('completion')) in (int, float)]
        if completions:
            data[problem_id]['completion'] = max(completions)
            data[problem_id]['completion_source'] = 'llm'
    return data


def generate_economics_data(base_dir=BASE_DIR, data_dir=None):
    """Validate, then write embedded JS data and local downloadable TeX copies.

    root build_site.py calls this function with no arguments. The optional
    paths make isolated tests and preview packages straightforward.
    """
    base_dir = Path(base_dir)
    data_dir = Path(data_dir) if data_dir is not None else base_dir / 'docs/data'
    data = build_economics_data(base_dir)
    # Support both the root build and this module's standalone command.
    if __package__:
        from .we_solve_links import attach_we_solve_links
    else:
        from we_solve_links import attach_we_solve_links
    attach_we_solve_links(data, 'economics', base_dir)
    classification = json.loads((base_dir / JEL_CODES_PATH).read_text(encoding='utf-8'))
    if classification.get('schema_version') != 1 or not isinstance(classification.get('labels'), dict):
        raise ValueError('Unsupported JEL classification format')
    labels = classification['labels']
    used_codes = sorted({record['jel_code'] for record in data.values()})
    for code in used_codes:
        if not isinstance(labels.get(code), str) or not labels[code].strip():
            raise ValueError(f'Missing JEL description for {code}')
    # Store each description once, alongside the already-loaded catalogue data.
    jel_labels = json.dumps({code: labels[code] for code in used_codes}, ensure_ascii=False,
                            indent=2).replace('</', '<\\/')
    serialized = json.dumps(data, ensure_ascii=False, indent=2).replace('</', '<\\/')
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / 'economics_data.js').write_text(
        '// Generated from fixed Economics identities and mutable rankings.\n'
        'window.ECONOMICS_JEL_LABELS = ' + jel_labels + ';\n'
        'window.ECONOMICS_DATA = ' + serialized + ';\n', encoding='utf-8')
    download_dir = data_dir / 'economics/statements'
    download_dir.mkdir(parents=True, exist_ok=True)
    for problem_id, record in data.items():
        (download_dir / f'{problem_id}.tex').write_bytes(
            (base_dir / record['definitionFile']).read_bytes())
    for record in data.values():
        for attack in record['attacks']:
            destination = data_dir.parent / attack['download_url']
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((base_dir / attack['file_path']).read_bytes())
    return data


if __name__ == '__main__':
    catalogue = generate_economics_data()
    print(f'Generated {len(catalogue)} Economics statements')
