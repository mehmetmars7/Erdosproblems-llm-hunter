#!/usr/bin/env python3
"""
Build script for Erdosproblems-llm-hunter website.
Reads TeX files from the attacks directory and saved problem catalogs,
generates JSON data files for the static site.
"""

import os
import json
import csv
import html
import hashlib
import re
import subprocess
from datetime import datetime
from functools import lru_cache
from pathlib import Path

# Directories
BASE_DIR = Path(__file__).parent
ATTACKS_DIR = BASE_DIR / "attacks"
LISTS_DIR = BASE_DIR / "lists"
DATA_DIR = BASE_DIR / "docs" / "data"
REVIEWS_DIR = BASE_DIR / "reviews"
ERDOS_STATUS_PATH = LISTS_DIR / "erdos_status.json"
OPEN_PROBLEMS_PATH = ATTACKS_DIR / "open_problems" / "top_problems"
# Tao's database includes independence results in its total solved count.
RESOLVED_ERDOS_STATUSES = {'proved', 'disproved', 'solved', 'independent'}
# Requested display rule for the Erdos LLM Claim column. This deliberately
# differs from the database's resolved categories and from individual attempts.
UNRESOLVED_ERDOS_CLAIM_STATUSES = {'open', 'falsifiable', 'decidable'}


def load_erdos_status():
    """Load the versioned upstream snapshot; ordinary builds work offline."""
    with ERDOS_STATUS_PATH.open(encoding='utf-8') as f:
        return json.load(f)


def apply_erdos_status(problems, snapshot):
    """Apply the database display rule while preserving actual attempt claims."""
    statuses = snapshot['problems']
    missing = sorted(set(problems) - set(statuses), key=int)
    if missing:
        raise ValueError(
            'Missing upstream status for Erdos problems: '
            + ', '.join(missing)
            + '. Run python scripts/sync_erdos_status.py before building.'
        )

    for number, problem in problems.items():
        upstream = statuses[number]
        has_attempts = any(
            attack.get('entry_kind') != 'statement_only'
            for attack in problem.get('attacks', [])
        )
        problem['attempt_status'] = problem['status'] if has_attempts else 'none'
        problem['llm_status'] = (
            'unresolved'
            if upstream['informal_status'] in UNRESOLVED_ERDOS_CLAIM_STATUSES
            else 'solved'
        )
        problem['llm_status_source'] = 'database_rule'
        problem['status'] = upstream['status']
        problem['status_updated'] = upstream['status_updated']
        problem['is_solved'] = upstream['informal_status'] in RESOLVED_ERDOS_STATUSES
        problem['statement_formalization'] = upstream['statement_formalization']
        problem['solution_formalization'] = upstream['solution_formalization']
        problem['database_url'] = snapshot['database_url']
        if isinstance(problem.get('completion'), (int, float)):
            problem['llm_completion'] = problem['completion']
            problem['completion_source'] = 'llm'
        if problem['is_solved']:
            problem['completion'] = 100
            problem['completion_source'] = 'database'
    return problems


