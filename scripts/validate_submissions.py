#!/usr/bin/env python3
"""Prospective submission structure/identity checks, never proof verification.

Explicit paths are strict. --base REF checks changed/untracked submissions only and
protects historical identity; unchanged manuscripts keep their legacy conventions.
No TeX execution or external source/code fetching is performed.
"""
import argparse
import csv
from datetime import date
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_site import (declared_attempt_status, extract_completion,
                        parse_numbered_problem_tex, parse_openai_claim,
                        validate_open_problems_catalog)
from scripts.economics_catalog import (extract_statement, load_registry,
                                       read_ranking_csv)
from scripts.import_economics import braced_argument

PREFIX = 'attacks/open_problems/'
CATEGORIES = {'erdos', 'top_problems', 'mo', 'economics'}
TOP_REGISTRY = 'lists/unsolvedmath/problems.json'
ECON_REGISTRY = 'lists/economics/problems.json'
REGISTRY_FILES = {TOP_REGISTRY, ECON_REGISTRY, 'lists/unsolvedmath/display_order.json',
                  'lists/economics/rankings.csv', 'lists/erdos_problems.csv',
                  'lists/erdos_status.json', 'lists/mo_problems.csv'}
# Three pre-policy identical CSV repetitions, retained without rewriting history.
LEGACY_MO_DUPLICATE_COUNTS = {'339137': 2, '377545': 2, '185834': 2}
LITERALS = {'verbatim', 'verbatim*', 'Verbatim', 'lstlisting', 'minted', 'comment'}
GENERIC_MODELS = {'gpt', 'chatgpt', 'claude', 'gemini', 'opus', 'gpt codex'}


def scan_tex(content):
    """Mask comments and literal code, preserving offsets/newlines for diagnostics.

    Collect actual leading metadata comments, never examples inside literal code.
    This is lexical inspection, not a TeX engine (macros/conditionals aren't run).
    """
    output = list(content)
    headers = {}
    index = 0
    in_document = False

    def mask(start, end):
        for pos in range(start, end):
            if output[pos] not in '\r\n':
                output[pos] = ' '

    while index < len(content):
        if content[index] == '%':
            end = content.find('\n', index)
            end = len(content) if end < 0 else end
            prefix = content[content.rfind('\n', 0, index) + 1:index]
            marker = re.fullmatch(r'%[ \t]*([A-Z_]+):[ \t]*(.*?)\s*', content[index:end])
            if not prefix.strip() and content[index:end].rstrip('\r') in {'% BEGIN ECONOMICS STATEMENT', '% END ECONOMICS STATEMENT'}:
                headers.setdefault('_ECONOMICS_BOUNDARIES', []).append((index, end, content[index:end]))
            if not in_document and not prefix.strip() and marker:
                headers.setdefault(marker[1], []).append(marker[2])
                headers.setdefault('_HEADER_LINES', []).append((marker[1], prefix + content[index:end].rstrip('\r')))
            mask(index, end)
            index = end
        elif content[index] == '\\':
            verb = re.match(r'\\verb\*?([^A-Za-z\s])', content[index:])
            env = re.match(r'\\begin\s*\{([^}]+)\}', content[index:])
            if verb:
                start = index + verb.end()
                end = content.find(verb[1], start)
                if end < 0 or '\n' in content[start:end]:
                    raise ValueError('Unterminated inline verbatim')
                mask(index, end + 1)
                index = end + 1
            elif env and env[1] in LITERALS:
                closing = re.search(r'\\end\s*\{' + re.escape(env[1]) + r'\}',
                                    content[index + env.end():])
                if not closing:
                    raise ValueError('Unterminated literal environment')
                end = index + env.end() + closing.end()
                mask(index, end)
                index = end
            else:
                if env and env[1] == 'document':
                    in_document = True
                # TeX control symbols consume the following character: \% isn't
                # a comment; \\ followed by % is a comment after a line break.
                command = re.match(r'\\(?:[A-Za-z]+|[^A-Za-z])', content[index:])
                index += command.end() if command else 1
        else:
            index += 1
    return ''.join(output), headers


