#!/usr/bin/env node
import {readFileSync,writeFileSync,mkdirSync,readdirSync,copyFileSync} from 'node:fs';
import {resolve,join,basename} from 'node:path';
import {marked} from 'marked';
import hljs from 'highlight.js';
import {buildDiagrams} from './render-diagrams.mjs';
import {buildSourceFlows} from './render-source-flows.mjs';

const root=resolve(import.meta.dirname,'..');
buildDiagrams(root);
const sourceFlows=buildSourceFlows(root);
const usedSourceFlows=new Set();
const sourceLinks=new Map(JSON.parse(readFileSync(join(root,'sources','maintenance.json'),'utf8')).map(source=>[source.project,source]));
const chapterDir=join(root,'book','chapters');
const out=join(root,'wiki');
const outChapters=join(out,'chapters');
mkdirSync(outChapters,{recursive:true});
const illustrations=join(out,'assets','illustrations');
mkdirSync(illustrations,{recursive:true});
for(const file of readdirSync(join(root,'book','illustrations'))){
  if(file.endsWith('.svg')) copyFileSync(join(root,'book','illustrations',file),join(illustrations,file));
}
const summary=readFileSync(join(root,'book','SUMMARY.md'),'utf8');
const entries=[...summary.matchAll(/^\d+\. \[([^\]]+)\]\(chapters\/([^)]+)\.md\)$/gm)].map((m,i)=>({title:m[1],slug:m[2],index:i+1}));
marked.use({gfm:true,renderer:{
  heading({tokens,depth,text}){const id=String(text).toLowerCase().replace(/[^\p{Letter}\p{Number}]+/gu,'-').replace(/^-|-$/g,'');return `<h${depth} id="${id}">${this.parser.parseInline(tokens)}</h${depth}>`;},
  code({text,lang}){const l=(lang||'').split(/\s/)[0];const html=l&&hljs.getLanguage(l)?hljs.highlight(text,{language:l}).value:hljs.highlightAuto(text,['python','typescript','bash','json','text']).value;return `<pre tabindex="0"><code class="hljs">${html}</code></pre>`;}
}});
const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function layout(title,body,depth='',extra='') {return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Agent Memory from Scratch 中文电子书"><title>${esc(title)} · Agent Memory from Scratch</title><link rel="stylesheet" href="${depth}assets/wiki.css"></head><body><a class="skip" href="#main">跳到正文</a><div class="shell"><header class="topbar"><a class="brand" href="${depth}index.html">Agent Memory</a><span class="spacer"></span><a class="control hide-mobile" href="${depth}search.html">搜索</a><button class="control" data-size="-1" aria-label="减小字号">A−</button><button class="control" data-size="1" aria-label="增大字号">A＋</button></header>${body}</div>${extra}<script src="${depth}assets/wiki.js"></script></body></html>`;}
const groups=[['从一条教训开始',0,5],['让记忆在任务中起作用',5,9],['对照真实实现',9,14],['验证、接入与选择',14,19]];
const chapterRow=e=>`<a class="chapter-row" href="chapters/${e.slug}.html"><span class="num">${e.slug==='00-preface'?'序':e.slug==='appendix-sources'?'附':e.slug.slice(0,2)}</span><span>${esc(e.title)}</span><span class="arrow">→</span></a>`;
const indexBody=`<main id="main" class="book"><h1 class="home-title">Agent Memory<br>from Scratch</h1><p class="deck">写邮件、修提醒 bug、找代码评审人：从这些小事理解记忆怎样保存、找回和纠正。第 4 章用 SQLite 从零实现，不需要模型密钥。</p><p class="reading-start"><a href="chapters/00-preface.html">从前言开始阅读 →</a></p><figure class="lesson-illustration home-illustration"><img src="assets/illustrations/memory-desk.svg" alt="外部存储像柜子，模型只看到应用放到桌上的当前上下文" width="440" height="440"><figcaption>存下来只是第一步。放进本轮输入，模型才读得到。</figcaption></figure><p class="meta">先读正文、图解和动手检查；需要接入项目时，再展开例子与源码。</p><section class="resume" data-resume hidden><div class="meta">上次读到</div><a href="#">继续阅读</a></section><nav class="chapters" aria-label="全书目录">${groups.map(([title,start,end])=>`<section class="book-part"><h2>${title}</h2>${entries.slice(start,end).map(chapterRow).join('')}</section>`).join('')}</nav><p class="source-note">教学例子不等于项目实测。版本与资料来源见<a href="chapters/appendix-sources.html">附录</a>。</p></main>`;
writeFileSync(join(out,'index.html'),layout('目录',indexBody));
const searchDocs=[];
for(const entry of entries){
  const sourceFlowTexts=[];
  let md=readFileSync(join(chapterDir,entry.slug+'.md'),'utf8');
  md=md.replace(/\]\(\.\.\/\.\.\/sources\/repos\/([^/)]+)(?:\/([^)]*))?\)/g,(_,repo,file='')=>{
    const source=sourceLinks.get(repo);
    if(!source) throw new Error(`Missing source reference: ${repo}`);
    const kind=/\.[^/]+$/.test(file)?'blob':'tree';
    return `](${source.remote.replace(/\.git$/,'')}/${kind}/${source.head}${file?'/'+file:''})`;
  });
  md=md.replace('](../../examples/mini_memory.py)','](https://github.com/StarDust0083-GP03/agent-memory-from-scratch/blob/main/examples/mini_memory.py)');
  md=md.replace(/\]\(([^)]+)\.md(#[^)]+)?\)/g,']($1.html$2)');
  md=md.replace(/!\[本例流程\]\(\.\.\/\.\.\/wiki\/assets\/source-flows\/([^/)]+)\.svg\)/g,(_,id)=>{
    const flow=sourceFlows.get(id);
    if(!flow || usedSourceFlows.has(id)) throw new Error(`Unknown or repeated source flow: ${id}`);
    usedSourceFlows.add(id);
    sourceFlowTexts.push(flow.description);
    return `<figure class="source-flow"><img src="../../wiki/assets/source-flows/${id}.svg" alt="${esc(flow.title)}：Mem0 与 Graphiti 的案例流程" loading="lazy"><figcaption>检查点：${esc(flow.boundary)}</figcaption></figure>`;
  });
  md=md.replace(/src="\.\.\/\.\.\/wiki\/assets\//g,'src="../assets/');
  const teaching=md.replace(/<details class="implementation-notes">[\s\S]*?<\/details>/g,'');
  const headings=[...teaching.matchAll(/^##\s+(.+)$/gm)].map(x=>x[1]);
  const html=marked.parse(md);
  const toc=headings.length?`<details class="toc"><summary>本章目录</summary><ol>${headings.map(h=>{const id=h.toLowerCase().replace(/[^\p{Letter}\p{Number}]+/gu,'-').replace(/^-|-$/g,'');return `<li><a href="#${id}">${esc(h)}</a></li>`}).join('')}</ol></details>`:'';
  const prev=entries[entry.index-2],next=entries[entry.index];
  const pager=`<nav class="pager" aria-label="章节导航">${prev?`<a href="${prev.slug}.html"><small>上一章</small>${esc(prev.title)}</a>`:'<span></span>'}${next?`<a href="${next.slug}.html"><small>下一章</small>${esc(next.title)}</a>`:'<a href="../index.html"><small>读完了</small>返回目录</a>'}</nav>`;
  const label=entry.slug==='00-preface'?'前言':entry.slug==='appendix-sources'?'附录':`第 ${parseInt(entry.slug,10)} 章`;
  const body=`<main id="main" class="book" data-chapter="${entry.slug}"><div class="eyebrow">${label}</div>${toc}<article class="content">${html}</article>${pager}</main><div class="toolbar" role="group" aria-label="阅读工具"><a class="control" href="../index.html" aria-label="返回目录">目录</a><button class="control" data-size="-1" aria-label="减小字号">A−</button><button class="control" data-size="1" aria-label="增大字号">A＋</button></div>`;
  writeFileSync(join(outChapters,entry.slug+'.html'),layout(entry.title,body,'../'));
  searchDocs.push({title:entry.title,slug:entry.slug,text:md.replace(/```[\s\S]*?```/g,' ').replace(/<figure[\s\S]*?<\/figure>/g,' ').replace(/<\/?[A-Za-z][^>]*>/g,' ').replace(/[#*`>|\[\]()_-]/g,' ').replace(/\s+/g,' ').trim()+' '+sourceFlowTexts.join(' ')});
}
if(usedSourceFlows.size!==sourceFlows.size) throw new Error('Source flows and chapter references differ');
writeFileSync(join(out,'assets','search-index.json'),JSON.stringify(searchDocs));
const searchBody=`<main id="main" class="search"><div class="eyebrow">全书检索</div><h1 class="chapter-title">搜索</h1><input class="search-input" type="search" autofocus placeholder="输入概念、项目或机制" aria-label="搜索电子书"><div id="results"></div></main>`;
const searchScript=`<script>fetch('assets/search-index.json').then(r=>r.json()).then(d=>{const i=document.querySelector('.search-input'),o=document.querySelector('#results');function run(){const q=i.value.trim().toLowerCase();if(!q){o.innerHTML='<p class="meta">搜索标题与正文。</p>';return}const hits=d.map(x=>({...x,pos:(x.title+' '+x.text).toLowerCase().indexOf(q)})).filter(x=>x.pos>=0).slice(0,30);o.innerHTML=hits.map(x=>{const p=Math.max(0,x.pos-70);return '<article class="result"><a href="chapters/'+x.slug+'.html">'+x.title+'</a><p>'+x.text.slice(p,p+220)+'</p></article>'}).join('')||'<p class="meta">没有结果。</p>'}i.addEventListener('input',run);run()})</script>`;
writeFileSync(join(out,'search.html'),layout('搜索',searchBody,'',searchScript));
console.log(`Built ${entries.length} chapters`);
