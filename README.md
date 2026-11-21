# Agent Memory from Scratch

一部用工程师大白话拆透 Agent 长期记忆机制的中文电子书。

全书围绕开发者每天真实面对的**工程研发助手**（负责代码审查、发布检查、故障排查与 on-call 交接）展开，从“为什么聊天记录不等于记忆”讲起，先用 300 行纯 Python + SQLite 亲手跑通持久化、隔离、版本替代与 Token 预算，再顺着写入、混合检索、双时间图谱、遗忘巩固、Agent 自管理、安全隔离、Jev 判别门控与架构选型，把 **16 个主流开源项目与 11 篇核心论文**的源码边界逐一扒清。

本次重编已将 11 个活跃上游仓库（Mem0、Graphiti、Letta Code、Cognee、MemOS、Hippo Memory、MCP Memory Service、Basic Memory、Agent Beacon、Hermes Jev Skills、TencentDB Agent Memory）的提交锚点与机制分析同步至 **2026-11-21** 快照，同时保留其余 5 个静态/归档仓库作为设计思想与迁移对照。

## 在线阅读与部署

- 页面：<https://StarDust0083-GP03.github.io/agent-memory-from-scratch/>
- 代码：<https://github.com/StarDust0083-GP03/agent-memory-from-scratch>

仓库配置的 GitHub Actions 会在推送至 `main` 后自动渲染图解、构建静态阅读页、跑完校验，再发布 `wiki/`。上游源码链接在构建阶段会自动重写为 `sources/maintenance.json` 中对应提交的 GitHub 永久链接，因此离线或线上阅读都不依赖本地克隆的第三方源码。

## 本地阅读与构建

准备 Node.js 22 与 Python 3，然后安装锁定的构建依赖并生成站点：

```bash
npm ci --prefix wiki
node wiki/build.mjs
python3 wiki/verify.py
python3 -m unittest discover -s wiki -p 'test_*.py' -v
python3 -m unittest discover -s examples -v
python3 -m http.server 8000 --bind 127.0.0.1
```

在浏览器打开 `http://localhost:8000/wiki/`。章节源稿位于 `book/chapters/`，图解配置位于 `book/rewrite-diagrams.txt`，零依赖最小实现位于 `examples/mini_memory.py`。

生成静态站后，运行 `python3 wiki/export_book.py` 可重建 `exports/agent-memory-from-scratch.epub` 和 `exports/agent-memory-from-scratch.pdf`（A5）。导出需要 Chromium 和中文字体（推荐 Noto Serif CJK SC）。

## 动手跑通最小实现

无需配置大模型 API Key，也不需要 GPU，直接用 Python 标准库 + SQLite 即可验证跨进程持久记忆、用户隔离、显式替代与上下文预算：

```bash
python3 -m unittest discover -s examples -v
python3 examples/mini_memory.py --db dev-assistant.sqlite remember \
  "支付网关发布前必须核对幂等键 idempotency_key 配置" --user linyuan --kind procedural --source release-14
python3 examples/mini_memory.py --db dev-assistant.sqlite recall \
  "支付网关 幂等键" --user linyuan
```

建议把练习库建在临时目录中，避免误碰业务数据库。

## 资料与事实边界

- `sources/maintenance.json` 记录了 16 个项目的最新锁定提交与维护统计（其中 11 个活跃项目已同步至 2026-11-09 ~ 2026-11-21，5 个静态/研究项目保持原归档快照）。
- 不同开源项目公布的 Benchmark 分数在数据切分、检索粒度、回答模型和裁判模型上往往不统一，本书不拼凑虚假的“大一统榜单”，只比**数据流、控制边界、失败模式和工程代价**。
