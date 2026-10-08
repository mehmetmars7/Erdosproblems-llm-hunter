#!/usr/bin/env python3
"""Import reviewed Economics definitions, keeping provenance separate from status.

IDs must first be reserved with allocate_openai_problem_ids.py. This importer
does not allocate identities, create attempts, approve solutions or publish to
an external catalogue. Run --check to validate without writing files.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = {'theoretical', 'identification', 'empirical', 'design'}
BASES = {'source_statement', 'adapted_research_question', 'proposed_specification'}
EVIDENCE = {'explicit_open', 'research_agenda', 'not_verified', 'resolved_or_misstated'}
PRIORITY = {'verified_original', 'earliest_found', 'not_established'}
REFERENCE_FIELDS = ('authors', 'title', 'year', 'url', 'doi', 'locator', 'evidence_summary')


def tex_text(value):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%',
                    '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{',
                    '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(c, c) for c in str(value))


def reference_text(source):
    authors = source.get('authors') or []
    if isinstance(authors, str):
        authors = [authors]
    parts = [', '.join(authors), str(source.get('year') or 'Year not verified'),
             source['title'], source.get('locator', '')]
    return '. '.join(tex_text(p) for p in parts if p) + '.'


def status_for(record):
    if record['source_status'] in {'not_verified', 'resolved_or_misstated'}:
        return 'provenance_pending'
    if record['formalization_basis'] == 'source_statement' and record['kind'] == 'theoretical':
        return 'open'
    return 'research_question'


def validate_reference(source):
    if not isinstance(source, dict):
        raise ValueError('References must be attributed objects')
    for key in ['title', 'locator', 'evidence_summary']:
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError(f'Reference {key} is required')
    url = source.get('url')
    if not isinstance(url, str) or not url.startswith(('https://', 'http://')) or any(c in url for c in '{}\n\r'):
        raise ValueError('References require safe HTTP(S) URLs')
    authors = source.get('authors')
    if not (isinstance(authors, str) and authors.strip()) and not (
            isinstance(authors, list) and all(isinstance(a, str) and a.strip() for a in authors)):
        raise ValueError('Reference authors must be a string or a list of author names')
    if source.get('year') is not None and (type(source['year']) is not int or source['year'] < 1):
        raise ValueError('Reference year must be a positive integer or unverified')
    if source.get('doi') is not None and (not isinstance(source['doi'], str) or not source['doi'].strip()):
        raise ValueError('Reference DOI must be a nonempty string or unverified')


def validate_record(record):
    if type(record.get('id')) is not int or record['id'] < 1:
        raise ValueError('Economics identity must be a reserved positive integer')
    if type(record.get('original_id')) is not int or not 1 <= record['original_id'] <= 250:
        raise ValueError('Original catalogue position must be in 1..250')
    for key, allowed in [('kind', KINDS), ('formalization_basis', BASES),
                         ('source_status', EVIDENCE), ('priority_status', PRIORITY)]:
        if record.get(key) not in allowed:
            raise ValueError(f'Invalid {key} for {record["id"]}')
    for key in ['title', 'field', 'statement_tex', 'short_statement',
                'formalization_note', 'priority_note', 'status_qualification']:
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f'Missing {key} for {record["id"]}')
    first = record.get('earliest_verified_reference')
    for key in ['earliest_verified_reference', 'current_reference']:
        if record.get(key) is not None:
            validate_reference(record[key])
    if record['source_status'] in {'explicit_open', 'research_agenda'} and not first:
        raise ValueError('Verified open-question evidence requires a located reference')
    if record['formalization_basis'] == 'source_statement' and record['source_status'] != 'explicit_open':
        raise ValueError('A published mathematical statement requires explicit open-question evidence')
    if record['priority_status'] != 'not_established' and not first:
        raise ValueError('Priority evidence requires an earliest verified reference')
    if record['source_status'] in {'not_verified', 'resolved_or_misstated'} and first:
        raise ValueError('Unverified or misstated wording cannot claim a verified first reference')
    sources = record.get('references')
    if not isinstance(sources, list) or not sources:
        raise ValueError('At least one attributed supporting source is required')
    for source in sources:
        validate_reference(source)
    if first and any(sources[0].get(key) != first.get(key) for key in REFERENCE_FIELDS):
        raise ValueError('The earliest verified question reference and its audited metadata must be listed first')


def provenance(record):
    return {key: record.get(key) for key in ['original_id', 'field', 'kind',
      'formalization_basis', 'source_status', 'priority_status', 'priority_note',
      'earliest_verified_reference', 'current_reference', 'formalization_note']}


def canonical_record(record, category):
    return dict(id=record['id'], problem_number=f'LOCAL-{record["id"]}',
                title=record['title'], category_id=category['id'], category=category,
                status=status_for(record), external_url=None, legacy_ids=[],
                published=False, statement=record['short_statement'],
                economics=provenance(record))


def definition_tex(record, category, posted_date):
    metadata = canonical_record(record, category)
    metadata.update(statusQualification=record['status_qualification'],
                    statusReviewedAt=posted_date)
    n = record['id']
    first = record.get('earliest_verified_reference')
    evidence = ('An explicit question or research agenda was verified at the source locator. '
                'This does not by itself certify that every later version remains unresolved.' if first else
                'An explicit published open-question statement was not verified. Sources below '
                'are supporting literature and must not be treated as a first listing.')
    sources = []
    for index, source in enumerate(record['references'], 1):
        role = 'Earliest verified question/agenda reference; historical priority qualified below.' if first and index == 1 else source.get('reference_role', 'Supporting or current literature; see evidence qualification.')
        sources.append(r'\item[\textnormal{[S' + str(index) + r']}]\hypertarget{source:' + str(n) + ':' + str(index) + r'}{} '
          + reference_text(source) + '\n' + r'\url{' + source['url'] + '}.\n'
          + (tex_text('DOI: ' + source['doi']) + '.\n' if source.get('doi') else '')
          + r'{\small\textit{' + tex_text(role + ' ' + source['evidence_summary']) + '}}')
    return ('% TOP_PROBLEM: ' + json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
      + f'\n% FIRST_POSTED: {posted_date}\n% ENTRY_KIND: statement_only\n% !TeX program = lualatex\n'
      + r'''\documentclass[11pt]{article}
\usepackage{fontspec}
\usepackage[a4paper,margin=25mm]{geometry}
\usepackage{amsmath,amssymb,mathtools}
\usepackage{xurl}
\usepackage[hidelinks]{hyperref}
\newcommand{\sref}[2]{\hyperlink{source:#1:#2}{[S#2]}}
\setlength{\emergencystretch}{3em}
\begin{document}
'''
      + f'% problemId:{n}\n' + r'\section*{' + tex_text(record['title']) + r'}\label{' + str(n) + '}\n'
      + r'\subsection{Definitions and mathematical statement}' + '\n' + record['statement_tex']
      + '\n\n' + r'\par\textbf{Formulation and scope.} ' + tex_text(record['formalization_note'])
      + '\n\n' + r'\par\textbf{Open-question provenance.} ' + tex_text(evidence.rstrip('.') if first else evidence)
      + (r' \sref{' + str(n) + '}{1}.' if first else '')
      + '\n\n' + r'\par\textbf{Historical priority.} ' + tex_text(record['priority_note'])
      + '\n\n' + r'\subsection{Short English statement}' + '\n' + tex_text(record['short_statement'])
      + '\n\n' + r'\subsection{Sources}' + '\n' + r'\begin{itemize}\raggedright' + '\n'
      + '\n\n'.join(sources) + '\n' + r'\end{itemize}' + '\n' + r'\end{document}' + '\n')


def import_records(manifest, *, check=False, root=ROOT):
    records, category = manifest['records'], manifest['category']
    if len(records) != 250 or {r.get('original_id') for r in records} != set(range(1, 251)):
        raise ValueError('This batch must preserve all 250 original positions exactly once')
    if len({r.get('id') for r in records}) != len(records):
        raise ValueError('Duplicate reserved Economics identity')
    allocation = manifest.get('allocation', {})
    if allocation.get('reserved') is not True:
        raise ValueError('Economics identities must be reserved before import')
    assignments = allocation.get('assignments', [])
    reserved = {a.get('proposal_key'): a.get('id') for a in assignments}
    if len(assignments) != 250 or len(reserved) != 250 or any(
        reserved.get(f'economics-{r["original_id"]:03}') != r.get('id') for r in records
    ):
        raise ValueError('Economics identities must match the reservation report')
    watermark_path = root / 'lists/unsolvedmath/id_registry.json'
    watermark = json.loads(watermark_path.read_text())
    if watermark.get('last_allocated_id', 0) < max(r['id'] for r in records):
        raise ValueError('The ID watermark must preserve the complete reservation')
    if category.get('name') != 'economics' or category.get('display_name') != 'Economics':
        raise ValueError('This importer only adds the Economics category')
    registry_path = root / 'lists/unsolvedmath/problems.json'
    order_path = root / 'lists/unsolvedmath/display_order.json'
    registry, order = json.loads(registry_path.read_text()), json.loads(order_path.read_text())
    existing = {r['id']: r for r in registry}
    definitions = root / 'attacks/open_problems/top_problems/definitions'
    pending = []
    for record in sorted(records, key=lambda r: r['original_id']):
        validate_record(record)
        canonical = canonical_record(record, category)
        text = definition_tex(record, category, manifest['prepared_at'])
        path = definitions / f'{record["id"]}.tex'
        if record['id'] in existing:
            if existing[record['id']] != canonical or not path.exists() or path.read_text() != text:
                raise ValueError(f'Refusing to replace a different existing identity: {record["id"]}')
            if order.count(record['id']) != 1:
                raise ValueError('Every existing Economics identity requires exactly one display-order entry')
            continue
        if path.exists() or record['id'] in order:
            raise ValueError(f'Refusing to reuse an existing file or rank: {record["id"]}')
        if record['id'] <= max(existing):
            raise ValueError('New identities must exceed every existing catalogue ID')
        pending.append((canonical, path, text))
    if not check:
        for canonical, path, text in pending:
            path.write_text(text, encoding='utf-8')
            registry.append(canonical)
            order.append(canonical['id'])
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2)+'\n')
        order_path.write_text(json.dumps(order, ensure_ascii=False, indent=2)+'\n')
    return dict(validated=len(records), new_records=len(pending), wrote=not check)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'lists/economics/manifest.json')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(import_records(json.loads(args.manifest.read_text()), check=args.check)))
