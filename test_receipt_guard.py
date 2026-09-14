"""Disposable ledgers and ephemeral receipt keys; no key is written to results."""
import json,secrets,sqlite3,subprocess,sys,tempfile
from pathlib import Path
from receipt_guard import ReceiptGuard
from signal_guard_sim import sign

def run():
 checks={};key=secrets.token_bytes(32);message=sign(0,[0]*128)
 with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);p=root/'normal.sqlite';g=ReceiptGuard(p,key,initialize=True)
    first=g.inspect(message,0);again=g.inspect(message,.1)
    assert first['receipt']==again['receipt'] and first['mac']==again['mac'] and again['recovered'];checks['duplicate_returns_original_receipt']=True
    assert g.db.execute('SELECT count(*) FROM receipts').fetchone()[0]==1;checks['duplicate_does_not_add_receipt']=True;g.close()
    g=ReceiptGuard(p,key);assert g.inspect(message,1)['receipt']==first['receipt'];checks['restart_recovers_receipt']=True
    changed=sign(0,[.01]*128);assert g.inspect(changed,1)['reason']=='sequence_conflict';checks['sequence_payload_conflict_rejected']=True
    changed=sign(0,[0]*128);changed['payload']['samples'][0]=1
    assert g.inspect(changed,1)['reason']=='reject_authentication';checks['invalid_message_cannot_recover_receipt']=True
    for seq in range(1,20):assert g.inspect(sign(seq,[0]*128),.1)['receipt']['outcome']=='allow'
    limited=g.inspect(sign(20,[0]*128),.2);assert limited['receipt']['outcome']=='reject_rate'
    assert g.inspect(sign(20,[0]*128),2)['receipt']==limited['receipt'];checks['rate_rejection_receipt_is_stable']=True
    g.close()
    try:ReceiptGuard(p,secrets.token_bytes(32));raise AssertionError('Wrong key accepted')
    except ValueError:checks['wrong_receipt_key_rejected']=True
    for fault,code,recovered in [('before_commit',71,False),('after_commit',72,True)]:
        q=root/(fault+'.sqlite');g=ReceiptGuard(q,key,initialize=True);g.close()
        program='import sys\nfrom receipt_guard import ReceiptGuard\nfrom signal_guard_sim import sign\ng=ReceiptGuard(sys.argv[1],bytes.fromhex(sys.stdin.read()));g.inspect(sign(0,[0]*128),0,crash=sys.argv[2])'
        child=subprocess.run([sys.executable,'-c',program,str(q),fault],input=key.hex(),text=True,capture_output=True)
        assert child.returncode==code
        g=ReceiptGuard(q,key);receipt=g.inspect(message,1);assert receipt['recovered']==recovered
        assert receipt['receipt']['recorded_at']==(0 if recovered else 1)
        assert g.db.execute('SELECT count(*) FROM receipts').fetchone()[0]==1;g.close();checks[fault+'_atomic_recovery']=True
    q=root/'concurrent.sqlite';g=ReceiptGuard(q,key,initialize=True);g.close()
    program='import sys,json\nfrom receipt_guard import ReceiptGuard\nfrom signal_guard_sim import sign\ng=ReceiptGuard(sys.argv[1],bytes.fromhex(sys.stdin.read()));print(json.dumps(g.inspect(sign(0,[0]*128),0)));g.close()'
    workers=[subprocess.Popen([sys.executable,'-c',program,str(q)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    for worker in workers:worker.stdin.write(key.hex());worker.stdin.close();worker.stdin=None
    results=[]
    for worker in workers:
        out,err=worker.communicate(timeout=20);assert worker.returncode==0,err;results.append(json.loads(out))
    assert results[0]['receipt']==results[1]['receipt'] and results[0]['mac']==results[1]['mac']
    assert sorted(r['recovered'] for r in results)==[False,True];checks['concurrent_duplicate_same_receipt']=True
    db=sqlite3.connect(p);db.execute("UPDATE receipts SET body='{}' WHERE seq=0");db.commit();db.close();g=ReceiptGuard(p,key)
    try:g.inspect(message,3);raise AssertionError('Altered receipt accepted')
    except ValueError:checks['altered_receipt_rejected']=True
    finally:g.close()
    db=sqlite3.connect(p);db.execute("UPDATE state SET body='{}'");db.commit();db.close()
    try:ReceiptGuard(p,key);raise AssertionError('Altered state accepted')
    except ValueError:checks['altered_state_rejected']=True
 return checks
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
