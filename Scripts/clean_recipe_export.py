#!/usr/bin/env python3
"""Conservative, auditable cleanup of an exported Markdown recipe folder."""
import argparse, collections, difflib, hashlib, html, json, re, shutil
from pathlib import Path

def heading(line):
    m = re.match(r'^(#{1,6})\s+(.*)', line.strip())
    return (len(m[1]), re.sub(r'[*_⭐️]', '', m[2]).strip().rstrip(':').lower()) if m else None

PROMO = re.compile(r'^(you may also like|related|related recipes|more recipes you may enjoy|did you make this recipe\??|rate the recipe!?|follow along on social.*|more kimchi recipes you may like)$', re.I)
PROTECTED = re.compile(r'ingredient|instruction|direction|method|note|tip|storage|serving|nutrition|sauce|marinade|garnish|how to', re.I)
UI = {'measure','scale','units','shares','my other videos','my newsletter'}

def clean(text):
    lines = text.splitlines(); kept=[]; removed=[]; section=None; index=0
    # Preserve the metadata verbatim.
    if lines and lines[0].strip() == '---':
        end = next((i for i in range(1,len(lines)) if lines[i].strip() == '---'), None)
        if end is not None: kept.extend(lines[:end+1]); index=end+1
    seen_titles=set()
    for i in range(index,len(lines)):
        line=lines[i]; stripped=line.strip(); h=heading(line); reason=None
        if section and h and (h[0] <= section or PROTECTED.search(h[1])): section=None
        if h and PROMO.fullmatch(h[1]): section=h[0]; reason='Website recommendation or engagement section'
        elif section: reason='Website recommendation or engagement section'
        elif stripped.lower() in UI: reason='Website widget label'
        elif re.fullmatch(r'\[(?:Print|Print Recipe|Jump to Recipe|Pin Recipe|Save Recipe)\]\([^\n]+\)',stripped,re.I): reason='Website action link'
        elif re.match(r'^(?:Tried this recipe\?Mention|Did You Make This\?I love seeing|\*?\*?⭐️.*RATE THE RECIPE)',stripped,re.I): reason='Rating or social-sharing prompt'
        elif re.fullmatch(r'#+\s*',stripped): reason='Empty heading'
        elif ('![[' in stripped or '![' in stripped) and re.search(r'\\?\|1x1(?:\]|\))',stripped) and stripped.startswith('!'): reason='Tracking-pixel image'
        elif h and h[0]==1:
            # Remove only literally repeated headings, never infer equivalence of recipes.
            if h[1] in seen_titles: reason='Repeated identical title'
            seen_titles.add(h[1])
        if reason:
            removed.append({'line':i+1,'reason':reason,'text':line})
        else: kept.append(line)
    output=re.sub(r'\n{3,}','\n\n','\n'.join(kept)).strip()+'\n'
    return output,removed

