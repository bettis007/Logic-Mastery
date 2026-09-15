"""Single-worker synthetic outbox; destination is a disposable local SQLite table."""
import math,sqlite3
from pathlib import Path
from receipt_guard import ReceiptGuard

class DeliveryGuard(ReceiptGuard):
    def __init__(self,path,key,initialize=False):
        super().__init__(path,key,initialize)
        try:
            if initialize:self.db.execute('CREATE TABLE outbox (seq INTEGER PRIMARY KEY, attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT "pending")')
            self.db.execute('SELECT seq,attempts,next_at,status FROM outbox LIMIT 0')
        except Exception:self.close();raise
    def record_effect(self,receipt,body,mac):
        if receipt['outcome']=='allow':self.db.execute('INSERT INTO outbox(seq) VALUES(?)',(receipt['seq'],))

def initialize_sink(path):
    with Path(path).open('xb'):pass
    db=sqlite3.connect(path)
    try:
        db.execute('CREATE TABLE effects (effect_id TEXT PRIMARY KEY, body TEXT NOT NULL, mac TEXT NOT NULL)');db.commit()
    finally:db.close()

def deliver_one(guard,sink_path,now,fail=False,crash=None,max_attempts=3):
    if not isinstance(now,(int,float)) or not math.isfinite(now) or now<0:raise ValueError('Invalid clock')
    if type(max_attempts) is not int or max_attempts<1:raise ValueError('Invalid retry budget')
    if not Path(sink_path).is_file():raise ValueError('Missing sink; initialization is explicit')
    sink=sqlite3.connect(sink_path,isolation_level=None)
    try:
        sink.execute('PRAGMA synchronous=FULL')
        guard.db.execute('BEGIN IMMEDIATE')
        try:
            guard.read_state()
            row=guard.db.execute('SELECT seq,attempts,next_at,status FROM outbox WHERE status!="delivered" ORDER BY seq LIMIT 1').fetchone()
            if not row:guard.db.execute('COMMIT');return 'empty'
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
