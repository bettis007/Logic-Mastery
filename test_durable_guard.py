"""Real subprocess exits on disposable SQLite ledgers. No power-loss claim."""
import json,sqlite3,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
from durable_guard import DurableGuard
from signal_guard_sim import sign

def run():
 checks={}
 with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);p=root/'state.sqlite';g=DurableGuard(p,initialize=True)
    m=sign(0,np.zeros(128));assert g.inspect(m,0)=='allow';g.close();g=DurableGuard(p)
    assert g.inspect(m,.1)=='reject_replay';checks['restart_replay_rejected']=True
    for i in range(1,20):assert g.inspect(sign(i,np.zeros(128)),.1)=='allow'
    g.close();g=DurableGuard(p);assert g.inspect(sign(20,np.zeros(128)),.2)=='reject_rate';checks['restart_quota_preserved']=True
    assert g.inspect(sign(21,np.zeros(128)),1.1)=='allow';checks['quota_expires']=True
    assert g.inspect(sign(22,np.zeros(128)),.5)=='reject_clock';checks['clock_rollback_rejected']=True;g.close()
    try:DurableGuard(p,initialize=True);raise AssertionError('Reset accepted')
    except FileExistsError:checks['existing_ledger_reset_refused']=True
    try:DurableGuard(root/'absent');raise AssertionError('Missing ledger accepted')
    except ValueError:checks['missing_ledger_refused']=True
    for fault,code,expected in [('before_commit',71,'allow'),('after_commit',72,'reject_replay')]:
        q=root/(fault+'.sqlite');g=DurableGuard(q,initialize=True);g.close()
        program='from durable_guard import DurableGuard\nfrom signal_guard_sim import sign\nimport sys\ng=DurableGuard(sys.argv[1]);g.inspect(sign(0,[0]*128),0,crash=sys.argv[2])'
        proc=subprocess.run([sys.executable,'-c',program,str(q),fault],check=False)
        assert proc.returncode==code
        g=DurableGuard(q);assert g.inspect(m,.1)==expected;g.close();checks[fault+'_recovery']=True
    q=root/'concurrent.sqlite';g=DurableGuard(q,initialize=True);g.close()
    program='from durable_guard import DurableGuard\nfrom signal_guard_sim import sign\nimport sys\ng=DurableGuard(sys.argv[1]);print(g.inspect(sign(0,[0]*128),0));g.close()'
    workers=[subprocess.Popen([sys.executable,'-c',program,str(q)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    outputs=[]
    for worker in workers:
        out,err=worker.communicate(timeout=20);assert worker.returncode==0,err;outputs.append(out.strip())
    assert sorted(outputs)==['allow','reject_replay'];checks['concurrent_duplicate_serialized']=True
    db=sqlite3.connect(p);db.execute("UPDATE state SET binding='altered'");db.commit();db.close()
    g=DurableGuard(p)
    try:g.inspect(sign(23,np.zeros(128)),2);raise AssertionError('Binding mismatch accepted')
    except ValueError:checks['altered_binding_refused']=True
    finally:g.close()
    bad=root/'corrupt.sqlite';bad.write_bytes(b'not a SQLite file')
    try:DurableGuard(bad);raise AssertionError('Corrupt ledger accepted')
    except sqlite3.DatabaseError:checks['corrupt_ledger_refused']=True
 return checks
if __name__=='__main__':print(json.dumps(run(),indent=2,sort_keys=True))
