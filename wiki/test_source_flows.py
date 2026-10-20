"""Checks for the chapter-authored figures replacing the retired flow template."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CHAPTERS = ROOT.parent / 'book' / 'chapters'
NS = '{http://www.w3.org/2000/svg}'


class AuthoredFigureTests(unittest.TestCase):
    def test_each_source_example_has_its_own_new_figure(self):
        used = set()
        for chapter in CHAPTERS.glob('*.md'):
            text = chapter.read_text()
            sections = re.findall(r'<details class="source-example">(.*?)</details>', text, re.S)
            self.assertTrue(sections, chapter.name)
            for section in sections:
                refs = re.findall(r'!\[[^\]]+\]\(../../wiki/assets/([^)]+\.svg)\)', section)
                self.assertEqual(len(refs), 1, chapter.name)
                self.assertNotIn(refs[0], used, f'reused section illustration: {refs[0]}')
                self.assertTrue(refs[0].startswith(('rewrite-memory-a/', 'rewrite-memory-b/')))
                used.add(refs[0])
        self.assertGreater(len(used), 100)

    def test_referenced_figures_are_parseable_and_accessible(self):
        for chapter in CHAPTERS.glob('*.md'):
            refs = re.findall(r'!\[[^\]]+\]\(../../wiki/assets/([^)]+\.svg)\)', chapter.read_text())
            for relative in refs:
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
