#!/usr/bin/env python3
"""Apply a complete Economics ranking CSV while preserving permanent IDs.

Example: python scripts/update_economics_ranks.py revised-ranks.csv
CSV columns: Problem ID,New rank (title and JEL are optional cross-checks).
Use --allow-source-ids only for legacy OP CSVs, with title/JEL for reused IDs.
"""

import argparse
from pathlib import Path

try:
    from .economics_catalog import (BASE_DIR, RANKINGS_PATH, generate_economics_data,
                                    load_registry, ranking_csv_text, read_ranking_csv)
except ImportError:
    from economics_catalog import (BASE_DIR, RANKINGS_PATH, generate_economics_data,
                                   load_registry, ranking_csv_text, read_ranking_csv)


def update_economics_ranks(csv_path, base_dir=BASE_DIR, allow_source_ids=False, check_only=False):
    base_dir = Path(base_dir)
    records = load_registry(base_dir)['problems']
    rankings = read_ranking_csv(csv_path, records, allow_source_ids=allow_source_ids)
    # Validate every statement before the mutable file is touched.
    try:
        from .economics_catalog import extract_statement
    except ImportError:
        from economics_catalog import extract_statement
    for record in records:
        extract_statement((base_dir / record['statement_file']).read_text(encoding='utf-8'))
    if not check_only:
        target = base_dir / RANKINGS_PATH
        temporary = target.with_suffix('.csv.tmp')
        temporary.write_text(ranking_csv_text(records, rankings), encoding='utf-8')
        temporary.replace(target)
        generate_economics_data(base_dir)
    return rankings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--root', type=Path, default=BASE_DIR)
    parser.add_argument('--allow-source-ids', action='store_true')
    parser.add_argument('--check', action='store_true', help='Validate without writing files')
    args = parser.parse_args()
    result = update_economics_ranks(args.csv, args.root, args.allow_source_ids, args.check)
    action = 'Validated' if args.check else 'Updated'
    print(f'{action} {len(result)} Economics ranks; permanent IDs unchanged')


if __name__ == '__main__':
    main()