def main():
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path);args=parser.parse_args()
    src=args.source.resolve(); dest=args.destination.resolve()
    if dest.exists(): raise SystemExit('Destination already exists; refusing to overwrite.')
    if dest==src or src in dest.parents: raise SystemExit('Destination must be outside the source export.')
    imported=dest/'Import' / src.name; imported.mkdir(parents=True)
    audit=dest/'Review';audit.mkdir()
    records=[]; urls=collections.defaultdict(list);before={}
    for f in sorted(src.glob('*.md')):
        original=f.read_text();before[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
        cleaned,removed=clean(original)
        (imported/f.name).write_text(cleaned)
        patch=''.join(difflib.unified_diff(original.splitlines(True),cleaned.splitlines(True),fromfile='original/'+f.name,tofile='cleaned/'+f.name))
        (audit/(f.name+'.diff.txt')).write_text(patch)
        hs=[heading(l)[1] for l in cleaned.splitlines() if heading(l)]
        flags=[]
        if not any('ingredient' in x for x in hs): flags.append('No explicit ingredients heading; may be a personal note or alternative layout.')
        if not any(re.search(r'instruction|direction|method|how to',x) for x in hs): flags.append('No explicit method heading; review structure manually.')
        if len(cleaned)>18000:flags.append('Long clipping retained: review introductions, comments and repeated recipe narrative.')
        if len(re.findall(r'^#{1,6}\s+\**Ingredients\b',cleaned,re.M|re.I))>1:flags.append('Multiple ingredient sections retained; may be components or repeated recipe cards.')
        if re.search(r'!\[[^\]]*\]\(https?://',cleaned): flags.append('Remote image references remain; not all photos can be offline from this export.')
        if sum(1 for x in removed if x['text'].strip())>len([x for x in original.splitlines() if x.strip()])*.3:flags.append('More than 30% of nonblank lines removed; inspect diff before importing.')
        source=re.search(r'^Source URL:\s*(\S+)',original,re.M)
        if source:urls[source[1].rstrip('/')].append(f.name)
        records.append({'file':f.name,'removed':removed,'flags':flags,'before_chars':len(original),'after_chars':len(cleaned)})
    if (src/'_resources').exists():shutil.copytree(src/'_resources',imported/'_resources')
    duplicates=[{'source':u,'files':fs} for u,fs in urls.items() if len(fs)>1]
    for group in duplicates:
        for row in records:
            if row['file'] in group['files']:row['flags'].append('Possible duplicate: same source URL as another file. Both retained.')
    # Verify no source changes and exact preservation of copied resources.
    assert all(hashlib.sha256((src/n).read_bytes()).hexdigest()==h for n,h in before.items())
    resources=[p for p in (src/'_resources').rglob('*') if p.is_file()]
    assert all(hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256((imported/p.relative_to(src)).read_bytes()).digest() for p in resources)
    assert len(list(imported.glob('*.md')))==len(records)
    report={'recipes':len(records),'changed':sum(bool(r['removed']) for r in records),'removed_nonblank_lines':sum(bool(x['text'].strip()) for r in records for x in r['removed']),'resource_files_verified':len(resources),'possible_duplicate_groups':duplicates,'records':records}
    (audit/'cleanup-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    rows=[]
    for r in records:
        removals=''.join('<li>'+html.escape(x['reason']+': '+x['text'])+'</li>' for x in r['removed'] if x['text'].strip())
        flags=''.join('<li>'+html.escape(x)+'</li>' for x in r['flags'])
        rows.append('<details><summary>'+html.escape(r['file'])+f" — {len(r['removed'])} lines removed</summary>"+('<ul class="flags">'+flags+'</ul>' if flags else '')+'<ul>'+removals+'</ul></details>')
    (dest/'Cleanup-Report.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Recipe cleanup review</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:24px;background:#f8f7f2;color:#26332c}summary{cursor:pointer;font-weight:600}details{padding:16px;margin:10px 0;background:white;border-radius:10px}li{margin:10px 0;overflow-wrap:anywhere}.flags{color:#765318}</style><h1>Asian Cooking · first cleanup pass</h1>'''+f"<p>{len(records)} recipes retained · {report['changed']} with clutter removed · {report['removed_nonblank_lines']} nonblank lines removed · {len(resources)} resource files verified.</p>"+'''<p>Original files were not modified. Ingredients, quantities and cooking instructions were not rewritten. Narrative, nutrition, tips and uncertain sections were retained. Expand each recipe to inspect removals and review flags. Full before/after diffs are in Review.</p><p><strong>Import only the Import/Asian Cooking folder.</strong> Cleaned recipes may import as new entries alongside existing originals; this pack does not replace your current app library.</p>'''+''.join(rows)+'</html>')
    (dest/'START-HERE.txt').write_text('Asian Cooking cleanup pilot\n\nOpen Cleanup-Report.html first. Import only Import/Asian Cooking.\n\nAll 97 recipes remain, including possible duplicates. Review flags identify ambiguous content. Full change details are in Review/cleanup-audit.json and per-file diffs. Every original resource file was copied and hash-verified. Your source export was not changed.\n\nDo not bulk-import over the current library expecting replacement: changed files receive new entries. Try a few cleaned recipes first, then remove the older versions using Recently deleted if preferred.\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
