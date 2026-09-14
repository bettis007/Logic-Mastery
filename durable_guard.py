"""SQLite-backed restart simulation for the fixture guard, not production auth."""
import hashlib,json,sqlite3
from collections import deque
from pathlib import Path
from signal_guard_sim import Guard,CONFIG,FIXTURE_KEY,canonical
BINDING=hashlib.sha256(canonical(CONFIG)+FIXTURE_KEY+Path(__file__).with_name('signal_guard_sim.py').read_bytes()).hexdigest()

class DurableGuard:
    def __init__(self,path,initialize=False):
        self.path=Path(path)
        if initialize:
            # Exclusive file creation prevents resetting an existing replay ledger.
            with self.path.open('xb'):pass
        elif not self.path.is_file():raise ValueError('Missing replay ledger; explicit initialization required')
        self.db=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        try:
            self.db.execute('PRAGMA synchronous=FULL')
            if initialize:
                self.db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), binding TEXT NOT NULL, payload TEXT NOT NULL)')
                self.db.execute('INSERT INTO state VALUES (1,?,?)',(BINDING,json.dumps({'last':-1,'last_time':None,'arrivals':[]})))
            if self.db.execute('PRAGMA quick_check').fetchone()!=('ok',):raise ValueError('Replay ledger integrity failure')
        except Exception:self.db.close();raise
    def inspect(self,message,now,crash=None):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            rows=self.db.execute('SELECT binding,payload FROM state').fetchall()
            if len(rows)!=1 or rows[0][0]!=BINDING:raise ValueError('Ledger binding mismatch')
            s=json.loads(rows[0][1]);g=Guard()
            if set(s)!={'last','last_time','arrivals'} or type(s['last']) is not int or s['last']< -1:raise ValueError('Invalid replay state')
            import math
            if s['last_time'] is not None and (type(s['last_time']) not in (int,float) or not math.isfinite(s['last_time'])):raise ValueError('Invalid stored clock')
            if not isinstance(s['arrivals'],list) or len(s['arrivals'])>CONFIG['requests_per_second'] or any(type(t) not in (int,float) or not math.isfinite(t) for t in s['arrivals']):raise ValueError('Invalid stored quota')
            if s['arrivals']!=sorted(s['arrivals']) or (s['arrivals'] and (s['last_time'] is None or s['arrivals'][-1]>s['last_time'])):raise ValueError('Inconsistent quota clock')
            g.last=s['last'];g.last_time=s['last_time'] if s['last_time'] is not None else -math.inf;g.arrivals=deque(s['arrivals'])
            outcome=g.inspect(message,now)
            state={'last':g.last,'last_time':g.last_time if math.isfinite(g.last_time) else None,'arrivals':list(g.arrivals)}
            self.db.execute('UPDATE state SET payload=? WHERE id=1',(canonical(state).decode(),))
            if crash=='before_commit':
                import os;os._exit(71)
            self.db.execute('COMMIT')
            if crash=='after_commit':
                import os;os._exit(72)
            return outcome
        except Exception:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise
    def close(self):self.db.close()
