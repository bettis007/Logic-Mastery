"""Single-worker synthetic outbox; destination is a disposable local SQLite table."""
import math,sqlite3
from signal_guard_sim import canonical
from pathlib import Path
from receipt_guard import ReceiptGuard

class DeliveryGuard(ReceiptGuard):
    def __init__(self,path,key,initialize=False,max_attempts=None,max_rows=None):
        super().__init__(path,key,initialize)
        try:
            if initialize:
                attempts=3 if max_attempts is None else max_attempts
                rows=10000 if max_rows is None else max_rows
                if type(attempts) is not int or not 1<=attempts<=64 or type(rows) is not int or not 1<=rows<=1000000:
                    raise ValueError('Invalid delivery policy limits')
                self.db.execute('BEGIN IMMEDIATE')
                self.db.execute('CREATE TABLE outbox (seq INTEGER PRIMARY KEY, attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT "pending")')
                self.db.execute('CREATE INDEX pending_queue ON outbox(status,next_at,seq)')
                self.db.execute('CREATE TABLE delivery_policy (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL, mac TEXT NOT NULL)')
                body=canonical({'binding':self.binding,'max_attempts':attempts,'max_rows':rows}).decode()
                self.db.execute('INSERT INTO delivery_policy VALUES(1,?,?)',(body,self.mac('delivery-policy',body)))
                self.db.execute('COMMIT')
            policy=self.policy()
            if max_attempts is not None and max_attempts!=policy['max_attempts']:raise ValueError('Retry budget differs from stored policy')
            if max_rows is not None and max_rows!=policy['max_rows']:raise ValueError('Capacity differs from stored policy')
            self.db.execute('SELECT seq,attempts,next_at,status FROM outbox LIMIT 0')
        except Exception:self.close();raise
    def policy(self):
        rows=self.db.execute('SELECT body,mac FROM delivery_policy').fetchall()
        if len(rows)!=1:raise ValueError('Missing delivery policy')
        policy=self.verify('delivery-policy',*rows[0])
        if policy['binding']!=self.binding:raise ValueError('Delivery policy binding mismatch')
        return policy
    def queue_status(self):
        return dict(self.db.execute('SELECT status,count(*) FROM outbox GROUP BY status').fetchall())
    def record_effect(self,receipt,body,mac):
        if receipt['outcome']=='allow':
            if self.db.execute('SELECT count(*) FROM outbox').fetchone()[0]>=self.policy()['max_rows']:
                raise ValueError('Delivery ledger capacity reached; preserve and archive before accepting more effects')
            self.db.execute('INSERT INTO outbox(seq) VALUES(?)',(receipt['seq'],))

def initialize_sink(path):
    with Path(path).open('xb'):pass
    db=sqlite3.connect(path)
    try:
        db.execute('CREATE TABLE effects (effect_id TEXT PRIMARY KEY, body TEXT NOT NULL, mac TEXT NOT NULL)');db.commit()
    finally:db.close()

def deliver_one(guard,sink_path,now,fail=False,crash=None,max_attempts=None):
    if type(now) not in (int,float) or not math.isfinite(now) or now<0:raise ValueError('Invalid clock')
    policy=guard.policy()
    if max_attempts is not None and (type(max_attempts) is not int or max_attempts!=policy['max_attempts']):raise ValueError('Retry override differs from stored policy')
    max_attempts=policy['max_attempts']
    if not Path(sink_path).is_file():raise ValueError('Missing sink; initialization is explicit')
    sink=sqlite3.connect(sink_path,isolation_level=None)
    try:
        sink.execute('PRAGMA synchronous=FULL')
        guard.db.execute('BEGIN IMMEDIATE')
        try:
            guard.read_state()
            row=guard.db.execute('SELECT seq,attempts,next_at,status FROM outbox WHERE status="pending" ORDER BY CASE WHEN attempts>=? OR next_at<=? THEN 0 ELSE 1 END, seq LIMIT 1',(max_attempts,now)).fetchone()
            if not row:
                status='exhausted' if guard.db.execute('SELECT 1 FROM outbox WHERE status="exhausted" LIMIT 1').fetchone() else 'empty'
                guard.db.execute('COMMIT');return status
            seq,attempts,next_at,status=row
            stored=guard.db.execute('SELECT body,mac FROM receipts WHERE seq=?',(seq,)).fetchone()
            if stored is None:raise ValueError('Missing authorized receipt')
            receipt=guard.verify('receipt',*stored)
            if receipt['seq']!=seq or receipt['binding']!=guard.binding or receipt['outcome']!='allow':raise ValueError('Invalid effect authorization')
            effect_id=receipt['binding']+':'+receipt['request_sha256']
            old=sink.execute('SELECT body,mac FROM effects WHERE effect_id=?',(effect_id,)).fetchone()
            if old:
                if tuple(old)!=tuple(stored):raise ValueError('Sink payload conflict')
                guard.db.execute('UPDATE outbox SET status="delivered" WHERE seq=?',(seq,));guard.db.execute('COMMIT');return 'reconciled'
            if attempts>=max_attempts:
                guard.db.execute('UPDATE outbox SET status="exhausted" WHERE seq=?',(seq,));guard.db.execute('COMMIT');return 'exhausted'
            if now<next_at:guard.db.execute('COMMIT');return 'deferred'
            attempts+=1
            guard.db.execute('UPDATE outbox SET attempts=?,next_at=? WHERE seq=?',(attempts,now+2**(attempts-1),seq))
            guard.db.execute('COMMIT')
        except Exception:
            if guard.db.in_transaction:guard.db.execute('ROLLBACK')
            raise
        if fail:return 'retry_scheduled'
        sink.execute('BEGIN IMMEDIATE')
        try:
            old=sink.execute('SELECT body,mac FROM effects WHERE effect_id=?',(effect_id,)).fetchone()
            if old and tuple(old)!=tuple(stored):raise ValueError('Sink payload conflict')
            if not old:sink.execute('INSERT INTO effects VALUES(?,?,?)',(effect_id,*stored))
            sink.execute('COMMIT')
        except Exception:
            if sink.in_transaction:sink.execute('ROLLBACK')
            raise
        if crash=='after_sink_commit':
            import os;os._exit(72)
        guard.db.execute('UPDATE outbox SET status="delivered" WHERE seq=?',(seq,))
        return 'delivered'
    finally:sink.close()
