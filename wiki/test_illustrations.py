"""Offline checks for the book's compact teaching illustrations."""
from pathlib import Path
import math
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
NS = {'svg': 'http://www.w3.org/2000/svg'}


class IllustrationTests(unittest.TestCase):
    def test_accessible_offline_assets_are_copied_and_used(self):
        sources = list((ROOT / 'book/illustrations').glob('*.svg'))
        self.assertEqual(len(sources), 9)
        pages = [ROOT / 'wiki/index.html', *sorted((ROOT / 'wiki/chapters').glob('*.html'))]
        html = '\n'.join(page.read_text() for page in pages)
        for source in sources:
            with self.subTest(source=source.name):
                deployed = ROOT / 'wiki/assets/illustrations' / source.name
                self.assertEqual(source.read_bytes(), deployed.read_bytes())
                self.assertIn(f'illustrations/{source.name}', html)
                svg = ET.parse(source).getroot()
                self.assertEqual(svg.attrib['role'], 'img')
                self.assertEqual(svg.attrib['viewBox'].split()[2], '440')
                ids = {node.attrib['id']: node for node in svg.iter() if 'id' in node.attrib}
                self.assertEqual(len(ids), sum('id' in node.attrib for node in svg.iter()))
                for ref in svg.attrib['aria-labelledby'].split():
                    self.assertTrue(ids[ref].text.strip())
                self.assertIsNotNone(svg.find('svg:title', NS))
                self.assertIsNotNone(svg.find('svg:desc', NS))
                self.assertNotIn('<script', source.read_text())
                self.assertNotIn('https://', source.read_text())

    def test_examples_use_everyday_and_development_scenarios(self):
        preface = (ROOT / 'book/chapters/00-preface.md').read_text()
        for example in ('这封邮件用英文', '重复提醒', '别改文件'):
            self.assertIn(example, preface)
        for source in (ROOT / 'book').rglob('*'):
            if source.suffix not in ('.md', '.svg', '.json', '.tsv'):
                continue
            with self.subTest(source=source.name):
                text = source.read_text()
                for obsolete in ('Atlas', 'atlas-release', '发布助手', '迁移检查'):
                    self.assertNotIn(obsolete, text)

    def test_decay_curve_and_markers_match_seven_day_half_life(self):
        svg = ET.parse(ROOT / 'book/illustrations/decay.svg').getroot()
        curve = svg.find('svg:polyline', NS)
        points = [tuple(map(float, point.split(','))) for point in curve.attrib['points'].split()]
        self.assertEqual(len(points), 85)
        for x, y in points:
            day = (x - 56) / 16
            self.assertTrue(math.isclose(y, 244 - 184 * 2 ** (-day / 7), abs_tol=1e-6))
        markers = svg.findall('svg:circle', NS)
        self.assertEqual(len(markers), 4)
        for marker, day in zip(markers, (0, 7, 14, 21)):
            self.assertAlmostEqual(float(marker.attrib['cx']), 56 + day * 16)
            self.assertAlmostEqual(float(marker.attrib['cy']), 244 - 184 * 2 ** (-day / 7))

    def test_repeated_project_examples_stay_optional(self):
        for chapter in (ROOT / 'wiki/chapters').glob('*.html'):
            with self.subTest(chapter=chapter.name):
                html = chapter.read_text()
                self.assertIn('<summary>项目例子与源码（选读）</summary>', html)
                self.assertNotIn('源码对照：</p>', html)
                self.assertNotIn('<details class="source-example" open', html)
                # Opening text and a collapsible note both remain in each chapter.
                self.assertIn('答案提示：', html)


if __name__ == '__main__':
    unittest.main()
