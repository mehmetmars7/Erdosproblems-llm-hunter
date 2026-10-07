#!/usr/bin/env python3
"""Import labeled UnsolvedMath statements without replacing existing files.

The full registry verifies identity. The website's portable registry and display
order are extended only for newly created standalone statements.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_site import parse_numbered_problem_tex, replace_tex_command
from scripts.migrate_unsolvedmath import atomic_write, encode_json, upstream_problem_url

MARKER = re.compile(r'^% UnsolvedMath ID ([1-9]\d*); source catalogue code ([^\r\n]+)', re.M)
DEFINITIONS = r'\subsection{Definitions and mathematical statement}'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def prepare_import(source, registry_path, catalog_dir, export_dir):
    source, registry_path = Path(source), Path(registry_path)
    catalog_dir, export_dir = Path(catalog_dir), Path(export_dir)
    source_bytes = source.read_bytes()
    content = source_bytes.decode('utf-8')
    if content.count(r'\begin{document}') != 1 or content.count(r'\end{document}') != 1:
        raise ValueError('Expected one complete source document')
    preamble, body = content.split(r'\begin{document}', 1)
    body, trailing = body.split(r'\end{document}', 1)
    if trailing.strip():
        raise ValueError('Unexpected text after the document')
    markers = list(MARKER.finditer(body))
    if not markers:
        raise ValueError('No UnsolvedMath section markers')
    introduction = body[:markers[0].start()]
    notation = re.search(r'\\textbf\{Notation\.\}([\s\S]+?)\\textbf\{Attribution\.\}', introduction)
    if not notation:
        raise ValueError('Missing shared notation: do not discard inherited conventions')
    notation = r'\paragraph{Shared notation.}' + notation[1].strip() + '\n\n'
    registry_bytes = registry_path.read_bytes()
    registry = json.loads(registry_bytes)
    by_id = {record['id']: record for record in registry}
    if len(by_id) != len(registry):
        raise ValueError('Duplicate IDs in the full UnsolvedMath registry')
    code_counts = collections.Counter(record['problem_number'] for record in registry)
    records_path, order_path = export_dir / 'problems.json', export_dir / 'display_order.json'
    export_before = {path.name: path.read_bytes() for path in (records_path, order_path)}
    records, order = json.loads(export_before['problems.json']), json.loads(export_before['display_order.json'])
    selected_ids = {record['id'] for record in records}
    if len(selected_ids) != len(records) or len(set(order)) != len(order) or set(order) != selected_ids:
        raise ValueError('Invalid existing website registry or display order')
    documents, duplicates, entries, seen = {}, [], [], set()
    for index, marker in enumerate(markers):
        problem_id, code = int(marker[1]), marker[2].strip()
        if problem_id in seen:
            raise ValueError(f'Repeated source ID: {problem_id}')
        seen.add(problem_id)
        record = by_id.get(problem_id)
        if not record or record['problem_number'] != code:
            raise ValueError(f'UnsolvedMath ID/code mismatch: {problem_id} ({code})')
        stop = markers[index + 1].start() if index + 1 < len(markers) else len(body)
        chunk = body[marker.start():stop]
        end_label = rf'\label{{end:{problem_id}}}'
        if chunk.count(end_label) != 1:
            raise ValueError(f'Missing or repeated end label for {problem_id}')
        end = chunk.index(end_label) + len(end_label)
        if chunk[end:].replace(r'\clearpage', '').strip():
            raise ValueError(f'Unexpected trailing content for {problem_id}')
        section = chunk[:end]
        numeric_labels = re.findall(r'\\label\{(\d+)\}', section)
        if numeric_labels != [str(problem_id)]:
            raise ValueError(f'Numeric label does not match UnsolvedMath ID {problem_id}')
        if rf'\setcounter{{section}}{{{problem_id - 1}}}' not in section:
            raise ValueError(f'Section counter does not match ID {problem_id}')
        visible = re.search(r'UnsolvedMath ID (\d+) · ([^}\n]+)\}', section)
        if not visible or int(visible[1]) != problem_id or visible[2] != record['category']['display_name']:
            raise ValueError(f'Visible ID/category mismatch for {problem_id}')
        attribution_codes = (code, code.replace('_', r'\_'))
        if not any(f'record {problem_id} ({value})' in section for value in attribution_codes):
            raise ValueError(f'Source attribution disagrees with ID {problem_id}')
        titles = []
        replace_tex_command(section, 'section', 1, lambda title: titles.append(title) or '')
        if len(titles) != 1:
            raise ValueError(f'Expected one section title for {problem_id}')
        headings = re.findall(r'^\\subsection\{([^}\n]+)\}', section, re.M)
        if headings != ['Definitions and mathematical statement', 'Short English statement', 'Sources']:
            raise ValueError(f'Unexpected statement structure for {problem_id}')
        if section.count(r'\cataloguescope{') != 1:
            raise ValueError(f'Expected one recorded target for {problem_id}')
        refs = re.findall(r'\\sref\{(\d+)\}\{(\d+)\}', section)
        anchors = set(re.findall(r'\\hypertarget\{source:(\d+):(\d+)\}', section))
        if any(scope != str(problem_id) or (scope, number) not in anchors for scope, number in refs):
            raise ValueError(f'Nonlocal or missing source reference for {problem_id}')
        destination = catalog_dir / f'{problem_id}.tex'
        audit = {'id': problem_id, 'problem_number': code, 'title': record['title'],
                 'source_title': titles[0], 'category_id': record['category_id'],
                 'identity_verified': True, 'source_section_sha256': sha256(section.encode()),
                 'destination': str(destination), 'action': 'created'}
        if destination.exists():
            audit.update(action='skipped_existing', destination_sha256=sha256(destination.read_bytes()))
            duplicates.append({'id': problem_id, 'title': record['title'], 'path': str(destination)})
            entries.append(audit)
            continue
        if problem_id in selected_ids:
            raise ValueError(f'Website registry already contains {problem_id} but its statement is missing')
        metadata = {key: record[key] for key in ('id', 'title', 'category_id', 'category', 'status')}
        # These are display-wrapper changes only. The target and reference prose
        # stay as supplied, including explicit repairs and scope qualifications.
        rendered = replace_tex_command(section, 'cataloguescope', 1,
            lambda target: r'\paragraph{Statement recorded in the supplied source.}' + '\n' + target)
        rendered = re.sub(r'(\\item\[\\hypertarget\{source:\d+:\d+\}\{)\[([A-Z]\d+)\](\}\])',
                          r'\1\2\3', rendered)
        rendered = rendered.replace(DEFINITIONS, DEFINITIONS + '\n\n' + notation, 1)
        wrapper = re.sub(r'^% Compile twice:.*$', f'% Compile twice: lualatex {problem_id}.tex', preamble, flags=re.M)
        wrapper = re.sub(r'pdftitle=\{[^}]*\}', f'pdftitle={{UnsolvedMath Problem {problem_id}}}', wrapper)
        document = ('% TOP_PROBLEM: ' + json.dumps(metadata, ensure_ascii=False) + '\n'
                    '% FIRST_POSTED: null\n% ENTRY_KIND: statement_only\n'
                    f'% Imported from: {source.name}; UnsolvedMath ID {problem_id}\n'
                    + wrapper + '\\begin{document}\n' + rendered + '\n\\end{document}\n')
        parsed = parse_numbered_problem_tex(document, require_source_urls=False)
        if not parsed['sources'] or not any(source.get('url') for source in parsed['sources']):
            raise ValueError(f'No attributable sources for {problem_id}')
        if len(parsed['sources']) != len(anchors):
            raise ValueError(f'Lost source entries while importing {problem_id}')
        if parsed['researchTeX']:
            raise ValueError(f'Statement unexpectedly includes research for {problem_id}')
        selected = {key: record[key] for key in ('id', 'problem_number', 'title', 'category_id', 'category', 'status')}
        selected.update(external_url=upstream_problem_url(record, code_counts), legacy_ids=[],
                        statement=parsed['exactTarget'])
        records.append(selected)
        order.append(problem_id)
        documents[problem_id] = document
        audit.update(destination_sha256=sha256(document.encode()), sources=len(parsed['sources']))
        entries.append(audit)
    return dict(source=source, source_sha256=sha256(source_bytes), registry_path=registry_path,
                registry_sha256=sha256(registry_bytes), catalog_dir=catalog_dir, export_dir=export_dir,
                export_before=export_before, documents=documents, duplicates=duplicates,
                records=records, order=order, entries=entries)


def apply_import(plan):
    # Recheck inputs and all destinations before the first write.
    for key in ('source', 'registry'):
        path = plan['source'] if key == 'source' else plan['registry_path']
        if sha256(path.read_bytes()) != plan[key + '_sha256']:
            raise ValueError(f'{key} changed since validation')
    for name, previous in plan['export_before'].items():
        if (plan['export_dir'] / name).read_bytes() != previous:
            raise ValueError(f'Website export changed since validation: {name}')
    for problem_id in plan['documents']:
        if (plan['catalog_dir'] / f'{problem_id}.tex').exists():
            raise ValueError(f'Destination appeared after validation: {problem_id}.tex')
    for problem_id, document in plan['documents'].items():
        with (plan['catalog_dir'] / f'{problem_id}.tex').open('xb') as output:
            output.write(document.encode('utf-8'))
    if plan['documents']:
        atomic_write(plan['export_dir'] / 'problems.json', encode_json(plan['records']))
        atomic_write(plan['export_dir'] / 'display_order.json', encode_json(plan['order']))


def main():
    root = Path(__file__).resolve().parents[1]
    local = root.parent / '_Local/Erdos_problems/UnsolvedMath'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--registry', type=Path, default=local / 'problems.json')
    parser.add_argument('--catalog-dir', type=Path, default=root / 'attacks/open_problems/top_problems/definitions',
                        help='Directory containing numbered definition files')
    parser.add_argument('--export-dir', type=Path, default=root / 'lists/unsolvedmath')
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--apply', action='store_true', help='Create validated missing files; otherwise dry run')
    args = parser.parse_args()
    plan = prepare_import(args.source, args.registry, args.catalog_dir, args.export_dir)
    if args.apply:
        apply_import(plan)
    report = {key: plan[key] for key in ('source_sha256', 'registry_sha256', 'duplicates', 'entries')}
    report.update(source=str(args.source), applied=args.apply, source_entries=len(plan['entries']),
                  created=len(plan['documents']) if args.apply else 0, planned=len(plan['documents']),
                  skipped_existing=len(plan['duplicates']), catalogue_total=len(plan['records']))
    if args.audit:
        atomic_write(args.audit, encode_json(report))
    print(json.dumps({key: value for key, value in report.items() if key != 'entries'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