def one_header(headers, key, required=True):
    values = headers.get(key, [])
    if not values and not required:
        return None
    if len(values) != 1:
        raise ValueError(f'Require exactly one leading {key} header')
    return values[0]


def unique_json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON field: {key}')
        result[key] = value
    return result


def exact_build_header(headers, key):
    for name, line in headers.get('_HEADER_LINES', []):
        if name == key and not line.startswith('% ' + key + ': '):
            raise ValueError(f'{key} must use exact builder header syntax: % {key}: value')


def json_header(headers, key):
    value = json.loads(one_header(headers, key), object_pairs_hook=unique_json_pairs)
    if not isinstance(value, dict):
        raise ValueError(f'{key} must be a JSON object')
    return value


def require_text(record, fields):
    for field in fields:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f'Require nonempty declaration field: {field}')


def iso_date(value, label):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError(f'{label} must be YYYY-MM-DD')


def body_tex(active, standalone=False):
    begins = list(re.finditer(r'\\begin\s*\{document\}', active))
    ends = list(re.finditer(r'\\end\s*\{document\}', active))
    if not begins and not ends and not standalone:
        return active
    if len(begins) != 1 or len(ends) != 1 or begins[0].end() >= ends[0].start():
        raise ValueError('Expected one complete TeX document')
    if active[ends[0].end():].strip():
        raise ValueError('Unexpected content after document')
    body = active[begins[0].end():ends[0].start()]
    if not body.strip():
        raise ValueError('Empty mathematical document')
    return body


def headings(body):
    """Read balanced heading arguments using the existing importer lexer."""
    result = []
    for match in re.finditer(r'\\(section|subsection|subsubsection|paragraph)\*?\s*(?:\[[^\]]*\]\s*)?(?=\{)', body):
        title, end = braced_argument(body, match.end())
        result.append((match.start(), end, match[1], title.strip()))
    return result


def has_references(body):
    sections = headings(body)
    for index, (_, end, _, title) in enumerate(sections):
        stop = sections[index + 1][0] if index + 1 < len(sections) else len(body)
        if title.casefold() in {'references', 'bibliography', 'sources'} and body[end:stop].strip():
            return True
    if re.search(r'\\begin\s*\{thebibliography\}.*?\\bibitem\b', body, re.S):
        return True
    return bool(re.search(r'\\bibliography\s*\{[^}]+\}|\\printbibliography\b', body))


def completion(body, status):
    matches = list(re.finditer(re.escape(r'\section{Completion Estimate}'), body))
    if len(matches) != 1:
        raise ValueError(r'Require exactly one active \section{Completion Estimate}')
    start = matches[0].end()
    end = next((h[0] for h in headings(body) if h[0] >= start), len(body))
    block = body[start:end]
    values = re.findall(r'\bCOMPLETION\s*:\s*([+-]?\d+(?:\.\d+)?)\s*\\%', block)
    if len(values) != 1 or not 0 <= float(values[0]) <= 100:
        raise ValueError('Require one numeric COMPLETION: number\\% between 0 and 100')
    value = float(values[0])
    if status != 'solved' and value == 100:
        raise ValueError('Partial/unresolved attempts cannot claim 100% completion')
    if extract_completion(body) != value:
        raise ValueError('Completion must match site parser; put value within three lines of heading')
    # Existence of a justification is checkable; its mathematical adequacy isn't.
    justification = re.sub(r'\\noindent|\\textbf|[{}\s]', '', block)
    justification = re.sub(r'COMPLETION:[+-]?\d+(?:\.\d+)?\\%', '', justification)
    if not justification:
        raise ValueError('Completion estimate needs a mathematical justification')


