"""Attach the checked-in We-Solve destinations without consulting ranks or the network."""

import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
import warnings


BASE_DIR = Path(__file__).resolve().parents[1]
MAPPING_PATH = Path('lists/we_solve_links.json')


def _validate_url(url, kind):
    parsed = urlsplit(url)
    prefix = ('/we-solve/research/blob/main/' if kind == 'source'
              else '/problems/' if kind == 'problem' else '/contributions/')
    host = 'github.com' if kind == 'source' else 'we-solve.github.io'
    if (parsed.scheme != 'https' or parsed.netloc != host
            or not parsed.path.startswith(prefix) or parsed.query or parsed.fragment
            or any(part in {'.', '..'} for part in unquote(parsed.path).split('/'))):
        raise ValueError(f'Invalid We-Solve {kind} URL: {url!r}')


def load_mapping(base_dir=BASE_DIR):
    path = Path(base_dir) / MAPPING_PATH
    if not path.exists():
        # Isolated catalogues and new collections can still build before mapping.
        return {'schema_version': 1, 'problems': {}, 'sources': {}}
    mapping = json.loads(path.read_text(encoding='utf-8'))
    if (mapping.get('schema_version') != 1
            or not isinstance(mapping.get('problems'), dict)
            or not isinstance(mapping.get('sources'), dict)):
        raise ValueError('Unsupported We-Solve link mapping')
    for key, entry in mapping['problems'].items():
        if not re.fullmatch(r'WS-[1-9][0-9]*', entry['code']):
            raise ValueError(f'Invalid permanent We-Solve code for {key}')
        if 'record_code' in entry and not re.fullmatch(r'WS-[1-9][0-9]*', entry['record_code']):
            raise ValueError(f'Invalid original We-Solve record code for {key}')
        _validate_url(entry['url'], 'problem')
        if entry.get('source_url'):
            _validate_url(entry['source_url'], 'source')
    for entry in mapping['sources'].values():
        _validate_url(entry['url'], 'contribution')
        if entry.get('source_url'):
            _validate_url(entry['source_url'], 'source')
    return mapping


def _source_current(base_dir, path, digest):
    if not digest:
        return True
    source = Path(base_dir) / path
    if source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest() == digest:
        return True
    warnings.warn(f'We-Solve source mapping needs updating for {path}; keeping its local source link.',
                  RuntimeWarning, stacklevel=3)
    return False


def attach_we_solve_links(problems, category, base_dir=BASE_DIR):
    """Add navigation metadata while leaving identities and manuscript content intact.

    Unmapped records retain their existing sources. A changed manuscript must be
    remapped before its source/review control can identify a We-Solve revision.
    """
    mapping = load_mapping(base_dir)
    for key, problem in problems.items():
        lookup = f'{category}:{key}'
        if category == 'open_problems' and str(key).startswith('mo:'):
            lookup = str(key)
        entry = mapping['problems'].get(lookup)
        if entry:
            public = {field: entry[field] for field in
                      ('code', 'record_code', 'alias', 'problem_id', 'canonical_alias',
                       'canonical_problem_id', 'url', 'source_url') if field in entry}
            if entry.get('source_path') and not _source_current(
                    base_dir, entry['source_path'], entry.get('local_sha256')):
                public.pop('source_url', None)
            problem['we_solve'] = public
        else:
            problem.pop('we_solve', None)
        for attack in problem.get('attacks', []):
            path = attack.get('file_path', '')
            source = mapping['sources'].get(path)
            if source and _source_current(base_dir, path, source.get('local_sha256')):
                attack['we_solve'] = {field: source[field] for field in
                                     ('alias', 'revision', 'url', 'source_url') if field in source}
            else:
                attack.pop('we_solve', None)
    return problems
