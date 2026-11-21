#!/usr/bin/env node
import {readFileSync,writeFileSync,mkdirSync,readdirSync,copyFileSync} from 'node:fs';
import {resolve,join,basename} from 'node:path';
import {marked} from 'marked';
import hljs from 'highlight.js';
import {execFileSync} from 'node:child_process';
const root=resolve(import.meta.dirname,'..');
execFileSync('python3',[join(root,'wiki','render-rewrite-diagrams.py')],{stdio:'inherit'});
const sourceLinks=new Map(JSON.parse(readFileSync(join(root,'sources','maintenance.json'),'utf8')).map(source=>[source.project,source]));
const chapterDir=join(root,'book','chapters');
const out=join(root,'wiki');
const outChapters=join(out,'chapters');
mkdirSync(outChapters,{recursive:true});
const summary=readFileSync(join(root,'book','SUMMARY.md'),'utf8');
const entries=[...summary.matchAll(/^\d+\. \[([^\]]+)\]\(chapters\/([^)]+)\.md\)$/gm)].map((m,i)=>({title:m[1],slug:m[2],index:i+1}));
marked.use({gfm:true,renderer:{
  heading({tokens,depth,text}){const id=String(text).toLowerCase().replace(/[^\p{Letter}\p{Number}]+/gu,'-').replace(/^-|-$/g,'');return `<h${depth} id="${id}">${this.parser.parseInline(tokens)}</h${depth}>`;},
  code({text,lang}){const l=(lang||'').split(/\s/)[0];const html=l&&hljs.getLanguage(l)?hljs.highlight(text,{language:l}).value:hljs.highlightAuto(text,['python','typescript','bash','json','text']).value;return `<pre tabindex="0"><code class="hljs">${html}</code></pre>`;}
}});
const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function layout(title,body,depth='',extra='') {return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Agent Memory from Scratch 中文电子书"><title>${esc(title)} · Agent Memory from Scratch</title><link rel="stylesheet" href="${depth}assets/wiki.css"></head><body><a class="skip" href="#main">跳到正文</a><div class="shell"><header class="topbar"><a class="brand" href="${depth}index.html">Agent Memory</a><span class="spacer"></span><a class="control hide-mobile" href="${depth}search.html">搜索</a><button class="control" data-size="-1" aria-label="减小字号">A−</button><button class="control" data-size="1" aria-label="增大字号">A＋</button></header>${body}</div>${extra}<script src="${depth}assets/wiki.js"></script></body></html>`;}
const indexBody=`<main id="main" class="book"><div class="eyebrow">从原理到能跑通的代码</div><h1 class="home-title">Agent Memory<br>from Scratch</h1><p class="deck">以一个每天帮你做代码审查、发布检查、故障排查和 on-call 交接的工程研发助手为主线，拆透 Agent 记忆怎么写、怎么搜、怎么随时间演化、怎么防注入与隔离权限。先讲清大白话原理，再扒开 16 个开源项目源码逐一核验边界。</p><p class="meta">17 章教程 + 前言与附录 · 16 个开源仓库 · 11 篇核心论文 · 同步 2026-11-21 上游快照</p><section class="resume" data-resume hidden><div class="meta">上次读到</div><a href="#">继续阅读</a></section><nav class="chapters" aria-label="全书目录">${entries.map(e=>`<a class="chapter-row" href="chapters/${e.slug}.html"><span class="num">${e.slug==='00-preface'?'序':e.slug==='appendix-sources'?'附':e.slug.slice(0,2)}</span><span>${esc(e.title)}</span><span class="arrow">→</span></a>`).join('')}</nav><p class="source-note">2026-11 重编版：全书采用研发工程真实场景与大白话重写，并同步 Mem0、Graphiti、Letta Code、Cognee、MemOS、MCP Memory Service 等 11 个活跃仓库截至 2026-11-21 的最新提交。</p></main>`;
writeFileSync(join(out,'index.html'),layout('目录',indexBody));
const searchDocs=[];
for(const entry of entries){
  let md=readFileSync(join(chapterDir,entry.slug+'.md'),'utf8');
  md=md.replace(/\]\(\.\.\/\.\.\/sources\/repos\/([^/)]+)(?:\/([^)]*))?\)/g,(_,repo,file='')=>{
    const source=sourceLinks.get(repo);
    if(!source) throw new Error(`Missing source reference: ${repo}`);
    const kind=/\.[^/]+$/.test(file)?'blob':'tree';
    return `](${source.remote.replace(/\.git$/,'')}/${kind}/${source.head}${file?'/'+file:''})`;
  });
  md=md.replaceAll('](../../examples/mini_memory.py)','](https://github.com/StarDust0083-GP03/agent-memory-from-scratch/blob/main/examples/mini_memory.py)');
  md=md.replace(/\]\(((?!https?:\/\/)[^)]+)\.md(#[^)]+)?\)/g,']($1.html$2)');
  // Chapter-authored SVGs replace the former shared diagram templates.
  for (const match of md.matchAll(/!\[[^\]]*\]\(\.\.\/\.\.\/wiki\/assets\/([^)]+)\)/g)) {
    if (!readFileSync(join(out,'assets',match[1]),'utf8').includes('<svg'))
      throw new Error(`Invalid chapter illustration: ${match[1]}`);
  }
  const teaching=md.replace(/<details class="implementation-notes">[\s\S]*?<\/details>/g,'');
  const headings=[...teaching.replace(/^```[\s\S]*?^```/gm,'').matchAll(/^##\s+(.+)$/gm)].map(x=>x[1]);
  const html=marked.parse(md).replace(/src="\.\.\/\.\.\/wiki\/assets\//g,'src="../assets/');
  const toc=headings.length?`<details class="toc"><summary>本章目录</summary><ol>${headings.map(h=>{const id=h.toLowerCase().replace(/[^\p{Letter}\p{Number}]+/gu,'-').replace(/^-|-$/g,'');return `<li><a href="#${id}">${esc(h)}</a></li>`}).join('')}</ol></details>`:'';
  const prev=entries[entry.index-2],next=entries[entry.index];
  const pager=`<nav class="pager" aria-label="章节导航">${prev?`<a href="${prev.slug}.html"><small>上一章</small>${esc(prev.title)}</a>`:'<span></span>'}${next?`<a href="${next.slug}.html"><small>下一章</small>${esc(next.title)}</a>`:'<a href="../index.html"><small>读完了</small>返回目录</a>'}</nav>`;
  const label=entry.slug==='00-preface'?'前言':entry.slug==='appendix-sources'?'附录':`第 ${parseInt(entry.slug,10)} 章`;
  const body=`<main id="main" class="book" data-chapter="${entry.slug}"><div class="eyebrow">${label}</div>${toc}<article class="content">${html}</article>${pager}</main><div class="toolbar" role="group" aria-label="阅读工具"><a class="control" href="../index.html" aria-label="返回目录">目录</a><button class="control" data-size="-1" aria-label="减小字号">A−</button><button class="control" data-size="1" aria-label="增大字号">A＋</button></div>`;
  writeFileSync(join(outChapters,entry.slug+'.html'),layout(entry.title,body,'../'));
  searchDocs.push({title:entry.title,slug:entry.slug,text:md.replace(/```[\s\S]*?```/g,' ').replace(/<figure[\s\S]*?<\/figure>/g,' ').replace(/<\/?[A-Za-z][^>]*>/g,' ').replace(/[#*`>|\[\]()_-]/g,' ').replace(/\s+/g,' ').trim()});
}
writeFileSync(join(out,'assets','search-index.json'),JSON.stringify(searchDocs));
writeFileSync(join(out,'assets','search-index.js'),`window.BOOK_SEARCH=${JSON.stringify(searchDocs)};\n`);
const searchBody=`<main id="main" class="search"><div class="eyebrow">全书搜索</div><h1 class="chapter-title">搜索</h1><input class="search-input" type="search" autofocus placeholder="Mem0 / Graphiti / 遗忘" aria-label="搜索电子书"><p class="search-hint" id="search-status" aria-live="polite">输入概念、项目或机制，例如 Mem0、Graphiti、遗忘。</p><div id="results"></div></main>`;
const searchScript=`<script src="assets/search-index.js"></script><script>(()=>{const d=window.BOOK_SEARCH||[];const i=document.querySelector('.search-input'),o=document.querySelector('#results'),s=document.querySelector('#search-status');function run(){const q=i.value.trim().toLowerCase();o.replaceChildren();if(!q){s.textContent='输入概念、项目或机制，例如 Mem0、Graphiti、遗忘。';return}const hits=d.map(x=>({...x,pos:(x.title+' '+x.text).toLowerCase().indexOf(q)})).filter(x=>x.pos>=0).slice(0,30);s.textContent=hits.length?'找到 '+hits.length+' 章':'没有匹配结果，换个更短的说法，或清空后浏览目录。';for(const x of hits){const row=document.createElement('article');row.className='result';const a=document.createElement('a');a.href='chapters/'+x.slug+'.html';a.textContent=x.title;const p=document.createElement('p');const st=Math.max(0,x.pos-70);p.textContent=x.text.slice(st,st+220).replace(/^[，。；：、,.;:!?！？\\s]+/,'');row.append(a,p);o.append(row)}}i.addEventListener('input',run);run()})()</script>`;
writeFileSync(join(out,'search.html'),layout('搜索',searchBody,'',searchScript));
console.log(`Built ${entries.length} chapters`);
