#!/usr/bin/env python3
"""
Build script for Erdosproblems-llm-hunter website.
Reads TeX files from Attacks directory and CSV lists,
generates JSON data files for the static site.
"""

import os
import json
import csv
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Directories
BASE_DIR = Path(__file__).parent
ATTACKS_DIR = BASE_DIR / "attacks"
LISTS_DIR = BASE_DIR / "lists"
DATA_DIR = BASE_DIR / "docs" / "data"


def read_tex_file(filepath):
    """Read a TeX file and return its content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""


def get_file_date(filepath):
    """Get the date when a file was added/modified.
    
    First tries to get the git commit date, then falls back to
    file modification time.
    
    Returns date in YYYY-MM-DD format.
    """
    try:
        # Try to get git commit date (when file was first added)
        result = subprocess.run(
            ['git', 'log', '--format=%aI', '--diff-filter=A', '--', str(filepath)],
            capture_output=True,
            text=True,
            cwd=filepath.parent
        )
        if result.returncode == 0 and result.stdout.strip():
            # Parse ISO format date and extract just the date part
            git_date = result.stdout.strip().split('\n')[-1]  # Get oldest commit (first added)
            return datetime.fromisoformat(git_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except Exception as e:
        pass
    
    # Fall back to file modification time
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    except Exception as e:
        print(f"Warning: Could not get date for {filepath}: {e}")
        return datetime.now().strftime('%Y-%m-%d')


def parse_attack(content, model_name, date_posted=None):
    """Parse an attack TeX file and extract structured data."""
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
    status = 'unresolved' if re.search(r'unresolved', content, re.IGNORECASE) else 'solved'

    attack_data = {
        'model': model_name,
        'sections': sections,
        'status': status,
        'raw': content
    }
    
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


def build_erdos_data():
    """Build data for Erdos problems.

    Problem statements are NOT included - users are directed to
    erdosproblems.com for the actual problem content.
    """
    attacks_dir = ATTACKS_DIR / "erdos"
    problems_list = load_erdos_problems_list()

    problems = {}

    # Initialize problems from the CSV list (link to external sources only)
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
                for tex_file in model_dir.glob("*.tex"):
                    problem_num = tex_file.stem
                    content = read_tex_file(tex_file)
                    date_posted = get_file_date(tex_file)
                    parsed = parse_attack(content, model_name, date_posted)
                    parsed['file_path'] = tex_file.relative_to(BASE_DIR).as_posix()

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

    # Aggregate status across all attacks for each problem
    problems = aggregate_problem_status(problems)

    return problems


def build_mo_data():
    """Build data for MathOverflow problems.

    Problem statements are NOT included - users are directed to
    MathOverflow for the actual problem content.
    """
    attacks_dir = ATTACKS_DIR / "mo"
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
                for tex_file in model_dir.glob("*.tex"):
                    # Extract question ID from filename
                    filename = tex_file.stem
                    qid_match = re.match(r'^(\d+)', filename)
                    if qid_match:
                        qid = qid_match.group(1)
                        content = read_tex_file(tex_file)
                        date_posted = get_file_date(tex_file)
                        parsed = parse_attack(content, model_name, date_posted)
                        parsed['file_path'] = tex_file.relative_to(BASE_DIR).as_posix()

                        # Check for "solved" in filename without overriding unresolved content.
                        if '--solved--' in filename.lower() and parsed.get('status') != 'unresolved':
                            parsed['status'] = 'solved'

                        if qid in problems:
                            problems[qid]['attacks'].append(parsed)

    # Aggregate status across all attacks for each problem
    problems = aggregate_problem_status(problems)

    return problems


def aggregate_problem_status(problems):
    """Aggregate status for each problem based on all its attacks.
    
    Rule: If at least one attack has status 'unresolved' (case-insensitive),
    then the problem status is 'unresolved'. Otherwise, it's 'solved'.
    """
    for problem_id, problem_data in problems.items():
        attacks = problem_data.get('attacks', [])
        
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


def generate_js_data(erdos_problems, mo_problems):
    """Generate JavaScript data files for the frontend."""
    DATA_DIR.mkdir(exist_ok=True)

    # Generate erdos_data.js
    with open(DATA_DIR / "erdos_data.js", 'w', encoding='utf-8') as f:
        # Sort by problem number
        sorted_problems = dict(sorted(erdos_problems.items(), key=lambda x: int(x[0]) if x[0].isdigit() else float('inf')))
        f.write(f"var erdosProblems = {json.dumps(sorted_problems, indent=2)};\n")

    # Generate mo_data.js
    with open(DATA_DIR / "mo_data.js", 'w', encoding='utf-8') as f:
        # Sort by question ID
        sorted_problems = dict(sorted(mo_problems.items(), key=lambda x: int(x[0]) if x[0].isdigit() else float('inf')))
        f.write(f"var moProblems = {json.dumps(sorted_problems, indent=2)};\n")

    # Generate summary statistics
    stats = {
        'erdos': {
            'total_problems': len(erdos_problems),
            'with_attacks': sum(1 for p in erdos_problems.values() if p.get('attacks')),
            'models': list(set(
                a['model']
                for p in erdos_problems.values()
                for a in p.get('attacks', [])
            ))
        },
        'mo': {
            'total_problems': len(mo_problems),
            'with_attacks': sum(1 for p in mo_problems.values() if p.get('attacks')),
            'models': list(set(
                a['model']
                for p in mo_problems.values()
                for a in p.get('attacks', [])
            ))
        }
    }

    with open(DATA_DIR / "stats.js", 'w', encoding='utf-8') as f:
        f.write(f"var siteStats = {json.dumps(stats, indent=2)};\n")

    print(f"Generated data files in {DATA_DIR}")
    print(f"  Erdos problems: {stats['erdos']['total_problems']} ({stats['erdos']['with_attacks']} with attacks)")
    print(f"  MO problems: {stats['mo']['total_problems']} ({stats['mo']['with_attacks']} with attacks)")


def main():
    print("Building Erdosproblems-llm-hunter site data...")

    erdos_problems = build_erdos_data()
    mo_problems = build_mo_data()

    generate_js_data(erdos_problems, mo_problems)

    print("Build complete!")


if __name__ == "__main__":
    main()
