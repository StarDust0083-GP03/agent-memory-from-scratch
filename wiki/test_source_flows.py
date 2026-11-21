"""Checks for the chapter-authored figures replacing the retired flow template."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CHAPTERS = ROOT.parent / 'book' / 'chapters'
NS = '{http://www.w3.org/2000/svg}'
FIGURE = re.compile(r'(?:!\[[^\]]*\]\(|src=")../../wiki/assets/([^)"]+\.svg)')


class AuthoredFigureTests(unittest.TestCase):
    def test_each_chapter_has_its_own_overview_and_illustrations(self):
        used = set()
        for chapter in CHAPTERS.glob('*.md'):
            refs = FIGURE.findall(chapter.read_text())
            prefix = chapter.stem.split('-')[0]
            overviews = [Path(ref).name for ref in refs if ref.endswith('-overview.svg')]
            self.assertEqual(overviews, [f'{prefix}-overview.svg'], chapter.name)
            for ref in refs:
                self.assertNotIn(ref, used, f'reused illustration: {ref}')
                self.assertTrue(ref.startswith(('rewrite-memory-a/', 'rewrite-memory-b/')), ref)
                used.add(ref)

    def test_referenced_figures_are_parseable_and_accessible(self):
        for chapter in CHAPTERS.glob('*.md'):
            for relative in FIGURE.findall(chapter.read_text()):
                with self.subTest(chapter=chapter.name, image=relative):
                    svg = ET.parse(ROOT / 'assets' / relative).getroot()
                    self.assertTrue(svg.get('viewBox'))
                    title = svg.find(NS + 'title')
                    self.assertIsNotNone(title)
                    self.assertTrue(title.text)
                    self.assertTrue(svg.get('role') == 'img' or svg.find(NS + 'desc') is not None)

    def test_builder_does_not_restore_retired_case_data(self):
        builder = (ROOT / 'build.mjs').read_text()
        self.assertNotIn('buildSourceFlows', builder)
        self.assertNotIn('buildDiagrams(root)', builder)


if __name__ == '__main__':
    unittest.main()
