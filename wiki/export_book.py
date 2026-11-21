#!/usr/bin/env python3
"""Export the built wiki chapters to EPUB 3 and a printable PDF."""
import html
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

WIKI = Path(__file__).resolve().parent
ROOT = WIKI.parent
OUT = ROOT / 'exports'
TITLE = 'Agent Memory from Scratch'
STEM = 'agent-memory-from-scratch'
EDITION = '2026-11-21'
CSS = '''
body {font-family:"Noto Serif CJK SC",serif; color:#252820; line-height:1.65}
a {color:#29564c; overflow-wrap:anywhere}
h1,h2,h3,summary {break-after:avoid}
figure {margin:1em 0; break-inside:avoid}
img,svg {display:block; width:auto; max-width:100%; max-height:110mm; height:auto; margin:0 auto}
figcaption {font-size:.85em}
pre {padding:.6em; font-size:.82em; background:#f4f1e8; white-space:pre-wrap; overflow-wrap:anywhere}
code {font-family:"Noto Sans Mono CJK SC",monospace; overflow-wrap:anywhere}
table {width:100%; border-collapse:collapse; table-layout:fixed; font-size:.87em}
th,td {padding:.3em; border-bottom:1px solid #d9d2c3; vertical-align:top; overflow-wrap:anywhere}
blockquote {margin:1em 0; padding-left:1em; border-left:1px solid #d9d2c3}
@media print {
  @page {size:A5; margin:15mm 14mm 17mm}
  body {margin:0; font-size:10.5pt; orphans:3; widows:3}
  .cover {padding-top:36mm; break-after:page}
  .chapter {break-before:page}
}
'''


def document(title, body, style):
    return (f'<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" '
            f'xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN" xml:lang="zh-CN">'
            f'<head><meta charset="utf-8"/><title>{html.escape(title)}</title>{style}</head>'
            f'<body>{body}</body></html>')


