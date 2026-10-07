#!/usr/bin/env python3
"""A dependency-free agent memory reference implementation.

It demonstrates the mechanisms discussed in the book, not production readiness:
SQLite persistence, lexical + hashed-semantic retrieval, temporal validity,
reinforcement on recall, decay, supersession, and token-budgeted context.
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
    words: list[str] = []
    for token in TOKEN_RE.findall(text.lower()):
        # English is word-based; Chinese falls back to overlapping characters/bigrams.
        if re.search(r"[\u4e00-\u9fff]", token):
            chars = list(token)
            words.extend(chars)
            words.extend("".join(chars[i : i + 2]) for i in range(len(chars) - 1))
        else:
            words.append(token)
    return words


def hashed_vector(text: str, dimensions: int = 256) -> dict[int, float]:
    vector: dict[int, float] = {}
    for token in terms(text):
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        index = int.from_bytes(digest, "big") % dimensions
        vector[index] = vector.get(index, 0.0) + 1.0
    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {key: value / norm for key, value in vector.items()}


def cosine(left: dict[int, float], right: dict[int, float]) -> float:
    return sum(value * right.get(key, 0.0) for key, value in left.items())


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
    def __init__(self, path: str | Path = "memory.db") -> None:
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
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
              FOREIGN KEY(supersedes) REFERENCES memories(id)
            );
            CREATE INDEX IF NOT EXISTS idx_memory_scope
              ON memories(user_id, valid_to, created_at);
            """
        )
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
        now = now or time.time()
        memory_id = uuid.uuid4().hex[:12]
        if supersedes:
            self.db.execute(
                "UPDATE memories SET valid_to=? WHERE id=? AND user_id=? AND valid_to IS NULL",
                (now, supersedes, user_id),
            )
        self.db.execute(
            """INSERT INTO memories
               (id,user_id,text,kind,importance,confidence,created_at,last_accessed,
                valid_from,valid_to,supersedes,source)
               VALUES (?,?,?,?,?,?,?,?,?,NULL,?,?)""",
            (
                memory_id,
                user_id,
                text.strip(),
                kind,
                max(0.0, min(1.0, importance)),
                max(0.0, min(1.0, confidence)),
                now,
                now,
                now,
                supersedes,
                source,
            ),
        )
        self.db.commit()
        return memory_id

    def recall(
        self,
        query: str,
        *,
        user_id: str = "default",
        limit: int = 5,
        as_of: float | None = None,
        reinforce: bool = True,
    ) -> list[Hit]:
        now = time.time()
        as_of = as_of or now
        rows = self.db.execute(
            """SELECT * FROM memories
               WHERE user_id=? AND valid_from<=?
                 AND (valid_to IS NULL OR valid_to>?)""",
            (user_id, as_of, as_of),
        ).fetchall()
        query_terms = set(terms(query))
        query_vector = hashed_vector(query)
        scored: list[tuple[float, sqlite3.Row, tuple[float, ...]]] = []
        for row in rows:
            doc_terms = terms(row["text"])
            overlap = len(query_terms.intersection(doc_terms))
            lexical = overlap / max(1.0, math.sqrt(len(query_terms) * len(set(doc_terms))))
            semantic = cosine(query_vector, hashed_vector(row["text"]))
            age_days = max(0.0, (now - row["created_at"]) / 86400)
            recency = math.exp(-age_days / 30.0)
            reinforcement = min(1.0, math.log2(row["access_count"] + 2) / 4)
            score = (
                0.42 * lexical
                + 0.28 * semantic
                + 0.10 * recency
                + 0.10 * row["importance"]
                + 0.07 * row["confidence"]
                + 0.03 * reinforcement
            )
            scored.append((score, row, (lexical, semantic, recency)))
        scored.sort(key=lambda item: item[0], reverse=True)
        hits = [
            Hit(
                id=row["id"],
                text=row["text"],
                kind=row["kind"],
                score=round(score, 4),
                lexical=round(parts[0], 4),
                semantic=round(parts[1], 4),
                recency=round(parts[2], 4),
                importance=row["importance"],
                confidence=row["confidence"],
                source=row["source"],
            )
            for score, row, parts in scored[:limit]
            if score > 0.05
        ]
        if reinforce and hits:
            self.db.executemany(
                "UPDATE memories SET access_count=access_count+1,last_accessed=? WHERE id=?",
                [(now, hit.id) for hit in hits],
            )
            self.db.commit()
        return hits

    def context(self, query: str, *, user_id: str = "default", budget: int = 800) -> str:
        """Return observed facts within an approximate token budget."""
        remaining = budget * 4  # deliberately conservative token approximation
        lines: list[str] = []
        for hit in self.recall(query, user_id=user_id, limit=20):
            line = f"- [{hit.kind}; confidence={hit.confidence:.2f}] {hit.text}"
            if len(line) > remaining:
                continue
            lines.append(line)
            remaining -= len(line)
        return "# Relevant memory\n" + ("\n".join(lines) or "- No relevant memory found.")

    def forget_decayed(
        self,
        *,
        user_id: str = "default",
        half_life_days: float = 30,
        threshold: float = 0.12,
        dry_run: bool = True,
        now: float | None = None,
    ) -> list[str]:
        now = now or time.time()
        rows = self.db.execute(
            "SELECT * FROM memories WHERE user_id=? AND valid_to IS NULL", (user_id,)
        ).fetchall()
        forgotten: list[str] = []
        for row in rows:
            age = max(0.0, (now - row["last_accessed"]) / 86400)
            strength = row["importance"] * row["confidence"] * (0.5 ** (age / half_life_days))
            if strength < threshold:
                forgotten.append(row["id"])
        if forgotten and not dry_run:
            self.db.executemany("UPDATE memories SET valid_to=? WHERE id=?", [(now, x) for x in forgotten])
            self.db.commit()
        return forgotten

    def close(self) -> None:
        self.db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="memory.db")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("remember")
    add.add_argument("text")
    add.add_argument("--user", default="default")
    add.add_argument("--kind", default="episodic")
    add.add_argument("--importance", type=float, default=0.5)
    add.add_argument("--confidence", type=float, default=0.7)
    add.add_argument("--source")
    add.add_argument("--supersedes")
    search = sub.add_parser("recall")
    search.add_argument("query")
    search.add_argument("--user", default="default")
    search.add_argument("--limit", type=int, default=5)
    ctx = sub.add_parser("context")
    ctx.add_argument("query")
    ctx.add_argument("--user", default="default")
    ctx.add_argument("--budget", type=int, default=800)
    forget = sub.add_parser("forget-decayed")
    forget.add_argument("--user", default="default")
    forget.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    store = MemoryStore(args.db)
    try:
        if args.command == "remember":
            print(store.remember(args.text, user_id=args.user, kind=args.kind,
                                 importance=args.importance, confidence=args.confidence,
                                 source=args.source, supersedes=args.supersedes))
        elif args.command == "recall":
            print(json.dumps([asdict(x) for x in store.recall(args.query, user_id=args.user, limit=args.limit)], ensure_ascii=False, indent=2))
        elif args.command == "context":
            print(store.context(args.query, user_id=args.user, budget=args.budget))
        else:
            print(json.dumps(store.forget_decayed(user_id=args.user, dry_run=not args.apply)))
    finally:
        store.close()


if __name__ == "__main__":
    main()
