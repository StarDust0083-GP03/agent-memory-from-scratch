#!/usr/bin/env python3
"""Render explicitly authored evidence diagrams for the rewritten first half and appendix."""
from html import escape
from pathlib import Path
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent


def wrap(value, limit):
    lines, line, width = [], '', 0
    for char in value:
        size = 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
        if width + size > limit:
            lines.append(line)
            line, width = '', 0
        line += char
        width += size
    return lines + [line] if line else lines


def text(x, y, value, limit=64, color='#243b48', size=19):
    lines = wrap(value, limit)
    return ''.join(f'<text x="{x}" y="{y+i*28}" font-size="{size}" fill="{color}">{escape(line)}</text>'
                   for i, line in enumerate(lines))


def render():
    count = 0
    for line in (ROOT / 'book/rewrite-diagrams.txt').read_text().splitlines():
        if not line.strip():
            continue
        name, layout, title, *items = line.strip().split('|')
        rows = [item.split('~', 1) for item in items]
        assert layout in ('steps', 'matrix') and len(rows) == 3, name
        group, filename = name.split('/')
        out = ROOT / 'wiki/assets' / f'rewrite-memory-{group}' / f'{filename}.svg'
        out.parent.mkdir(parents=True, exist_ok=True)
        description = '；'.join(f'{label}：{value}' for label, value in rows)
        height = 440
        body = text(30, 42, title, 70, size=24)
        if layout == 'matrix':
            body += text(45, 90, '核对对象', size=16, color='#536772')
            body += text(270, 90, '具体状态与验收条件', size=16, color='#536772')
            for i, (label, value) in enumerate(rows):
                y = 110 + i * 100
                body += f'<rect x="28" y="{y}" width="824" height="88" fill="{["#e5ede9", "#e7edf2"][i%2]}"/>'
                body += text(45, y+29, label, 22, size=18)
                body += text(270, y+29, value, 60, size=18)
        else:
            for i, (label, value) in enumerate(rows):
                y = 100 + i * 105
                body += f'<circle cx="58" cy="{y+30}" r="22" fill="#285d75"/>'
                body += text(52, y+37, str(i+1), color='white', size=21)
                body += f'<rect x="105" y="{y}" width="745" height="85" fill="#e8ede7"/>'
                body += text(122, y+28, label, 72, size=19)
                body += text(122, y+57, value, 78, size=18)
                if i < 2:
                    body += f'<path d="M58 {y+53} V{y+82}" stroke="#285d75" stroke-width="2"/>'
                    body += f'<path d="M52 {y+76} L58 {y+85} L64 {y+76}" fill="none" stroke="#285d75" stroke-width="2"/>'
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc><rect width="880" height="{height}" fill="#faf8f1"/><g font-family="Noto Sans CJK SC,system-ui,sans-serif">{body}</g></svg>\n'
        ET.fromstring(svg)
        out.write_text(svg)
        count += 1
    print(f'Rendered {count} new chapter-specific diagrams')


if __name__ == '__main__':
    render()
