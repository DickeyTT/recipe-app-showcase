#!/usr/bin/env python3
"""Transfer approved catalogue metadata to tidy notes; never replace existing files."""
import argparse
import csv
import json
from pathlib import Path


def confined(root, relative):
    value = Path(relative)
    root = Path(root).resolve()
    if value.is_absolute() or '..' in value.parts or not value.parts:
        raise ValueError(f'Unsafe relative path: {relative}')
    target = (root / value).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f'Path escapes its root: {relative}')
    return target


def transfer(mapping, working):
    working = Path(working).resolve()
    tidy = working / 'tidy'
    plans = []
    missing = []
    seen = set()
    with Path(mapping).open(newline='', encoding='utf-8-sig') as handle:
        for row in csv.DictReader(handle):
            relative = row['tidy_file']
            if relative in seen:
                raise ValueError(f'Duplicate map entry: {relative}')
            seen.add(relative)
            source = confined(tidy, relative)
            if source.suffix != '.md' or not source.is_file():
                raise ValueError(f'Missing Markdown: {relative}')
            if row['type'] not in ('recipe', 'note'):
                raise ValueError(f'Invalid type: {relative}')
            if not row['catalogue_sidecar']:
                missing.append(relative)
                continue
            prefix, separator, rest = row['catalogue_sidecar'].partition('/')
            if prefix != 'catalogue-full' or not separator:
                raise ValueError(f'Sidecar must be in catalogue-full: {relative}')
            original = confined(working / 'catalogue-full', rest)
            data = json.loads(original.read_text(encoding='utf-8'))
            data['sourceFile'] = relative
            data.pop('cleanTitle', None)
            data['likelyDuplicateOf'] = None
            data['duplicateStatus'] = None
            data['isRecipe'] = row['type'] == 'recipe'
            destination = source.with_suffix('.catalogue.json')
            # Refuse a symlink destination, including a dangling one.
            if destination.is_symlink():
                raise ValueError(f'Symlink destination: {relative}')
            if destination.exists():
                if json.loads(destination.read_text(encoding='utf-8')) != data:
                    raise ValueError(f'Refusing to replace different sidecar: {relative}')
            else:
                plans.append((destination, data))
    # Validate every row before any write. Exclusive creation prevents replacement.
    for destination, data in plans:
        with destination.open('x', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
    return {'created': len(plans), 'mapped': len(seen) - len(missing), 'missing': missing}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', required=True, type=Path)
    parser.add_argument('--working', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(transfer(args.map, args.working), ensure_ascii=False, indent=2))
