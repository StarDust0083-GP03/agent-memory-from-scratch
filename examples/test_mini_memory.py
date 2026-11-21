"""本地教学回放：仪器预约、校准交接与安全检查，不访问外部服务。"""
import json
import math
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from dataclasses import asdict, fields
from pathlib import Path
from unittest.mock import patch

from mini_memory import Hit, MemoryStore, cosine, hashed_vector, terms

DAY = 86400
CLOCK = 1_800_000_000.0
SCRIPT = Path(__file__).with_name("mini_memory.py").resolve()


class MemoryStoreTest(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.database = Path(self.workspace.name) / "instrument.sqlite"
        self.store = MemoryStore(self.database)
        self.clock = patch("mini_memory.time.time", return_value=CLOCK)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.workspace.cleanup)
        self.addCleanup(self.store.close)

    def row(self, identifier):
        return self.store.db.execute(
            "SELECT * FROM memories WHERE id = ?", (identifier,)
        ).fetchone()

    def test_scope_and_recall(self):
        allowed = self.store.remember(
            "光谱仪预约须核对激光培训证", user_id="optics", source="safety-19"
        )
        blocked = self.store.remember(
            "光谱仪预约须核对激光培训证，另有未公开样品编号", user_id="chemistry"
        )
        with patch("mini_memory.hashed_vector", wraps=hashed_vector) as vectorize:
            hits = self.store.recall("光谱仪 预约 培训证", user_id="optics")
        self.assertEqual([hit.id for hit in hits], [allowed])
        self.assertEqual(hits[0].source, "safety-19")
        self.assertNotIn(self.row(blocked)["text"], [call.args[0] for call in vectorize.call_args_list])
        self.assertEqual(self.row(blocked)["access_count"], 0)
        self.assertEqual(self.store.recall("光谱仪", user_id="visitors"), [])

    def test_insert_defaults_and_explicit_metadata(self):
        identifier = self.store.remember("  天平预约结束后清理称量纸 \n")
        self.assertRegex(identifier, r"^[0-9a-f]{12}$")
        row = self.row(identifier)
        self.assertEqual(row["text"], "天平预约结束后清理称量纸")
        self.assertEqual((row["user_id"], row["kind"]), ("default", "episodic"))
        self.assertEqual((row["importance"], row["confidence"]), (0.5, 0.7))
        self.assertEqual((row["valid_from"], row["last_accessed"]), (CLOCK, CLOCK))
        self.assertEqual(row["access_count"], 0)
        self.assertIsNone(row["valid_to"])
        custom = self.store.remember(
            "校准证书复核通过", kind="procedural", importance=3, confidence=-2, source="cert-42"
        )
        self.assertEqual((self.row(custom)["importance"], self.row(custom)["confidence"]), (1, 0))
        hit = self.store.recall("校准证书", reinforce=False)[0]
        self.assertEqual(hit.kind, "procedural")
        self.assertEqual(hit.source, "cert-42")

    def test_persistence_uses_same_schema_on_a_new_connection(self):
        identifier = self.store.remember("低温箱预约上限为两小时", user_id="cold-room")
        reopened = MemoryStore(self.database)
        try:
            hit = reopened.recall("低温箱预约", user_id="cold-room", reinforce=False)[0]
            self.assertEqual(hit.id, identifier)
            self.assertEqual(reopened.db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(self.row(identifier)["access_count"], 0)
        finally:
            reopened.close()

    def test_supersession_preserves_history(self):
        old = self.store.remember(
            "光谱仪校准周期为十四天", user_id="optics", now=CLOCK - 2 * DAY
        )
        new = self.store.remember(
            "光谱仪校准周期改为七天", user_id="optics", now=CLOCK - DAY, supersedes=old
        )
        for point, expected in ((CLOCK - 3 * DAY, []), (CLOCK - 2 * DAY, [old]),
                                (CLOCK - DAY - 0.001, [old]), (CLOCK - DAY, [new]), (CLOCK, [new])):
            with self.subTest(point=point):
                hits = self.store.recall("光谱仪 校准周期", user_id="optics", as_of=point, reinforce=False)
                self.assertEqual([hit.id for hit in hits], expected)
        self.assertEqual(self.row(old)["valid_to"], CLOCK - DAY)
        self.assertEqual(self.row(new)["supersedes"], old)
        self.assertEqual(self.row(old)["text"], "光谱仪校准周期为十四天")

    def test_replacement_cannot_target_another_scope_or_invalid_time(self):
        old = self.store.remember("离心机开盖前确认停转", user_id="bio")
        for owner, point, target in (("optics", CLOCK, old), ("bio", CLOCK - 1, old),
                                     ("bio", CLOCK, "missing-safety-record")):
            with self.subTest(owner=owner, point=point, target=target):
                with self.assertRaises(ValueError):
                    self.store.remember("离心机检查要求变更", user_id=owner, now=point, supersedes=target)
                self.assertIsNone(self.row(old)["valid_to"])
        replacement = self.store.remember("停转后还须完成清洁检查", user_id="bio", supersedes=old)
        with self.assertRaises(ValueError):
            self.store.remember("再次修改已结束记录", user_id="bio", supersedes=old)
        self.assertEqual(self.row(replacement)["supersedes"], old)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM memories").fetchone()[0], 2)

    def test_insert_failure_rolls_back_the_old_interval(self):
        old = self.store.remember("光谱仪预约由值班员确认")
        self.store.db.execute("""
            CREATE TRIGGER stop_test_insert BEFORE INSERT ON memories
            BEGIN SELECT RAISE(ABORT, 'simulated disk write rejection'); END
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.remember("预约由实验室管理员确认", supersedes=old)
        self.assertIsNone(self.row(old)["valid_to"])
        self.assertEqual([hit.id for hit in self.store.recall("预约确认")], [old])

    def test_zero_timestamp_and_future_records(self):
        ancient = self.store.remember("校准台账初始登记", now=0, importance=1, confidence=1)
        future = self.store.remember("下周启用新的预约窗口", now=CLOCK + DAY)
        self.assertEqual(self.row(ancient)["created_at"], 0)
        self.assertEqual([hit.id for hit in self.store.recall("校准台账", as_of=0)], [ancient])
        self.assertNotIn(future, [hit.id for hit in self.store.recall("预约")])
        self.assertNotIn(future, self.store.forget_decayed(now=CLOCK, threshold=1))

    def test_score_components_match_the_teaching_formula(self):
        identifier = self.store.remember(
            "laser calibration", now=CLOCK - 30 * DAY, importance=0.8, confidence=0.9
        )
        hit = self.store.recall("laser calibration", reinforce=False)[0]
        self.assertEqual(hit.id, identifier)
        expected = 0.42 + 0.28 + 0.10 * math.exp(-1) + 0.10 * 0.8 + 0.07 * 0.9 + 0.03 * 0.25
        self.assertEqual(hit.score, round(expected, 4))
        self.assertEqual((hit.lexical, hit.semantic, hit.recency), (1, 1, round(math.exp(-1), 4)))
        self.assertEqual(set(asdict(hit)), {field.name for field in fields(Hit)})

    def test_limit_and_reinforcement_are_separate_from_observation(self):
        target = self.store.remember("光谱仪校准证书", now=CLOCK - DAY)
        other = self.store.remember("冰箱温度巡检表", now=CLOCK - DAY)
        before = self.store.recall("光谱仪校准证书", limit=1, reinforce=False)[0]
        self.assertEqual(before.id, target)
        self.assertEqual(self.row(target)["access_count"], 0)
        self.store.recall("光谱仪校准证书", limit=1)
        self.assertEqual(self.row(target)["access_count"], 1)
        self.assertEqual(self.row(target)["last_accessed"], CLOCK)
        self.assertEqual(self.row(other)["access_count"], 0)
        after = self.store.recall("光谱仪校准证书", limit=1, reinforce=False)[0]
        self.assertGreater(after.score, before.score)
        self.assertEqual(self.store.recall("校准", limit=0), [])
        self.assertEqual(self.row(target)["access_count"], 1)

    def test_frequency_signal_has_an_upper_bound(self):
        identifier = self.store.remember("真空泵开机前核对油位")
        self.store.db.execute("UPDATE memories SET access_count = 14 WHERE id = ?", (identifier,))
        self.store.db.commit()
        saturated = self.store.recall("真空泵开机前核对油位", reinforce=False)[0].score
        self.store.db.execute("UPDATE memories SET access_count = 1000 WHERE id = ?", (identifier,))
        self.store.db.commit()
        self.assertEqual(self.store.recall("真空泵开机前核对油位", reinforce=False)[0].score, saturated)

    def test_threshold_uses_the_unrounded_score(self):
        identifier = self.store.remember("旧校准台账索引", now=0, importance=0.42501, confidence=0)
        hit = self.store.recall("", reinforce=False)[0]
        self.assertEqual((hit.id, hit.score), (identifier, 0.05))
        self.store.db.execute("UPDATE memories SET importance = 0.4 WHERE id = ?", (identifier,))
        self.store.db.commit()
        self.assertEqual(self.store.recall("", reinforce=False), [])

    def test_context_obeys_budget(self):
        long_id = self.store.remember("光谱仪校准 " * 100, importance=1)
        short_id = self.store.remember("光谱仪校准证待复核", importance=0.8)
        self.store.remember("另一课题组的预约备注", user_id="other-lab")
        context = self.store.context("光谱仪校准", budget=20)
        lines = context.splitlines()
        self.assertEqual(lines[0], "# 实验室记忆")
        self.assertEqual(len(lines), 2)
        self.assertIn("光谱仪校准证待复核", lines[1])
        self.assertLessEqual(sum(map(len, lines[1:])), 20 * 4)
        self.assertNotIn("另一课题组", context)
        self.assertEqual(self.row(long_id)["access_count"], 1)
        self.assertEqual(self.row(short_id)["access_count"], 1)
        self.assertEqual(self.store.context("校准", budget=0), "# 实验室记忆\n- 未找到可装入的记录。")

    def test_context_packs_multiple_whole_records(self):
        for instrument in ("天平", "光谱仪", "离心机"):
            self.store.remember(f"{instrument}预约完成后签退")
        result = self.store.context("预约签退", budget=24)
        body = result.splitlines()[1:]
        self.assertEqual(len(body), 2)
        self.assertLessEqual(sum(map(len, body)), 96)
        self.assertTrue(all(line.endswith("预约完成后签退") for line in body))

    def test_decay_is_dry_run_by_default(self):
        identifier = self.store.remember(
            "校准期间临时改用备用天平", now=CLOCK - 120 * DAY, importance=0.4, confidence=0.5
        )
        self.assertEqual(self.store.forget_decayed(), [identifier])
        self.assertIsNone(self.row(identifier)["valid_to"])
        self.assertEqual(self.row(identifier)["access_count"], 0)
        self.assertEqual(self.store.forget_decayed(dry_run=False), [identifier])
        self.assertEqual(self.row(identifier)["valid_to"], CLOCK)
        self.assertEqual(self.store.recall("备用天平"), [])
        history = self.store.recall("备用天平", as_of=CLOCK - DAY, reinforce=False)
        self.assertEqual([hit.id for hit in history], [identifier])
        self.assertEqual(self.store.forget_decayed(dry_run=False), [])
        self.assertIn("临时", self.row(identifier)["text"])

    def test_half_life_threshold_is_strict_and_scoped(self):
        identifier = self.store.remember(
            "校准证书集中复核通知", now=CLOCK - 7 * DAY, importance=1, confidence=1
        )
        foreign = self.store.remember("化学实验室临时停机通知", user_id="chemistry", now=0)
        self.assertEqual(self.store.forget_decayed(half_life_days=7, threshold=0.5), [])
        self.assertEqual(self.store.forget_decayed(half_life_days=7, threshold=0.5001), [identifier])
        self.assertEqual(self.store.forget_decayed(now=CLOCK + 7 * DAY, half_life_days=7, threshold=0.251), [identifier])
        self.assertIsNone(self.row(foreign)["valid_to"])

    def test_recall_resets_idle_age_but_does_not_change_confidence(self):
        identifier = self.store.remember(
            "天平校准后记录砝码编号", now=CLOCK - 120 * DAY, importance=0.8, confidence=0.9
        )
        self.assertEqual(self.store.forget_decayed(), [identifier])
        self.store.recall("天平校准")
        self.assertEqual(self.store.forget_decayed(), [])
        self.assertEqual(self.row(identifier)["confidence"], 0.9)
        self.assertEqual(self.row(identifier)["importance"], 0.8)

    def test_validation_rejects_inputs_before_changing_state(self):
        invalid_calls = [
            lambda: self.store.remember(" \n"),
            lambda: self.store.remember("校准观察", user_id=""),
            lambda: self.store.remember("校准观察", importance=float("nan")),
            lambda: self.store.remember("校准观察", confidence=float("inf")),
            lambda: self.store.remember("校准观察", now=float("nan")),
            lambda: self.store.recall("校准", limit=-1),
            lambda: self.store.recall("校准", as_of=float("inf")),
            lambda: self.store.context("校准", budget=-1),
            lambda: self.store.forget_decayed(half_life_days=0),
            lambda: self.store.forget_decayed(half_life_days=-7),
            lambda: self.store.forget_decayed(threshold=float("nan")),
        ]
        for call in invalid_calls:
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM memories").fetchone()[0], 0)

    def test_sql_punctuation_is_stored_as_text(self):
        scope = "lab'; DROP TABLE memories; --"
        identifier = self.store.remember("样品标签含 ' 和 ?，保存时不可解释为 SQL", user_id=scope)
        self.assertEqual([hit.id for hit in self.store.recall("样品标签", user_id=scope)], [identifier])
        self.assertEqual(self.store.recall("样品标签"), [])


class RepresentationTest(unittest.TestCase):
    def test_mixed_language_terms_keep_repeat_counts(self):
        self.assertEqual(terms("LASER laser，校准!"), ["laser", "laser", "校", "准", "校准"])
        self.assertEqual(terms("..."), [])
        self.assertEqual(terms("S7校准"), ["s", "7", "校", "准", "s7", "7校", "校准"])

    def test_vector_normalization_and_empty_input(self):
        vector = hashed_vector("laser calibration calibration")
        self.assertAlmostEqual(sum(value * value for value in vector.values()), 1)
        self.assertEqual(vector, hashed_vector("LASER calibration calibration"))
        self.assertAlmostEqual(cosine(vector, vector), 1)
        self.assertEqual(hashed_vector(""), {})
        self.assertEqual(cosine({}, vector), 0)
        self.assertTrue(all(0 <= bucket < 256 for bucket in vector))

    def test_hash_collisions_do_not_prove_shared_meaning(self):
        self.assertEqual(hashed_vector("laser", dimensions=1), {0: 1.0})
        self.assertEqual(cosine(hashed_vector("laser", 1), hashed_vector("centrifuge", 1)), 1)
        with self.assertRaises(ValueError):
            hashed_vector("calibration", dimensions=0)


class CommandLineTest(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.database = Path(self.workspace.name) / "booking.sqlite"

    def run_cli(self, *arguments, success=True):
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "--db", str(self.database), *arguments],
            text=True, capture_output=True, timeout=10,
        )
        if success:
            self.assertEqual(process.returncode, 0, process.stderr)
        else:
            self.assertNotEqual(process.returncode, 0)
        return process

    def test_booking_calibration_and_safety_handoff(self):
        old = self.run_cli(
            "remember", "光谱仪校准由周一值班员复核", "--user", "optics",
            "--kind", "procedural", "--importance", "0.85", "--confidence", "0.95",
            "--source", "calibration-notice-12",
        ).stdout.strip()
        self.assertRegex(old, r"^[0-9a-f]{12}$")
        new = self.run_cli(
            "remember", "光谱仪校准改由周三值班员复核，安全签字仍需保留",
            "--user", "optics", "--supersedes", old, "--source", "handoff-13",
        ).stdout.strip()
        hits = json.loads(self.run_cli("recall", "光谱仪校准", "--user", "optics", "--limit", "1").stdout)
        self.assertEqual(len(hits), 1)
        self.assertEqual((hits[0]["id"], hits[0]["source"]), (new, "handoff-13"))
        self.assertIn("安全签字", hits[0]["text"])
        self.assertEqual(set(hits[0]), {field.name for field in fields(Hit)})
        self.assertEqual(json.loads(self.run_cli("recall", "光谱仪校准", "--user", "chemistry").stdout), [])
        context = self.run_cli("context", "光谱仪校准", "--user", "optics", "--budget", "60").stdout
        self.assertIn("安全签字仍需保留", context)
        self.assertNotIn("周一", context)

    def test_forgetting_cli_previews_then_applies(self):
        identifier = self.run_cli(
            "remember", "昨日临时借用砝码的备注", "--user", "metrology",
            "--importance", "0.01", "--confidence", "0.1",
        ).stdout.strip()
        preview = json.loads(self.run_cli("forget-decayed", "--user", "metrology").stdout)
        self.assertEqual(preview, [identifier])
        self.assertEqual(json.loads(self.run_cli("forget-decayed", "--user", "other-lab", "--apply").stdout), [])
        with closing(sqlite3.connect(self.database)) as database:
            self.assertIsNone(database.execute("SELECT valid_to FROM memories WHERE id = ?", (identifier,)).fetchone()[0])
        self.assertEqual(json.loads(self.run_cli("forget-decayed", "--user", "metrology", "--apply").stdout), [identifier])
        self.assertEqual(json.loads(self.run_cli("recall", "借用砝码", "--user", "metrology").stdout), [])
        with closing(sqlite3.connect(self.database)) as database:
            body, end = database.execute("SELECT text, valid_to FROM memories WHERE id = ?", (identifier,)).fetchone()
            self.assertIn("砝码", body)
            self.assertIsNotNone(end)

    def test_help_and_invalid_arguments(self):
        help_text = self.run_cli("--help").stdout
        for command in ("remember", "recall", "context", "forget-decayed"):
            self.assertIn(command, help_text)
        for arguments in ((), ("remember", " "), ("recall", "校准", "--limit", "-1"),
                          ("context", "预约", "--budget", "-1")):
            with self.subTest(arguments=arguments):
                error = self.run_cli(*arguments, success=False)
                self.assertIn("error:", error.stderr)
                self.assertNotIn("Traceback", error.stderr)


if __name__ == "__main__":
    unittest.main()
