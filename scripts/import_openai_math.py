#!/usr/bin/env python3
"""Generate original OpenAI claim summaries from an approved, pinned inventory.

No network operations are performed. The source checkout must already contain
the inventory's pinned commit. Summary inputs are JSON, either a mapping of
problem IDs to section objects or a directory of <id>.json section objects.
The required keys are claim, outline, scope, formal_verification, status_caveat.
They contain original TeX prose; the generator supplies the wrapper and Sources.

Approval is a separate JSON artifact with source_commit and approved_solved_ids.
Only IDs explicitly approved there can receive a solved claim. Every supporting
full/stronger row must also have second_pass: agreed. No approval is implied by
running this script. Review the adjudication and get user approval first.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from functools import lru_cache
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = 'https://github.com/openai/math'
SOURCE_COMMIT = 'adc7f1241b42e322a6451854ab7e4b4c146bf78a'
RELEASE_DATE = '2026-10-06'
SECTION_KEYS = {
    'claim': "OpenAI's claim",
    'outline': 'Outline of the argument',
    'scope': 'Scope relative to this problem',
    'formal_verification': 'Formal verification',
    'status_caveat': 'Status caveat',
}
PREAMBLE = r'''\documentclass[11pt]{article}
\usepackage[margin=25mm]{geometry}
\usepackage{fontspec}
\setmainfont{Latin Modern Roman}
\usepackage{amsmath,amssymb,mathtools}
\usepackage{unicode-math}
\setmathfont{Latin Modern Math}
\usepackage{enumitem}
\usepackage{xurl,hyperref,bookmark}
\hypersetup{colorlinks=true,urlcolor=blue}
\setcounter{secnumdepth}{0}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\setlength{\emergencystretch}{3em}
\begin{document}
'''


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def json_line(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def source_path(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError(f'Invalid source path: {value!r}')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path) != value:
        raise ValueError(f'Invalid source path: {value!r}')
    return value


def git(repo, *args, binary=False):
    result = subprocess.run(
        ['git', '-C', str(repo), *args], check=False, capture_output=True,
    )
    if result.returncode:
        raise ValueError(f'Local git operation failed: {result.stderr.decode("utf-8", "replace").strip()}')
    return result.stdout if binary else result.stdout.decode('utf-8')


def validate_inventory(inventory):
    if not isinstance(inventory, dict) or inventory.get('schema_version') != 1:
        raise ValueError('Unsupported inventory schema_version')
    if inventory.get('source_repo') != SOURCE_REPO or inventory.get('source_commit') != SOURCE_COMMIT:
        raise ValueError('Inventory must use the approved OpenAI source repository and pinned SHA')
    families = inventory.get('families')
    if not isinstance(families, list) or not families:
        raise ValueError('Inventory requires families')
    seen = set()
    indexed = {}
    for family in families:
        number = family.get('family')
        if not isinstance(number, str) or not re.fullmatch(r'\d{3}', number) or number in seen:
            raise ValueError(f'Invalid or duplicate family number: {number!r}')
        seen.add(number)
        for key in ('title', 'subject'):
            if not isinstance(family.get(key), str) or not family[key].strip():
                raise ValueError(f'Family {number} requires {key}')
        for key in ('lean_doc', 'reasoning_trace'):
            if family.get(key) is not None:
                source_path(family[key])
        manuscripts = family.get('manuscripts')
        if not isinstance(manuscripts, list) or not manuscripts:
            raise ValueError(f'Family {number} requires manuscripts')
        for manuscript in manuscripts:
            folder = manuscript.get('dir')
            if not isinstance(folder, str) or '/' in folder or '\\' in folder or folder in {'', '.', '..'}:
                raise ValueError('Manuscript dir must be a folder basename')
            key = (number, folder)
            if key in indexed:
                raise ValueError(f'Duplicate manuscript: {key}')
            if not isinstance(manuscript.get('title'), str) or not manuscript['title'].strip():
                raise ValueError('Manuscript requires a title')
            for name in ('pdf_path', 'readme_path', 'source_tex_dir'):
                source_path(manuscript.get(name))
            prefix = f'preprints/{folder}/'
            if not manuscript['pdf_path'].startswith(prefix) or not manuscript['pdf_path'].endswith('.pdf'):
                raise ValueError('PDF path must belong to its manuscript directory')
            if manuscript['readme_path'] != prefix + 'README.md':
                raise ValueError('README path must belong to its manuscript directory')
            date.fromisoformat(manuscript['date'])
            if manuscript.get('inputs_md') is not None:
                source_path(manuscript['inputs_md'])
            comparators = manuscript.get('comparators', [])
            if not isinstance(comparators, list):
                raise ValueError('Comparators must be an array')
            for comparator in comparators:
                for name in ('json', 'lean'):
                    source_path(comparator.get(name))
                if comparator.get('file'):
                    source_path(comparator['file'])
            indexed[key] = (family, manuscript)
    return indexed


def validate_checkout(repo, inventory):
    """Respect the prompt's stop rule; never silently change the checkout."""
    commit = git(repo, 'rev-parse', 'HEAD').strip()
    if commit != inventory['source_commit']:
        raise ValueError(f'Source checkout HEAD {commit} differs from pinned SHA {inventory["source_commit"]}; stop for review')
    if git(repo, 'status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('Source checkout has working-tree changes; use the clean pinned snapshot')
    return repo


def unicode_math_character(char):
    """Render mathematical Unicode with the document's math font in prose."""
    symbols = {'ℓ': r'\ell', 'ℂ': r'\mathbb C', 'ℝ': r'\mathbb R',
               'ℚ': r'\mathbb Q', 'ℤ': r'\mathbb Z', 'ℕ': r'\mathbb N',
               '≤': r'\leq', '≥': r'\geq', '≠': r'\neq', '≅': r'\cong',
               '∈': r'\in', '⊂': r'\subset', '⊆': r'\subseteq',
               '∩': r'\cap', '∪': r'\cup', '⊗': r'\otimes',
               '∞': r'\infty', '∗': r'\ast', '∼': r'\sim', '−': '-'}
    greek = 'αβγδεζηθικλμνξοπρστυφχψω'
    names = 'alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega'.split()
    symbols.update({letter: '\\' + name for letter, name in zip(greek, names)
                    if name != 'omicron'})
    symbols['ο'] = 'o'
    if char in symbols:
        return r'\(' + symbols[char] + r'\)'
    for alphabet, script in [('₀₁₂₃₄₅₆₇₈₉', '_'), ('⁰¹²³⁴⁵⁶⁷⁸⁹', '^')]:
        if char in alphabet:
            return r'\({}' + script + '{' + str(alphabet.index(char)) + r'}\)'
    return None


def tex_escape(text):
    escapes = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}',
               '%': r'\%', '#': r'\#', '_': r'\_', '&': r'\&',
               '$': r'\$', '^': r'\textasciicircum{}', '~': r'\textasciitilde{}'}
    return ''.join(escapes.get(char, unicode_math_character(char) or char)
                   for char in str(text))


