# Agent Memory from Scratch

从写邮件、修 Todo 待办 App 的提醒 bug、选择 npm / pnpm 和找代码评审人这些小事开始，学会保存、检索、纠正和遗忘。每章都有例子、动手检查和答案提示；第 4 章用 SQLite 实现持久记忆，不需要模型密钥。

正文先讲任务和机制，用流程图、关系图、时间轴与曲线解释关键步骤。Mem0 / Graphiti 的逐节例子、源码细节和 16 个项目的对照表保留在选读区，不打断连续阅读。教学示例、源码观察与项目自报实测分别标注。

图示无需在线图表库：

- `book/illustrations/`：9 张概念 SVG，使用窄版布局，适合手机阅读。
- `book/diagrams.json`：章节总览图。
- `book/source-flows.tsv`：逐节项目案例的输入、处理、结果与边界。

构建会复制概念图、生成流程图并更新搜索索引。校验覆盖章节、选读例子、练习、图示、链接和搜索；离线测试另外检查 SVG 元数据、引用与衰减曲线的计算。

## 在线阅读与部署

- 阅读：<https://StarDust0083-GP03.github.io/agent-memory-from-scratch/>
- 仓库：<https://github.com/StarDust0083-GP03/agent-memory-from-scratch>

推送到 `main` 后，GitHub Actions 安装锁定依赖、构建网页、运行校验和离线测试，再将 `wiki/` 部署到 GitHub Pages。首次部署需在仓库 Pages 设置中选择 GitHub Actions。

公开仓库不包含第三方源码克隆、下载的全文资料、虚拟环境与本地缓存；保留来源清单和版本记录。网页源码链接指向上游对应提交，不依赖本地 `sources/repos/`。

## 本地阅读

安装 Node.js 22 和 Python 3 后，先运行 `npm ci --prefix wiki`。

构建后打开 [`wiki/index.html`](wiki/index.html)。书稿源文件在 [`book/chapters`](book/chapters)，配套最小实现位于 [`examples/mini_memory.py`](examples/mini_memory.py)。

```bash
node wiki/build.mjs
python3 wiki/verify.py
python3 -m unittest discover -s wiki -p 'test_*.py' -v
python3 -m http.server 8000 --bind 127.0.0.1
```

浏览器访问 `http://localhost:8000/wiki/`。

## 本地资料

- `sources/repos/`：16 个浅克隆开源项目，随后为维护分析补取了最多约 300 条历史；部分小仓库是完整历史。
- `sources/papers/pdf/`：11 篇论文 PDF。
- `sources/papers/text/`：PDF 的可搜索文本。
- `sources/maintenance.json`：截至 2026-09-21 的本地 Git 活跃度快照。
- `sources/repos.txt`、`sources/papers/papers.tsv`：来源清单。

## 验证最小实现

```bash
cd examples
python3 -m unittest -v
python3 mini_memory.py --db demo.db remember "用户偏好深色模式" --user alice
python3 mini_memory.py --db demo.db recall "深色模式偏好" --user alice
```

## 说明

这是研究与工程学习材料，不是统一 benchmark 排名。不同项目使用的 LoCoMo、LongMemEval 版本、候选范围、检索粒度、reader、LLM judge 和指标经常不同，书中只在协议相同或明确注明限制时比较数字。
