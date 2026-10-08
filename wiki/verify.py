#!/usr/bin/env python3
"""Check the built tutorials, comparison coverage, and offline diagrams."""
from html.parser import HTMLParser
from pathlib import Path
import json
import csv
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BOOK = ROOT.parent / 'book'
entries = re.findall(r'\]\(chapters/([^)]+)\.md\)', (BOOK / 'SUMMARY.md').read_text())
errors = []
flow_references = set()


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []
        self.ids = set()
        self.duplicates = []
        self.images_without_alt = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                self.duplicates.append(attrs['id'])
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.resources.append(attrs[key])
        if tag == 'img' and not attrs.get('alt', '').strip():
            self.images_without_alt.append(attrs.get('src', 'unknown'))


for slug in entries:
    chapter = ROOT / 'chapters' / f'{slug}.html'
    if not chapter.exists():
        errors.append(f'missing {chapter}')
        continue
    md = (BOOK / 'chapters' / f'{slug}.md').read_text()
    if md.count('## 动手检查') != 1 or '答案提示：' not in md:
        errors.append(f'missing exercise/answer guidance: {slug}')
    if md.count('<details class="implementation-notes">') != 1:
        errors.append(f'expected one optional implementation section: {slug}')
    if md.count('<details') != md.count('</details>'):
        errors.append(f'unbalanced optional sections: {slug}')
    teaching = md.split('<details class="implementation-notes">')[0]
    references = re.findall(r'!\[本例流程\]\(../../wiki/assets/source-flows/([^/]+)\.svg\)', teaching)
    prefix = 'appendix' if slug.startswith('appendix-') else slug[:2]
    expected = [f'{prefix}-{i:02d}' for i in range(1, teaching.count('<details class="source-example">') + 1)]
    if references != expected:
        errors.append(f'source flow/order mismatch: {slug}')
    flow_references.update(references)
    visible = re.sub(r'<details class="source-example">.*?</details>', '', teaching, flags=re.S)
    for title, section in re.findall(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)', visible, re.M | re.S):
        if title == '动手检查':
            continue
        for project in ('Mem0', 'Graphiti'):
            examples = re.findall(rf'^{project}：(.+)$', section, re.M)
            if len(examples) != 1 or len(examples[0]) > 180:
                errors.append(f'expected one short visible {project} example: {slug}: {title}')
    if md.count('## 本章对照结论') != 1:
        errors.append(f'expected one closing comparison: {slug}')
    elif not re.search(r'^\|.+\|$', md.split('## 本章对照结论')[1], re.M):
        errors.append(f'missing conclusion table: {slug}')
    if f'diagrams/{slug}.svg' not in md:
        errors.append(f'missing chapter diagram reference: {slug}')

for path in ROOT.rglob('*.html'):
    page = Page()
    page.feed(path.read_text())
    if 'main' not in page.ids:
        errors.append(f'no main: {path}')
    if page.duplicates:
        errors.append(f'duplicate IDs in {path}: {page.duplicates}')
    if page.images_without_alt:
        errors.append(f'images without alt in {path}: {page.images_without_alt}')
    for resource in page.resources:
        if resource.startswith('../../wiki/assets/'):
            errors.append(f'book-relative asset path in rendered page: {path}: {resource}')
        if resource.startswith(('http:', 'https:', 'mailto:', 'data:', '#')) or '+' in resource:
            continue
        local = resource.split('#')[0].split('?')[0]
        if local and not (path.parent / local).resolve().exists():
            errors.append(f'broken {path}: {resource}')

specs = json.loads((BOOK / 'diagrams.json').read_text())
if set(specs) != set(entries):
    errors.append('diagram specification/chapter mismatch')
ns = {'svg': 'http://www.w3.org/2000/svg'}
for slug in entries:
    path = ROOT / 'assets' / 'diagrams' / f'{slug}.svg'
    try:
        svg = ET.parse(path).getroot()
        for tag in ('title', 'desc'):
            node = svg.find(f'svg:{tag}', ns)
            if node is None or not node.text:
                errors.append(f'missing SVG {tag}: {path}')
        if 'viewBox' not in svg.attrib:
            errors.append(f'missing SVG viewBox: {path}')
    except (OSError, ET.ParseError) as error:
        errors.append(f'invalid diagram {path}: {error}')

with (BOOK / 'source-flows.tsv').open() as source:
    flows = list(csv.DictReader(source, delimiter='\t'))
flow_ids = {f'{row["chapter"]}-{int(row["section"]):02d}' for row in flows}
if len(flow_ids) != len(flows) or flow_ids != flow_references:
    errors.append('source flow data/reference mismatch')
if {p.stem for p in (ROOT / 'assets' / 'source-flows').glob('*.svg')} != flow_ids:
    errors.append('source flow assets/data mismatch')
for row in flows:
    flow_id = f'{row["chapter"]}-{int(row["section"]):02d}'
    path = ROOT / 'assets' / 'source-flows' / f'{flow_id}.svg'
    try:
        svg = ET.parse(path).getroot()
        title = svg.find('svg:title', ns)
        desc = svg.find('svg:desc', ns)
        if title is None or not title.text or desc is None or not desc.text or 'viewBox' not in svg.attrib:
            errors.append(f'missing accessible source flow metadata: {flow_id}')
        elif any(value not in desc.text for key, value in row.items() if key not in ('chapter', 'section')):
            errors.append(f'source flow content mismatch: {flow_id}')
    except (OSError, ET.ParseError) as error:
        errors.append(f'invalid source flow {path}: {error}')

index = ROOT / 'assets' / 'search-index.json'
if not index.exists() or len(json.loads(index.read_text())) != len(entries):
    errors.append('search index mismatch')
else:
    indexed = {item['slug']: item['text'] for item in json.loads(index.read_text())}
    for row in flows:
        slug = next((s for s in entries if s.startswith(row['chapter'] + '-')), None)
        if slug is None or any(value not in indexed.get(slug, '') for key, value in row.items() if key not in ('chapter', 'section')):
            errors.append(f'source flow missing from search index: {row["chapter"]}:{row["section"]}')
    for slug in entries:
        teaching = (BOOK / 'chapters' / f'{slug}.md').read_text().split('<details class="implementation-notes">')[0]
        for heading in re.findall(r'^## (.+)$', teaching, re.M):
            normalized = ' '.join(re.sub(r'[#*`>|\[\]()_-]', ' ', heading).split())
            if normalized not in indexed.get(slug, ''):
                errors.append(f'heading missing from search index: {slug}: {heading}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'OK: {len(entries)} tutorials/exercises, short project examples, {len(flows)} source flows, optional notes, closing tables, accessible SVGs, links/images and search index verified')
