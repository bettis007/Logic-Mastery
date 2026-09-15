"""Atomic recovery receipts for the synthetic message guard.
Message authentication still uses the public fixture key; receipt/state keys are
supplied by the caller, never persisted by this module. No external side effects.
"""
import hashlib,hmac,json,math,sqlite3
from collections import deque
from pathlib import Path
from signal_guard_sim import Guard,canonical,CONFIG

class ReceiptGuard:
    def __init__(self,path,key,initialize=False):
        if not isinstance(key,bytes) or len(key)<32:raise ValueError('Supply at least 32 bytes of receipt key material')
        self.key=key;self.path=Path(path)
        self.binding=hashlib.sha256(key+canonical(CONFIG)+Path(__file__).with_name('signal_guard_sim.py').read_bytes()).hexdigest()
        if initialize:
            with self.path.open('xb'):pass
        elif not self.path.is_file():raise ValueError('Missing ledger')
        self.db=sqlite3.connect(self.path,isolation_level=None,timeout=10)
        try:
            self.db.execute('PRAGMA synchronous=FULL')
            if initialize:
                self.db.execute('BEGIN IMMEDIATE')
                self.db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL, mac TEXT NOT NULL)')
                self.db.execute('CREATE TABLE receipts (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, mac TEXT NOT NULL)')
                body=canonical({'binding':self.binding,'last':-1,'last_time':None,'arrivals':[]}).decode()
                self.db.execute('INSERT INTO state VALUES(1,?,?)',(body,self.mac('state',body)))
                self.db.execute('COMMIT')
            if self.db.execute('PRAGMA quick_check').fetchone()!=('ok',):raise ValueError('Invalid SQLite ledger')
            self.read_state()
        except Exception:self.db.close();raise
    def mac(self,domain,body):return hmac.new(self.key,domain.encode()+b'\0'+body.encode(),hashlib.sha256).hexdigest()
    def verify(self,domain,body,mac):
        if not hmac.compare_digest(self.mac(domain,body),mac):raise ValueError('Ledger authentication failed')
        return json.loads(body)
    def read_state(self):
        rows=self.db.execute('SELECT body,mac FROM state').fetchall()
        if len(rows)!=1:raise ValueError('Missing state')
        state=self.verify('state',*rows[0])
        if state['binding']!=self.binding:raise ValueError('Wrong key/configuration')
        return state
    def record_effect(self,receipt,body,mac):
        """Subclass hook; runs inside the receipt/state transaction."""
        pass
    def inspect(self,message,now,crash=None):
        # Authenticate and validate before returning any stored receipt.
        preflight=Guard().inspect(message,now)
        if preflight not in ('allow','review_signal'):return {'status':'rejected','reason':preflight}
        request_hash=hashlib.sha256(canonical(message)).hexdigest();seq=message['payload']['seq']
        self.db.execute('BEGIN IMMEDIATE')
        try:
            s=self.read_state();old=self.db.execute('SELECT body,mac FROM receipts WHERE seq=?',(seq,)).fetchone()
            if old:
                receipt=self.verify('receipt',*old)
                if receipt['request_sha256']!=request_hash:
                    self.db.execute('ROLLBACK');return {'status':'rejected','reason':'sequence_conflict'}
                self.db.execute('COMMIT');return {'status':'receipt','recovered':True,'receipt':receipt,'mac':old[1]}
            g=Guard();g.last=s['last'];g.last_time=s['last_time'] if s['last_time'] is not None else -math.inf;g.arrivals=deque(s['arrivals'])
            outcome=g.inspect(message,now)
            # Clock/replay rejections do not consume a new sequence or create a receipt.
            if outcome in ('reject_clock','reject_replay'):
                self.db.execute('ROLLBACK');return {'status':'rejected','reason':outcome}
            state={'binding':self.binding,'last':g.last,'last_time':g.last_time,'arrivals':list(g.arrivals)}
            body=canonical(state).decode();self.db.execute('UPDATE state SET body=?,mac=? WHERE id=1',(body,self.mac('state',body)))
            receipt={'binding':self.binding,'seq':seq,'request_sha256':request_hash,'outcome':outcome,'recorded_at':now}
            body=canonical(receipt).decode();mac=self.mac('receipt',body)
            self.db.execute('INSERT INTO receipts VALUES(?,?,?)',(seq,body,mac))
            self.record_effect(receipt,body,mac)
            if crash=='before_commit':
                import os;os._exit(71)
            self.db.execute('COMMIT')
            if crash=='after_commit':
                import os;os._exit(72)
            return {'status':'receipt','recovered':False,'receipt':receipt,'mac':mac}
        except Exception:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise
    def close(self):self.db.close()
