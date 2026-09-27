#!/usr/bin/env python3
"""Audited, non-destructive import of the local mathematical catalogue.

Legacy inputs and correspondence decisions belong to the migration audit only.
The website consumes the exported registry and its independent display order.
Run --dry-run before --apply. Sources are copied, never moved or overwritten.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO.parent / '_Local' / 'Erdos_problems'
REQUIRED = ('Definitions and mathematical statement', 'Short English statement', 'Sources')
SUBSECTION = re.compile(r'^[ \t]*\\subsection\*?\{([^\n{}]+)\}', re.M)
STAMP = '2026-09-27T00:00:00Z'
PROSE_REFERENCES = {10: [9], 17: [19], 18: [20], 19: [17], 30: [7], 33: [8],
                    34: [50], 41: [48], 44: [15], 48: [41], 50: [50], 64: [55], 106: [102]}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def encode_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        f.write(data)
    os.replace(temporary, path)


def sections(text):
    matches = list(SUBSECTION.finditer(text))
    result = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else text.rfind(r'\end{document}')
        if end < match.end():
            raise ValueError('Missing document ending')
        if match[1] in result:
            raise ValueError(f'Duplicate subsection {match[1]}')
        result[match[1]] = text[match.end():end].strip()
    return result


def definition_only(text):
    """Retain the source preamble/macros and statement, summary and sources."""
    parts = sections(text)
    if not all(name in parts for name in REQUIRED):
        raise ValueError('A recovered definition lacks required statement/source sections')
    first = SUBSECTION.search(text)
    prefix = text[:first.start()]
    prefix = re.sub(r'^% ATTEMPT_STATUS:.*\n', '', prefix, flags=re.M)
    return prefix + '\n'.join(r'\subsection{' + name + '}\n' + parts[name] + '\n'
                               for name in REQUIRED) + '\n\\end{document}\n'


def tex_escape(text):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
                    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(char, char) for char in text)


def tex_title(title):
    # Registry titles sometimes contain genuine inline mathematical notation.
    return ''.join(piece if i % 2 else tex_escape(piece)
                   for i, piece in enumerate(re.split(r'(\$[^$]+\$)', title)))


def replace_first_title(text, title):
    match = re.search(r'^[ \t]*\\section\*?\{', text, re.M)
    if not match:
        raise ValueError('No problem section heading')
    start = match.end() - 1
    depth = 0
    for pos in range(start, len(text)):
        char = text[pos]
        # Count braces unless escaped (including the second slash in \\{).
        slashes = 0
        prior = pos - 1
        while prior >= 0 and text[prior] == '\\':
            slashes += 1
            prior -= 1
        if slashes % 2:
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                new = r'\section*{\texorpdfstring{' + tex_title(title) + '}{' + tex_escape(title) + '}}'
                return text[:match.start()] + new + text[pos + 1:]
    raise ValueError('Unbalanced section heading')


def first_posted_dates(repo):
    result = subprocess.run(['git', '-c', 'core.quotePath=false', 'log', '--no-renames',
                             '--diff-filter=A', '--format=POSTED:%aI', '--name-only',
                             '--', 'attacks'], cwd=repo, capture_output=True, text=True, check=True)
    dates = {}
    date = None
    for line in result.stdout.splitlines():
        if line.startswith('POSTED:'):
            date = line[7:17]
        elif line.startswith('attacks/') and date:
            dates[line] = min(date, dates.get(line, date))
    return dates


def transform(text, record, legacy_number, mapping, *, posted=None, statement_only=False):
    """Update structurally identified catalogue identifiers, never raw numbers."""
    canonical = record['id']
    old = str(legacy_number)
    local_labels = set(re.findall(r'\\label\{([^{}]+)\}', text))
    if canonical != legacy_number and str(canonical) in local_labels:
        raise ValueError(f'Canonical label would collide with local label {canonical}')
    text = re.sub(r'^[ \t]*% (?:TOP_PROBLEM|FIRST_POSTED|ENTRY_KIND):[^\n]*\n', '', text, flags=re.M)
    text = re.sub(r'^[ \t]*% problemId:[^\n]*$', f'% problemId: {canonical}', text, flags=re.M)
    text = re.sub(r'^[ \t]*% source releaseRank:[^\n]*$',
                  f'% Canonical problem ID: {canonical}', text, flags=re.M)
    text = re.sub(r'^% No catalogue problemId or releaseRank[^\n]*\n', '', text, flags=re.M)
    text = re.sub(r'^% (?:Research batch|Standalone research notebook.*original catalogue)[^\n]*\n',
                  '', text, flags=re.M)
    text = re.sub(r'^% Standalone notebook for original catalogue section[^\n]*\n', '', text, flags=re.M)
    text = re.sub(r'^% Standalone export\. Original section \d+[^\n]*$',
                  '% Standalone export. Original research content preserved.', text, flags=re.M)
    text = re.sub(r'^% Definitions and sources retained from research_batch_[^\n]*$',
                  '% Definitions and sources retained from the original research notebook.', text, flags=re.M)
    # Some independent notebooks still carry the section counter of a batch.
    text = re.sub(r'\\setcounter\{section\}\{\d+\}', r'\\setcounter{section}{0}', text)
    text = text.replace(r'\label{' + old + '}', r'\label{' + str(canonical) + '}')
    for macro in ('sref', 'eref'):
        text = text.replace('\\' + macro + '{' + old + '}', '\\' + macro + '{' + str(canonical) + '}')
    for kind in ('source', 'extra'):
        text = re.sub(r'(?<=\{)' + kind + ':' + re.escape(old) + ':',
                      kind + ':' + str(canonical) + ':', text)
    # Numbered batch notebooks also namespace local equation/theorem labels by
    # their problem ID. Rewrite label declarations and uses together.
    def scoped_reference(match):
        target = re.sub(r'^(?:(eq|thm|lem|prop|cor|sec|subsec|app|def):)?' + re.escape(old) + ':',
                        lambda m: (m[1] + ':' if m[1] else '') + str(canonical) + ':', match[2])
        return '\\' + match[1] + '{' + target + '}'
    text = re.sub(r'\\(label|ref|eqref|autoref|nameref|pageref|hyperlink|hypertarget)\{([^{}]+)\}',
                  scoped_reference, text)
    def reference(match):
        number = int(match['number'])
        if number == legacy_number:
            target = canonical
        elif str(number) in local_labels:
            return match[0]
        else:
            target = mapping.get(number)
        if target is None:
            raise ValueError(f'Unresolved catalogue cross-reference {number} in {legacy_number}')
        return '\\' + match['macro'] + '{' + str(target) + '}'

    text = re.sub(r'\\(?P<macro>ref|autoref|nameref|pageref)\{(?P<number>\d+)\}', reference, text)
    # Header/footer/PDF title and compile instructions are identifiers, unlike
    # numbered problems cited in the mathematical prose of a research paper.
    lines = []
    for line in text.splitlines(keepends=True):
        if ('pdftitle=' in line or '\\fancyhead' in line
                or line.lstrip().startswith('%') and ('Compile' in line or 'compile' in line)):
            line = re.sub(r'(?i)((?:problem|section)\s+)' + re.escape(old) + r'\b',
                          lambda m: m[1] + str(canonical), line)
            line = re.sub(r'(?<![\w])' + re.escape(old) + r'\.tex\b', f'{canonical}.tex', line)
        lines.append(line)
    text = ''.join(lines)
    # Manually reviewed cross-catalogue references. Restrict by source document
    # and target so that cited Smale/Erdos/source-paper numbering is unchanged.
    for target in PROSE_REFERENCES.get(legacy_number, []):
        pattern = r'(?i)\bproblem([ ~]+)' + str(target) + r'\b'
        if not re.search(pattern, text):
            continue
        destination = mapping.get(target)
        if destination is None:
            raise ValueError(f'Unresolved prose catalogue reference {target} in {legacy_number}')
        text = re.sub(pattern,
                      lambda m: 'UnsolvedMath problem' + m[1] + str(destination), text)
    text = replace_first_title(text, record['title'])
    # Each independent document has a canonical problem label even when the
    # original author chose a descriptive label; existing descriptive labels stay.
    if r'\label{' + str(canonical) + '}' not in text:
        heading = re.search(r'^[ \t]*\\section\*?\{[^\n]*', text, re.M)
        text = text[:heading.end()] + r'\label{' + str(canonical) + '}' + text[heading.end():]
    metadata = {key: record[key] for key in ('id', 'title', 'category_id', 'category', 'status')}
    header = '% TOP_PROBLEM: ' + json.dumps(metadata, ensure_ascii=False) + '\n'
    header += '% FIRST_POSTED: ' + (posted or 'null') + '\n'
    if statement_only:
        header += '% ENTRY_KIND: statement_only\n'
    result = header + text
    if 'releaseRank' in result or re.search(r'(?i)proofatlas', result):
        raise ValueError(f'Untranslated catalogue metadata in problem {legacy_number}')
    return result


def registry_sections(source_text):
    """Use our display parser, expanding document-local mathematical macros."""
    spec = importlib.util.spec_from_file_location('catalogue_build', REPO / 'build_site.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    parsed = build.parse_numbered_problem_tex(source_text, require_source_urls=False)
    content = parsed['definitionTeX']
    preamble = source_text.split(r'\begin{document}', 1)[0]
    macros = {}
    for match in re.finditer(r'\\(?:newcommand|renewcommand|providecommand)\s*\{\\([A-Za-z]+)\}\s*\{', preamble):
        start = match.end()
        depth, pos = 1, start
        while pos < len(preamble) and depth:
            if preamble[pos] == '\\':
                pos += 2
                continue
            if preamble[pos] == '{':
                depth += 1
            elif preamble[pos] == '}':
                depth -= 1
            pos += 1
        if depth:
            raise ValueError(f'Unclosed macro definition {match[1]}')
        macros[match[1]] = '{' + preamble[start:pos - 1] + '}'
    if macros:
        pattern = re.compile(r'\\(' + '|'.join(sorted(macros, key=len, reverse=True)) + r')(?![A-Za-z])')
        for _ in range(20):
            expanded = pattern.sub(lambda m: macros[m[1]], content)
            if expanded == content:
                break
            content = expanded
        else:
            raise ValueError('Recursive document macros in registry text')
    return sections('\\begin{document}\n' + content + '\n\\end{document}\n')


def discover_maximum(registry_dir, baseline):
    """Inspect authoritative exports and known allocator/reservation structures."""
    sources = {'problems.json': max(record['id'] for record in baseline)}
    dataset_path = registry_dir / 'dataset.json'
    if dataset_path.exists():
        records = read_json(dataset_path)['problems']
        sources['dataset.json'] = max(record['id'] for record in records)
    reserved = []
    for path in registry_dir.glob('*.json'):
        if not re.search(r'reserv|allocat|tombstone|deleted|registry', path.name, re.I):
            continue
        data = read_json(path)
        def visit(value, key=''):
            if isinstance(value, dict):
                for k, v in value.items():
                    visit(v, k)
            elif isinstance(value, list):
                for v in value:
                    visit(v, key)
            elif type(value) is int and re.search(r'id|watermark|maximum', key, re.I):
                reserved.append(value)
        visit(data)
        if reserved:
            sources[path.name] = max(reserved)
    return max(sources.values()), sources


def new_record(row, catalogue, source_text, categories, difficulties):
    parts = sections(source_text)
    category = categories[row['category_id']]
    source = catalogue.get('formalStatementSource') or {}
    background = parts.get('Short English statement', '').strip()
    references = parts.get('Sources', '').strip()
    return {
        'id': row['canonical_id'], 'problem_number': f"LOCAL-{row['canonical_id']}",
        'title': catalogue['canonicalTitle'],
        'statement': parts['Definitions and mathematical statement'],
        'background': background + ('\n\nReferences (LaTeX):\n' + references if references else ''),
        'difficulty_level_id': 4, 'status': 'open',
        'proposed_by': None, 'proposed_year': None,
        'category_id': category['id'], 'set_id': None,
        'view_count': 0, 'favorite_count': 0,
        'created_at': STAMP, 'updated_at': STAMP, 'published': False,
        'category': category, 'difficulty': difficulties[4], 'set': None,
        'source_url': source.get('url'), 'source_citation': source.get('citation'),
    }


def extra_targets():
    return [
        {'legacy_number': None, 'source_key': 'prime-gap-236', 'existing_id': None,
         'classification': 'related', 'related_ids': [11], 'candidate_ids': [11, 1517, 20000752],
         'category_id': 1, 'source_path': 'gpt_6_astra_pro/20.tex',
         'title': 'A certified bound of 236 for bounded prime gaps',
         'notes': 'The actual Pro20 target is a certified 48-dimensional sieve proof of H_1 <=236; '
                  'it is distinct from twin primes and general prime-tuple conjectures. '
                  'Searched registry titles and statements for bounded gaps and the numerical target.'},
        {'legacy_number': None, 'source_key': 'critical-percolation', 'existing_id': 10100001,
         'classification': 'exact', 'related_ids': [10000033], 'candidate_ids': [10100001, 10000033],
         'category_id': 19, 'source_path': 'gpt_6_astra_pro/501.tex',
         'notes': 'Both ask no infinite cluster at criticality for nearest-neighbour independent '
                  'bond percolation on Z^d (d>=2); the transitive-graph record is broader.'},
        {'legacy_number': None, 'source_key': 'irrational-e-plus-pi', 'existing_id': None,
         'classification': 'related', 'related_ids': [1510, 3349], 'candidate_ids': [1510, 3349],
         'category_id': 1, 'source_path': 'gpt_6_astra_pro/502.tex', 'title': 'Irrationality of e+pi',
         'notes': 'Irrationality of the sum is weaker than algebraic independence or transcendence. '
                  'Title and statement searches found no standalone exact record; preserve separately.'},
    ]


def allocate_pinned_id(allocations, source_key, high_watermark):
    """Reuse an assigned identity; only an unassigned target consumes an ID."""
    existing = allocations.get(source_key)
    if existing is not None:
        return existing, high_watermark
    return high_watermark + 1, high_watermark + 1


def upstream_problem_url(record, code_counts):
    """Public codes are routes, but reused codes need the unique numeric route."""
    if not record.get('published'):
        return None
    code = record['problem_number']
    route = code if code_counts[code] == 1 else record['id']
    return f'https://www.unsolvedmath.com/problems/{route}'


def plan(args):
    source = args.source.resolve()
    registry_dir = args.registry.resolve()
    audit = args.audit.resolve()
    audit.mkdir(parents=True, exist_ok=True)
    state_path = audit / 'allocation_state.json'
    state = read_json(state_path) if state_path.exists() else None
    manifest_path = audit / 'migration_manifest.json'
    # Publishing the migration adds these paths to Git history. Preserve the
    # original import dates (including unknown dates), rather than importing
    # the publication date on a subsequent validation run.
    posted_at_import = {item['destination']: item['first_posted']
                        for item in read_json(manifest_path)['files']} if state and manifest_path.exists() else {}
    registry_path = registry_dir / 'problems.json'
    current_registry = read_json(registry_path)
    original = (audit / 'original_problems.json').read_bytes() if state else registry_path.read_bytes()
    baseline = json.loads(original)
    by_id = {record['id']: record for record in baseline}
    code_counts = collections.Counter(record['problem_number'] for record in baseline)
    if len(by_id) != len(baseline):
        raise ValueError('Duplicate existing UnsolvedMath IDs')
    maximum, max_sources = discover_maximum(registry_dir, baseline)
    observed_maximum = max(maximum, max(record['id'] for record in current_registry))
    if state:
        maximum, max_sources = state['old_maximum_id'], state['maximum_sources']
    categories = {record['id']: record for record in read_json(registry_dir / 'categories.json')}
    difficulties = {record['id']: record for record in read_json(registry_dir / 'difficulty_levels.json')}
    catalogue = read_json(source / 'top500-v22.json')['records']
    by_number = {record['releaseRank']: record for record in catalogue}
    if set(by_number) != set(range(1, 501)):
        raise ValueError('Unexpected source catalogue numbering')
    crosswalk = source.parent / 'UnsolvedMath' / 'ProofAtlas_UnsolvedMath_crosswalk.csv'
    with crosswalk.open(encoding='utf-8-sig') as handle:
        candidates = {int(row['ProofAtlas']): int(row['UnsolvedMath']) if row['UnsolvedMath'] else None
                      for row in csv.DictReader(handle)}
    decisions = []
    for name in ('identity_001_250.json', 'identity_251_500.json'):
        decisions.extend(read_json(audit / name))
    override_file = audit / 'identity_overrides.json'
    if override_file.exists():
        overrides = {row['legacy_number']: row for row in read_json(override_file)}
        decisions = [overrides.get(row['legacy_number'], row) for row in decisions]
    if sorted(row['legacy_number'] for row in decisions) != list(range(1, 501)):
        raise ValueError('Need exactly one reviewed identity decision per catalogue entry')
    pinned = state['allocations'] if state else {}
    rows, mapping, used, allocated = [], {}, {}, observed_maximum
    added_ids = []
    for decision in sorted(decisions, key=lambda d: d['legacy_number']) + extra_targets():
        row = dict(decision)
        number = row['legacy_number']
        row['source_key'] = row.get('source_key', f'catalogue-{number}')
        row['legacy_title'] = by_number[number]['canonicalTitle'] if number else row.get('title')
        row['crosswalk_existing_id'] = candidates.get(number)
        row['source_paths'], row['destination_paths'] = [], []
        row['collision_status'] = 'none'
        classification = row['classification']
        if classification == 'needs_review' and (args.allocate_review_cases or pinned.get(row['source_key']) is not None):
            classification = row['classification'] = 'ambiguous_separate'
            row['notes'] += (' User authorized a separate new local ID rather than merging this '
                             'target with a potentially different existing record; mathematical '
                             'equivalence remains unasserted.')
        if classification not in {'exact', 'related', 'no_existing_match', 'needs_review', 'ambiguous_separate'}:
            raise ValueError(f'Unknown decision {classification}')
        if classification == 'needs_review':
            row.update(canonical_id=None, action='needs_review')
        elif classification == 'exact':
            canonical = row.get('existing_id')
            if type(canonical) is not int or canonical not in by_id:
                raise ValueError(f'Invalid exact identity {row}')
            if canonical in used:
                raise ValueError(f'Duplicate destination ID {canonical}: {used[canonical]} and {number}; review first')
            row.update(canonical_id=canonical, action='keep_existing_id' if number == canonical else 'rename_to_existing_id')
            row['category_id'] = by_id[canonical]['category_id']
        else:
            if row.get('existing_id') is not None:
                raise ValueError('A non-exact match cannot inherit an existing ID')
            canonical, allocated = allocate_pinned_id(pinned, row['source_key'], allocated)
            if pinned.get(row['source_key']) is None:
                added_ids.append(canonical)
            if canonical in used:
                raise ValueError(f'Duplicate pinned identity {canonical}')
            action = {'related': 'separate_variant_new_id', 'ambiguous_separate': 'separate_ambiguous_new_id'}.get(classification, 'create_new_id')
            row.update(canonical_id=canonical, action=action)
        if row['canonical_id']:
            used[row['canonical_id']] = row['source_key']
        if number:
            mapping[number] = row['canonical_id']
        rows.append(row)

    inventory = []
    for path in sorted(source.rglob('*')):
        if not path.is_file() or path.name == '.DS_Store':
            continue
        stat = path.stat()
        inventory.append({'path': str(path.relative_to(source)), 'sha256': digest(path.read_bytes()),
                          'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'atime_ns': stat.st_atime_ns})
    sources_by_path = {item['path']: item for item in inventory}
    dates = first_posted_dates(REPO)
    destination_root = REPO / 'attacks' / 'open_problems' / 'top_problems'
    operations, records, new_records = [], [], []
    originals_accounted = set()
    withheld = []
    for row in rows:
        number, canonical = row['legacy_number'], row['canonical_id']
        candidates_paths = ([source / f'{number}.tex'] + sorted(source.glob(f'*/{number}.tex')) if number
                            else [source / row['source_path']])
        paths = [path for path in candidates_paths if path.is_file()]
        if number == 20:
            paths = [path for path in paths if path.parent.name != 'gpt_6_astra_pro']
        row['source_paths'] = [str(path.relative_to(source)) for path in paths]
        for path in paths:
            if not number:
                continue
            text = path.read_text(encoding='utf-8')
            header = re.search(r'^% TOP_PROBLEM: (.+)$', text, re.M)
            metadata = json.loads(header[1]) if header else {}
            source_id = metadata.get('problemId')
            source_rank = metadata.get('releaseRank')
            if source_id and source_id != by_number[number]['problemId']:
                raise ValueError(f'Source mathematical identity disagrees with filename: {path}')
            if source_rank and str(source_rank) != str(number):
                raise ValueError(f'Source catalogue number disagrees with filename: {path}')
            marker = re.search(r'^% problemId: (problem\.[^\s]+)', text, re.M)
            if marker and marker[1] != by_number[number]['problemId']:
                raise ValueError(f'Source research marker disagrees with its target: {path}')
        if canonical is None:
            withheld.extend(row['source_paths'])
            originals_accounted.update(row['source_paths'])
            continue
        if not paths:
            raise ValueError(f'No source documents for {row["source_key"]}')
        definition_path = next((p for p in paths if p.parent == source), paths[0])
        recovered = definition_path.parent != source
        raw_definition = definition_path.read_text(encoding='utf-8')
        definition = definition_only(raw_definition) if recovered else raw_definition
        if number:
            target = by_number[number]
        else:
            target = {'canonicalTitle': row.get('title', by_id.get(canonical, {}).get('title'))}
        if canonical in by_id:
            record = by_id[canonical]
        else:
            record = new_record(row, target, definition, categories, difficulties)
            # Remove structural source labels before adding new registry text.
            cleaned = transform(definition, record, number or int(definition_path.stem), mapping,
                                statement_only=True)
            public_parts = registry_sections(cleaned)
            record['statement'] = public_parts['Definitions and mathematical statement']
            record['background'] = public_parts['Short English statement'] + '\n\nReferences (LaTeX):\n' + public_parts['Sources']
            new_records.append(record)
        # This is a portable projection, never a copy of upstream statement prose.
        selected = {key: record[key] for key in ('id', 'problem_number', 'title', 'category_id', 'category', 'status')}
        selected['external_url'] = upstream_problem_url(record, code_counts) if canonical in by_id else None
        selected['legacy_ids'] = [target['problemId']] if number else []
        clean_definition = transform(definition, record, number or int(definition_path.stem), mapping,
                                     statement_only=True)
        selected['statement'] = sections(clean_definition)['Short English statement']
        records.append(selected)
        row['canonical_title'] = record['title']
        row['recovered_definition'] = recovered
        jobs = [(definition_path, destination_root / f'{canonical}.tex', definition, True, recovered)]
        for path in paths:
            if path.parent == source:
                continue
            content = path.read_text(encoding='utf-8')
            parts = sections(content)
            statement_only = not any(name.startswith('Research attempt') and body.strip()
                                     for name, body in parts.items())
            jobs.append((path, destination_root / path.parent.name / f'{canonical}.tex', content, statement_only, False))
        for path, dest, content, statement_only, derived in jobs:
            source_relative = str(path.relative_to(source))
            old_repo_path = 'attacks/open_problems/top_problems/' + source_relative
            old_paths = [old_repo_path, old_repo_path.replace('/gpt_6_astra_ultra/', '/GPT_6_Astra_Ultra/')]
            known = [dates[p] for p in old_paths if p in dates]
            posted = posted_at_import.get(str(dest.relative_to(REPO)), min(known) if known else None)
            old_number = number or int(path.stem)
            rendered = transform(content, record, old_number, mapping, posted=posted,
                                 statement_only=statement_only)
            data = rendered.encode('utf-8')
            operation = {'source': source_relative, 'destination': str(dest.relative_to(REPO)),
                         'canonical_id': canonical, 'derived_definition': derived,
                         'statement_only': statement_only, 'first_posted': posted,
                         'source_sha256': sources_by_path[source_relative]['sha256'],
                         'destination_sha256': digest(data), 'content': data}
            operations.append(operation)
            row['destination_paths'].append(operation['destination'])
            originals_accounted.add(source_relative)
    all_tex = {item['path'] for item in inventory if item['path'].endswith('.tex')}
    if originals_accounted != all_tex:
        raise ValueError(f'Unaccounted source files: {sorted(all_tex-originals_accounted)}')
    destinations = [operation['destination'] for operation in operations]
    if len(set(destinations)) != len(destinations):
        raise ValueError('Destination file collision')
    collisions = [name for name, op in zip(destinations, operations)
                  if (REPO / name).exists() and (REPO / name).read_bytes() != op['content']]
    if collisions:
        raise ValueError(f'Refusing to overwrite different destination files: {collisions[:10]}')
    # Check every planned label/ref before any destination or registry mutation.
    if len(records) != len(used):
        raise ValueError('Catalogue record count mismatch')
    order = [record['id'] for record in records]
    if len(set(order)) != len(order):
        raise ValueError('Repeated display identity')
    # New approvals may occur earlier in display order. They still append after
    # every existing registry record and never shift a previously assigned ID.
    new_records.sort(key=lambda record: record['id'])
    expected_registry = baseline + new_records
    prior_allocated = set(state['allocated_ids']) if state else set()
    prior_registry = baseline + [record for record in new_records if record['id'] in prior_allocated]
    if current_registry != prior_registry and current_registry != expected_registry:
        raise ValueError('Canonical registry changed outside this migration; do not overwrite it')
    export = REPO / 'lists' / 'unsolvedmath'
    export_before = {}
    prior_catalogue_ids = {value for value in pinned.values() if value is not None}
    for filename, data in [('problems.json', records), ('display_order.json', order)]:
        path = export / filename
        export_before[filename] = path.read_bytes() if path.exists() else None
        if export_before[filename] is not None and export_before[filename] != encode_json(data):
            previous = ([record for record in records if record['id'] in prior_catalogue_ids]
                        if filename == 'problems.json' else [value for value in order if value in prior_catalogue_ids])
            if not args.allocate_review_cases or not added_ids or export_before[filename] != encode_json(previous):
                raise ValueError(f'Refusing to overwrite a changed or unowned export {path}')
    state_new = {'schema_version': 1, 'old_maximum_id': maximum, 'maximum_sources': max_sources,
                 'original_registry_sha256': digest(original),
                 'allocated_ids': [record['id'] for record in new_records],
                 'allocations': {row['source_key']: row['canonical_id'] for row in rows},
                 'source_inventory_sha256': digest(encode_json([{k:v for k,v in item.items() if k != 'atime_ns'} for item in inventory]))}
    if state:
        for key in ('schema_version', 'old_maximum_id', 'maximum_sources', 'original_registry_sha256'):
            if state[key] != state_new[key]:
                raise ValueError('Original migration identity state changed')
        for key, value in pinned.items():
            new_value = state_new['allocations'].get(key)
            if value != new_value and not (value is None and args.allocate_review_cases and new_value in added_ids):
                raise ValueError(f'Refusing to change previously allocated identity for {key}')
        if not prior_allocated.issubset(state_new['allocated_ids']):
            raise ValueError('Previously allocated IDs cannot be discarded')
    summary = {
        'old_maximum_id': maximum, 'maximum_sources': max_sources,
        'new_id_range': [maximum + 1, allocated] if allocated > maximum else None,
        'original_registry_count': len(baseline), 'final_registry_count': len(expected_registry),
        'catalogue_entries': len(records),
        'exact_existing_matches': sum(row['classification'] == 'exact' for row in rows),
        'new_problems': len(new_records),
        'scope_variants': sum(row['classification'] == 'related' for row in rows),
        'ambiguous_targets_separated': sum(row['classification'] == 'ambiguous_separate' for row in rows),
        'newly_assigned_ids_this_run': added_ids,
        'needs_review': sum(row['classification'] == 'needs_review' for row in rows),
        'destination_collisions': 0, 'duplicate_destination_ids': 0,
        'source_tex_files': len(all_tex), 'withheld_source_files': len(withheld),
        'migrated_original_tex_files': len(all_tex) - len(withheld),
        'written_tex_files': len(operations),
        'recovered_definitions': sum(operation['derived_definition'] for operation in operations),
        'root_statements': sum('/top_problems/' + str(op['canonical_id']) + '.tex' in op['destination'] for op in operations),
        'model_files': dict(collections.Counter(Path(op['destination']).parent.name for op in operations
                                             if Path(op['destination']).parent.name != 'top_problems')),
        'statement_only_model_files': sum(op['statement_only'] and Path(op['destination']).parent.name != 'top_problems' for op in operations),
        'upstream_linked_records': sum(record['external_url'] is not None for record in records),
        'local_extensions_without_upstream_page': sum(record['external_url'] is None for record in records),
        'source_files_untouched': True,
    }
    manifest = {'summary': summary, 'rows': rows, 'source_inventory': inventory,
                'files': [{key: value for key, value in op.items() if key != 'content'} for op in operations],
                'withheld_sources': withheld}
    atomic_write(audit / 'migration_manifest.json', encode_json(manifest))
    out = io.StringIO()
    fields = ['legacy_number','legacy_title','crosswalk_existing_id','existing_id','canonical_id',
              'canonical_title','classification','action','source_paths','destination_paths','collision_status','notes']
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
                         for key, value in row.items()})
    atomic_write(audit / 'migration_manifest.csv', out.getvalue().encode('utf-8-sig'))
    return locals()


def apply(result):
    audit, state = result['audit'], result['state_new']
    original_path = audit / 'original_problems.json'
    if not original_path.exists():
        atomic_write(original_path, result['original'])
    elif original_path.read_bytes() != result['original']:
        raise ValueError('Original registry backup does not match')
    atomic_write(audit / 'allocation_state.json', encode_json(state))
    if read_json(result['registry_path']) != result['current_registry']:
        raise ValueError('Registry changed after planning; refusing to apply')
    # Hash the complete source inventory immediately before applying the plan.
    for item in result['inventory']:
        if digest((result['source'] / item['path']).read_bytes()) != item['sha256']:
            raise ValueError(f'Source changed during migration: {item["path"]}')
    for op in result['operations']:
        dest = REPO / op['destination']
        if dest.exists():
            if dest.read_bytes() != op['content']:
                raise ValueError(f'Destination changed since dry run: {dest}')
            continue
        atomic_write(dest, op['content'])
        source_stat = (result['source'] / op['source']).stat()
        os.utime(dest, ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns))
    if read_json(result['registry_path']) != result['current_registry']:
        raise ValueError('Registry changed while writing assets; refusing to overwrite it')
    if result['current_registry'] != result['expected_registry']:
        atomic_write(result['registry_path'], encode_json(result['expected_registry']))
    # Preserve the high-water mark even if records are later archived/deleted.
    allocator = result['registry_dir'] / 'id_registry.json'
    high_watermark = max(record['id'] for record in result['expected_registry'])
    allocator_data = read_json(allocator) if allocator.exists() else {'schema_version': 1}
    allocator_data['last_allocated_id'] = max(allocator_data.get('last_allocated_id', 0), high_watermark)
    allocator_data['policy'] = 'Allocate monotonically above this value and all existing/reserved problem IDs; never fill gaps.'
    atomic_write(allocator, encode_json(allocator_data))
    export = REPO / 'lists' / 'unsolvedmath'
    for filename, data in [('problems.json', result['records']), ('display_order.json', result['order'])]:
        path = export / filename
        encoded = encode_json(data)
        current = path.read_bytes() if path.exists() else None
        if current != result['export_before'][filename]:
            raise ValueError(f'Export changed after planning: {path}')
        atomic_write(path, encoded)
    validation = validate(result)
    atomic_write(audit / 'validation.json', encode_json(validation))
    return validation


def validate(result):
    original = json.loads(result['original'])
    registry = read_json(result['registry_path'])
    if registry[:len(original)] != original:
        raise ValueError('An existing registry record changed')
    if len({row['id'] for row in registry}) != len(registry):
        raise ValueError('Duplicate canonical registry IDs')
    if registry != result['expected_registry']:
        raise ValueError('Unexpected appended registry data')
    for op in result['operations']:
        path = REPO / op['destination']
        if digest(path.read_bytes()) != op['destination_sha256']:
            raise ValueError(f'Transformation verification failed: {path}')
        data = path.read_text(encoding='utf-8')
        header = re.search(r'^% TOP_PROBLEM: (.+)$', data, re.M)
        if not header or json.loads(header[1])['id'] != op['canonical_id']:
            raise ValueError(f'Canonical metadata mismatch: {path}')
        if path.stem != str(op['canonical_id']):
            raise ValueError(f'Canonical filename mismatch: {path}')
        if r'\begin{document}' not in data or r'\end{document}' not in data:
            raise ValueError(f'Document structure damaged: {path}')
    for item in result['inventory']:
        if digest((result['source'] / item['path']).read_bytes()) != item['sha256']:
            raise ValueError('Source data was modified')
    return {'passed': True, **result['summary'], 'existing_registry_records_unchanged': len(original),
            'hodge_id': 6, 'hodge_display_position': result['order'].index(6)+1,
            'source_and_destination_sha256_verified': True,
            'research_preservation': 'Each output was verified against the deterministic structural-only transformation of its source.',
            'upstream_publication': 'Local extensions have no upstream page; external_url is null until publication is verified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--validate', action='store_true')
    parser.add_argument('--source', type=Path, default=LOCAL / 'top_problems')
    parser.add_argument('--registry', type=Path, default=LOCAL / 'UnsolvedMath')
    parser.add_argument('--audit', type=Path, default=LOCAL / 'UnsolvedMath' / 'migration_audit')
    parser.add_argument('--allocate-review-cases', action='store_true',
                        help='Assign separate new local IDs to held targets, preserving all prior allocations')
    args = parser.parse_args()
    result = plan(args)
    validation = apply(result) if args.apply else validate(result) if args.validate else None
    print(json.dumps(validation or result['summary'], indent=2))


if __name__ == '__main__':
    main()