def source_url(path, commit=SOURCE_COMMIT, mode='blob'):
    if mode not in {'blob', 'raw'}:
        raise ValueError('Source URL mode must be blob or raw')
    source_path(path)
    return f'{SOURCE_REPO}/{mode}/{commit}/' + quote(path, safe='/')


def tex_link(path, label, commit=SOURCE_COMMIT, mode='blob'):
    # Percent-encoding is performed before TeX escaping, including parentheses.
    url = tex_escape(source_url(path, commit, mode))
    return r'\href{' + url + '}{' + tex_escape(label) + '}'


def adjudication_rows(document):
    if isinstance(document, dict):
        if document.get('source_commit', SOURCE_COMMIT) != SOURCE_COMMIT:
            raise ValueError('Adjudication SHA differs from the pinned source')
        rows = document.get('rows')
    else:
        rows = document
    if not isinstance(rows, list):
        raise ValueError('Adjudication must contain a rows array')
    return rows


def approved_solved_ids(approval):
    if approval is None:
        return set()
    if not isinstance(approval, dict) or approval.get('source_commit') != SOURCE_COMMIT:
        raise ValueError('Approval artifact must identify the pinned source_commit')
    values = approval.get('approved_solved_ids', [])
    if not isinstance(values, list) or any(type(n) is not int or n < 1 for n in values):
        raise ValueError('Approval approved_solved_ids must contain positive integer IDs')
    if len(values) != len(set(values)):
        raise ValueError('Duplicate approved_solved_ids')
    return set(values)


