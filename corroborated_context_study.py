"""Two simulated attestations plus residual-spectrum review; no real witnesses."""
import argparse,hashlib,hmac,json,math,re
from pathlib import Path
import numpy as np
from signal_guard_sim import canonical
KEYS={'producer':b'PUBLIC-PRODUCER-CONTEXT-FIXTURE-KEY','registry':b'PUBLIC-REGISTRY-CONTEXT-FIXTURE-KEY'}
DEV_SEED=2026091501;TEST_SEED=2026091502
KINDS=('clean','stress','periodic','weak','off_bin','strong','producer_wrong','both_wrong','stale_registry','missing_registry','bad_signature','wrong_example_binding')

def attest(role,body):return {'body':body,'mac':hmac.new(KEYS[role],canonical(body),hashlib.sha256).hexdigest()}
def finite_number(value):
    if type(value) not in (int,float):return False
    try:return math.isfinite(value)
    except OverflowError:return False

def check_context(a,b,example,now):
    # Fixed-schema fixture boundary: malformed declarations request review.
    fields={'id','expected_amplitude','noise_std','bin','issued_at','expires_at'}
    if not isinstance(example,str) or not 0<len(example)<=200 or not finite_number(now) or now<0:return False
    for role,obj in [('producer',a),('registry',b)]:
        if not isinstance(obj,dict) or set(obj)!={'body','mac'}:return False
        body=obj['body'];mac=obj['mac']
        if not isinstance(body,dict) or set(body)!=fields:return False
        if not isinstance(mac,str) or re.fullmatch(r'[0-9a-f]{64}',mac) is None:return False
        if body['id']!=example or type(body['bin']) is not int or body['bin']!=15:return False
        for name in ('expected_amplitude','noise_std','issued_at','expires_at'):
            if not finite_number(body[name]):return False
        if body['noise_std']<=0 or body['issued_at']<0 or not body['issued_at']<=now<=body['expires_at']:return False
        if body['expires_at']-body['issued_at']>300:return False
        expected=hmac.new(KEYS[role],canonical(body),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,mac):return False
    return a['body']==b['body']

def dataset(seed,n,kinds):
    rng=np.random.default_rng(seed);tone=np.sin(2*np.pi*15*np.arange(128)/128);out={}
    for kind in kinds:
        sigma=np.full(n,.25);expected=np.full(n,.25);actual=np.full(n,.25)
        if kind=='stress':sigma=np.where(np.arange(n)%10==0,1.7,.9);expected[:]=0;actual[:]=0
        if kind=='periodic':expected[:]=.35;actual[:]=.35
        if kind in ('weak','producer_wrong','both_wrong','stale_registry','missing_registry','bad_signature','wrong_example_binding'):actual[:]=.35
        if kind=='strong':actual[:]=3.05
        declared=expected.copy()
        if kind in ('producer_wrong','both_wrong'):declared[:]=.35
        registry=expected.copy()
        if kind=='both_wrong':registry[:]=.35
        # Operational metadata is constructed before sample generation.
        valid=[]
        for i in range(n):
            identifier=f'{kind}-{i}';base={'id':identifier,'expected_amplitude':float(declared[i]),'noise_std':float(sigma[i]),'bin':15,'issued_at':0,'expires_at':10}
            other={**base,'expected_amplitude':float(registry[i])}
            if kind=='stale_registry':other['expires_at']=.5
            if kind=='wrong_example_binding':other['id']='different-example'
            a=attest('producer',base);b=attest('registry',other)
            if kind=='bad_signature':a['mac']='0'*64
            if kind=='missing_registry':b=None
            valid.append(check_context(a,b,identifier,1))
        x=rng.normal(size=(n,128))*sigma[:,None]+actual[:,None]*tone
        if kind=='off_bin':x+=.1*np.sin(2*np.pi*15.5*np.arange(128)/128)
        residual=x-declared[:,None]*tone
        known=np.abs(2*(residual*tone).mean(axis=1))/(sigma*np.sqrt(2/128))
        mean=np.abs(residual.mean(axis=1))/(sigma/np.sqrt(128))
        energy=np.abs(np.fft.rfft(residual-residual.mean(axis=1,keepdims=True),axis=1))**2
        spectrum=energy[:,1:-1].max(axis=1)/(128*sigma*sigma)
        out[kind]=(np.maximum(known,mean),spectrum,np.asarray(valid))
    return out

def develop():
    d=dataset(DEV_SEED,4000,KINDS[:3]);threshold=max(float(np.quantile(s,.9975,method='higher')) for _,s,_ in d.values())
    return {'development_seed':DEV_SEED,'known_threshold':3.1766241653501774,'spectrum_threshold':threshold,'selection':'Maximum per-benign-slice residual-spectrum 99.75th percentile; previous known-component threshold unchanged','test_seed':TEST_SEED,'test_n_per_slice':4000,'gates':{'benign_false_alarm_max':.01,'weak_recall_min':.5,'off_bin_recall_min':.5,'strong_recall_min':.99,'invalid_context_review_min':1.0,'both_wrong_recall_min':.5}}

def evaluate(config):
    d=dataset(TEST_SEED,4000,KINDS);result={};trace={}
    for k,(known,spectrum,valid) in d.items():
        narrow=(~valid)|(known>config['known_threshold']);broad=narrow|(spectrum>config['spectrum_threshold'])
        result[k]={'n':len(broad),'context_failures':int((~valid).sum()),'narrow_review_rate':float(narrow.mean()),'broad_review_rate':float(broad.mean()),'broad_reviewed':int(broad.sum())};trace[k]=broad.astype(int).tolist()
    gates={k+'_false_alarm':result[k]['broad_review_rate']<=.01 for k in KINDS[:3]}
    gates.update({k+'_recall':result[k]['broad_review_rate']>=limit for k,limit in [('weak',.5),('off_bin',.5),('strong',.99),('both_wrong',.5)]})
    gates.update({k+'_review':result[k]['broad_review_rate']==1 for k in ('producer_wrong','stale_registry','missing_registry','bad_signature','wrong_example_binding')})
    return {'scope':'Synthetic two-source agreement and residual-spectrum experiment, not independently verified context','n':48000,'seed':TEST_SEED,'slices':result,'gates':gates,'overall_pass':all(gates.values()),'config_sha256':hashlib.sha256(canonical(config)).hexdigest(),'trace_sha256':hashlib.sha256(canonical(trace)).hexdigest(),'limitations':['Both agreeing sources can be wrong','Fixture keys are public; no real sender or witness authentication','Residual spectral check omits Nyquist; no physical sampling model','Missing context review is not attack attribution']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['develop','evaluate']);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.stage=='develop':r=develop();dest=a.config
    else:
        if a.output is None:p.error('--output required')
        r=evaluate(json.loads(a.config.read_text()));dest=a.output
    with dest.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(r,indent=2))