def read_tex_file(filepath):
    """Read a TeX file and return its content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""


def extract_completion(content):
    """Extract completion estimate percentage from TeX content.

    Looks for 'COMPLETION ESTIMATE' and scans that line plus the next 3 lines.
    If multiple blocks are present, the latest block with a valid value wins.
    Returns a float percentage (0-100) or None.
    """
    lines = content.splitlines()
    last_value = None
    confidence_re = re.compile(r'\bconfiden\w*\b', re.IGNORECASE)

    def is_confidence_context(text, start, end, window=80):
        left = max(0, start - window)
        right = min(len(text), end + window)
        return confidence_re.search(text[left:right]) is not None

    def is_rejected_value(text, start, end):
        # Reviews may quote a completion claim only to reject it. Match the
        # rejection next to that value, without discarding a corrected estimate.
        formatting = r'\\[A-Za-z]+\*?|[{}\'"`“”‘’$]'
        before = re.sub(formatting, '', text[:start])
        after = re.sub(formatting, '', text[end:])
        return (
            re.search(r'\b(?:not|rather than)\s*$', before, re.IGNORECASE)
            or re.match(
                r'\s*(?:(?:is|was|would be)\s+)?'
                r'(?:false|incorrect|invalid|wrong|rejected|unsupported|unjustified)\b',
                after, re.IGNORECASE,
            )
        )

    for idx, line in enumerate(lines):
        if not re.search(r'COMPLETION\s*(?:RATE\s*)?ESTIMATE', line, re.IGNORECASE):
            continue

        window = lines[idx:idx + 4]
        window_text = "\n".join(window)

        # Prefer explicit percentages.
        local_values = []
        for match in re.finditer(r'(\d+(?:\.\d+)?)\s*\\?%', window_text):
            if is_confidence_context(window_text, match.start(), match.end()):
                continue
            if is_rejected_value(window_text, match.start(), match.end()):
                continue
            try:
                local_values.append(float(match.group(1)))
            except ValueError:
                continue

        if local_values:
            last_value = local_values[-1]
            continue

        # Fallback: decimal fraction (e.g., 0.10) -> convert to percent.
        for match in re.finditer(r'\b0?\.\d+\b', window_text):
            if re.match(r'\s*\\?%', window_text[match.end():]):
                continue
            if is_confidence_context(window_text, match.start(), match.end()):
                continue
            if is_rejected_value(window_text, match.start(), match.end()):
                continue
            try:
                decimal_value = float(match.group(0))
            except ValueError:
                continue
            if decimal_value <= 1:
                last_value = decimal_value * 100

    return last_value


@lru_cache(maxsize=None)
def load_first_posted_dates(repo_dir):
    """Read first additions once, avoiding one history scan per attempt."""
    result = subprocess.run(
        ['git', '-c', 'core.quotePath=false', 'log', '--no-renames',
         '--diff-filter=A', '--format=POSTED:%aI', '--name-only', '--', 'attacks'],
        capture_output=True, text=True, cwd=repo_dir
    )
    if result.returncode != 0:
        return {}
    dates = {}
    date = None
    for line in result.stdout.splitlines():
        if line.startswith('POSTED:'):
            date = datetime.fromisoformat(line[7:].replace('Z', '+00:00')).date().isoformat()
        elif line.startswith('attacks/') and date:
            dates[line] = min(date, dates.get(line, date))
    return dates


def get_file_date(filepath):
    """First recorded repository posting, not the last edit or checkout time.

    Preserve the known Erdos directory migration even when substantial rewrites
    prevent Git's similarity-based rename detection. Model/version filenames
    remain separate; an Astra copy does not inherit another model's date.
    Files without repository history have no inferred posting date.
    """
    try:
        relative = Path(filepath).resolve().relative_to(BASE_DIR.resolve()).as_posix()
        dates = load_first_posted_dates(str(BASE_DIR.resolve()))
        candidates = [relative]
        prefix = 'attacks/open_problems/erdos/'
        if relative.startswith(prefix):
            candidates.append('attacks/erdos/' + relative[len(prefix):])
        known = [dates[path] for path in candidates if path in dates]
        return min(known) if known else None
    except (OSError, ValueError):
        return None


def parse_collection_metadata(content):
    """Read an attributed collection record without treating its header as prose.

    Invalid metadata stops the build: silently discarding attribution could
    misrepresent an imported writeup as a new mathematical attempt.
    """
    first_line, separator, remainder = content.partition('\n')
    marker = re.match(r'^\s*%\s*COLLECTION_METADATA:\s*(.*)$', first_line)
    if not marker:
        return None, content
    try:
        metadata = json.loads(marker.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError('Invalid COLLECTION_METADATA JSON') from exc
    if not isinstance(metadata, dict) or metadata.get('schema_version') != 1:
        raise ValueError('Unsupported COLLECTION_METADATA schema_version')
    kind = metadata.get('kind')
    if kind not in {'reused_writeup', 'statement_only'}:
        raise ValueError('Invalid COLLECTION_METADATA kind')
    if metadata.get('independently_reviewed') is not False:
        raise ValueError('Collection imports must explicitly be independently_reviewed: false')
    if kind == 'reused_writeup':
        for key in ('source_model', 'primary_source'):
            if not isinstance(metadata.get(key), str) or not metadata[key].strip():
                raise ValueError(f'COLLECTION_METADATA requires {key}')
        paths = metadata.get('source_paths')
        if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p for p in paths):
            raise ValueError('COLLECTION_METADATA requires source_paths')
        if metadata.get('source_claim') not in {'solved', 'unresolved'}:
            raise ValueError('Invalid COLLECTION_METADATA source_claim')
        completion = metadata.get('source_completion')
        if completion is not None and (
            type(completion) not in (int, float) or not 0 <= completion <= 100
        ):
            raise ValueError('Invalid COLLECTION_METADATA source_completion')
    else:
        urls = metadata.get('source_urls')
        if not isinstance(urls, list) or not all(isinstance(url, str) for url in urls):
            raise ValueError('COLLECTION_METADATA requires source_urls')
    return metadata, remainder if separator else ''


def parse_attack(content, model_name, date_posted=None):
    """Parse an attack TeX file and extract structured data."""
    provenance, content = parse_collection_metadata(content)
    # Look for section markers
    sections = {}
    current_section = 'preamble'
    current_content = []

    for line in content.split('\n'):
        line_stripped = line.strip()
        # Check for section headers (numbered or named)
        section_match = re.match(r'^(\d+)\)\s*(.*)', line_stripped)
        if section_match:
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = section_match.group(2).upper() if section_match.group(2) else f"SECTION_{section_match.group(1)}"
            current_content = []
        elif line_stripped.startswith('PROBLEM') or line_stripped.startswith('OUTPUT'):
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line_stripped.split()[0]
            current_content = [line_stripped.replace(current_section, '').strip()]
        else:
            current_content.append(line)

    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()

    # Determine status from raw content.
    status = 'unresolved' if re.search(
        r'\bunresolved\b|\bremains\s+open\b', content, re.IGNORECASE
    ) else 'solved'

    completion = extract_completion(content)
    if provenance:
        if provenance['kind'] == 'statement_only':
            status, completion = 'unresolved', 0
        else:
            status = provenance['source_claim']
            # Other included versions may quote incompatible estimates. Only
            # the attributed primary source supplies this record's estimate.
            completion = provenance.get('source_completion')

    attack_data = {
        'model': model_name,
        'sections': sections,
        'status': status,
        'raw': content
    }

    if provenance:
        attack_data['provenance'] = provenance
        attack_data['entry_kind'] = provenance['kind']

    if completion is not None:
        attack_data['completion'] = completion
    
    if date_posted:
        attack_data['date_posted'] = date_posted
    
    return attack_data


def load_erdos_problems_list():
    """Load the Erdos problems list CSV."""
    csv_path = LISTS_DIR / "erdos_problems.csv"
    problems = {}
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                problems[row['number']] = {
                    'status_url': row.get('status', ''),
                    'problem_url': row.get('problem_url', f"https://www.erdosproblems.com/{row['number']}")
                }
    return problems


def load_mo_problems_list():
    """Load the MathOverflow problems list CSV."""
    csv_path = LISTS_DIR / "mo_problems.csv"
    problems = {}
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                qid = row['question_id']
                problems[qid] = {
                    'title': row.get('title', '').replace('&#39;', "'"),
                    'score': int(row.get('score', 0)),
                    'tags': row.get('tags', '').split(';'),
                    'creation_date': row.get('creation_date', ''),
                    'link': row.get('link', f"https://mathoverflow.net/questions/{qid}")
                }
    return problems


def replace_tex_command(text, command, count, replacement):
    """Replace a known TeX command without truncating nested or escaped braces."""
    pattern = re.compile(r'\\' + re.escape(command) + r'\b')
    parts, cursor = [], 0
    for match in pattern.finditer(text):
        if match.start() < cursor:
            continue
        end = match.end()
        arguments = []
        for _ in range(count):
            while end < len(text) and text[end].isspace():
                end += 1
            if end == len(text) or text[end] != '{':
                raise ValueError(f'Missing argument for TeX command {command}')
            start, depth = end + 1, 1
            end += 1
            while end < len(text) and depth:
                if text[end] == '\\':
                    end += 2
                    continue
                if text[end] == '{':
                    depth += 1
                elif text[end] == '}':
                    depth -= 1
                end += 1
            if depth:
                raise ValueError(f'Unclosed argument for TeX command {command}')
            arguments.append(text[start:end - 1])
        parts.extend((text[cursor:match.start()], replacement(*arguments)))
        cursor = end
    return ''.join(parts) + text[cursor:]


def parse_numbered_problem_tex(content):
    """Extract display content while leaving the downloadable source untouched."""
    document = re.search(r'\\begin\{document\}(.*?)\\end\{document\}\s*$',
                         content, re.DOTALL)
    if not document:
        raise ValueError('Expected one complete TeX document')
    body = re.sub(r'^[ \t]*%[^\n]*(?:\n|$)', '', document[1], flags=re.MULTILINE)
    headings = list(re.finditer(r'^[ \t]*\\subsection\{([^}\n]+)\}', body, re.MULTILINE))
    sections = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        if heading[1] in sections:
            raise ValueError(f'Duplicate TeX subsection: {heading[1]}')
        sections[heading[1]] = body[heading.end():end].strip()
    required = ['Definitions and mathematical statement', 'Short English statement', 'Sources']
    if any(not sections.get(name) for name in required):
        raise ValueError('Missing definition, summary, or sources')

    # Both the original standalone files and verbatim notebook sections use
    # local S/E source labels; the latter wrap them in textnormal/hypertarget.
    sources_tex = re.sub(r'\\item\[\\textnormal\{\[([SE]\d+)\]\}\]',
                         r'\\item[\1]', sections['Sources'])
    sources_tex = replace_tex_command(sources_tex, 'hypertarget', 2, lambda key, text: text)
    sources, urls = [], {}
    for item in re.finditer(r'\\item\[([SE]\d+)\]\s*(.*?)(?=\\item\[|\\end\{itemize\}|\Z)',
                            sources_tex, re.DOTALL):
        url = re.search(r'\\url\{([^}]+)\}', item[2])
        if not url:
            raise ValueError(f'Missing URL for source {item[1]}')
        urls[item[1]] = url[1]
        sources.append({'citation': item[2][:url.start()].strip(), 'url': url[1]})

    macros = {'N': r'{\mathbb{N}}', 'Z': r'{\mathbb{Z}}', 'Q': r'{\mathbb{Q}}',
              'R': r'{\mathbb{R}}', 'C': r'{\mathbb{C}}', 'F': r'{\mathbb{F}}',
              'A': r'{\mathbb{A}}', 'PP': r'{\mathbb{P}}', 'E': r'{\mathbb{E}}',
              'eps': r'\varepsilon', 'dd': r'\,\mathrm d'}

    def display(text):
        # The website uses the mathematical exposition, not the repeated
        # catalogue quotation. Keep that quotation in the original .tex file.
        text = replace_tex_command(text, 'cataloguescope', 1, lambda quote: '')
        for command, prefix in [('sref', 'S'), ('eref', 'E')]:
            def source_link(rank, number, prefix=prefix):
                label = prefix + number
                if label not in urls:
                    raise ValueError(f'Missing local source {label}')
                return r'\href{' + urls[label] + '}{[' + label + ']}'
            text = replace_tex_command(text, command, 2, source_link)
        text = replace_tex_command(text, 'needspace', 1, lambda space: '')
        text = re.sub(r'\\raggedright\b', '', text)
        return re.sub(r'\\(' + '|'.join(macros) + r')(?![A-Za-z])',
                      lambda match: macros[match[1]], text).strip()

    sections['Sources'] = sources_tex
    definition = '\n\n'.join(r'\subsection{' + name + '}\n' + display(sections[name])
                             for name in required)
    research = sections.get('Research attempt')
    if research:
        research = (r'\subsection{Research attempt}' + '\n' + display(research)
                    + '\n\n' + r'\subsection{Sources}' + '\n' + display(sources_tex))
    title = re.search(r'^[ \t]*\\section\*?\{[^\n]+', body, re.MULTILINE)
    document = ((title[0].strip() + '\n\n') if title else '') + '\n\n'.join(
        r'\subsection{' + name + '}\n' + display(text) for name, text in sections.items())
    return {'definitionTeX': definition, 'exactTarget': display(sections['Short English statement']),
            'sources': sources, 'researchTeX': research, 'documentTeX': document}


def load_open_problems_catalog():
    """Build the ranked collection from its numbered, source-annotated TeX files."""
    records = []
    for path in sorted(OPEN_PROBLEMS_PATH.glob('*.tex')):
        content = path.read_text(encoding='utf-8')
        header = re.search(r'^% TOP_PROBLEM: (.+)$', content, re.MULTILINE)
        if not header:
            raise ValueError(f'Missing TOP_PROBLEM metadata: {path}')
        record = json.loads(header[1])
        if path.stem != str(record.get('releaseRank')):
            raise ValueError(f'Definition filename must match its rank: {path}')
        try:
            record.update(parse_numbered_problem_tex(content))
        except ValueError as error:
            raise ValueError(f'{path}: {error}') from error
        record['definitionFile'] = f'attacks/open_problems/top_problems/{path.name}'
        records.append(record)
    snapshot = {'records': records, 'recordCount': len(records)}
    validate_open_problems_catalog(snapshot)
    if len(records) != 500:
        raise ValueError('The ranked collection requires all 500 numbered definitions')
    return snapshot


def validate_open_problems_catalog(snapshot):
    """Validate identities, ranks, mathematical content and source links."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('records'), list):
        raise ValueError('Open problems catalog requires a records array')
    records = snapshot['records']
    count = snapshot.get('recordCount')
    if type(count) is not int or count != len(records) or count < 1:
        raise ValueError('Open problems catalog recordCount does not match its records')
    ids, ranks = set(), set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('Malformed open problems catalog record')
        problem_id = record.get('problemId')
        if not isinstance(problem_id, str) or not re.fullmatch(
            r'problem\.[a-z0-9]+(?:[.-][a-z0-9]+)*', problem_id
        ):
            raise ValueError(f'Malformed open problem ID: {problem_id!r}')
        if problem_id in ids:
            raise ValueError(f'Duplicate open problem ID: {problem_id}')
        ids.add(problem_id)
        rank = record.get('releaseRank')
        if type(rank) is not int or rank < 1:
            raise ValueError(f'Malformed open problem rank for {problem_id}: {rank!r}')
        if rank in ranks:
            raise ValueError(f'Duplicate open problem rank: {rank}')
        ranks.add(rank)
        for key in ('canonicalTitle', 'exactTarget', 'primaryDomain',
                    'primaryDomainLabel', 'displayStatus', 'releaseStatus'):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f'Open problem {problem_id} requires {key}')
        sources = record.get('sources')
        if not isinstance(sources, list) or not sources or not all(
            isinstance(source, dict) and isinstance(source.get('url'), str)
            and source['url'].startswith(('https://', 'http://'))
            and isinstance(source.get('citation'), str) and source['citation'].strip()
            for source in sources
        ):
            raise ValueError(f'Open problem {problem_id} requires attributed sources')
    if ranks != set(range(1, count + 1)):
        raise ValueError('Open problems catalog ranks must be contiguous from 1 to recordCount')