def group_rows(document, inventory, approval=None):
    indexed = validate_inventory(inventory)
    approved = approved_solved_ids(approval)
    grouped = defaultdict(list)
    seen = set()
    for row in adjudication_rows(document):
        if not isinstance(row, dict):
            raise ValueError('Adjudication rows must be objects')
        # Deferred Erdős candidates are reported separately under default D4;
        # they are not mathematical verdicts or eligible site imports.
        if row.get('out_of_scope') is True:
            continue
        classification = row.get('class')
        if not isinstance(classification, str) or classification not in {'full', 'stronger', 'partial', 'related', 'none'}:
            raise ValueError('Unknown adjudication class')
        if classification in {'related', 'none'}:
            continue
        problem_id = row.get('candidate_id')
        if type(problem_id) is not int or problem_id < 1:
            raise ValueError('candidate_id must be a positive integer')
        key = (row.get('family'), row.get('manuscript_dir'))
        if key not in indexed:
            raise ValueError(f'Adjudication manuscript is absent from inventory: {key}')
        duplicate_key = (problem_id, *key)
        if duplicate_key in seen:
            raise ValueError(f'Duplicate adjudication row: {duplicate_key}')
        seen.add(duplicate_key)
        for field in ('openai_theorem_ref', 'our_clause', 'justification'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f'Adjudication requires {field}')
        if row.get('pool') not in {'A', 'B', 'C'}:
            raise ValueError('Adjudication pool must be A, B, or C (a new local target)')
        coverage = row.get('lean_covers_main_theorem')
        if coverage is not None and type(coverage) is not bool:
            raise ValueError('lean_covers_main_theorem must be true, false, or null')
        if classification in {'full', 'stronger'}:
            if row.get('resolution') not in {'proved', 'disproved'}:
                raise ValueError('A solved adjudication requires proved or disproved resolution')
            if row.get('second_pass') != 'agreed':
                raise ValueError('Solved rows require an agreed independent second pass')
            if problem_id not in approved:
                raise ValueError(f'Proposed solved label {problem_id} requires explicit user approval in approved_solved_ids')
        elif row.get('resolution') != 'partial':
            raise ValueError('Partial adjudication requires partial resolution')
        grouped[problem_id].append(row)
    return dict(sorted(grouped.items()))


