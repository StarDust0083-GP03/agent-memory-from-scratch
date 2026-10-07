import tempfile
import time
import unittest
from pathlib import Path

from mini_memory import MemoryStore


class MemoryStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.tmp.name) / "memory.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_scope_and_recall(self):
        self.store.remember("Alice prefers dark mode", user_id="alice")
        self.store.remember("Bob prefers light mode", user_id="bob")
        hits = self.store.recall("dark mode preference", user_id="alice")
        self.assertEqual([x.text for x in hits], ["Alice prefers dark mode"])

    def test_supersession_preserves_history(self):
        old = self.store.remember("Deployments use Docker", user_id="team")
        new = self.store.remember("Deployments use Kubernetes", user_id="team", supersedes=old)
        current = self.store.recall("deployment runtime", user_id="team")
        self.assertEqual(current[0].id, new)
        row = self.store.db.execute("SELECT valid_to FROM memories WHERE id=?", (old,)).fetchone()
        self.assertIsNotNone(row["valid_to"])

    def test_context_obeys_budget(self):
        for i in range(10):
            self.store.remember(f"API lesson {i}: retry with bounded exponential backoff", importance=0.8)
        context = self.store.context("API retry", budget=40)
        self.assertLessEqual(len(context), 40 * 4 + 40)

    def test_decay_is_dry_run_by_default(self):
        old = time.time() - 365 * 86400
        memory_id = self.store.remember("temporary detail", now=old, importance=0.1, confidence=0.2)
        self.store.db.execute("UPDATE memories SET last_accessed=? WHERE id=?", (old, memory_id))
        self.store.db.commit()
        self.assertIn(memory_id, self.store.forget_decayed(now=time.time()))
        row = self.store.db.execute("SELECT valid_to FROM memories WHERE id=?", (memory_id,)).fetchone()
        self.assertIsNone(row["valid_to"])


if __name__ == "__main__":
    unittest.main()
