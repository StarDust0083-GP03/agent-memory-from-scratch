"""Exercise the real SVG builder without a model, database, or npm package."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

MODULE = (Path(__file__).parent / 'render-source-flows.mjs').resolve().as_uri()
HEADER = 'chapter\tsection\tmem0_input\tmem0_action\tmem0_result\tgraphiti_input\tgraphiti_action\tgraphiti_result\tboundary\n'
ROW = '99\t1\t输入 <样例> & 原话\t应用核对\t保存正文\t材料 E1\t解析关系\t核对来源\t不能将猜测当作事实\n'


class SourceFlowTest(unittest.TestCase):
    def build(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'book/chapters').mkdir(parents=True)
            (root / 'book/chapters/99-fixture.md').write_text('# Fixture\n\n## 测试案例\n', encoding='utf-8')
            (root / 'book/source-flows.tsv').write_text(HEADER + rows, encoding='utf-8')
            command = f'import {{buildSourceFlows}} from {json.dumps(MODULE)}; buildSourceFlows(process.argv[1]);'
            result = subprocess.run(['node', '--input-type=module', '--eval', command, str(root)], capture_output=True, text=True)
            image = root / 'wiki/assets/source-flows/99-01.svg'
            return result, image.read_text(encoding='utf-8') if image.exists() else None

    def test_actual_svg_preserves_and_escapes_case_text(self):
        result, image = self.build(ROW)
        self.assertEqual(result.returncode, 0, result.stderr)
        svg = ET.fromstring(image)
        desc = svg.find('{http://www.w3.org/2000/svg}desc').text
        self.assertIn('输入 <样例> & 原话', desc)
        self.assertIn('不能将猜测当作事实', desc)
        self.assertEqual(len(svg.findall('{http://www.w3.org/2000/svg}rect')), 6)

    def test_duplicate_case_is_rejected(self):
        result, _ = self.build(ROW + ROW)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Duplicate flow: 99-01', result.stderr)

    def test_missing_case_is_rejected(self):
        result, _ = self.build('')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing source flow: 99:1', result.stderr)


if __name__ == '__main__':
    unittest.main()