def build_metadata(rows, inventory):
    indexed = validate_inventory(inventory)
    solved = [row for row in rows if row['class'] in {'full', 'stronger'}]
    resolutions = {row['resolution'] for row in solved}
    if len(resolutions) > 1:
        raise ValueError('Conflicting proof and disproof adjudications require review')
    match = ('stronger' if any(row['class'] == 'stronger' for row in solved) else 'full') if solved else 'partial'
    families = []
    by_family = defaultdict(list)
    for row in rows:
        by_family[row['family']].append(row)
    for number, family_rows in sorted(by_family.items()):
        original = indexed[(number, family_rows[0]['manuscript_dir'])][0]
        papers, comparator_paths, declarations = [], set(), set()
        for row in sorted(family_rows, key=lambda item: item['manuscript_dir']):
            manuscript = indexed[(number, row['manuscript_dir'])][1]
            papers.append({
                'title': manuscript['title'], 'pdf_path': manuscript['pdf_path'],
                'readme_path': manuscript['readme_path'], 'date': manuscript['date'],
                'theorem_ref': row['openai_theorem_ref'],
            })
            for comparator in manuscript.get('comparators', []):
                comparator_paths.update([comparator['lean'], comparator['json']])
                declaration = comparator.get('declaration')
                if isinstance(declaration, str) and declaration:
                    declarations.add(declaration)
                elif isinstance(declaration, list):
                    declarations.update(declaration)
        lean = None
        if original.get('lean_doc'):
            coverage = [row.get('lean_covers_main_theorem') for row in family_rows]
            # Mixed or unknown manuscript coverage cannot become full coverage.
            covers = False if False in coverage else None if None in coverage else True
            lean = {'doc_path': original['lean_doc'], 'comparators': sorted(comparator_paths),
                    'declarations': sorted(declarations), 'covers_main_theorem': covers}
        families.append({
            'family': number, 'title': original['title'], 'subject': original['subject'],
            'manuscripts': papers, 'lean': lean, 'reasoning_trace': original.get('reasoning_trace'),
        })
    return {
        'schema_version': 1, 'source_repo': SOURCE_REPO,
        'source_commit': SOURCE_COMMIT, 'release_date': RELEASE_DATE,
        'match': match, 'resolution': next(iter(resolutions)) if solved else 'partial',
        'independently_reviewed': False, 'second_pass': 'agreed' if solved else 'n/a',
        'families': families,
    }


def load_sections(path, problem_id):
    path = Path(path)
    document = read_json(path / f'{problem_id}.json') if path.is_dir() else read_json(path)
    sections = document.get(str(problem_id), document) if isinstance(document, dict) else document
    if not isinstance(sections, dict) or set(sections) != set(SECTION_KEYS):
        raise ValueError(f'Summary {problem_id} requires exactly: {", ".join(SECTION_KEYS)}')
    for key, text in sections.items():
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f'Summary {problem_id} has empty {key}')
        if re.search(r'(?m)^\s*%\s*(?:TOP_PROBLEM|FIRST_POSTED|ATTEMPT_STATUS|OPENAI_CLAIM|COLLECTION_METADATA|ENTRY_KIND):', text):
            raise ValueError('Summary prose cannot supply metadata headers')
        if re.search(r'\\(?:begin|end)\s*\{(?:document|filecontents\*?)\}|\\(?:section|subsection|input|include|write|immediate|openout|read|catcode|usepackage|documentclass)\b', text):
            raise ValueError('Summary inputs contain prose only; document, section, or external-file commands are forbidden')
        if re.search(r'https?://|\\(?:href|url)\b', text):
            raise ValueError('Summary links belong in deterministic Sources')
    return {key: sections[key].strip() for key in SECTION_KEYS}


def render_sources(metadata):
    items = []
    for family in metadata['families']:
        for manuscript in family['manuscripts']:
            folder = PurePosixPath(manuscript['pdf_path']).parts[1]
            title = tex_escape(manuscript['title'])
            citation = tex_escape('OAI:' + folder)
            items.append(r'\item OpenAI, \emph{' + title + '}, ' + manuscript['date']
                         + r'; citation key \texttt{' + citation + '}. '
                         + '; '.join([
                             tex_link(manuscript['pdf_path'], 'PDF (GitHub)'),
                             tex_link(manuscript['pdf_path'], 'PDF (direct)', mode='raw'),
                             tex_link(manuscript['readme_path'], 'Manuscript page and citation'),
                             tex_link(manuscript['pdf_path'], 'Latest version', commit='main'),
                         ]) + '.')
        if family['lean']:
            items.append(r'\item Family ' + family['family'] + ': '
                         + tex_link(family['lean']['doc_path'], 'Lean scope') + '.')
            for path in family['lean']['comparators']:
                items.append(r'\item ' + tex_link(path, 'Comparator ' + PurePosixPath(path).name) + '.')
        if family['reasoning_trace']:
            items.append(r'\item Family ' + family['family'] + ': '
                         + tex_link(family['reasoning_trace'], 'Reasoning summary') + '.')
    items.append(r'\item ' + tex_link('CONTENTS.md', 'OpenAI catalogue entry') + '.')
    return '\\subsection{Sources}\n\\begin{itemize}\n' + '\n'.join(items) + '\n\\end{itemize}\n'


