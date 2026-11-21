#!/usr/bin/env python3
"""用 SQLite 演示发布助手的持久记忆，只依赖 Python 标准库。

从仓库根目录执行：
    python3 examples/mini_memory.py --db dev-assistant.sqlite remember "支付网关发布前核对幂等键" --user linyuan --source release-14
    python3 examples/mini_memory.py --db dev-assistant.sqlite recall "支付网关 幂等键" --user linyuan
    python3 examples/mini_memory.py --db dev-assistant.sqlite context "支付网关 幂等键" --user linyuan --budget 60
    python3 examples/mini_memory.py --db dev-assistant.sqlite forget-decayed --user linyuan

首条命令保存正文并打印随机 ID；换进程查询仍能读到同一 ID 和来源。
换成未写入的用户应得到空列表。遗忘默认只列候选，--apply 才结束有效期。
这些命令只操作本地 SQLite，不访问实际发布系统。user_id 由调用者提供，不代表认证。
semantic 字段沿用接口名称，计算的是哈希词袋余弦，未使用语义模型。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def terms(text: str) -> list[str]:
    """英文按词取项，含汉字的片段取单字与相邻双字，不做专业分词。"""
    result: list[str] = []
    for part in TOKEN_RE.findall(text.lower()):
        if not re.search(r"[\u4e00-\u9fff]", part):
            result.append(part)
            continue
        result.extend(part)
        result.extend(a + b for a, b in zip(part, part[1:]))
    return result


def hashed_vector(text: str, dimensions: int = 256) -> dict[int, float]:
    """确定性地装桶并归一化；不同词落在同一桶时无法再区分。"""
    if dimensions <= 0:
        raise ValueError("哈希桶数量必须大于零")
    counts: dict[int, float] = {}
    for word in terms(text):
        bucket = int.from_bytes(
            hashlib.blake2b(word.encode("utf-8"), digest_size=8).digest(), "big"
        ) % dimensions
        counts[bucket] = counts.get(bucket, 0.0) + 1.0
    length = math.sqrt(sum(count ** 2 for count in counts.values()))
    return {bucket: count / length for bucket, count in counts.items()}


def cosine(left: dict[int, float], right: dict[int, float]) -> float:
    """输入已归一化时，稀疏点积就是余弦相似度。"""
    return sum(left.get(bucket, 0.0) * count for bucket, count in right.items())


def _timestamp(value: float | None) -> float:
    stamp = time.time() if value is None else float(value)
    if not math.isfinite(stamp):
        raise ValueError("时间戳必须是有限数值")
    return stamp


def _unit(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("权重必须是有限数值")
    return min(1.0, max(0.0, value))


@dataclass
class Hit:
    id: str
    text: str
    kind: str
    score: float
    lexical: float
    semantic: float
    recency: float
    importance: float
    confidence: float
    source: str | None


class MemoryStore:
    """一行保存一条观察，使用左闭右开的有效区间，不自动判定冲突。

    调用宿主须验证身份后再传 user_id。安全检查正文只是证据，不能授权开机。
    """

    def __init__(self, path: str | Path = "memory.db") -> None:
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                text TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'episodic',
                importance REAL NOT NULL DEFAULT 0.5,
                confidence REAL NOT NULL DEFAULT 0.7,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                valid_from REAL NOT NULL,
                valid_to REAL,
                supersedes TEXT,
                source TEXT,
                FOREIGN KEY (supersedes) REFERENCES memories (id)
            );
            CREATE INDEX IF NOT EXISTS idx_memory_scope
                ON memories (user_id, valid_to, created_at);
        """)
        self.db.commit()

    def remember(
        self,
        text: str,
        *,
        user_id: str = "default",
        kind: str = "episodic",
        importance: float = 0.5,
        confidence: float = 0.7,
        source: str | None = None,
        supersedes: str | None = None,
        now: float | None = None,
    ) -> str:
        """写入人工提供的事实；明确替代时，旧行结束与新行插入同成同败。"""
        body = text.strip()
        if not body or not user_id.strip():
            raise ValueError("正文和用户范围都不能为空")
        stamp = _timestamp(now)
        weight, certainty = _unit(importance), _unit(confidence)
        identifier = uuid.uuid4().hex[:12]
        with self.db:
            if supersedes is not None:
                changed = self.db.execute(
                    """UPDATE memories SET valid_to = ?
                       WHERE id = ? AND user_id = ?
                         AND valid_to IS NULL AND valid_from <= ?""",
                    (stamp, supersedes, user_id, stamp),
                ).rowcount
                if changed != 1:
                    raise ValueError("替代目标须为同一用户在该时刻有效的当前记录")
            self.db.execute(
                """INSERT INTO memories (
                       id, user_id, text, kind, importance, confidence,
                       created_at, last_accessed, valid_from, supersedes, source
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (identifier, user_id, body, kind, weight, certainty,
                 stamp, stamp, stamp, supersedes, source),
            )
        return identifier

    @staticmethod
    def _rank(row: sqlite3.Row, vocabulary: set[str], vector: dict[int, float], now: float) -> Hit:
        document = set(terms(row["text"]))
        lexical = len(document & vocabulary) / max(1.0, math.sqrt(len(document) * len(vocabulary)))
        semantic = cosine(vector, hashed_vector(row["text"]))
        recency = math.exp(-max(0.0, now - row["created_at"]) / (30 * 86400))
        frequency = min(1.0, math.log2(row["access_count"] + 2) / 4)
        score = sum((
            0.42 * lexical, 0.28 * semantic, 0.10 * recency,
            0.10 * row["importance"], 0.07 * row["confidence"], 0.03 * frequency,
        ))
        return Hit(
            row["id"], row["text"], row["kind"], score,
            round(lexical, 4), round(semantic, 4), round(recency, 4),
            row["importance"], row["confidence"], row["source"],
        )

    def recall(
        self,
        query: str,
        *,
        user_id: str = "default",
        limit: int = 5,
        as_of: float | None = None,
        reinforce: bool = True,
    ) -> list[Hit]:
        """先限定用户和有效时间，再排序。历史查询的热度仍按当前时钟计算。"""
        if limit < 0:
            raise ValueError("返回条数不能为负数")
        clock = _timestamp(None)
        point = clock if as_of is None else _timestamp(as_of)
        rows = self.db.execute(
            """SELECT * FROM memories WHERE user_id = ? AND valid_from <= ?
                 AND (valid_to IS NULL OR ? < valid_to)
               ORDER BY created_at, id""",
            (user_id, point, point),
        ).fetchall()
        vocabulary, vector = set(terms(query)), hashed_vector(query)
        # ponytail: 用户内全量评分仅适合小库，数据增大后换受限检索索引。
        ranked = [self._rank(row, vocabulary, vector, clock) for row in rows]
        ranked.sort(key=lambda hit: hit.score, reverse=True)
        hits = [hit for hit in ranked[:limit] if hit.score > 0.05]
        for hit in hits:
            hit.score = round(hit.score, 4)
        if hits and reinforce:
            with self.db:
                self.db.executemany(
                    """UPDATE memories SET access_count = access_count + 1,
                           last_accessed = ? WHERE id = ? AND user_id = ?""",
                    ((clock, hit.id, user_id) for hit in hits),
                )
        return hits

    def context(self, query: str, *, user_id: str = "default", budget: int = 800) -> str:
        """每单位预算近似四个字符，仅约束正文行，不含标题与行间换行。"""
        if budget < 0:
            raise ValueError("上下文预算不能为负数")
        capacity = budget * 4
        packed: list[str] = []
        for candidate in self.recall(query, user_id=user_id, limit=20):
            entry = f"- [{candidate.kind}; confidence={candidate.confidence:.2f}] {candidate.text}"
            if len(entry) <= capacity:
                packed.append(entry)
                capacity -= len(entry)
        # 召回已强化候选，即使长项未装入。这里没有任务成功反馈。
        return "# 实验室记忆\n" + ("\n".join(packed) if packed else "- 未找到可装入的记录。")

    def forget_decayed(
        self,
        *,
        user_id: str = "default",
        half_life_days: float = 30,
        threshold: float = 0.12,
        dry_run: bool = True,
        now: float | None = None,
    ) -> list[str]:
        """低强度记录退出当前视图，正文仍留在数据库，不能代替隐私删除。"""
        if not math.isfinite(half_life_days) or half_life_days <= 0:
            raise ValueError("半衰期必须是大于零的有限天数")
        if not math.isfinite(threshold):
            raise ValueError("遗忘阈值必须是有限数值")
        stamp = _timestamp(now)
        rows = self.db.execute(
            """SELECT id, importance, confidence, last_accessed FROM memories
               WHERE user_id = ? AND valid_to IS NULL AND valid_from <= ?
               ORDER BY created_at, id""",
            (user_id, stamp),
        ).fetchall()
        expired: list[str] = []
        for record in rows:
            idle_days = max(0.0, stamp - record["last_accessed"]) / 86400
            strength = record["importance"] * record["confidence"] * math.pow(
                0.5, idle_days / half_life_days
            )
            if strength < threshold:
                expired.append(record["id"])
        if expired and not dry_run:
            with self.db:
                self.db.executemany(
                    "UPDATE memories SET valid_to = ? WHERE id = ? AND user_id = ?",
                    ((stamp, identifier, user_id) for identifier in expired),
                )
        return expired

    def close(self) -> None:
        self.db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="memory.db", help="本地 SQLite 文件路径")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("remember", help="保存发布约束、故障观察或交接事项")
    add.add_argument("text", help="已经核验、适合保存的正文")
    add.add_argument("--kind", default="episodic")
    add.add_argument("--importance", type=float, default=0.5)
    add.add_argument("--confidence", type=float, default=0.7)
    add.add_argument("--source")
    add.add_argument("--supersedes")
    search = commands.add_parser("recall", help="以 JSON 返回有效记录及评分分项")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    context = commands.add_parser("context", help="将检索结果装入近似字符预算")
    context.add_argument("query")
    context.add_argument("--budget", type=int, default=800)
    decay = commands.add_parser("forget-decayed", help="预览低强度记录，不会物理删除")
    decay.add_argument("--apply", action="store_true", help="将候选有效期结束于当前时间")
    for command in (add, search, context, decay):
        command.add_argument("--user", default="default", help="由可信宿主确定的用户范围")
    options = vars(parser.parse_args())
    database = options.pop("db")
    operation = options.pop("command")
    options["user_id"] = options.pop("user")
    store = MemoryStore(database)
    try:
        if operation == "remember":
            output = store.remember(**options)
        elif operation == "context":
            output = store.context(**options)
        elif operation == "recall":
            output = json.dumps([asdict(hit) for hit in store.recall(**options)], ensure_ascii=False, indent=2)
        else:
            options["dry_run"] = not options.pop("apply")
            output = json.dumps(store.forget_decayed(**options))
        print(output)
    except ValueError as error:
        parser.error(str(error))
    finally:
        store.close()


if __name__ == "__main__":
    main()
