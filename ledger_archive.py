"""Validate and copy synthetic delivery ledgers; never prune or replace a source.

This is an offline maintenance API, not a production cutover protocol. Retain the
matching sink and stop writers before choosing a copy as the active ledger.
"""
import hashlib
import math
import os
import re
import sqlite3
import tempfile
from pathlib import Path

from receipt_guard import ReceiptGuard
from signal_guard_sim import CONFIG, canonical

SCHEMA = {
    'state': 'CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL, mac TEXT NOT NULL)',
    'receipts': 'CREATE TABLE receipts (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, mac TEXT NOT NULL)',
    'outbox': 'CREATE TABLE outbox (seq INTEGER PRIMARY KEY, attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT "pending")',
    'delivery_policy': 'CREATE TABLE delivery_policy (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL, mac TEXT NOT NULL)',
    'pending_queue': 'CREATE INDEX pending_queue ON outbox(status,next_at,seq)',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def limits(attempts, rows):
    require(type(attempts) is int and 1 <= attempts <= 64, 'Invalid retry limit')
    require(type(rows) is int and 1 <= rows <= 1000000, 'Invalid capacity limit')


def check_schema(db):
    """Accept only the exact current or supported legacy prototype schema."""
    entries = db.execute('SELECT type,name,sql FROM sqlite_master').fetchall()
    names = {name for _, name, _ in entries}
    legacy = names == {'state', 'receipts', 'outbox'}
    require(legacy or names == set(SCHEMA), 'Unsupported ledger schema')
    for kind, name, sql in entries:
        expected_kind = 'index' if name == 'pending_queue' else 'table'
        require(kind == expected_kind and isinstance(sql, str)
                and ' '.join(sql.split()) == ' '.join(SCHEMA[name].split()),
                'Unexpected schema definition')
    require(db.execute('PRAGMA quick_check').fetchall() == [('ok',)], 'SQLite integrity check failed')
    return legacy


def verified_object(guard, domain, body, mac, fields):
    value = guard.verify(domain, body, mac)
    require(type(value) is dict and set(value) == set(fields), 'Invalid ' + domain + ' fields')
    require(canonical(value).decode() == body, 'Noncanonical ' + domain)
    require(value['binding'] == guard.binding, 'Binding mismatch')
    return value


def validate_rows(guard, policy):
    db = guard.db
    rows = db.execute('SELECT id,body,mac FROM state').fetchall()
    require(len(rows) == 1 and rows[0][0] == 1, 'Invalid state row')
    state = verified_object(guard, 'state', *rows[0][1:], ('binding', 'last', 'last_time', 'arrivals'))
    require(type(state['last']) is int and state['last'] >= -1, 'Invalid sequence state')
    require(type(state['arrivals']) is list and len(state['arrivals']) <= CONFIG['requests_per_second'], 'Invalid arrival history')
    allowed, last, last_time, previous_time = set(), -1, None, None
    for seq, body, mac in db.execute('SELECT seq,body,mac FROM receipts ORDER BY seq'):
        r = verified_object(guard, 'receipt', body, mac,
                            ('binding', 'seq', 'request_sha256', 'outcome', 'recorded_at'))
        require(type(r['seq']) is int and r['seq'] == seq and seq >= 0, 'Invalid receipt sequence')
        require(isinstance(r['request_sha256'], str) and re.fullmatch('[0-9a-f]{64}', r['request_sha256']), 'Invalid request digest')
        require(r['outcome'] in ('allow', 'review_signal', 'reject_rate'), 'Invalid stored outcome')
        require(finite(r['recorded_at']) and (previous_time is None or r['recorded_at'] >= previous_time), 'Invalid receipt clock')
        if r['outcome'] == 'allow':
            allowed.add(seq)
        last, last_time, previous_time = seq, r['recorded_at'], r['recorded_at']
    require(state['last'] == last and state['last_time'] == last_time, 'Receipt/state mismatch')
    require((last == -1 and state['last_time'] is None) or finite(state['last_time']), 'Invalid state clock')
    arrivals = state['arrivals']
    require(all(finite(t) for t in arrivals), 'Invalid arrival clock')
    require(arrivals == sorted(arrivals) and (not arrivals or
            (finite(last_time) and all(last_time - 1 < t <= last_time for t in arrivals))), 'Invalid arrival interval')
    require(last != -1 or not arrivals, 'Unexpected empty-ledger history')
    queued = set()
    for seq, attempts, next_at, status in db.execute('SELECT seq,attempts,next_at,status FROM outbox'):
        require(type(attempts) is int and 0 <= attempts <= policy['max_attempts'], 'Invalid retry count')
        require(finite(next_at) and next_at >= 0, 'Invalid retry clock')
        require(status in ('pending', 'delivered', 'exhausted'), 'Invalid queue status')
        require(status != 'exhausted' or attempts == policy['max_attempts'], 'Invalid exhausted status')
        require(status != 'delivered' or attempts > 0, 'Invalid delivered status')
        require(attempts != 0 or next_at == 0, 'Invalid initial retry clock')
        queued.add(seq)
    require(queued == allowed, 'Queue does not match allowed receipts')
    require(len(queued) <= policy['max_rows'], 'Capacity exceeded')
    return {'receipts': db.execute('SELECT count(*) FROM receipts').fetchone()[0],
            'outbox': len(queued),
            'statuses': dict(db.execute('SELECT status,count(*) FROM outbox GROUP BY status'))}


def copy_ledger(source, destination, key, *, legacy_limits=None):
    """Create an exclusive validated snapshot; optionally migrate a legacy copy.

    legacy_limits=(historical_retry_budget, new_capacity) is an explicit operator
    declaration. The old ledger cannot prove which retry budget was used. A copy
    includes ALL rows and does not reclaim capacity. Queue metadata is checked for
    consistency, not authenticated. No sink or external effect is copied.
    """
    require(isinstance(key, bytes) and len(key) >= 32, 'Supply the original receipt key')
    source, destination = Path(source).resolve(), Path(destination).absolute()
    require(source.is_file(), 'Source ledger missing')
    require(source != destination.resolve(), 'Source and destination must differ')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    fd, name = tempfile.mkstemp(prefix='ledger-copy-', suffix='.sqlite', dir=destination.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        src = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
        dest = sqlite3.connect(temporary)
        try:
            src.backup(dest)  # Includes committed WAL data in a consistent SQLite snapshot.
            legacy = check_schema(dest)
        finally:
            src.close()
            dest.close()
        guard = ReceiptGuard(temporary, key)
        try:
            if legacy:
                require(type(legacy_limits) is tuple and len(legacy_limits) == 2,
                        'Legacy copy needs explicit historical retry budget and new capacity')
                attempts, capacity = legacy_limits
                limits(attempts, capacity)
                policy = {'binding': guard.binding, 'max_attempts': attempts, 'max_rows': capacity}
            else:
                require(legacy_limits is None, 'Current policy cannot be overridden')
                rows = guard.db.execute('SELECT id,body,mac FROM delivery_policy').fetchall()
                require(len(rows) == 1 and rows[0][0] == 1, 'Invalid policy row')
                policy = verified_object(guard, 'delivery-policy', *rows[0][1:], ('binding', 'max_attempts', 'max_rows'))
                limits(policy['max_attempts'], policy['max_rows'])
            summary = validate_rows(guard, policy)
            if legacy:
                guard.db.execute('BEGIN IMMEDIATE')
                guard.db.execute(SCHEMA['delivery_policy'])
                guard.db.execute(SCHEMA['pending_queue'])
                body = canonical(policy).decode()
                guard.db.execute('INSERT INTO delivery_policy VALUES(1,?,?)', (body, guard.mac('delivery-policy', body)))
                guard.db.execute('COMMIT')
            check_schema(guard.db)
        finally:
            guard.close()
        with temporary.open('rb') as stream:
            os.fsync(stream.fileno())
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        os.link(temporary, destination)  # Atomic, same-filesystem, refuses overwrite.
        directory = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return {**summary, 'legacy_migrated': legacy, 'policy': policy,
                'snapshot_sha256': digest, 'source_pruned': False,
                'scope': 'Validated local snapshot; no provenance, rollback, sink or cutover guarantee'}
    finally:
        temporary.unlink(missing_ok=True)
