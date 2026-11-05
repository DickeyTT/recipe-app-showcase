#!/usr/bin/env python3
"""Apply the 103 Codex-read catalogue decisions to unchanged tidy Markdown only."""
import argparse
import hashlib
import json
from pathlib import Path
from tidy_sidecars import confined


def apply(manifest, tidy):
    entries = json.loads(Path(manifest).read_text(encoding='utf-8'))
    plans = []
    seen = set()
    for entry in entries:
        data = entry['catalogue']
        name = data['sourceFile']
        if name in seen:
            raise ValueError(f'Duplicate decision: {name}')
        seen.add(name)
        source = confined(tidy, name)
        if source.suffix != '.md' or hashlib.sha256(source.read_bytes()).hexdigest() != entry['markdownSHA256']:
            raise ValueError(f'Markdown has changed: {name}')
        target = source.with_suffix('.catalogue.json')
        if target.is_symlink():
            raise ValueError(f'Symlink destination: {name}')
        if target.exists():
            if json.loads(target.read_text(encoding='utf-8')) != data:
                raise ValueError(f'Refusing to replace existing sidecar: {name}')
        else:
            plans.append((target, data))
    for target, data in plans:
        with target.open('x', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
    return len(plans)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tidy', required=True, type=Path)
    args = parser.parse_args()
    print(f'Created {apply(Path(__file__).with_name("tidy-catalogue-additions.json"), args.tidy)} sidecars.')
