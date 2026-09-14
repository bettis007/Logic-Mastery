"""Test the local HTTP boundary with synthetic fixtures."""
import json,threading,urllib.request,urllib.error
from pathlib import Path
from server import make_server
server=make_server(0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
url=f'http://127.0.0.1:{server.server_port}'
def call(path,body=None,headers=None):
    hdr={'Content-Type':'application/json',**(headers or {})}
    request=urllib.request.Request(url+path,data=json.dumps(body).encode() if body is not None else None,headers=hdr)
    try:
        with urllib.request.urlopen(request,timeout=20) as r:return r.status,r.read()
    except urllib.error.HTTPError as e:return e.code,e.read()
checks={}
try:
    code,body=call('/');assert code==200 and b'Decision ledger'.lower() in body.lower();checks['page_served']=True
    assert call('/originals/frozen_2026-09-03.json')[0]==404;checks['only_allowlisted_assets']=True
    assert call('/',headers={'Host':'untrusted.example'})[0]==403;checks['host_rejected']=True
    token=json.loads(call('/api/session')[1])['token'];headers={'X-Session-Token':token}
    demo=json.loads(call('/api/demo')[1]);labels=json.loads(call('/api/demo-labels')[1])
    assert call('/api/predict',demo)[0]==403;checks['token_required']=True
    assert call('/api/predict',demo,{**headers,'Origin':'https://untrusted.example'})[0]==403;checks['cross_origin_rejected']=True
    code,body=call('/api/predict',demo,headers);assert code==200;pred=json.loads(body);assert len(pred['records'])==13;checks['prediction_succeeds']=True
    code,body=call('/api/evaluate',{'predictions':pred,'labels':labels},headers);assert code==200 and json.loads(body)['accuracy']==1;checks['separate_evaluation_succeeds']=True
    assert call('/api/predict',{'examples':[demo['examples'][0]]*1001},headers)[0]==413;checks['batch_bound_enforced']=True
    assert call('/api/predict',{'examples':[None]},headers)[0]==400;checks['invalid_shape_rejected']=True
    bad={**demo,'labels':labels};assert call('/api/predict',bad,headers)[0]==400;checks['labels_not_passed_to_prediction']=True
finally:
    server.shutdown();server.server_close();thread.join()
Path('results').mkdir(exist_ok=True);Path('results/server_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