def render_record(definition, metadata, sections):
    first_line = definition.splitlines()[0] if definition else ''
    if not first_line.startswith('% TOP_PROBLEM: '):
        raise ValueError('Definition must start with TOP_PROBLEM metadata')
    canonical = json.loads(first_line.partition(': ')[2])
    if type(canonical.get('id')) is not int or not isinstance(canonical.get('title'), str):
        raise ValueError('Definition metadata requires a canonical numeric ID and title')
    status = 'solved' if metadata['match'] in {'full', 'stronger'} else 'unresolved'
    header = '\n'.join([first_line, '% FIRST_POSTED: ' + RELEASE_DATE,
                        '% ATTEMPT_STATUS: ' + status,
                        '% OPENAI_CLAIM: ' + json_line(metadata)]) + '\n'
    body = r'\section*{' + tex_escape(canonical['title']) + '}\n'
    for key, heading in SECTION_KEYS.items():
        body += '\n\\subsection{' + heading + '}\n' + sections[key].strip() + '\n'
    return header + PREAMBLE + body + '\n' + render_sources(metadata) + '\\end{document}\n'


def prose_text(text, *, record=False):
    """Conservative word extraction: omit math, URLs, metadata and TeX wrappers."""
    text = re.sub(r'(?m)^\s*%[^\n]*', ' ', text)
    if record:
        start = text.find(r'\begin{document}')
        if start >= 0:
            text = text[start + len(r'\begin{document}'):]
        text = text.split(r'\subsection{Sources}', 1)[0]
        text = re.sub(r'\\(?:subsection|section)\*?\{[^{}]*\}', ' ', text)
    text = re.sub(r'\$\$[\s\S]*?\$\$|(?<!\\)\$[^$]*?(?<!\\)\$', ' ', text)
    text = re.sub(r'\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)', ' ', text)
    text = re.sub(r'\\begin\{(equation\*?|align\*?|gather\*?|displaymath|math)\}[\s\S]*?\\end\{\1\}', ' ', text)
    text = re.sub(r'https?://[^\s{}<>]+', ' ', text)
    text = re.sub(r'\[[^\]\n]*\]\([^\n]*?\)', ' ', text)
    text = re.sub(r'\\(?:label|ref|eqref|cite|citep|citet|hypertarget)\{[^{}]*\}', ' ', text)
    text = re.sub(r'\\[A-Za-z]+\*?', ' ', text)
    return re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", text.lower(), re.UNICODE)


def ngrams(tokens, size=8):
    return {tuple(tokens[i:i + size]) for i in range(max(0, len(tokens) - size + 1))}


@lru_cache(maxsize=32)
def original_grams(text):
    # Catalogue summaries recur for every record. Cache their normalized grams
    # while retaining bounded memory for the much larger PDF corpus.
    return ngrams(prose_text(text))


def theorem_environments(source):
    """Read common theorem environments, including paper-specific aliases."""
    names = {'theorem', 'thm', 'proposition', 'prop', 'lemma', 'corollary', 'cor', 'conjecture'}
    names.update(re.findall(r'\\newtheorem\*?\{([^}]+)\}', source))
    pattern = r'\\begin\{(' + '|'.join(re.escape(name) + r'\*?' for name in sorted(names)) + r')\}(?:\[[^\]]*\])?([\s\S]*?)\\end\{\1\}'
    return '\n'.join(match[1] for match in re.findall(pattern, source))


