import {readFileSync, readdirSync, mkdirSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';

const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const wrap = text => {
  const lines = []; let line = '', width = 0;
  for (const char of text) {
    const size = /[\u0000-\u007f]/.test(char) ? 1 : 2;
    if (width + size > 36) { lines.push(line); line = ''; width = 0; }
    line += char; width += size;
  }
  if (line) lines.push(line);
  return lines;
};

// Author the concrete input, intermediate state, result, and failure check in TSV.
// Render static diagrams using only Node's standard library; the book stays offline.
export function buildSourceFlows(root) {
  const dir = join(root, 'book/chapters');
  const files = readdirSync(dir).filter(f => f.endsWith('.md'));
  const titles = new Map(files.map(file => {
    const teaching = readFileSync(join(dir, file), 'utf8').split('<details class="implementation-notes">')[0];
    const headings = [...teaching.matchAll(/^## (.+)$/gm)].map(m => m[1]).filter(t => t !== '动手检查');
    return [file.startsWith('appendix-') ? 'appendix' : file.slice(0, 2), headings];
  }));
  const out = join(root, 'wiki/assets/source-flows');
  mkdirSync(out, {recursive: true});
  const rows = readFileSync(join(root, 'book/source-flows.tsv'), 'utf8').trim().split('\n').slice(1);
  const flows = new Map();
  for (const row of rows) {
    const cells = row.split('\t');
    if (cells.length !== 9 || cells.some(c => !c.trim())) throw new Error('Expected nine nonempty flow fields');
    const [chapter, number, ...fields] = cells;
    if (!/^(\d{2}|appendix)$/.test(chapter) || !/^[1-9]\d*$/.test(number)) throw new Error('Invalid flow key');
    const title = titles.get(chapter)?.[Number(number) - 1];
    if (!title) throw new Error(`Unknown source section: ${chapter}:${number}`);
    const id = `${chapter}-${number.padStart(2, '0')}`;
    if (flows.has(id)) throw new Error(`Duplicate flow: ${id}`);
    const lanes = [['Mem0', fields.slice(0, 3)], ['Graphiti', fields.slice(3, 6)]];
    const boundary = fields[6];
    const description = lanes.map(([name, steps]) => `${name}：${steps.join(' → ')}`).join('；') + `。检查点：${boundary}`;
    const body = []; let y = 26;
    for (const [name, steps] of lanes) {
      body.push(`<text x="12" y="${y}" font-weight="600">${esc(name)}</text>`); y += 16;
      steps.forEach((text, i) => {
        const lines = wrap(`${i + 1}. ${text}`), height = Math.max(60, lines.length * 22 + 24);
        body.push(`<rect x="12" y="${y}" width="336" height="${height}" rx="4" fill="none" stroke="currentColor"/>`);
        lines.forEach((line, j) => body.push(`<text x="28" y="${y + 25 + j * 22}">${esc(line)}</text>`));
        y += height;
        if (i < 2) body.push(`<path d="M180 ${y + 3}v16m-5-5 5 5 5-5" fill="none" stroke="currentColor"/>`);
        y += 25;
      });
      y += 12;
    }
    body.push(`<text x="12" y="${y}" font-size="13">教学推演；“应用”步骤需自行实现。</text>`);
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 ${y + 18}" role="img" aria-labelledby="title desc"><title id="title">${esc(title)}：两条案例流程</title><desc id="desc">${esc(description)}</desc><style>svg{color:#29564c;font-family:system-ui,sans-serif}text{fill:currentColor;font-size:16px}rect{stroke-opacity:.6}@media(prefers-color-scheme:dark){svg{color:#87b7a8}}</style>${body.join('\n')}</svg>`;
    writeFileSync(join(out, `${id}.svg`), svg);
    flows.set(id, {title, boundary, description});
  }
  for (const [chapter, headings] of titles) {
    for (let i = 1; i <= headings.length; i++) {
      if (!flows.has(`${chapter}-${String(i).padStart(2, '0')}`)) throw new Error(`Missing source flow: ${chapter}:${i}`);
    }
  }
  return flows;
}
