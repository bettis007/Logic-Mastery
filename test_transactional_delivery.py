import json,secrets,sqlite3,subprocess,sys,tempfile
from pathlib import Path
from transactional_delivery import DeliveryGuard,initialize_sink,deliver_one
from signal_guard_sim import sign

def run():
 key=secrets.token_bytes(32);checks={}
 with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    def setup(name):
        p=root/(name+'.sqlite');s=root/(name+'-sink.sqlite');g=DeliveryGuard(p,key,initialize=True);initialize_sink(s);return p,s,g
    p,s,g=setup('normal');m=sign(0,[0]*128);g.inspect(m,0);g.inspect(m,.1)
    assert g.db.execute('SELECT count(*) FROM outbox').fetchone()[0]==1;checks['duplicate_queues_once']=True
    assert deliver_one(g,s,0)=='delivered';assert deliver_one(g,s,1)=='empty';checks['delivery_once']=True
    g.inspect(sign(1,[10]*128),2);assert g.db.execute('SELECT count(*) FROM outbox').fetchone()[0]==1;checks['review_does_not_queue_effect']=True;g.close()
    p,s,g=setup('retry');g.inspect(m,0)
    assert deliver_one(g,s,0,fail=True)=='retry_scheduled'
    assert deliver_one(g,s,.5,fail=True)=='deferred';g.close();g=DeliveryGuard(p,key)
    assert deliver_one(g,s,1,fail=True)=='retry_scheduled';assert deliver_one(g,s,3,fail=True)=='retry_scheduled'
    assert deliver_one(g,s,7)=='exhausted';assert g.db.execute('SELECT attempts FROM outbox').fetchone()[0]==3;checks['persistent_bounded_retries']=True;g.close()
    p,s,g=setup('transient');g.inspect(m,0);deliver_one(g,s,0,fail=True)
    assert deliver_one(g,s,1)=='delivered';checks['transient_failure_recovers']=True;g.close()
    program='import sys\nfrom transactional_delivery import DeliveryGuard,deliver_one\nfrom signal_guard_sim import sign\ng=DeliveryGuard(sys.argv[1],bytes.fromhex(sys.stdin.read()))\nif sys.argv[3]=="sink":deliver_one(g,sys.argv[2],0,crash="after_sink_commit")\nelse:g.inspect(sign(0,[0]*128),0,crash=sys.argv[3])'
    for fault,code in [('before_commit',71),('after_commit',72),('sink',72)]:
        p,s,g=setup(fault)
        if fault=='sink':g.inspect(m,0)
        g.close();r=subprocess.run([sys.executable,'-c',program,str(p),str(s),fault],input=key.hex(),text=True,capture_output=True);assert r.returncode==code
        g=DeliveryGuard(p,key)
        if fault=='before_commit':assert g.db.execute('SELECT count(*) FROM outbox').fetchone()[0]==0;g.inspect(m,1)
        if fault=='after_commit':assert g.db.execute('SELECT count(*) FROM outbox').fetchone()[0]==1
        outcome=deliver_one(g,s,2);assert outcome==('reconciled' if fault=='sink' else 'delivered')
        db=sqlite3.connect(s);assert db.execute('SELECT count(*) FROM effects').fetchone()[0]==1;db.close();g.close();checks[fault+'_crash_recovery']=True
    p,s,g=setup('altered');g.inspect(m,0);g.db.execute("UPDATE receipts SET body='{}'")
    try:deliver_one(g,s,0);raise AssertionError('Altered receipt delivered')
    except ValueError:checks['altered_receipt_blocks_delivery']=True
    finally:g.close()
 return checks
if __name__=='__main__':print(json.dumps(run(),indent=2,sort_keys=True))
