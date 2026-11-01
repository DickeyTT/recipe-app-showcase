#!/usr/bin/env python3
"""Optional, offline batch-log suggestions. Never imports or rewrites input notes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import uuid

DATE = re.compile(r'^\s*(?:#{1,6}\s*|[-*]\s*)?(\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})\b', re.M)


def date_value(value):
    for fmt in ('%Y-%m-%d', '%d %B %Y', '%d %b %Y'):
        try:
            return datetime.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def measurements(text):
    patterns = {
        'pH': r'\bpH\s*[:=]?\s*(\d+(?:\.\d+)?)',
        'saltGrams': r'(\d+(?:\.\d+)?)\s*g\s+salt\b',
        'ingredientWeightGrams': r'ingredient\s+weight\s*[:=]\s*(\d+(?:\.\d+)?)\s*g\b',
        'saltPercent': r'(\d+(?:\.\d+)?)\s*%\s+salt\b',
    }
    result = {}
    for key, pattern in patterns.items():
        values = set(re.findall(pattern, text, re.I))
        result[key] = float(next(iter(values))) if len(values) == 1 else None
    return result


def candidates(text, source):
    """Only explicit date headings define boundaries; ambiguous dates remain in full text."""
    matches = [m for m in DATE.finditer(text) if date_value(m[1])]
    starts = [(m.start(), date_value(m[1])) for m in matches]
    if not starts or starts[0][0] > 0:
        starts.insert(0, (0, None))
    result = []
    for index, (start, date) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        body = text[start:end]
        if not body.strip():
            continue
        identity = str(uuid.uuid5(uuid.NAMESPACE_URL, source + ':' + str(start) + ':' + body))
        # Do not infer dates, quantities, recipe associations or a split inside undated prose.
        result.append({'id': identity, 'sourceFile': source, 'startDate': date,
                       'text': body, 'recipeSuggestion': None, **measurements(body),
                       'needsReview': True, 'reason': 'Review date, batch boundaries and recipe link before accepting.' if date else 'No unambiguous date; choose a date and review the complete text.'})
    return result


def prepare(source, output):
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists; choose a new JSON file.')
    source_folder = source if source.is_dir() else source.parent
    if output == source or output == source_folder or source_folder in output.parents:
        raise ValueError('Output must be outside the source folder.')
    files = sorted(source.rglob('*.md')) if source.is_dir() else [source]
    entries = []
    hashes = {}
    for file in files:
        if file.is_symlink():
            raise ValueError('Symlinked notes are not processed.')
        raw = file.read_bytes()
        text = raw.decode('utf-8')
        name = str(file.relative_to(source)) if source.is_dir() else file.name
        hashes[name] = hashlib.sha256(raw).hexdigest()
        entries.extend(candidates(text, name))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'version': 1, 'sourceHashes': hashes, 'candidates': entries}, stream, ensure_ascii=False, indent=2)
    return len(entries)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(f'{prepare(args.source, args.output)} suggestions prepared; nothing imported.')
