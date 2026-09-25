#!/usr/bin/env python3
"""Split catalogue research batches into model attempts without rewriting TeX."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_site import OPEN_PROBLEMS_PATH, parse_numbered_problem_tex


MARKER = re.compile(r'^(?:[ \t]*% =+\r?\n)?[ \t]*% problemId: ([^\r\n]+)\r?\n', re.MULTILINE)
RANK = re.compile(r'^[ \t]*% source releaseRank: ([1-9]\d*);[^\r\n]*$', re.MULTILINE)
RESEARCH = re.compile(r'^[ \t]*\\subsection\{Research attempt\}', re.MULTILINE)


@dataclass(frozen=True)
class AttemptSection:
    rank: int
    problem_id: str
    preamble: str
    section: str


def read_exact(path):
    """Decode UTF-8 without translating the source's line endings."""
    return Path(path).read_bytes().decode('utf-8')


def extract_attempts(content):
    """Extract whole marked sections; definition-only sections are skipped."""
    begin = list(re.finditer(r'^[ \t]*\\begin\{document\}', content, re.MULTILINE))
    end = list(re.finditer(r'^[ \t]*\\end\{document\}', content, re.MULTILINE))
    if len(begin) != 1 or len(end) != 1 or begin[0].end() >= end[0].start():
        raise ValueError('Expected one complete TeX document')
    if content[end[0].end():].strip():
        raise ValueError('Unexpected content after the TeX document')
    preamble = content[:begin[0].start()]
    body = content[begin[0].end():end[0].start()]
    markers = list(MARKER.finditer(body))
    if not markers:
        raise ValueError('No problemId section markers found')
    if RESEARCH.search(body[:markers[0].start()]):
        raise ValueError('Research attempt has no problemId marker')

    attempts = []
    for index, marker in enumerate(markers):
        stop = markers[index + 1].start() if index + 1 < len(markers) else len(body)
        section = body[marker.start():stop]
        if not RESEARCH.search(section):
            continue
        ranks = list(RANK.finditer(section.replace('\r\n', '\n')))
        if len(ranks) != 1:
            raise ValueError(f'Expected one releaseRank for {marker[1]}')
        rank = int(ranks[0][1])
        if not re.fullmatch(r'problem\.[a-z0-9.-]+', marker[1]):
            raise ValueError(f'Invalid problemId: {marker[1]}')
        headings = re.findall(r'^[ \t]*\\section\*?\{', section, re.MULTILINE)
        if len(headings) != 1 or not re.search(r'\\label\{' + str(rank) + r'\}', section):
            raise ValueError(f'Expected one section labeled {rank}')
        document = preamble + '\\begin{document}\n' + section + '\\end{document}\n'
        parsed = parse_numbered_problem_tex(document)
        if not parsed['researchTeX']:
            raise ValueError(f'Empty Research attempt for {marker[1]}')
        attempts.append(AttemptSection(rank, marker[1], preamble, section))
    if not attempts:
        raise ValueError('No Research attempt subsections found')
    return attempts


def section_key(section):
    """Ignore wrapper and boundary whitespace when checking repeated imports."""
    return section.replace('\r\n', '\n').strip()


def import_attempts(sources, catalog_dir=OPEN_PROBLEMS_PATH,
                    model='GPT_6_Astra_Ultra', version=1):
    """Validate the complete import first, then create only missing attempts.

    Returns (created_paths, unchanged_paths). Existing files are never replaced.
    """
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', model):
        raise ValueError('Model must be a single folder name using letters, digits, _, ., or -')
    if type(version) is not int or version < 1:
        raise ValueError('Version must be a positive integer')
    catalog_dir = Path(catalog_dir)
    planned, unchanged, seen = {}, [], {}
    for source in sources:
        try:
            attempts = extract_attempts(read_exact(source))
        except (OSError, UnicodeError, ValueError) as error:
            raise ValueError(f'{source}: {error}') from error
        for attempt in attempts:
            root = catalog_dir / f'{attempt.rank}.tex'
            header = re.search(r'^% TOP_PROBLEM: (.+)$', read_exact(root), re.MULTILINE)
            if not header:
                raise ValueError(f'Missing TOP_PROBLEM metadata: {root}')
            metadata = json.loads(header[1])
            if (type(metadata.get('releaseRank')) is not int
                    or metadata['releaseRank'] != attempt.rank
                    or metadata.get('problemId') != attempt.problem_id):
                raise ValueError(f'Identity mismatch between {source} and {root}')
            suffix = '' if version == 1 else f'_v{version}'
            destination = catalog_dir / model / f'{attempt.rank}{suffix}.tex'
            key = section_key(attempt.section)
            if destination in seen:
                if seen[destination] != key:
                    raise ValueError(f'Conflicting input sections for {destination}')
                continue
            seen[destination] = key
            if destination.exists():
                try:
                    existing = extract_attempts(read_exact(destination))
                    same = (len(existing) == 1
                            and existing[0].problem_id == attempt.problem_id
                            and existing[0].rank == attempt.rank
                            and section_key(existing[0].section) == key)
                except (OSError, UnicodeError, ValueError):
                    same = False
                if not same:
                    raise ValueError(f'Existing attempt differs: {destination}; choose a new --version')
                unchanged.append(destination)
                continue
            # Only the wrapper is new. The source preamble and section remain exact.
            wrapper = ('% TOP_PROBLEM: ' + json.dumps(metadata, ensure_ascii=False) + '\n'
                       '% ATTEMPT_STATUS: unresolved\n'
                       + attempt.preamble + '\\begin{document}\n'
                       + f'\\setcounter{{section}}{{{attempt.rank - 1}}}\n')
            content = wrapper + attempt.section + '\\end{document}\n'
            parse_numbered_problem_tex(content)
            planned[destination] = content

    for destination, content in planned.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output:
            output.write(content.encode('utf-8'))
    return list(planned), unchanged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', nargs='+', type=Path, help='Catalogue-style research batch .tex files')
    parser.add_argument('--model', default='GPT_6_Astra_Ultra', help='Destination model folder')
    parser.add_argument('--version', type=int, default=1, help='Attempt version (default: 1; 2 produces N_v2.tex)')
    parser.add_argument('--catalog-dir', type=Path, default=OPEN_PROBLEMS_PATH,
                        help='Directory containing the numbered TOP_PROBLEM definitions')
    args = parser.parse_args()
    try:
        created, unchanged = import_attempts(args.sources, args.catalog_dir, args.model, args.version)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    for path in created:
        print(f'Created {path}')
    for path in unchanged:
        print(f'Unchanged {path}')
    print(f'{len(created)} created; {len(unchanged)} already present. Run python3 build_site.py to render.')


if __name__ == '__main__':
    main()
