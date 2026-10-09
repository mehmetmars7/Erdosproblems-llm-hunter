#!/usr/bin/env python3
"""One-time import of the supplied Economics statements and initial ranking.

Actual section/ProblemClassification pairs are authoritative. The source's
MERGED_PROBLEM comments and claimed count are stale and cannot own identity.
Once the registry exists, this command refuses to recreate permanent IDs.
Use update_economics_ranks.py for future ranking changes.
"""

import argparse
from bisect import bisect_left
import csv
import hashlib
import json
from pathlib import Path
import re

try:
    from .economics_catalog import (BASE_DIR, REGISTRY_PATH, RANKINGS_PATH,
                                    STATEMENTS_PATH, STATEMENT_START, STATEMENT_END,
                                    generate_economics_data, normalize_title,
                                    ranking_csv_text, validate_rank_values)
except ImportError:
    from economics_catalog import (BASE_DIR, REGISTRY_PATH, RANKINGS_PATH,
                                   STATEMENTS_PATH, STATEMENT_START, STATEMENT_END,
                                   generate_economics_data, normalize_title,
                                   ranking_csv_text, validate_rank_values)


def braced_argument(text, start):
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != '{':
        raise ValueError(f'Expected braced TeX argument near offset {start}')
    depth = 1
    index = start + 1
    while index < len(text):
        if text[index] == '\\':
            index += 2
            continue
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:index], index + 1
        index += 1
    raise ValueError(f'Unclosed TeX argument near offset {start}')


def common_conventions(tex):
    """Retain the source-wide assumptions needed by isolated statements."""
    contexts = {}
    group_names = iter(('atlas', 'game', 'definitions', 'beyond'))
    for match in re.finditer(r'\\section\*\s*\{', tex):
        title, end = braced_argument(tex, match.end() - 1)
        if title == 'Source mathematical conventions':
            key = next(group_names)
        elif title == 'BSDE conventions for SC-01--SC-06':
            key = 'bsde'
        elif title == 'Control and stopping conventions for SC-07--SC-08':
            key = 'control'
        elif title == 'Additional-source status and mathematical conventions':
            key = 'audited'
        else:
            continue
        boundary = re.search(
            r'^(?:[ \t]*% MERGED_PROBLEM:|[ \t]*(?:\\clearpage\s*)?'
            r'\\(?:section\*?\s*\{|part\s*\{|appendix\b))',
            tex[end:], re.MULTILINE)
        body_end = end + boundary.start() if boundary else len(tex)
        body = tex[end:body_end]
        body = re.sub(r'^% Insert before[^\n]*(?:\n|$)', '', body, flags=re.MULTILINE)
        # Drop navigation metadata, while retaining all mathematical prose.
        body = body.replace('\\phantomsection', '')
        while '\\addcontentsline' in body:
            navigation = re.search(r'\\addcontentsline\s*\{', body)
            if not navigation:
                break
            command_end = navigation.end() - 1
            for _ in range(3):
                _, command_end = braced_argument(body, command_end)
            body = body[:navigation.start()] + body[command_end:]
        body = re.sub(r'\\clearpage\s*$', '', body).strip()
        contexts[key] = {'title': title, 'tex': body}
    if set(contexts) != {'atlas', 'game', 'definitions', 'beyond', 'bsde', 'control', 'audited'}:
        raise ValueError('Source must contain all seven shared mathematical convention groups')
    return contexts


