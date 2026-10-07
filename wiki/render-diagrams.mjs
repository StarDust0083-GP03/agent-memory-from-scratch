import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {join} from 'node:path';

const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// Static SVG reuses the ebook's offline diagrams; no client-side chart dependency.
export function buildDiagrams(root) {
  const diagrams = JSON.parse(readFileSync(join(root, 'book/diagrams.json'), 'utf8'));
  const out = join(root, 'wiki/assets/diagrams');
  mkdirSync(out, {recursive:true});
  for (const [slug, data] of Object.entries(diagrams)) {
    if (!/^[a-z0-9-]+$/.test(slug)) throw new Error(`Invalid diagram slug: ${slug}`);
    const rows = data.rows || data.bars;
    if (!Array.isArray(rows) || !rows.length) throw new Error(`Missing rows: ${slug}`);
    const bars = Boolean(data.bars);
    const step = bars ? 42 : 100;
    const height = rows.length * step + 55;
    const parts = [`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 ${height}" role="img" aria-labelledby="title desc"><title id="title">${esc(data.title)}</title><desc id="desc">${esc(data.description)}</desc><style>svg{color:#29564c;font-family:system-ui,sans-serif}text{fill:currentColor;font-size:15px}rect,line,path{stroke:currentColor} @media(prefers-color-scheme:dark){svg{color:#87b7a8}}</style>`];
    rows.forEach((row, i) => {
      const y = i * step + 20;
      if (bars) {
        const [label, value] = row;
        if (!Number.isFinite(value) || value < 0 || value > data.maximum) throw new Error(`Invalid bar: ${slug}`);
        const width = value / data.maximum * 355;
        parts.push(`<text x="10" y="${y+20}">${esc(label)}</text><rect x="330" y="${y+5}" width="${width}" height="22" fill="currentColor" stroke="none"/><text x="${695}" y="${y+22}" style="font-variant-numeric:tabular-nums">${value} 天</text>`);
      } else {
        if (row.length !== 4) throw new Error(`Expected lane + three nodes: ${slug}`);
        parts.push(`<text x="12" y="${y+15}" font-weight="600">${esc(row[0])}</text>`);
        row.slice(1).forEach((label, j) => {
          const x = j * 250 + 12;
          parts.push(`<rect x="${x}" y="${y+30}" width="220" height="48" rx="4" fill="none" stroke-opacity=".6"/><text x="${x+110}" y="${y+60}" text-anchor="middle">${esc(label)}</text>`);
          if (j < 2) parts.push(`<path d="M${x+225} ${y+54}h19m-6-5 6 5-6 5" fill="none" stroke-width="1.5"/>`);
        });
      }
    });
    parts.push(`<text x="12" y="${height-5}" style="font-size:12px">${bars ? '维护快照，不是质量排名；同名组合行仅表示相同活跃天数。' : '概念图：箭头表示数据或控制流，不表示所有步骤默认启用。'}</text></svg>`);
    writeFileSync(join(out, `${slug}.svg`), parts.join('\n'));
  }
  return Object.keys(diagrams);
}
