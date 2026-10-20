#!/usr/bin/env python3
"""Validate the rewritten book, its authored figures and offline navigation."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BOOK = ROOT.parent / 'book'
SLUGS = re.findall(r'\]\(chapters/([^)]+)\.md\)', (BOOK / 'SUMMARY.md').read_text())


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.resources, self.missing_alt = [], [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        for key in ('href', 'src'):
            if key in a:
                self.resources.append(a[key])
        if tag == 'img' and not a.get('alt', '').strip():
            self.missing_alt.append(a.get('src', '?'))


def verify():
    assert len(SLUGS) == 19, 'chapter inventory changed'
    figures = set()
    indexed = {r['slug']: r['text'] for r in json.loads((ROOT / 'assets/search-index.json').read_text())}
    assert set(indexed) == set(SLUGS), 'search coverage mismatch'
    for slug in SLUGS:
        md = (BOOK / 'chapters' / f'{slug}.md').read_text()
        assert md.count('## 动手检查') == 1 and '答案提示：' in md, slug
        assert md.count('<details class="implementation-notes">') == 1, slug
        assert md.count('<details') == md.count('</details>'), slug
        assert md.count('## 本章对照结论') == 1, slug
        assert re.search(r'^\|.+\|$', md.split('## 本章对照结论')[1], re.M), slug
        sections = re.findall(r'<details class="source-example">(.*?)</details>', md, re.S)
        assert sections, f'missing source examples: {slug}'
        for section in sections:
            assert len(re.findall(r'!\[[^\]]+\]\([^)]+\.svg\)', section)) == 1, slug
        refs = re.findall(r'(?:\]\(|src=")../../wiki/assets/([^\)" ]+\.svg)', md)
        assert len(refs) >= len(sections) + 1, f'missing overview: {slug}'
        assert not any(r.startswith(('diagrams/', 'source-flows/')) for r in refs), f'old diagram still referenced: {slug}'
        figures.update(refs)
        assert len(indexed[slug]) > 1000, f'empty search text: {slug}'
    for relative in figures:
        path = ROOT / 'assets' / relative
        svg = ET.parse(path).getroot()
        ns = '{http://www.w3.org/2000/svg}'
        assert svg.get('viewBox'), path
        title = svg.find(ns + 'title')
        assert title is not None and title.text, f'missing SVG title: {path}'
        assert svg.get('role') == 'img' or svg.find(ns + 'desc') is not None, path
    pages = {p.resolve(): Page(p.read_text()) for p in list(ROOT.glob('*.html')) + list((ROOT / 'chapters').glob('*.html'))}
    for path, page in pages.items():
        assert 'main' in page.ids, path
        assert len(page.ids) == len(set(page.ids)), f'duplicate IDs: {path}'
        assert not page.missing_alt, path
        for resource in page.resources:
            assert not resource.startswith('../../wiki/assets/'), (path, resource)
            url = urlsplit(resource)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            assert target.exists(), (path, resource)
            if url.fragment and target in pages:
                assert unquote(url.fragment) in pages[target].ids, (path, resource)
    print(f'OK: {len(SLUGS)} chapters, exercises/answers, {len(figures)} new SVGs, local links, IDs and search')


if __name__ == '__main__':
    verify()