def parse_source(tex):
    contexts = common_conventions(tex)
    sections = []
    for match in re.finditer(r'\\section\s*\{', tex):
        title, end = braced_argument(tex, match.end() - 1)
        sections.append((match.start(), end, title))
    section_starts = [section[0] for section in sections]
    markers = list(re.finditer(r'^\s*% MERGED_PROBLEM:\s*(\{[^\n]+\})\s*$', tex, re.MULTILINE))
    entries = []
    previous_section = -1
    for match in re.finditer(r'\\ProblemClassification\s*\{', tex):
        args = []
        end = match.end() - 1
        for _ in range(4):
            argument, end = braced_argument(tex, end)
            args.append(argument)
        index = bisect_left(section_starts, match.start()) - 1
        if index < 0:
            raise ValueError('ProblemClassification has no preceding problem section')
        section_start, section_end, title = sections[index]
        if section_start == previous_section:
            raise ValueError(f'Multiple classification blocks for {title}')
        if tex[section_end:match.start()].strip():
            raise ValueError(f'Unexpected content before classification for {title}')
        source_id, jel, catalog, original_id = args
        if not re.fullmatch(r'OP-\d{4}', source_id) or not re.fullmatch(r'[A-Z]\d{2}', jel):
            raise ValueError(f'Invalid source identity: {source_id}/{jel}')
        # Cut before any new problem, part, catalogue audit or appendix. These
        # structures can appear before the next MERGED_PROBLEM comment.
        boundary = re.search(
            r'^(?:[ \t]*% MERGED_PROBLEM:|[ \t]*(?:\\clearpage\s*)?'
            r'\\(?:section\*?\s*\{|part\s*\{|appendix\b))',
            tex[end:], re.MULTILINE)
        body_end = end + boundary.start() if boundary else len(tex)
        body = tex[end:body_end]
        body = re.sub(r'\\label\{difficulty-rank:[^}]+\}\s*', '', body)
        body = re.sub(r'\\label\{' + re.escape(jel) + r'\}\s*', '', body)
        # Classification prose is superseded by primary JEL metadata. Keep
        # adjacent provenance, formulation, scope and status qualifications.
        body = re.sub(r'\\textbf\{Classification:\}\s*[\s\S]*?(?=\\textbf\{Formulation:\})', '', body)
        body = body.strip() + '\n'
        if not re.search(r'\\subsection\*?\s*\{', body):
            raise ValueError(f'No statement subsections for {source_id}: {title}')
        nearby_markers = [marker for marker in markers
                          if previous_section < marker.start() < section_start]
        metadata = json.loads(nearby_markers[-1][1]) if nearby_markers else {}
        comment_metadata = {}
        if metadata and (metadata.get('id') != source_id or metadata.get('jel') != jel):
            # A replaced section retained an obsolete comment in the upload.
            # Keep that discrepancy for audit, never present it as provenance.
            comment_metadata, metadata = metadata, {}
        source_labels = list(dict.fromkeys(re.findall(r'\\label\{([^}]+)\}', body)))
        group = {'Atlas': 'atlas', 'Game theory': 'game', 'Supplement': 'game',
                 'Research addendum': 'game', 'Formal definitions': 'definitions',
                 'Beyond game theory': 'beyond', 'Audited economics': 'audited'}.get(catalog)
        if not group:
            raise ValueError(f'Unknown source collection for shared conventions: {catalog}')
        context_keys = [group]
        if catalog == 'Beyond game theory' and original_id in {f'SC-{n:02}' for n in range(1, 7)}:
            context_keys.append('bsde')
        if catalog == 'Beyond game theory' and original_id in {'SC-07', 'SC-08'}:
            context_keys.append('control')
        if group != 'audited' and any(label.startswith('audited:') for label in source_labels):
            context_keys.append('audited')
        for context_key in context_keys:
            context = contexts[context_key]
            body += ('\n\\subsection*{Common conventions: ' + context['title'] + '}\n\n'
                     + context['tex'] + '\n')
        entries.append({
            'title': title, 'jel_code': jel, 'source_id': source_id,
            'source_catalog': catalog, 'source_original_id': original_id,
            'source_metadata': metadata,
            'source_comment_metadata': comment_metadata,
            'source_labels': source_labels,
            'convention_groups': context_keys,
            'body': body,
        })
        previous_section = section_start
    keys = [(entry['source_id'], normalize_title(entry['title']), entry['jel_code'])
            for entry in entries]
    if len(set(keys)) != len(keys):
        raise ValueError('The source contains duplicate OP/title/JEL statement identities')
    return entries