def classify(path):
    parts = Path(path).parts
    if (len(parts) != 5 or tuple(parts[:2]) != ('attacks', 'open_problems')
            or parts[2] not in CATEGORIES):
        raise ValueError('Invalid submission location; expected category/folder/file.tex')
    category, folder, filename = parts[2:]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', folder):
        raise ValueError('Invalid submission folder')
    statement = (category, folder) in {('top_problems', 'definitions'), ('economics', 'statements')}
    if folder in {'definitions', 'statements'} and not statement:
        raise ValueError('Unsupported statement-only location for category')
    if category == 'economics':
        expression = r'([A-Z][0-9]{2}-[1-9][0-9]*)(?:_v([1-9][0-9]*))?\.tex'
    elif category == 'mo':
        expression = r'([1-9][0-9]*)-[A-Za-z0-9][A-Za-z0-9_.-]*?(?:_v([1-9][0-9]*))?\.tex'
    else:
        expression = r'([1-9][0-9]*)(?:_v([1-9][0-9]*))?\.tex'
    match = re.fullmatch(expression, filename)
    if not match or (match[2] and (int(match[2]) < 2 or statement)):
        raise ValueError('Invalid category filename or version (versions start at _v2)')
    return category, folder, match[1], statement


def read_csv_records(text, key, label, legacy_duplicate_counts=None):
    result, counts = {}, {}
    legacy_duplicate_counts = legacy_duplicate_counts or {}
    for row in csv.DictReader(io.StringIO(text)):
        identifier = row.get(key, '')
        counts[identifier] = counts.get(identifier, 0) + 1
        if not re.fullmatch(r'[1-9][0-9]*', identifier) or (identifier in result and
                (row != result[identifier] or counts[identifier] > legacy_duplicate_counts.get(identifier, 1))):
            raise ValueError(f'Duplicate/invalid {label} identifier: {identifier}')
        result[identifier] = row
    return result


def load_catalogs(root):
    """Reuse the site's catalogue validation, without enforcing new legacy rules."""
    registry = json.loads((root / TOP_REGISTRY).read_text())
    if not isinstance(registry, list):
        raise ValueError('Top registry must be an array')
    top = {}
    records = []
    for record in registry:
        identifier = record.get('id')
        if type(identifier) is not int or identifier < 1 or str(identifier) in top:
            raise ValueError(f'Duplicate/invalid Top identifier: {identifier}')
        top[str(identifier)] = record
        definition = root / PREFIX / 'top_problems/definitions' / f'{identifier}.tex'
        raw = definition.read_text()
        records.append({**record, **parse_numbered_problem_tex(raw, require_source_urls=False)})
    validate_open_problems_catalog({'records': records, 'recordCount': len(records),
                                   'displayOrder': json.loads((root / 'lists/unsolvedmath/display_order.json').read_text())})
    economics = load_registry(root)
    read_ranking_csv(root / 'lists/economics/rankings.csv', economics['problems'])
    erdos = read_csv_records((root / 'lists/erdos_problems.csv').read_text(), 'number', 'Erdos')
    erdos.update({identifier: {} for identifier in
                 json.loads((root / 'lists/erdos_status.json').read_text())['problems']})
    mo = read_csv_records((root / 'lists/mo_problems.csv').read_text(), 'question_id', 'MO', LEGACY_MO_DUPLICATE_COUNTS)
    for identifier, record in mo.items():
        url = urlsplit(record.get('link', ''))
        if (url.scheme != 'https' or url.netloc != 'mathoverflow.net'
                or not re.match(r'/questions/' + identifier + r'(?:/|$)', url.path)):
            raise ValueError(f'MO source URL does not match identity: {identifier}')
    return {'top_problems': top, 'economics': {r['id']: r for r in economics['problems']},
            'erdos': erdos, 'mo': mo}