def allowed_exception_grams(exceptions, titles):
    """Exceptions are explicit, short, justified names; never general prose."""
    allowed = set()
    if exceptions is None:
        return allowed
    entries = exceptions.get('exceptions') if isinstance(exceptions, dict) else None
    if not isinstance(entries, list):
        raise ValueError('No-copy exceptions require an exceptions array')
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {'phrase', 'kind', 'justification'}:
            raise ValueError('Exceptions require phrase, kind, and justification')
        phrase, kind = entry['phrase'], entry['kind']
        if kind not in {'proper_name', 'conjecture_title'} or not isinstance(phrase, str):
            raise ValueError('Only proper-name and conjecture-title exceptions are allowed')
        words = prose_text(phrase)
        if not 8 <= len(words) <= 12 or not isinstance(entry['justification'], str) or len(entry['justification'].strip()) < 20:
            raise ValueError('An exception needs 8–12 words and a concrete justification')
        if kind == 'conjecture_title':
            if tuple(words) not in {tuple(prose_text(title)) for title in titles} or not re.search(r'\b(conjecture|hypothesis|problem|question)\b', phrase, re.I):
                raise ValueError('Conjecture-title exception must equal a known complete title')
        else:
            # Capitalizing prose cannot turn it into a vetted proper name.
            # Short names never form an entire eight-word matching gram. For
            # long titles require the known conjecture-title rule above.
            raise ValueError('Proper-name exceptions must identify names, not ordinary prose; complete eight-word matches require a known conjecture title')
        allowed.update(ngrams(words))
    return allowed


def original_texts(metadata, inventory, repo):
    """Collect all mandated original sources; missing tools or paths fail shut."""
    indexed = validate_inventory(inventory)
    # CONTENTS and overview include summaries and abstracts. Comparing their
    # complete prose is stricter than trying to guess summary boundaries.
    def pinned_text(path):
        return git(repo, 'show', f'{SOURCE_COMMIT}:{source_path(path)}')

    originals = [('CONTENTS.md', pinned_text('CONTENTS.md')),
                 ('overview.tex', pinned_text('overview.tex'))]

    def add_pdf(path):
        pdf = git(repo, 'show', f'{SOURCE_COMMIT}:{source_path(path)}', binary=True)
        try:
            result = subprocess.run(['pdftotext', '-enc', 'UTF-8', '-', '-'], input=pdf,
                                    check=False, capture_output=True)
        except FileNotFoundError as exc:
            raise ValueError('pdftotext is required for the no-copy check') from exc
        if result.returncode:
            raise ValueError(f'Cannot extract PDF: {path}')
        originals.append((path, result.stdout.decode('utf-8')))

    for family in metadata['families']:
        if family.get('reasoning_trace'):
            add_pdf(family['reasoning_trace'])
        for paper in family['manuscripts']:
            folder = PurePosixPath(paper['pdf_path']).parts[1]
            manuscript = indexed[(family['family'], folder)][1]
            add_pdf(paper['pdf_path'])
            # Some papers put their main theorem in build/paper.tex rather
            # than build/source/*.tex. Scan the complete manuscript build.
            source_dir = f'preprints/{folder}/build'
            sources = sorted(path for path in git(repo, 'ls-tree', '-r', '--name-only',
                SOURCE_COMMIT, '--', source_dir).splitlines() if path.endswith('.tex'))
            if not sources:
                raise ValueError(f'No source TeX found for {folder}')
            for path in sources:
                original = theorem_environments(pinned_text(path))
                if original:
                    originals.append((path, original))
    return originals


def check_no_copy(record, originals, exceptions=None, titles=()):
    own = ngrams(prose_text(record, record=True))
    allowed = allowed_exception_grams(exceptions, titles)
    failures = []
    for path, text in originals:
        for shared in sorted((own & original_grams(text)) - allowed):
            failures.append({'source': path, 'phrase': ' '.join(shared)})
    return failures


