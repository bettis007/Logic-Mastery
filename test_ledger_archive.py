"""Disposable-fixture preservation, rejection and recovery tests."""
import hashlib
import secrets
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ledger_archive import copy_ledger
from signal_guard_sim import sign
from transactional_delivery import DeliveryGuard, deliver_one, initialize_sink


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source, self.target, self.sink = [self.root / p for p in ('source.sqlite', 'copy.sqlite', 'sink.sqlite')]
        self.key = secrets.token_bytes(32)
        self.g = DeliveryGuard(self.source, self.key, initialize=True, max_attempts=2, max_rows=8)
        initialize_sink(self.sink)

    def tearDown(self):
        self.g.close()
        self.temp.cleanup()

    def put(self, seq):
        return self.g.inspect(sign(seq, [0] * 128), seq)

    def snapshot(self, db):
        return {name: db.execute('SELECT * FROM ' + name + ' ORDER BY 1').fetchall()
                for name in ('state', 'receipts', 'outbox')}

    def archive(self, **kwargs):
        return copy_ledger(self.source, self.target, self.key, **kwargs)

    def legacy(self):
        self.g.db.execute('DROP TABLE delivery_policy')
        self.g.db.execute('DROP INDEX pending_queue')

    def test_current_copy_preserves_history_and_continues_pending_work(self):
        for seq in range(3):
            self.put(seq)
        self.assertEqual(deliver_one(self.g, self.sink, 0), 'delivered')
        deliver_one(self.g, self.sink, 1, fail=True)
        deliver_one(self.g, self.sink, 2, fail=True)
        self.assertEqual(deliver_one(self.g, self.sink, 3), 'exhausted')
        before = self.snapshot(self.g.db)
        source_bytes = self.source.read_bytes()
        result = self.archive()
        self.assertEqual(self.source.read_bytes(), source_bytes)
        self.assertEqual(result['statuses'], {'delivered': 1, 'exhausted': 1, 'pending': 1})
        self.assertEqual(result['snapshot_sha256'], hashlib.sha256(self.target.read_bytes()).hexdigest())
        g = DeliveryGuard(self.target, self.key)
        try:
            self.assertEqual(self.snapshot(g.db), before)
            self.assertEqual(g.policy(), self.g.policy())
            self.assertTrue(g.inspect(sign(0, [0] * 128), 4)['recovered'])
            self.assertEqual(deliver_one(g, self.sink, 4), 'delivered')
            self.assertEqual(deliver_one(g, self.sink, 5), 'exhausted')
            self.assertEqual(g.db.execute('SELECT attempts FROM outbox WHERE seq=1').fetchone(), (2,))
        finally:
            g.close()
        self.assertEqual(self.snapshot(self.g.db), before)
        with sqlite3.connect(self.sink) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM effects').fetchone(), (2,))

    def test_committed_wal_records_are_included(self):
        self.g.db.execute('PRAGMA journal_mode=WAL')
        self.put(0)
        self.assertTrue(Path(str(self.source) + '-wal').is_file())
        self.archive()
        with sqlite3.connect(self.target) as db:
            self.assertEqual(self.snapshot(db), self.snapshot(self.g.db))

    def test_review_and_rate_receipts_are_preserved_without_effects(self):
        for seq in range(20):
            result = self.g.inspect(sign(seq, [10] * 128), 0)
            self.assertEqual(result['receipt']['outcome'], 'review_signal')
        result = self.g.inspect(sign(20, [10] * 128), .2)
        self.assertEqual(result['receipt']['outcome'], 'reject_rate')
        summary = self.archive()
        self.assertEqual(summary['receipts'], 21)
        self.assertEqual(summary['outbox'], 0)
        with sqlite3.connect(self.target) as db:
            self.assertEqual(self.snapshot(db), self.snapshot(self.g.db))

    def test_legacy_migration_requires_limits_and_keeps_attempts(self):
        self.put(0)
        deliver_one(self.g, self.sink, 0, fail=True)
        self.legacy()
        original = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, 'explicit historical'):
            self.archive()
        self.assertFalse(self.target.exists())
        result = self.archive(legacy_limits=(2, 8))
        self.assertTrue(result['legacy_migrated'])
        self.assertEqual(self.source.read_bytes(), original)
        g = DeliveryGuard(self.target, self.key)
        try:
            self.assertEqual(self.snapshot(g.db), self.snapshot(self.g.db))
            self.assertEqual(deliver_one(g, self.sink, 1, fail=True), 'retry_scheduled')
            self.assertEqual(deliver_one(g, self.sink, 3), 'exhausted')
            self.assertEqual(g.db.execute('SELECT attempts FROM outbox').fetchone(), (2,))
        finally:
            g.close()

    def test_existing_destination_and_same_source_are_preserved(self):
        self.target.write_bytes(b'keep this')
        with self.assertRaises(FileExistsError):
            self.archive()
        self.assertEqual(self.target.read_bytes(), b'keep this')
        with self.assertRaises(ValueError):
            copy_ledger(self.source, self.source, self.key)

    def test_wrong_key_and_altered_receipt_rejected(self):
        self.put(0)
        with self.assertRaises(ValueError):
            copy_ledger(self.source, self.target, secrets.token_bytes(32))
        self.g.db.execute("UPDATE receipts SET body='{}'")
        with self.assertRaises(ValueError):
            self.archive()
        self.assertFalse(self.target.exists())

    def test_policy_alteration_and_override_rejected(self):
        with self.assertRaises(ValueError):
            self.archive(legacy_limits=(8, 8))
        self.g.db.execute("UPDATE delivery_policy SET body='{}'")
        with self.assertRaises(ValueError):
            self.archive()
        self.assertFalse(self.target.exists())

    def test_missing_queue_invalid_status_and_deleted_receipt_rejected(self):
        self.put(0)
        for statement in ('DELETE FROM outbox', "UPDATE outbox SET status='unknown'", 'DELETE FROM receipts'):
            # Backup sees committed rows; create each mutation in a separate fixture.
            with sqlite3.connect(self.root / 'bad.sqlite') as db:
                self.g.db.backup(db)
                db.execute(statement)
            with self.assertRaises(ValueError):
                copy_ledger(self.root / 'bad.sqlite', self.target, self.key)
            self.assertFalse(self.target.exists())

    def test_schema_trigger_and_unreadable_database_rejected(self):
        self.g.db.execute('CREATE TRIGGER unexpected AFTER INSERT ON outbox BEGIN DELETE FROM receipts; END')
        with self.assertRaises(ValueError):
            self.archive()
        bad = self.root / 'bad.sqlite'
        bad.write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError):
            copy_ledger(bad, self.target, self.key)
        self.assertFalse(self.target.exists())

    def test_failed_publication_preserves_source_and_cleans_temporary_copy(self):
        self.put(0)
        before = self.source.read_bytes()
        with patch('ledger_archive.os.link', side_effect=OSError('injected publication failure')):
            with self.assertRaises(OSError):
                self.archive()
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.root.glob('ledger-copy-*')), [])

    def test_legacy_limits_cannot_erase_spent_retries_or_rows(self):
        self.put(0)
        self.put(1)
        deliver_one(self.g, self.sink, 0, fail=True)
        deliver_one(self.g, self.sink, 1, fail=True)
        self.legacy()
        for limits in ((1, 8), (2, 1), (True, 8), (2, 0)):
            with self.assertRaises(ValueError):
                self.archive(legacy_limits=limits)
            self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
