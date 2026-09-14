"""Offline feature-based claim triage. Prediction never opens the labels file."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import argparse,json,hashlib
from functools import lru_cache
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from decision_reporting import decisions, frozen as m
ROOT=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

@lru_cache(maxsize=1)
def model_bundle():
    seed=m.SEEDS[0];build=m._make_dataset(seed,4200,11);cal=m._make_dataset(seed,1600,23);sel=m._make_dataset(seed,1800,47)
    clf=LogisticRegression(max_iter=1200,solver='lbfgs',class_weight='balanced',random_state=seed,C=1.0).fit(build.x,build.y)
    temp,_=m._fit_temperature(clf.predict_proba(cal.x),cal.y)
    policy=m._select_policy(m._temperature_scale(clf.predict_proba(sel.x),temp),sel.x,sel.y)
    return clf,temp,policy

def predict(request, reuse_model=True):
    if not isinstance(request,dict) or set(request)!={'examples'} or not isinstance(request['examples'],list) or not request['examples']:
        raise ValueError('Input must contain only a nonempty examples list; no labels.')
    ids=[]; features=[]
    for e in request['examples']:
        if not isinstance(e,dict) or set(e)!={'id','features'} or not isinstance(e['id'],str) or not e['id'] or len(e['id'])>200:
            raise ValueError('Each example requires only a nonempty string id and features.')
        if not isinstance(e['features'],dict) or set(e['features'])!=set(m.FEATURES):raise ValueError('Feature names must match the frozen schema exactly.')
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in e['features'].values()):
            raise ValueError('Features must be numeric, not strings or booleans.')
        ids.append(e['id']);features.append([e['features'][k] for k in m.FEATURES])
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate example IDs.')
    x=np.asarray(features,dtype=float)
    if not np.all(np.isfinite(x)) or np.any((x<0)|(x>1)):raise ValueError('Features must be finite and in [0,1].')
    # Reconstruct the frozen canonical classifier; never fit on user examples.
    seed=m.SEEDS[0]
    clf,temp,policy=model_bundle() if reuse_model else model_bundle.__wrapped__()
    records=decisions(m._temperature_scale(clf.predict_proba(x),temp),x,policy['minimum_confidence'],policy['accept_evidence_gate'])
    return {'schema_version':'1.0','scope':'Feature-based inference; no automatic source verification or text understanding.',
        'model_seed':seed,'temperature':temp,'policy':dict(policy),'reference_source_sha256':digest(ROOT/'originals/pure_intelligence_logic_mastery.py'),
        'training_examples':'Original synthetic BUILD; CAL and SELECT only. User examples are inference-only.',
        'records':[{'id':i,**r} for i,r in zip(ids,records)]}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    result=predict(json.loads(args.input.read_text()));result['input_sha256']=digest(args.input)
    # Exclusive creation prevents overwriting an earlier prediction receipt.
    with args.output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
