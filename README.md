# Agent Memory from Scratch

一部讲解 Agent 记忆机制的中文电子书。本次沿用原有章与节的次序，正文、案例、练习和图解重新编写。

前半部以大学共享仪器预约为背景，追踪检查要求如何形成记录、进入检索并影响下一次任务；后半部用博物馆借展资料观察不同项目的证据、关系和生命周期。场景均为虚构教学数据，源码事实仍以归档快照为依据。

Mem0 与 Graphiti 的说明用于核对两种记忆组织方式，不声称已运行相应线上服务。每章保留练习、答案提示、折叠实现说明与项目对照表。配套 SQLite 程序不依赖模型服务，可独立检查保存、范围筛选和上下文预算。

新版 SVG 由章节直接引用，位于 `wiki/assets/rewrite-memory-a/` 与 `wiki/assets/rewrite-memory-b/`。每幅图围绕对应案例重新表达，不再在构建中生成旧的六格流程模板。验证器检查练习与答案、折叠结构、图覆盖、可访问描述、唯一锚点、资源路径和搜索记录。

## 在线阅读与部署

- 页面：<https://StarDust0083-GP03.github.io/agent-memory-from-scratch/>
- 代码：<https://github.com/StarDust0083-GP03/agent-memory-from-scratch>

仓库配置的 GitHub Actions 会在推送至 `main` 后构建和校验，再发布 `wiki/`。本次仅修改本地内容，没有执行提交、推送或公开发布。首次使用 Pages 时仍需在仓库设置中选择 GitHub Actions。

第三方仓库和全文研究材料不属于公开阅读产物。上游代码链接固定到相应提交，使阅读页面无需依赖本机的第三方克隆目录。

## 本地阅读

准备 Node.js 22 与 Python 3，然后安装锁定的前端构建依赖：

```bash
npm ci --prefix wiki
node wiki/build.mjs
python3 wiki/verify.py
python3 -m unittest discover -s wiki -p 'test_*.py' -v
python3 -m http.server 8000 --bind 127.0.0.1
```

打开 `http://localhost:8000/wiki/`。章节源稿位于 `book/chapters/`，最小实现位于 `examples/mini_memory.py`，搜索和阅读页面由构建器更新。

## 本地资料

`sources/repos/` 保存项目学习副本；论文 PDF 和搜索文本分别位于 `sources/papers/pdf/`、`sources/papers/text/`。仓库与论文清单可查 `sources/repos.txt`、`sources/papers/papers.tsv`。

`sources/maintenance.json` 记录 2026-09-21 的维护快照。内容重写没有刷新该统计，也不将当时的项目状态作为当前在线状态的保证。

## 验证最小实现

```bash
python3 -m unittest discover -s examples -v
python3 examples/mini_memory.py --db booking.sqlite remember \
  "预约光谱仪前核对校准证书覆盖实验日期" --user optics
python3 examples/mini_memory.py --db booking.sqlite recall \
  "光谱仪校准" --user optics
```

使用练习库，避免把教学命令指向有价值的数据库。命令只操作本地 SQLite，不执行真实预约，也不验证抽取模型的质量。

## 说明

不同项目的评测数据、检索粒度、reader 和 judge 条件未必一致，不能把各自公布的分数直接排成统一榜单。教材比较的是机制与边界；实际接入仍需验证权限、时间语义、删除传播和任务效果。