def initial_ranking(path, entries):
    by_source = {(entry['source_id'], normalize_title(entry['title']), entry['jel_code']): entry
                 for entry in entries}
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        required = {'Problem ID', 'New rank', 'Problem title', 'JEL code'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Initial ranking requires Problem ID, New rank, Problem title and JEL code')
        rows = list(reader)
    ranks = {}
    for row_number, row in enumerate(rows, 2):
        key = ((row.get('Problem ID') or '').strip(),
               normalize_title(row.get('Problem title') or ''),
               (row.get('JEL code') or '').strip())
        if key not in by_source:
            raise ValueError(f'Row {row_number}: no exact OP/title/JEL source match: {key}')
        if key in ranks:
            raise ValueError(f'Row {row_number}: duplicate source identity: {key}')
        value = (row.get('New rank') or '').strip()
        if not re.fullmatch(r'[1-9][0-9]*', value):
            raise ValueError(f'Row {row_number}: New rank must be a positive integer')
        ranks[key] = int(value)
    missing = set(by_source) - set(ranks)
    if missing:
        raise ValueError(f'Ranking coverage is incomplete; {len(missing)} statements missing')
    validate_rank_values(list(ranks.values()), len(entries))
    return ranks


def statement_document(record, body):
    # Preserve the supplied notation and metadata macros. Each downloadable
    # statement is a self-contained XeLaTeX/LuaLaTeX article, without attempts.
    preamble = r'''% !TeX program = xelatex
\documentclass[11pt,a4paper]{article}
\usepackage[margin=23mm]{geometry}
\usepackage{fontspec}
\setmainfont{Latin Modern Roman}
\usepackage{amsmath,amssymb,mathtools}
\usepackage{xcolor,enumitem,booktabs,longtable,array,xurl,hyperref}
\definecolor{muted}{HTML}{53636C}
\hypersetup{colorlinks=true,urlcolor=blue,linkcolor=blue}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\newcommand{\R}{\mathbb R}
\newcommand{\E}{\mathbb E}
\newcommand{\N}{\mathbb N}
\newcommand{\ind}{\mathbf 1}
\newcommand{\Var}{\operatorname{Var}}
\newcommand{\Cov}{\operatorname{Cov}}
\newcommand{\supp}{\operatorname{supp}}
\DeclareMathOperator*{\argmin}{arg\,min}
\DeclareMathOperator*{\argmax}{arg\,max}
\newcommand{\entrymeta}[3]{{\sffamily\small\color{muted}\textbf{\texttt{#1}}\quad|\quad #2\par #3\par}}
\newcommand{\Problemref}[1]{\texttt{#1}}
\newcommand{\JELref}[2]{\texttt{#2} (JEL \texttt{#1})}
\begin{document}
'''
    metadata = json.dumps({key: record[key] for key in ('id', 'title', 'jel_code', 'source_id')}, ensure_ascii=False)
    heading = (f"\\section*{{{record['title']}}}\n"
               f"\\textbf{{Problem ID:}} \\texttt{{{record['id']}}}\\quad "
               f"\\textbf{{JEL:}} \\texttt{{{record['jel_code']}}}\\par\n")
    return ('% ECONOMICS_PROBLEM: ' + metadata + '\n' + preamble + heading
            + STATEMENT_START + body + STATEMENT_END + '\n\\end{document}\n')


def assign_verified_reference_aliases(records):
    """Resolve only the cross-reference whose supplied wording is unambiguous.

    The quitting-game statement says 'stochastic games in OP-0590'. The source
    reused OP-0590 for an unrelated EFX statement, so a global OP lookup would
    be ambiguous. Resolve its explicitly named stochastic-game target once.
    """
    by_source = {(record['source_id'], record['title'], record['jel_code']): record
                 for record in records}
    quitting = by_source.get(('OP-0591', 'Ordinary uniform approximate equilibria in quitting games', 'C73'))
    stochastic = by_source.get(('OP-0590', 'Equilibrium payoffs in finite multiplayer stochastic games', 'C73'))
    if quitting and stochastic:
        quitting['reference_aliases'] = {'problem:OP-0590': stochastic['id']}


def import_economics(tex_path, ranking_path, base_dir=BASE_DIR):
    base_dir = Path(base_dir)
    if (base_dir / REGISTRY_PATH).exists():
        raise ValueError('Economics registry already exists; permanent IDs cannot be regenerated. '
                         'Use scripts/update_economics_ranks.py to change ranks.')
    tex_bytes = Path(tex_path).read_bytes()
    entries = parse_source(tex_bytes.decode('utf-8-sig'))
    ranks = initial_ranking(ranking_path, entries)
    records = []
    statements = {}
    for entry in entries:
        key = (entry['source_id'], normalize_title(entry['title']), entry['jel_code'])
        rank = ranks[key]
        problem_id = f"{entry['jel_code']}-{rank}"
        body = entry.pop('body')
        record = dict(entry, id=problem_id, initial_rank=rank,
                      statement_file=str(STATEMENTS_PATH / f'{problem_id}.tex'))
        records.append(record)
        statements[problem_id] = statement_document(record, body)
    records.sort(key=lambda record: record['initial_rank'])
    assign_verified_reference_aliases(records)
    outputs = [base_dir / record['statement_file'] for record in records]
    outputs.extend([base_dir / REGISTRY_PATH, base_dir / RANKINGS_PATH])
    if any(path.exists() for path in outputs):
        raise ValueError('Economics import would overwrite existing files; no files were changed')
    registry = {
        'schema_version': 1,
        'identity_policy': 'ID assigned from JEL and initial CSV rank once; current ranks never rename IDs',
        'problem_count': len(records),
        'source_tex_name': Path(tex_path).name,
        'source_tex_sha256': hashlib.sha256(tex_bytes).hexdigest(),
        'initial_ranking_name': Path(ranking_path).name,
        'initial_ranking_sha256': hashlib.sha256(Path(ranking_path).read_bytes()).hexdigest(),
        'source_note': ('Source prose reports 653 entries, but 657 actual classified statements match '
                        'all 657 CSV rows. Reused OP IDs are resolved by exact OP/title/JEL triplets.'),
        'problems': records,
    }
    for record in records:
        path = base_dir / record['statement_file']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(statements[record['id']], encoding='utf-8')
    (base_dir / REGISTRY_PATH).parent.mkdir(parents=True, exist_ok=True)
    (base_dir / REGISTRY_PATH).write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    mutable_ranks = {record['id']: record['initial_rank'] for record in records}
    (base_dir / RANKINGS_PATH).write_text(ranking_csv_text(records, mutable_ranks), encoding='utf-8')
    generate_economics_data(base_dir)
    return registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tex', type=Path, required=True)
    parser.add_argument('--ranks', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=BASE_DIR)
    args = parser.parse_args()
    registry = import_economics(args.tex, args.ranks, args.root)
    print(f"Imported {registry['problem_count']} Economics statements; permanent IDs frozen")


if __name__ == '__main__':
    main()
