# Agent Memory from Scratch

一本从保存第一条发布教训，到自己理解、实现和选择 Agent Memory 的中文教程。

跟着 Atlas 发布助手学习：先看具体问题，再跟踪原话、记录、候选与最终输入怎样变化。正文展开机制的判断过程、适用条件和失败反例，术语随例子解释，每章都有动手检查和答案提示。第 4 章包含可复制运行的 SQLite 实验，不需要模型密钥。

每个正文概念小节都用 Mem0 和 Graphiti 各举一个短例：用户说了什么，保存或查回什么，本次应该怎样处理。默认语言、单次例外、发布教训与批准人变更等例子先讲具体结果，不要求读者先懂函数名。“源码与边界（选读）”先用本节例子画出 Mem0 与 Graphiti 的输入、处理和结果，再给出具体检查点，最后对照 API、字段与计算过程。图中“应用”步骤需要自行实现；原有项目比较继续保留。例子中的记录和关系是教学示意，不是两套服务的实测输出，源码说明锁定本地 commit。

项目讲解覆盖全部 16 个本地仓库（包括历史 Letta）。19 个章节文件保留图示，章末项目对照表收进可展开的速查区；版本、源码、评测与完整技术比较放在实现笔记中。连续阅读时可以跳过这些资料，接入时再查。教学示例、代码观察和项目自报实测分开标注。

章节总览图在 `book/diagrams.json`；逐节案例流程在 `book/source-flows.tsv`，每行分别写两套实现的输入、处理、结果和边界。构建时生成离线 SVG：案例流程按上下两组排列，小屏无需横向读三列；无需在线图表库。`wiki/verify.py` 检查各正文小节是否都有简短的 Mem0 与 Graphiti 例子，以及练习与答案提示、选读区结构、章节对照表、图示覆盖、逐节流程顺序与数据一致性、SVG 可访问性、链接/图片与搜索索引。

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
