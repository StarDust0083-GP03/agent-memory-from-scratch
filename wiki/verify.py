#!/usr/bin/env python3
"""Check the built tutorials, comparison coverage, and offline diagrams."""
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BOOK = ROOT.parent / 'book'
entries = re.findall(r'\]\(chapters/([^)]+)\.md\)', (BOOK / 'SUMMARY.md').read_text())
errors = []


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

index = ROOT / 'assets' / 'search-index.json'
if not index.exists() or len(json.loads(index.read_text())) != len(entries):
    errors.append('search index mismatch')
else:
    indexed = {item['slug']: item['text'] for item in json.loads(index.read_text())}
    for slug in entries:
        teaching = (BOOK / 'chapters' / f'{slug}.md').read_text().split('<details class="implementation-notes">')[0]
        for heading in re.findall(r'^## (.+)$', teaching, re.M):
            normalized = ' '.join(re.sub(r'[#*`>|\[\]()_-]', ' ', heading).split())
            if normalized not in indexed.get(slug, ''):
                errors.append(f'heading missing from search index: {slug}: {heading}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'OK: {len(entries)} tutorials/exercises, short project examples, optional notes, closing tables, accessible SVGs, links/images and search index verified')