def read_definition(catalog_dir, problem_id):
    path = Path(catalog_dir) / 'definitions' / f'{problem_id}.tex'
    content = path.read_text(encoding='utf-8')
    first_line = content.splitlines()[0] if content else ''
    metadata = json.loads(first_line.removeprefix('% TOP_PROBLEM: '))
    if not first_line.startswith('% TOP_PROBLEM: ') or metadata.get('id') != problem_id:
        raise ValueError(f'Definition ID must match filename: {path}')
    return content


def prepare_import(inventory, adjudication, summaries, catalog_dir, *, approval=None,
                   version=1, repo=None, exceptions=None, manifest=None, export_dir=None):
    if type(version) is not int or version < 1:
        raise ValueError('Version must be a positive integer')
    groups = group_rows(adjudication, inventory, approval)
    export_dir = Path(export_dir or ROOT / 'lists/unsolvedmath')
    registry = read_json(export_dir / 'problems.json')
    order = read_json(export_dir / 'display_order.json')
    if not isinstance(registry, list) or not isinstance(order, list):
        raise ValueError('Site registry and display order must be arrays')
    registered = {record['id'] for record in registry}
    if len(registered) != len(registry) or len(set(order)) != len(order) or set(order) != registered:
        raise ValueError('Site registry and display order must contain the same unique IDs')
    missing = set(groups) - registered
    if missing:
        raise ValueError(f'Import missing statements into the site registry before generating records: {sorted(missing)}')
    repo = Path(repo or inventory.get('repo_path', ''))
    validate_checkout(repo, inventory)
    # Import lazily so inventory and diff modes do not require site build setup.
    sys.path.insert(0, str(ROOT))
    from build_site import parse_openai_claim
    pending, unchanged = {}, []
    for problem_id, rows in groups.items():
        definition = read_definition(catalog_dir, problem_id)
        metadata = build_metadata(rows, inventory)
        record = render_record(definition, metadata, load_sections(summaries, problem_id))
        parse_openai_claim(record, manifest=manifest)
        title = json.loads(definition.splitlines()[0].partition(': ')[2])['title']
        titles = [title] + [family['title'] for family in metadata['families']]
        titles.extend(paper['title'] for family in metadata['families'] for paper in family['manuscripts'])
        failures = check_no_copy(record, original_texts(metadata, inventory, repo), exceptions, titles)
        if failures:
            raise ValueError(f'No-copy check failed for {problem_id}: {json.dumps(failures, ensure_ascii=False)}')
        suffix = '' if version == 1 else f'_v{version}'
        destination = Path(catalog_dir) / 'openai' / f'{problem_id}{suffix}.tex'
        if destination.exists():
            if destination.read_bytes() != record.encode('utf-8'):
                raise ValueError(f'Existing OpenAI record differs: {destination}; choose a new --version')
            unchanged.append(destination)
        else:
            pending[destination] = record
    return pending, unchanged


def apply_import(pending):
    """Preflight every destination, then create exclusively; never overwrite."""
    if any(path.exists() for path in pending):
        raise ValueError('A destination appeared after validation; rerun the dry run')
    for path, record in pending.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as output:
            output.write(record.encode('utf-8'))