def load_review(problem_type, problem_id):
    """Load review metadata for a problem, if present."""
    review_path = REVIEWS_DIR / problem_type / f"{problem_id}.json"
    if not review_path.exists():
        return None
    try:
        with open(review_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load review for {problem_type} {problem_id}: {e}")
        return None


def build_erdos_data():
    """Build data for Erdos problems.

    Problem statements are NOT included - users are directed to
    erdosproblems.com for the actual problem content.
    """
    attacks_dir = ATTACKS_DIR / "open_problems" / "erdos"
    problems_list = load_erdos_problems_list()
    status_snapshot = load_erdos_status()
    for problem_num in status_snapshot['problems']:
        problems_list.setdefault(problem_num, {})

    problems = {}

    # Include the full upstream catalogue, retaining any CSV-specific links.
    for problem_num, list_info in problems_list.items():
        problems[problem_num] = {
            'number': problem_num,
            'problem_url': list_info.get('problem_url', f"https://www.erdosproblems.com/{problem_num}"),
            'database_url': list_info.get('status_url', 'https://teorth.github.io/erdosproblems/'),
            'attacks': []
        }

    # Load attacks
    if attacks_dir.exists():
        for model_dir in attacks_dir.iterdir():
            if model_dir.is_dir() and not model_dir.name.startswith('.'):
                model_name = model_dir.name.replace('_', ' ')
                for tex_file in sorted(model_dir.glob("*.tex")):
                    filename = tex_file.stem
                    match = re.match(r'^(?P<id>\d+)(?:_v(?P<ver>\d+))?$', filename)
                    if not match:
                        continue
                    problem_num = match.group('id')
                    version = int(match.group('ver') or 1)
                    content = read_tex_file(tex_file)
                    date_posted = get_file_date(tex_file)
                    parsed = parse_attack(content, model_name, date_posted)
                    parsed['file_path'] = tex_file.relative_to(BASE_DIR).as_posix()
                    parsed['version'] = version

                    if problem_num in problems:
                        problems[problem_num]['attacks'].append(parsed)
                    else:
                        # Problem not in CSV list but has attack - still add it
                        problems[problem_num] = {
                            'number': problem_num,
                            'problem_url': f"https://www.erdosproblems.com/{problem_num}",
                            'database_url': 'https://teorth.github.io/erdosproblems/',
                            'attacks': [parsed]
                        }

    # Attach review metadata, if any
    for problem_num, problem_data in problems.items():
        review = load_review('erdos', problem_num)
        if review:
            problem_data['review'] = review

    # Sort attacks so versioned files appear after base attempts
    for problem_data in problems.values():
        problem_data['attacks'].sort(
            key=lambda attack: (
                attack.get('model', ''),
                attack.get('version', 1),
                attack.get('file_path', '')
            )
        )

    # Aggregate completion across all attacks for each problem
    for problem_num, problem_data in problems.items():
        completions = [
            attack.get('completion')
            for attack in problem_data.get('attacks', [])
            if isinstance(attack.get('completion'), (int, float))
        ]
        if completions:
            problem_data['completion'] = max(completions)

    # Aggregate status across all attacks for each problem
    problems = aggregate_problem_status(problems)

    return apply_erdos_status(problems, status_snapshot)


def build_mo_data():
    """Build data for MathOverflow problems.

    Problem statements are NOT included - users are directed to
    MathOverflow for the actual problem content.
    """
    attacks_dir = ATTACKS_DIR / "open_problems" / "mo"
    problems_list = load_mo_problems_list()

    problems = {}

    # Load from CSV list (link to external sources only)
    for qid, info in problems_list.items():
        problems[qid] = {
            'id': qid,
            'title': info['title'],
            'score': info['score'],
            'tags': info['tags'],
            'creation_date': info['creation_date'],
            'link': info['link'],
            'attacks': []
        }

    # Load attacks
    if attacks_dir.exists():
        for model_dir in attacks_dir.iterdir():
            if model_dir.is_dir() and not model_dir.name.startswith('.'):
                model_name = model_dir.name.replace('_', ' ')
                for tex_file in sorted(model_dir.glob("*.tex")):
                    # Extract question ID from filename
                    filename = tex_file.stem
                    qid_match = re.match(r'^(\d+)', filename)
                    if qid_match:
                        qid = qid_match.group(1)
                        version_match = re.search(r'_v(\d+)', filename)
                        version = int(version_match.group(1)) if version_match else 1
                        content = read_tex_file(tex_file)
                        date_posted = get_file_date(tex_file)
                        parsed = parse_attack(content, model_name, date_posted)
                        parsed['file_path'] = tex_file.relative_to(BASE_DIR).as_posix()
                        parsed['version'] = version

                        # Check for "solved" in filename without overriding unresolved content.
                        if '--solved--' in filename.lower() and parsed.get('status') != 'unresolved':
                            parsed['status'] = 'solved'

                        if qid in problems:
                            problems[qid]['attacks'].append(parsed)

    # Attach review metadata, if any
    for qid, problem_data in problems.items():
        review = load_review('open_problems/mo', qid) or load_review('mo', qid)
        if review:
            problem_data['review'] = review

    # Sort attacks so versioned files appear after base attempts
    for problem_data in problems.values():
        problem_data['attacks'].sort(
            key=lambda attack: (
                attack.get('model', ''),
                attack.get('version', 1),
                attack.get('file_path', '')
            )
        )

    # Aggregate completion across all attacks for each problem
    for qid, problem_data in problems.items():
        completions = [
            attack.get('completion')
            for attack in problem_data.get('attacks', [])
            if isinstance(attack.get('completion'), (int, float))
        ]
        if completions:
            problem_data['completion'] = max(completions)

    # Aggregate status across all attacks for each problem
    problems = aggregate_problem_status(problems)

    return problems


def summarize_open_problem_attempts(problem):
    """Keep writeup claims and estimates separate from catalog status."""
    problem['attacks'].sort(key=lambda attack: (
        attack.get('model', ''), attack.get('version', 1), attack.get('file_path', '')
    ))
    attempts = [a for a in problem['attacks'] if a.get('entry_kind') != 'statement_only']
    problem['llm_status'] = (
        'none' if not attempts else
        'unresolved' if any(a.get('status') == 'unresolved' for a in attempts) else 'solved'
    )
    problem['llm_status_source'] = 'attempts'
    completions = [a['completion'] for a in attempts
                   if type(a.get('completion')) in (int, float)]
    if completions:
        problem['completion'] = max(completions)
        problem['completion_source'] = 'llm'


def build_open_problems_data(mo_problems=None, snapshot=None):
    """Join numbered definitions, their attempts, and the legacy MO collection.

    Stable problem IDs preserve existing URLs and reviews. Numbered files in
    top_problems/<model>/ follow the same convention as the Erdos collection.
    """
    if snapshot is None:
        snapshot = load_open_problems_catalog()
    if mo_problems is None:
        mo_problems = build_mo_data()
    problems = {}
    for record in sorted(snapshot['records'], key=lambda item: item['releaseRank']):
        problem_id = record['problemId']
        formal_source = record.get('formalStatementSource') or {}
        problems[problem_id] = {
            'id': problem_id,
            'title': record['canonicalTitle'],
            'collection': 'ranked',
            'rank': record['releaseRank'],
            'domain': record['primaryDomain'],
            'domain_label': record['primaryDomainLabel'],
            'exact_target': record['exactTarget'],
            'definition_tex': record.get('definitionTeX'),
            'definition_file': record.get('definitionFile'),
            'link': formal_source.get('url') or record['sources'][0]['url'],
            'sources': record['sources'],
            'status': record['displayStatus'],
            'release_status': record['releaseStatus'],
            'status_statement': record.get('statusStatement'),
            'status_qualification': record.get('statusQualification'),
            'status_reviewed_at': record.get('statusReviewedAt') or None,
            'attacks': [],
        }
        if record.get('researchTeX'):
            notebook = parse_attack(record['researchTeX'], 'Research notebook')
            # Notebook reductions and exploratory work are not declarations
            # that the original open problem has been solved.
            notebook['status'] = 'unresolved'
            notebook['file_path'] = record['definitionFile']
            notebook['version'] = 1
            problems[problem_id]['attacks'].append(notebook)

    attacks_dir = ATTACKS_DIR / 'open_problems'
    if attacks_dir.exists():
        model_dirs = []
        for model_dir in sorted(attacks_dir.iterdir()):
            if not model_dir.is_dir() or model_dir.name.startswith('.') or model_dir.name in {'mo', 'erdos', 'top_problems'}:
                continue
            model_dirs.append((model_dir, False))
        numbered_dir = attacks_dir / 'top_problems'
        if numbered_dir.exists():
            model_dirs.extend((directory, True) for directory in sorted(numbered_dir.iterdir())
                              if directory.is_dir() and not directory.name.startswith('.'))
        ids_by_number = {str(problem['rank']): problem_id for problem_id, problem in problems.items()}
        for model_dir, numbered in model_dirs:
            for tex_file in sorted(model_dir.glob('*.tex')):
                pattern = r'(?P<id>[1-9]\d*)' if numbered else r'(?P<id>problem\.[a-z0-9.-]+)'
                match = re.fullmatch(pattern + r'(?:_v(?P<ver>[1-9]\d*))?', tex_file.stem)
                problem_id = match.group('id') if match else None
                if numbered:
                    problem_id = ids_by_number.get(problem_id)
                if problem_id not in problems:
                    raise ValueError(
                        f'Unknown ranked open problem attempt: {tex_file}. '
                        'Use a numbered file in top_problems/<model>/, or a stable problemId in <model>/.'
                    )
                content = read_tex_file(tex_file)
                raw = content
                if numbered and r'\subsection{Definitions and mathematical statement}' in content:
                    raw = parse_numbered_problem_tex(content)['documentTeX']
                parsed = parse_attack(raw, model_dir.name.replace('_', ' '), get_file_date(tex_file))
                declared_status = re.search(r'^% ATTEMPT_STATUS: (solved|unresolved)\s*$', content, re.MULTILINE)
                if declared_status:
                    parsed['status'] = declared_status[1]
                parsed['file_path'] = tex_file.relative_to(BASE_DIR).as_posix()
                parsed['version'] = int(match.group('ver') or 1)
                problems[problem_id]['attacks'].append(parsed)

    for problem_id, problem in problems.items():
        review = load_review('open_problems', problem_id)
        if review:
            problem['review'] = review
        summarize_open_problem_attempts(problem)

    for qid, original in sorted(mo_problems.items(), key=lambda item: int(item[0])):
        problem = {
            **original,
            'id': f'mo:{qid}',
            'title': html.unescape(original['title']),
            'mo_id': qid,
            'collection': 'mo',
            'rank': None,
            'domain': 'mathoverflow',
            'domain_label': 'MathOverflow',
            'exact_target': None,
            'sources': [{'citation': html.unescape(original['title']), 'url': original['link']}],
            'status': 'unreviewed',
            'status_qualification': 'Legacy MathOverflow collection; current mathematical status has not been reviewed against the ranked catalog.',
            'status_reviewed_at': None,
        }
        # Recompute from actual attempts; a statement-only MO record must not
        # inherit the old empty-aggregate "solved" state or estimate.
        problem.pop('completion', None)
        summarize_open_problem_attempts(problem)
        problems[problem['id']] = problem
    return problems


def aggregate_problem_status(problems):
    """Aggregate status for each problem based on all its attacks.
    
    Rule: If at least one attack has status 'unresolved' (case-insensitive),
    then the problem status is 'unresolved'. Otherwise, it's 'solved'.
    """
    for problem_id, problem_data in problems.items():
        attacks = [
            attack for attack in problem_data.get('attacks', [])
            if attack.get('entry_kind') != 'statement_only'
        ]
        
        # Check if any attack is unresolved
        has_unresolved = any(
            attack.get('status', '').lower() == 'unresolved' 
            for attack in attacks
        )
        
        if has_unresolved:
            problem_data['status'] = 'unresolved'
        else:
            problem_data['status'] = 'solved'
    
    return problems


def generate_js_data(erdos_problems, mo_problems, open_problems=None, open_catalog=None):
    """Generate JavaScript data files for the frontend."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if open_catalog is None:
        open_catalog = load_open_problems_catalog()
    if open_problems is None:
        open_problems = build_open_problems_data(mo_problems, open_catalog)

    # Generate erdos_data.js
    with open(DATA_DIR / "erdos_data.js", 'w', encoding='utf-8') as f:
        # Sort by problem number
        sorted_problems = dict(sorted(erdos_problems.items(), key=lambda x: int(x[0]) if x[0].isdigit() else float('inf')))
        f.write(f"var erdosProblems = {json.dumps(sorted_problems, indent=2)};\n")
        source = {key: value for key, value in load_erdos_status().items() if key != 'problems'}
        f.write(f"var erdosStatusSync = {json.dumps(source, indent=2)};\n")

    # Generate mo_data.js
    with open(DATA_DIR / "mo_data.js", 'w', encoding='utf-8') as f:
        # Sort by question ID
        sorted_problems = dict(sorted(mo_problems.items(), key=lambda x: int(x[0]) if x[0].isdigit() else float('inf')))
        f.write(f"var moProblems = {json.dumps(sorted_problems, indent=2)};\n")

    with open(DATA_DIR / 'open_problems_data.js', 'w', encoding='utf-8') as f:
        f.write(f'var openProblems = {json.dumps(open_problems, indent=2)};\n')
        f.write('window.OPEN_PROBLEMS_DATA = openProblems;\n')
        catalog_info = {
            'ranking_source': 'https://www.proofatlas.ai/',
            'source_path': 'attacks/open_problems/top_problems',
        }
        f.write(f'var openProblemsCatalog = {json.dumps(catalog_info, indent=2)};\n')
        f.write('window.OPEN_PROBLEMS_CATALOG = openProblemsCatalog;\n')

    # Detail pages load a small current record independently of cached index
    # data. Both formats are generated from the same TeX source in this build.
    detail_dir = DATA_DIR / 'top_problems'
    detail_dir.mkdir(exist_ok=True)
    for problem in open_problems.values():
        if problem.get('collection') == 'ranked':
            (detail_dir / f"{problem['rank']}.json").write_text(
                json.dumps(problem, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # Changing the generated content changes the URL, so a new page cannot
    # accidentally pair with a pre-TeX copy of the index in the browser cache.
    data_version = hashlib.sha256((DATA_DIR / 'open_problems_data.js').read_bytes()).hexdigest()[:16]
    for page in DATA_DIR.parent.glob('*.html'):
        original = page.read_text(encoding='utf-8')
        versioned = re.sub(r'(?<=src=")data/open_problems_data\.js(?:\?v=[a-zA-Z0-9_-]+)?(?=")',
                           f'data/open_problems_data.js?v={data_version}', original)
        if versioned != original:
            page.write_text(versioned, encoding='utf-8')

    # Generate summary statistics
    stats = {
        'erdos': {
            'total_problems': len(erdos_problems),
            'with_attacks': sum(
                1 for p in erdos_problems.values()
                if any(a.get('entry_kind') != 'statement_only' for a in p.get('attacks', []))
            ),
            'solved_problems': sum(1 for p in erdos_problems.values() if p['is_solved']),
            'models': sorted(set(
                a['model']
                for p in erdos_problems.values()
                for a in p.get('attacks', [])
            ))
        },
        'mo': {
            'total_problems': len(mo_problems),
            'with_attacks': sum(
                1 for p in mo_problems.values()
                if any(a.get('entry_kind') != 'statement_only' for a in p.get('attacks', []))
            ),
            'models': sorted(set(
                a['model']
                for p in mo_problems.values()
                for a in p.get('attacks', [])
                if a.get('entry_kind') != 'statement_only'
            ))
        },
        'open_problems': {
            'total_problems': len(open_problems),
            'ranked_total': sum(p['collection'] == 'ranked' for p in open_problems.values()),
            'mo_total': sum(p['collection'] == 'mo' for p in open_problems.values()),
            'with_attacks': sum(
                1 for p in open_problems.values()
                if any(a.get('entry_kind') != 'statement_only' for a in p.get('attacks', []))
            ),
            'ranked_with_attacks': sum(
                1 for p in open_problems.values() if p['collection'] == 'ranked'
                and any(a.get('entry_kind') != 'statement_only' for a in p.get('attacks', []))
            ),
            'models': sorted(set(
                a['model'] for p in open_problems.values() for a in p.get('attacks', [])
                if a.get('entry_kind') != 'statement_only'
            )),
        }
    }

    with open(DATA_DIR / "stats.js", 'w', encoding='utf-8') as f:
        f.write(f"var siteStats = {json.dumps(stats, indent=2)};\n")

    print(f"Generated data files in {DATA_DIR}")
    print(f"  Erdos problems: {stats['erdos']['total_problems']} ({stats['erdos']['with_attacks']} with attacks)")
    print(f"  MO problems: {stats['mo']['total_problems']} ({stats['mo']['with_attacks']} with attacks)")
    print(f"  Open problems: {stats['open_problems']['total_problems']} ({stats['open_problems']['ranked_total']} ranked, {stats['open_problems']['with_attacks']} with attacks)")


def main():
    print("Building Erdosproblems-llm-hunter site data...")

    erdos_problems = build_erdos_data()
    mo_problems = build_mo_data()
    open_catalog = load_open_problems_catalog()
    open_problems = build_open_problems_data(mo_problems, open_catalog)

    generate_js_data(erdos_problems, mo_problems, open_problems, open_catalog)

    print("Build complete!")


if __name__ == "__main__":
    main()