def validate_file(root, path, catalogs):
    category, folder, identifier, statement = classify(path)
    if identifier not in catalogs[category]:
        raise ValueError(f'Unregistered {category} identity: {identifier}')
    if not (root / path).resolve().is_relative_to(root.resolve()):
        raise ValueError('Submission must resolve inside the repository')
    raw = (root / path).read_text(encoding='utf-8')
    active, headers = scan_tex(raw)
    body = body_tex(active, standalone=statement or category == 'economics')
    canonical = catalogs[category][identifier]
    if category in {'top_problems', 'economics'}:
        key = 'TOP_PROBLEM' if category == 'top_problems' else 'ECONOMICS_PROBLEM'
        exact_build_header(headers, key)
        metadata = json_header(headers, key)
        fields = ('id', 'title', 'category_id', 'status') if category == 'top_problems' else ('id', 'title', 'jel_code', 'source_id')
        for field in fields:
            if metadata.get(field) != canonical.get(field) or (field == 'id' and type(metadata.get(field)) is not type(canonical.get(field))):
                raise ValueError(f'{key} {field} does not match registered identity')
    entry_kind = one_header(headers, 'ENTRY_KIND', required=False)
    if category == 'top_problems' and folder == 'openai':
        # This specialized, pinned external summary has no new LLM proof attribution.
        parse_openai_claim(raw, json.loads((root / 'lists/openai_math/manifest.json').read_text()))
        return 'external claim (specialist build checks apply)'
    if category == 'top_problems' and folder == 'Human_Contribution':
        if entry_kind != 'human_contribution' or not has_references(body):
            raise ValueError('Human contribution needs human_contribution kind and references')
        return 'human contribution (scope/contribution review required)'
    declaration = json_header(headers, 'SUBMISSION')
    expected = 'statement_only' if statement else 'research_attempt'
    if (declaration.get('kind') != expected or declaration.get('category') != category
            or declaration.get('problem_id') != identifier):
        raise ValueError('SUBMISSION kind/category/problem_id conflicts with file identity')
    if entry_kind is not None and entry_kind != expected:
        raise ValueError('ENTRY_KIND conflicts with submission location')
    if statement:
        if any(key in headers for key in ('ATTEMPT_STATUS', 'FULL_SOLUTION_SCOPE')):
            raise ValueError('Statement-only files cannot carry research status or scope headers')
        if any(key in declaration for key in ('model', 'other_models', 'tools', 'target', 'scope',
                                              'human_contributions', 'verification', 'reproducibility', 'completion', 'status')):
            raise ValueError('Statement-only declaration cannot carry research-attempt fields')
        if re.search(r'Completion\s+(?:Rate\s+)?Estimate|\bCOMPLETION\s*:', body, re.I):
            raise ValueError('Statement-only files cannot carry research completion estimates')
        require_text(declaration, ('source', 'status_evidence', 'status_checked_on', 'duplicate_check', 'attribution'))
        iso_date(declaration['status_checked_on'], 'status_checked_on')
        if declaration.get('proposal_type') not in {'established', 'new_conjecture'}:
            raise ValueError('Require proposal_type established or new_conjecture')
        if declaration['proposal_type'] == 'new_conjecture':
            require_text(declaration, ('proposer', 'motivation', 'related_problems', 'boundary_tests',
                                      'counterexample_search', 'nontriviality', 'novelty_disclosure'))
        if category == 'top_problems':
            if entry_kind != 'statement_only':
                raise ValueError('Top definitions require ENTRY_KIND: statement_only')
            parsed = parse_numbered_problem_tex(active)
            for title in ('Definitions and mathematical statement', 'Short English statement', 'Sources'):
                if not re.search(r'^\s*\\subsection\{' + re.escape(title) + r'\}', body, re.M):
                    raise ValueError(f'Missing active statement heading: {title}')
            if parsed.get('researchTeX'):
                raise ValueError('Statement-only file cannot contain Research attempt subsection')
            if not parsed['sources']:
                raise ValueError('Top statement requires attributed source structure')
        else:
            # Boundaries are purposeful comments, read from the code-masked source,
            # not from a literal example of a boundary in the document.
            boundary_source = list(active)
            for start, end, text in headers.get('_ECONOMICS_BOUNDARIES', []):
                boundary_source[start:end] = text
            extract_statement(''.join(boundary_source))
            if not has_references(body):
                raise ValueError('Economics statement requires references')
        return 'statement-only declaration checked'
    require_text(declaration, ('other_models', 'tools', 'target', 'scope',
                              'human_contributions', 'verification', 'reproducibility'))
    model = declaration.get('model')
    if not isinstance(model, dict):
        raise ValueError('Research attempt requires model attribution object')
    require_text(model, ('provider', 'version', 'reasoning', 'generated_on'))
    iso_date(model['generated_on'], 'generated_on')
    if (model['version'].strip().casefold() in GENERIC_MODELS
            or model['version'].strip().casefold() in {'unknown', 'not exposed', 'unavailable'}):
        require_text(model, ('version_uncertainty',))
    status = one_header(headers, 'ATTEMPT_STATUS')
    declared_attempt_status('% ATTEMPT_STATUS: ' + status)
    if status not in {'solved', 'partial', 'unresolved'}:
        raise ValueError('Invalid ATTEMPT_STATUS')
    if category == 'economics':
        exact_build_header(headers, 'ATTEMPT_STATUS')
        exact_build_header(headers, 'FIRST_POSTED')
        iso_date(one_header(headers, 'FIRST_POSTED'), 'FIRST_POSTED')
        if raw.split(r'\end{document}', 1)[-1].strip():
            raise ValueError('Economics builder requires no trailing text/comments after document')
    if not has_references(body):
        raise ValueError('Research attempt requires active References or standard bibliography')
    completion(body, status)
    if status == 'solved':
        require_text(json_header(headers, 'FULL_SOLUTION_SCOPE'),
                     ('target', 'result', 'coverage', 'dependencies', 'human_verification', 'unverified', 'novelty'))
    elif 'FULL_SOLUTION_SCOPE' in headers:
        raise ValueError('FULL_SOLUTION_SCOPE conflicts with partial/unresolved status')
    # Only obvious leading declarations in a final-status section are checked;
    # quoted/rejected claims and titles are not guessed to be solution verdicts.
    for index, (_, end, _, title) in enumerate(headings(body)):
        if title.casefold() in {'final status', 'status', 'final'}:
            stop = headings(body)[index + 1][0] if index + 1 < len(headings(body)) else len(body)
            text = re.sub(r'\\[A-Za-z]+\*?|[{}\s]', ' ', body[end:stop]).strip()
            verdict = re.match(r'(SOLVED|FULL SOLUTION|PARTIAL|UNRESOLVED)\b', text)
            if verdict and ((verdict[1] in {'SOLVED', 'FULL SOLUTION'}) != (status == 'solved')):
                raise ValueError('Final status conflicts with ATTEMPT_STATUS')
    return 'research declaration checked (not proof verified)'


