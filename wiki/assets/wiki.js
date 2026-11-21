(() => {
  const key = 'agent-memory-book';
  const state = JSON.parse(localStorage.getItem(key) || '{}');
  const save = () => localStorage.setItem(key, JSON.stringify(state));
  const root = document.documentElement;
  const size = Math.min(28, Math.max(17, Number(state.size) || 20));
  root.style.setProperty('--body-size', size + 'px');
  document.querySelectorAll('[data-size]').forEach(button => button.addEventListener('click', () => {
    const next = Math.min(28, Math.max(17, (Number(state.size) || 20) + Number(button.dataset.size)));
    state.size = next; root.style.setProperty('--body-size', next + 'px'); save();
  }));
  const article = document.querySelector('[data-chapter]');
  if (article) {
    const chapter = article.dataset.chapter;
    let timer;
    const remember = () => { state.chapter = chapter; state.y = scrollY / Math.max(1, document.documentElement.scrollHeight - innerHeight); state.title = document.title.replace(' · Agent Memory from Scratch',''); save(); };
    addEventListener('scroll', () => { clearTimeout(timer); timer = setTimeout(remember, 120); }, {passive:true});
    addEventListener('pagehide', remember);
  }
  const resume = document.querySelector('[data-resume]');
  if (resume && state.chapter) {
    resume.hidden = false;
    const link = resume.querySelector('a'); link.href = `chapters/${state.chapter}.html#resume`; link.textContent = `继续阅读：${state.title || state.chapter}`;
  }
  if (location.hash === '#resume' && state.chapter && location.pathname.endsWith('/' + state.chapter + '.html')) {
    requestAnimationFrame(() => scrollTo(0, (state.y || 0) * Math.max(1, document.documentElement.scrollHeight - innerHeight)));
  }
  document.querySelectorAll('table').forEach(table => { const wrap=document.createElement('div'); wrap.className='table-wrap'; wrap.tabIndex=0; table.parentNode.insertBefore(wrap,table); wrap.appendChild(table); });
})();