#!/usr/bin/env python3
"""Reserve local identities for reviewed new targets without changing old records.

This does not import statements, write pages, or approve solved labels. Proposal
identity review must precede allocation. The output can be reviewed before
--reserve advances the local registry watermark.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import re
import unicodedata


def normalized_title(value):
    value = value.translate(str.maketrans({c: ' ' for c in '–—−‐‑‒'}))
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', value.lower()).split())


def allocate(registry, watermark, proposals):
    if not isinstance(registry, list) or not registry:
        raise ValueError('A complete, nonempty registry is required')
    ids = [record.get('id') for record in registry]
    if any(type(n) is not int or n < 1 for n in ids) or len(set(ids)) != len(ids):
        raise ValueError('Registry IDs must be unique positive integers')
    if not isinstance(watermark, dict) or watermark.get('schema_version') != 1 \
            or type(watermark.get('last_allocated_id')) is not int:
        raise ValueError('Invalid ID registry watermark')
    if not isinstance(proposals, list):
        raise ValueError('Proposals must be an array')
    if any(not isinstance(item, dict) or item.get('identity_reviewed') is not True
           for item in proposals):
        raise ValueError('Each new target requires explicit identity review')
    if any(not isinstance(item.get('proposal_key'), str) for item in proposals):
        raise ValueError('Proposal keys must be unique nonempty strings')
    titles = {normalized_title(record['title']) for record in registry}
    keys, allocated = set(), []
    next_id = max(max(ids), watermark['last_allocated_id']) + 1
    for proposal in sorted(proposals, key=lambda item: item.get('proposal_key', '')):
        key, title = proposal.get('proposal_key'), proposal.get('title')
        if not isinstance(key, str) or not key.strip() or key in keys:
            raise ValueError('Proposal keys must be unique nonempty strings')
        if not isinstance(title, str) or not title.strip():
            raise ValueError('Each proposal requires a title')
        normalized = normalized_title(title)
        if normalized in titles:
            raise ValueError(f'Title already identifies a registry target: {title}')
        if 'id' in proposal or 'candidate_id' in proposal:
            raise ValueError('New proposals must not supply their own IDs')
        parents = proposal.get('parent_candidate_ids', [])
        if not isinstance(parents, list) or any(type(n) is not int or n not in ids for n in parents):
            raise ValueError('Parent IDs must refer to existing registry records')
        allocated.append({**proposal, 'id': next_id, 'problem_number': f'LOCAL-{next_id}',
                          'published': False})
        keys.add(key)
        titles.add(normalized)
        next_id += 1
    updated = dict(watermark)
    if allocated:
        updated['last_allocated_id'] = allocated[-1]['id']
    return allocated, updated


def execute(args):
    original = args.watermark.read_bytes()
    registry_bytes = args.registry.read_bytes()
    assignments, updated = allocate(json.loads(registry_bytes), json.loads(original),
                                    json.loads(args.proposals.read_text()))
    output = {'registry_sha256': hashlib.sha256(registry_bytes).hexdigest(),
              'previous_watermark': json.loads(original)['last_allocated_id'],
              'next_watermark': updated['last_allocated_id'], 'reserved': args.reserve,
              'assignments': assignments}
    if args.output.exists():
        previous = json.loads(args.output.read_text())
        if {k: v for k, v in previous.items() if k != 'reserved'} != {k: v for k, v in output.items() if k != 'reserved'}:
            raise ValueError('Refusing to overwrite a changed allocation report')
        if previous.get('reserved') is True and not args.reserve:
            raise ValueError('A reserved report cannot become a dry-run report')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.reserve:
        # Reject an intervening reservation rather than allocate duplicate IDs.
        if args.watermark.read_bytes() != original or args.registry.read_bytes() != registry_bytes:
            raise ValueError('Registry changed during allocation; recompute before reserving')
        temporary = args.watermark.with_suffix(args.watermark.suffix + '.openai.tmp')
        with temporary.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(updated, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(args.watermark)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'allocated': len(assignments), 'reserved': args.reserve,
                      'previous_watermark': output['previous_watermark'],
                      'next_watermark': output['next_watermark']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--watermark', type=Path, required=True)
    parser.add_argument('--proposals', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reserve', action='store_true', help='Advance the local watermark after reviewing the output')
    args = parser.parse_args()
    if args.reserve:
        # A stable sidecar lock survives the atomic replacement of the watermark.
        lock_path = args.watermark.with_suffix(args.watermark.suffix + '.openai.lock')
        with lock_path.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            execute(args)
    else:
        execute(args)


if __name__ == '__main__':
    main()
