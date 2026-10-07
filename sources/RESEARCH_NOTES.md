# Research notes

## Scope

Agent memory systems, with maintenance recency and cadence weighted above stars. Snapshot date: 2026-09-21 UTC.

## Primary source set

- 16 repositories in `repos/`, including the active `letta-code` successor.
- 11 papers in `papers/pdf/`, extracted text in `papers/text/`.
- Git activity in `maintenance.json`.
- Paper abstract/conclusion working extracts in `papers/extracts.md`.

## Candidate matrix

| Family | Projects | Transferable mechanism | Main caveat |
|---|---|---|---|
| Fact/profile | Mem0, Memobase | extraction, profile, event timeline | hosted/OSS gap; Memobase inactive |
| Temporal graph | Graphiti | episode provenance, validity intervals | structured extraction and graph ops cost |
| Graph platform | Cognee | modular ingest, graph/vector/relational stores | high complexity and config surface |
| Associative retrieval | HippoRAG | OpenIE graph + PPR multi-hop retrieval | research framework, not full memory service |
| Agent-managed | Letta Code | core blocks, deferred memory, MemFS, Git | agent self-edit needs policy boundaries |
| Memory OS | MemOS, MemoryOS | hierarchy, scheduler, heterogeneous memory | maturity differs by memory type |
| Lifecycle | Hippo | decay, reinforcement, consolidation, outcomes | single active author in 30-day sample |
| Team assets | TencentDB Agent Memory | ACL, loadout, Chat/Skill/Wiki/CodeGraph | new system; benchmark breadth limited |
| Local files | Basic Memory | Markdown source of truth + MCP | AGPL and explicit-note bias |
| Shared service | MCP Memory Service | MCP/REST/OAuth/backends/operations | broad attack surface; secure configuration required |
| Capture | Agent Beacon | cross-harness trace normalization | capture is not automatically useful memory |
| Decision layer | Hermes Jev Skills | typed rerank/filter/sufficiency | cloud decision API, not a memory store |

## Contradictions and non-comparable claims

1. Mem0's latest README benchmark includes proprietary managed-platform optimization, so it is not an OSS SDK score.
2. Projects report LoCoMo using evidence Recall@k, F1/BLEU, or LLM-judge answer accuracy. These are not interchangeable.
3. LongMemEval per-question haystack retrieval can approach saturation; global-pool retrieval is much harder.
4. Hippo's Jev reranker improves private-set R@1, but graded answer tests did not beat the local cross-encoder.
5. Hippo retracted an earlier sequential-learning magnitude after formal runs did not reproduce it.
6. Cognee's 100K and 10M BEAM results use different data and procedures; its README says to read methodology before comparison.
7. `letta-ai/letta` looks quiet because current development moved to `letta-ai/letta-code`.

## Outline decision

Teach mechanisms before products. The final sequence is: mental model, taxonomy, write path, runnable implementation, retrieval, temporal graphs, lifecycle, agent-native memory, maintenance-weighted landscape, project families, evaluation, production, Jev, selection.

Sections without primary evidence were removed. Project claims are qualified as paper results, README claims, or local source observations.