def build():
    summary = (ROOT / 'book/SUMMARY.md').read_text(encoding='utf-8')
    entries = re.findall(r'^\d+\. \[([^\]]+)\]\(chapters/([^)]+)\.md\)$', summary, re.M)
    assert entries, 'no chapters in SUMMARY.md'
    names = {slug + '.html' for _, slug in entries}
    css_link = '<link rel="stylesheet" href="style.css"/>'
    cover = f'<section class="cover"><h1>{TITLE}</h1><p>Agent 长期记忆设计与实现 · {EDITION} 重编版</p></section>'
    files = {'style.css': CSS, 'cover.xhtml': document(TITLE, cover, css_link)}
    manifest = ['<item id="css" href="style.css" media-type="text/css"/>',
                '<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>']
    spine = ['<itemref idref="cover"/>']
    epub_toc, print_toc, print_chapters = [], [], []
    images = set()

    for i, (title, slug) in enumerate(entries):
        source = (WIKI / 'chapters' / (slug + '.html')).read_text(encoding='utf-8')
        body = re.search(r'<article class="content">([\s\S]+?)</article>', source)[1]
        body = re.sub(r'<details(?=[\s>])', '<details open="open"', body)
        body = re.sub(r'<(img|hr|br)\b([^>]*?)(?<!/)>', r'<\1\2/>', body)
        images.update(re.findall(r'\bsrc="\.\./(assets/[^"]+\.svg)"', body))

        def links(text, printing):
            def rewrite(match):
                value = html.unescape(match[1])
                url = urlsplit(value)
                if url.scheme or url.netloc:
                    return match[0]
                assert not url.path or url.path in names, (slug, value)
                target = url.path.removesuffix('.html') or slug
                if printing:
                    return f'href="#{target}{"-" + url.fragment if url.fragment else ""}"'
                fragment = '#' + url.fragment if url.fragment else ''
                return f'href="{target}.xhtml{fragment}"'
            return re.sub(r'\bhref="([^"]+)"', rewrite, text)

        filename = slug + '.xhtml'
        chapter = links(body, False).replace('src="../assets/', 'src="assets/')
        files[filename] = document(title, chapter, css_link)
        props = ' properties="svg"' if '<svg ' in chapter else ''
        manifest.append(f'<item id="c{i}" href="{filename}" media-type="application/xhtml+xml"{props}/>')
        spine.append(f'<itemref idref="c{i}"/>')
        epub_toc.append(f'<li><a href="{filename}">{html.escape(title)}</a></li>')
        print_toc.append(f'<li><a href="#{slug}">{html.escape(title)}</a></li>')
        printable = links(body, True).replace('src="../assets/', f'src="{WIKI.as_uri()}/assets/')
        printable = re.sub(r'\b(id|aria-labelledby)="([^"]+)"',
                           lambda m: f'{m[1]}="{" ".join(f"{slug}-{x}" for x in m[2].split())}"', printable)
        print_chapters.append(f'<section class="chapter" id="{slug}">{printable}</section>')

    for i, image in enumerate(sorted(images)):
        files[image] = (WIKI / image).read_bytes()
        manifest.append(f'<item id="img{i}" href="{image}" media-type="image/svg+xml"/>')
    files['nav.xhtml'] = document('目录', '<nav epub:type="toc"><h1>目录</h1><ol>' + ''.join(epub_toc) + '</ol></nav>', css_link)
    manifest.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
    opf = f'''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="book-id">urn:uuid:a17ad34c-8445-401e-9657-01da54002931</dc:identifier>
<dc:title>{TITLE}</dc:title><dc:language>zh-CN</dc:language><dc:date>{EDITION}</dc:date>
<meta property="dcterms:modified">{EDITION}T00:00:00Z</meta></metadata>
<manifest>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine></package>'''
    files['content.opf'] = opf
    validate(files)
    print_html = document(TITLE, cover + '<nav><h1>目录</h1><ol>' + ''.join(print_toc) +
                          '</ol></nav>' + ''.join(print_chapters), f'<style>{CSS}</style>')
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        temp = Path(directory)
        with ZipFile(temp / f'{STEM}.epub', 'w') as z:
            z.writestr(ZipInfo('mimetype'), 'application/epub+zip', compress_type=ZIP_STORED)
            z.writestr(ZipInfo('META-INF/container.xml'), '''<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>''', compress_type=ZIP_DEFLATED)
            for name, data in files.items():
                z.writestr(ZipInfo(f'OEBPS/{name}'), data, compress_type=ZIP_DEFLATED)
        page = temp / 'print.html'
        page.write_text(print_html, encoding='utf-8')
        pdf = temp / f'{STEM}.pdf'
        subprocess.run([os.environ.get('CHROME', 'chromium'), '--headless=new', '--disable-gpu',
                        '--no-pdf-header-footer', f'--user-data-dir={temp / "chromium"}',
                        f'--print-to-pdf={pdf}', page.as_uri()], check=True)
        assert pdf.is_file() and pdf.stat().st_size > 0, 'Chromium did not produce a PDF'
        for suffix in ('epub', 'pdf'):
            name = f'{STEM}.{suffix}'
            (temp / name).replace(OUT / name)
    print(f'Exported {len(entries)} chapters and {len(images)} SVG assets to exports/')


def validate(files):
    docs = {name: ET.fromstring(data) for name, data in files.items() if not name.endswith('.css')}
    ids = {name: {node.get('id') for node in root.iter()} for name, root in docs.items()}
    for name, root in docs.items():
        for node in root.iter():
            for attr in ('href', 'src'):
                if attr not in node.attrib:
                    continue
                url = urlsplit(node.attrib[attr])
                if url.scheme or url.netloc:
                    continue
                target = unquote(url.path) or name
                assert target in files, (name, target)
                if url.fragment:
                    assert unquote(url.fragment) in ids[target], (name, target, url.fragment)


if __name__ == '__main__':
    build()
