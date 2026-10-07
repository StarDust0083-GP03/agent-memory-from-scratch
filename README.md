# Agent Memory from Scratch

一本从保存第一条发布教训，到自己理解、实现和选择 Agent Memory 的中文教程。

跟着 Atlas 发布助手学习：先看具体问题，再跟踪原话、记录、候选与最终输入怎样变化。正文展开机制的判断过程、适用条件和失败反例，术语随例子解释，每章都有动手检查和答案提示。第 4 章包含可复制运行的 SQLite 实验，不需要模型密钥。

正文概念小节以 Mem0 和 Graphiti 为贯穿的标志性实现。前言从零解释两套程序各自负责什么，展示消息、短事实、对象、关系与来源怎样变化；后续逐节以 Atlas 的具体输入和结果讲解，再对照调用入口与应用责任，不要求读者先认识这些项目。重点展开批量提取、语义候选池、评分与 RRF、实体和边解析、双时间过滤、删除残留及失败恢复，附调用形状与计算例子。源码讲解锁定本地 commit，教学代码不冒充两套服务的独立运行结果。

项目讲解覆盖全部 16 个本地仓库（包括历史 Letta）。19 个章节文件保留图示，章末项目对照表收进可展开的速查区；版本、源码、评测与完整技术比较放在实现笔记中。连续阅读时可以跳过这些资料，接入时再查。教学示例、代码观察和项目自报实测分开标注。

图示数据在 `book/diagrams.json`，构建时生成离线 SVG，包括流程、层级/时间对照与维护快照图；无需在线图表库。`wiki/verify.py` 检查练习与答案提示、选读区结构、章节对照表、图示覆盖、SVG 可访问性、链接/图片与搜索索引。

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