def inventory_diff(inventory, repo, new_sha):
    """Compare a locally available commit without fetching or changing HEAD."""
    validate_inventory(inventory)
    if not re.fullmatch(r'[0-9a-f]{40}', new_sha or ''):
        raise ValueError('--diff requires a complete lowercase 40-character commit SHA')
    git(repo, 'cat-file', '-e', new_sha + '^{commit}')
    old_sha = inventory['source_commit']
    git(repo, 'cat-file', '-e', old_sha + '^{commit}')
    old = git(repo, 'ls-tree', '-r', '-z', old_sha, '--', 'preprints', binary=True)
    new = git(repo, 'ls-tree', '-r', '-z', new_sha, '--', 'preprints', binary=True)

    def folders(tree):
        found = defaultdict(dict)
        for entry in tree.split(b'\0'):
            if not entry:
                continue
            details, path = entry.split(b'\t', 1)
            path = path.decode('utf-8')
            parts = PurePosixPath(path).parts
            if len(parts) >= 3:
                found[parts[1]][path] = details.decode('ascii').split()[2]
        return found

    before, after = folders(old), folders(new)
    # The inventory identifies the previous manuscript folders, rather than
    # accidentally treating miscellaneous preprints files as known papers.
    known = {paper['dir'] for family in inventory['families'] for paper in family['manuscripts']}
    return {'source_commit': old_sha, 'new_commit': new_sha,
            'added': sorted(set(after) - known),
            'removed': sorted(known - set(after)),
            'changed': sorted(folder for folder in known & set(after) if before.get(folder) != after[folder])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--repo', type=Path, help='Existing pinned source checkout; never fetched or reset')
    parser.add_argument('--adjudication', type=Path)
    parser.add_argument('--summaries', type=Path, help='Per-ID original section JSON file or directory')
    parser.add_argument('--approval', type=Path, help='User-approved source_commit and approved_solved_ids JSON')
    parser.add_argument('--manifest', type=Path, default=ROOT / 'lists/openai_math/manifest.json')
    parser.add_argument('--catalog-dir', type=Path, default=ROOT / 'attacks/open_problems/top_problems')
    parser.add_argument('--export-dir', type=Path, default=ROOT / 'lists/unsolvedmath')
    parser.add_argument('--version', type=int, default=1)
    parser.add_argument('--dry-run', action='store_true', help='Validate all records without writing')
    parser.add_argument('--diff', metavar='NEW_SHA', help='Compare only a commit already present in local git')
    parser.add_argument('--check-no-copy', type=Path, metavar='RECORD', help='Check an existing generated record')
    parser.add_argument('--exceptions', type=Path, help='Explicit justified proper-name/conjecture-title exceptions')
    args = parser.parse_args()
    try:
        inventory = read_json(args.inventory)
        repo = args.repo or inventory.get('repo_path')
        if not repo:
            raise ValueError('An existing source checkout is required via --repo or inventory repo_path')
        if args.diff:
            if args.check_no_copy or args.adjudication or args.summaries:
                raise ValueError('--diff cannot be combined with generation or no-copy inputs')
            print(json.dumps(inventory_diff(inventory, repo, args.diff), ensure_ascii=False, indent=2))
            return
        exceptions = read_json(args.exceptions) if args.exceptions else None
        manifest = read_json(args.manifest)
        if args.check_no_copy:
            validate_checkout(repo, inventory)
            sys.path.insert(0, str(ROOT))
            from build_site import parse_openai_claim
            record = args.check_no_copy.read_text(encoding='utf-8')
            metadata, _ = parse_openai_claim(record, manifest=manifest)
            if not metadata:
                raise ValueError('No OPENAI_CLAIM metadata found in record')
            title = json.loads(record.splitlines()[0].partition(': ')[2])['title']
            titles = [title] + [family['title'] for family in metadata['families']]
            titles.extend(paper['title'] for family in metadata['families'] for paper in family['manuscripts'])
            failures = check_no_copy(record, original_texts(metadata, inventory, Path(repo)), exceptions, titles)
            print(json.dumps({'passed': not failures, 'failures': failures}, ensure_ascii=False, indent=2))
            if failures:
                raise ValueError('No-copy check failed')
            return
        if not args.adjudication or not args.summaries:
            raise ValueError('Generation requires --adjudication and --summaries')
        pending, unchanged = prepare_import(
            inventory, read_json(args.adjudication), args.summaries, args.catalog_dir,
            approval=read_json(args.approval) if args.approval else None,
            version=args.version, repo=repo, exceptions=exceptions, manifest=manifest,
            export_dir=args.export_dir,
        )
        if not args.dry_run:
            apply_import(pending)
        print(json.dumps({'dry_run': args.dry_run, 'planned': [str(path) for path in pending],
                          'created': [] if args.dry_run else [str(path) for path in pending],
                          'unchanged': [str(path) for path in unchanged]}, indent=2))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
