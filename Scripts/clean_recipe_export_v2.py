#!/usr/bin/env python3
"""Second-pass recipe cleanup informed by review of the Asian Cooking export."""
import re
import sys
import json
import clean_recipe_export as base
original_clean=base.clean

def clean(text):
    lines=text.splitlines(); masked=list(lines); changes=[]; section=False; footer=False; rating=False
    def remove(i,why):
        if masked[i].strip():changes.append({'line':i+1,'reason':why,'text':lines[i]})
        masked[i]=''
    roundup='15 Recipes that Use Gochujang' in text[:600] or 'Traditional Korean Party Menu Ideas' in text[:600]
    smitten='Source URL: https://smittenkitchen.com/' in text
    body=False; delimiters=0
    for i,line in enumerate(lines):
        t=line.strip(); h=base.heading(line)
        if t=='---' and not body:
            delimiters+=1
            if delimiters==2:body=True
            continue
        if not body:continue
        # These two reviewed articles finish their actual recipe before taxonomy/comment footers.
        if smitten and (t.startswith('See more:') or h and re.match(r'(?:\d+ comments on|leave a reply|rate this|share this|post navigation|like this post)',h[1])):footer=True
        if footer:remove(i,'Reader comments, site navigation and repeated footer capture');continue
        promo=h and re.search(r'^(?:more .*(?:recipes|bowls)|other .*recipes|related articles|thank you for rating|subscribe|you may also like)',h[1])
        if promo and not roundup:section=True
        elif section and h:
            # Recommendation cards sometimes use the SAME heading level as the section.
            # A linked card heading stays in the section; a genuine recipe heading ends it.
            linked=bool(re.match(r'^#{1,6}\s*[*_]*\[',t))
            if not linked and not promo:section=False
        if section:remove(i,'Unrelated recipe recommendations, cards or newsletter section');continue
        if re.fullmatch(r'(?:[*-]\s*)?\d+(?:[.,]\d+)?[kK]?',t):
            nearby=' '.join(lines[max(0,i-2):i+4]).lower()
            if 'shares' in nearby:remove(i,'Share counter detached from its website control');continue
        if t.startswith('[★★★★★') or t=='★★★★★' or t=='[★★★★★':rating=True
        if rating:
            if not t or 'reviews' in t.lower() or '★' in t:
                remove(i,'Website star-rating widget')
                if 'reviews' in t.lower():rating=False
                continue
            rating=False
        if re.fullmatch(r'\[?\d+(?:\.\d+)? from \d+ reviews?\]?(?:\([^\n]+\))?',t,re.I) or t.lower()=='no reviews':remove(i,'Website review count');continue
        if re.match(r'^\*?\*?Clip source:',t):remove(i,'Redundant clip-source line; source URL retained in metadata');continue
        if re.fullmatch(r'(?:[*-]|\d+\.)\s+\[[^\]]+\]\(https?://[^\n]*#h-[^\n]*\)',t):remove(i,'In-page table-of-contents link');continue
        if re.fullmatch(r'\[(?:Leave a Review|Print|Print Recipe|Jump to Recipe)\]\([^\n]+\)',t,re.I):remove(i,'Website action link');continue
        if t.startswith('http://www.flickr.com/photos/'):remove(i,'Redundant Flickr link; embedded photograph retained');continue
        if re.match(r'^\*\*(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten) years? ago:',t):remove(i,'Unrelated archive recommendation');continue
        if re.match(r'^(?:Subscribe|to get recipes via email|Share what you love\.\.\.|Happy Week!|xoxo|~ Suwanee)$',t,re.I):remove(i,'Newsletter or author sign-off');continue
        if re.match(r'^(?:_Love this recipe_\?|We appreciate your feedback!|This post contains affiliate links\.)',t):remove(i,'Website engagement or affiliate disclosure; recipe attribution retained');continue
        if re.search(r'!\[.*(?:svg_\d+\.svg|All-things-beautiful-\.png)',t) and t.startswith('!'):remove(i,'Reviewed decorative rating or promotional graphic');continue
    result, prior=original_clean('\n'.join(masked))
    # Retain one top-level title; the opening exported title is redundant when the page title follows.
    out=result.splitlines(); headings=[i for i,l in enumerate(out) if re.match(r'^#\s+',l)]
    if len(headings)>=2 and headings[1]-headings[0]<8:
        first=out[headings[0]];out.pop(headings[0]);result='\n'.join(out)+'\n'
        n=next((i for i,l in enumerate(lines) if l==first),0)
        changes.append({'line':n+1,'reason':'Export wrapper title; original page title retained','text':first})
    # Reviewed personal-note style recipe: explicitly label its ingredient run and method.
    if smitten and '# chana masala' in result:
        result=result.replace('\n1 tablespoon vegetable oil\n','\n## Ingredients\n\n1 tablespoon vegetable oil\n',1)
        result=result.replace('\nHeat oil in a large skillet.','\n## Method\n\nHeat oil in a large skillet.',1)
        active=False; formatted=[]
        for l in result.splitlines():
            if l=='## Ingredients':active=True
            elif l=='## Method':active=False
            if active and l and not l.startswith('#'):l='* '+l
            formatted.append(l)
        result='\n'.join(formatted)+'\n'
    return re.sub(r'\n{3,}','\n\n',result),sorted(changes+prior,key=lambda x:x['line'])

if __name__=='__main__':
    base.clean=clean
    base.main()
    destination = base.Path(sys.argv[2]).resolve()
    notes = """<h2>Editorial review — second pass</h2><ul><li>Removed orphaned share counts only where the source identifies them as Shares; quantities, timings and serving counts are retained.</li><li>Removed unrelated recipe cards and their displayed pictures, website ratings, navigation and newsletter material.</li><li>Chana masala and peanut sesame noodles: removed reader-comment threads and repeated footer captures; retained substitution and storage notes. Added Ingredients and Method headings and ingredient bullets to chana masala without changing quantities.</li><li>Retained the gochujang recipe roundup and Korean party-menu article: their collections of recipe links are intentional content.</li><li><strong>Source issue:</strong> Chicken, Lentil &amp; Pumpkin Curry mentions onion in its method but has no onion quantity in the ingredients. Check the source before cooking; no quantity has been invented.</li><li>Some introductory narrative and repeated step-by-step explanations remain where they may contain useful technique. This is not a fully rewritten recipe-card collection.</li></ul>"""
    report = destination / 'Cleanup-Report.html'
    page = report.read_text().replace('first cleanup pass', 'second cleanup pass').replace('<p>Original files', notes + '<p>Original files')
    report.write_text(page)
    audit = destination / 'Review/cleanup-audit.json'
    payload = json.loads(audit.read_text())
    payload['editorial_notes'] = ['Chana masala: added section headings and ingredient bullets, quantities unchanged.', 'Chicken, Lentil & Pumpkin Curry: method mentions onion but no ingredient quantity; unresolved source issue.', 'Recipe roundups retained intentionally.']
    audit.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
