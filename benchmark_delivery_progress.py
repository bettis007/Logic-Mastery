"""Compare bounded queue progress with a pinned pre-refinement implementation."""
import hashlib,importlib.util,json,secrets,subprocess,tempfile
from pathlib import Path
from signal_guard_sim import sign
import transactional_delivery as current
BASELINE='4fd6b21e9a69ef3b5cd4d66a93f1a87aa3af6ebb'

def workload(module,root,key):
    queue=root/'queue.sqlite';sink=root/'sink.sqlite'
    guard=module.DeliveryGuard(queue,key,initialize=True);module.initialize_sink(sink)
    try:
        for seq in range(256):guard.inspect(sign(seq,[0]*128),seq*2)
        for now in (0,1,3):assert module.deliver_one(guard,sink,now,fail=True)=='retry_scheduled'
        for tick in range(264):module.deliver_one(guard,sink,7+tick)
        return dict(guard.db.execute('SELECT status,count(*) FROM outbox GROUP BY status'))
    finally:guard.close()

def run():
    source=subprocess.check_output(['git','show',BASELINE+':transactional_delivery.py'])
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);path=root/'baseline.py';path.write_bytes(source)
        spec=importlib.util.spec_from_file_location('baseline_delivery_progress',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        key=secrets.token_bytes(32);a=root/'before';a.mkdir();b=root/'after';b.mkdir()
        before=workload(old,a,key);after=workload(current,b,key)
    assert before=={'exhausted':1,'pending':255}
    assert after=={'delivered':255,'exhausted':1}
    return {'scope':'Synthetic bounded progress workload, not a throughput or latency benchmark','baseline_commit':BASELINE,'baseline_source_sha256':hashlib.sha256(source).hexdigest(),'queued':256,'simulated_initial_failures':3,'subsequent_worker_calls':264,'baseline':before,'refined':after,'records_deleted':False}
if __name__=='__main__':print(json.dumps(run(),indent=2,sort_keys=True))