def git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True)
    if result.returncode:
        raise ValueError('Git command failed: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout


def baseline_text(root, commit, path):
    if not git(root, 'ls-tree', '--name-only', commit, '--', path).strip():
        return None
    return git(root, 'show', f'{commit}:{path}').decode('utf-8')


def changed_paths(root, commit):
    tokens = git(root, 'diff', '--name-status', '-z', '--find-renames', commit, '--').decode().split('\0')
    changed, removed = set(), set()
    index = 0
    while index < len(tokens) and tokens[index]:
        status, path = tokens[index:index + 2]
        index += 2
        if status.startswith(('R', 'C')):
            destination = tokens[index]
            index += 1
            changed.add(destination)
            if status.startswith('R'):
                removed.add(path)
        elif status == 'D':
            removed.add(path)
        else:
            changed.add(path)
    changed.update(p for p in git(root, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0') if p)
    return changed, removed


def protect_identities(root, commit, catalogs):
    """Keep old identities/aliases/source links; a rank change is not a rename."""
    for path, category, fields in (
        (TOP_REGISTRY, 'top_problems', ('problem_number', 'external_url')),
        (ECON_REGISTRY, 'economics', ('initial_rank', 'jel_code', 'source_id', 'statement_file', 'title')),
    ):
        old = baseline_text(root, commit, path)
        if old is None:
            continue
        records = json.loads(old)
        if category == 'economics':
            records = records['problems']
        for record in records:
            current = catalogs[category].get(str(record['id']))
            if current is None:
                raise ValueError(f'Removed/reassigned permanent {category} identity: {record["id"]}')
            for field in fields:
                if current.get(field) != record.get(field):
                    raise ValueError(f'Changed permanent {category} identity field {field}: {record["id"]}')
            if not set(record.get('legacy_ids', [])).issubset(current.get('legacy_ids', [])):
                raise ValueError(f'Removed legacy identity aliases: {record["id"]}')
    old_snapshot = baseline_text(root, commit, 'lists/erdos_status.json')
    if old_snapshot is not None:
        old_ids = set(json.loads(old_snapshot)['problems'])
        new_ids = set(json.loads((root / 'lists/erdos_status.json').read_text())['problems'])
        if not old_ids.issubset(new_ids):
            raise ValueError('Removed permanent Erdos source-database identities')
    for path, category, key, source_field in (
        ('lists/mo_problems.csv', 'mo', 'question_id', 'link'),
        ('lists/erdos_problems.csv', 'erdos', 'number', 'problem_url'),
    ):
        old = baseline_text(root, commit, path)
        if old is None:
            continue
        allowance = LEGACY_MO_DUPLICATE_COUNTS if category == 'mo' else None
        current_rows = read_csv_records((root / path).read_text(), key, category, allowance)
        for identifier, record in read_csv_records(old, key, category, allowance).items():
            if identifier not in current_rows or record.get(source_field) != current_rows[identifier].get(source_field):
                raise ValueError(f'Removed/changed {category} catalogue identity/link: {identifier}')


def validate(root=ROOT, paths=None, base=None):
    """Return (checked paths, informational specialist messages, errors)."""
    root = Path(root).resolve()
    errors, notes, checked = [], [], []
    try:
        if base:
            commit = git(root, 'rev-parse', '--verify', f'{base}^{{commit}}').decode().strip()
            changed, removed = changed_paths(root, commit)
            for path in sorted(removed):
                if path.startswith(PREFIX) and path.endswith('.tex'):
                    errors.append(f'{path}: removal/rename would break historical submission links')
            selected = changed if paths is None else set(paths) & changed
        else:
            if not paths:
                raise ValueError('Supply explicit paths or --base REF; no retroactive whole-repo default')
            selected = set(paths)
        relevant = {p for p in selected if p.startswith(PREFIX) and p.endswith('.tex')}
        if paths is not None:
            for path in set(selected) - relevant:
                if path not in REGISTRY_FILES:
                    errors.append(f'{path}: invalid submission location or non-TeX filename')
        if not relevant and not (set(selected) & REGISTRY_FILES):
            return checked, notes, errors
        catalogs = load_catalogs(root)
        if base:
            protect_identities(root, commit, catalogs)
        for path in sorted(relevant):
            try:
                note = validate_file(root, path, catalogs)
                checked.append(path)
                if 'specialist' in note or 'human contribution' in note:
                    notes.append(f'{path}: {note}')
            except (OSError, ValueError, TypeError, KeyError) as error:
                errors.append(f'{path}: {error}')
    except (OSError, ValueError, TypeError, KeyError) as error:
        errors.append(f'Catalogue/diff validation: {error}')
    return checked, notes, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', help='Repository-relative TeX paths; strict without --base')
    parser.add_argument('--base', help='Git commit/ref to compare with the working tree')
    parser.add_argument('--root', type=Path, default=ROOT, help='Repository root (also for isolated fixture repositories)')
    args = parser.parse_args()
    paths = []
    try:
        for path in args.paths:
            candidate = Path(path)
            if not candidate.is_absolute():
                candidate = args.root / candidate
            paths.append(candidate.resolve().relative_to(args.root.resolve()).as_posix())
    except ValueError:
        parser.error('All paths must be inside the repository root')
    checked, notes, errors = validate(args.root, paths or None, args.base)
    for note in notes:
        print('NOTE:', note)
    for error in errors:
        print('ERROR:', error, file=sys.stderr)
    print(f'Checked {len(checked)} changed/selected submissions; {len(errors)} errors. '
          'Structure and identity only; mathematical proofs are not verified.')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
