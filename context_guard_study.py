"""Synthetic context-assisted signal review. Context truth is not authenticated by a MAC."""
import argparse,hashlib,hmac,json
from pathlib import Path
import numpy as np
from signal_guard_sim import canonical
from refine_signal_guard import flags
KEY=b'PUBLIC-CONTEXT-FIXTURE-NOT-FOR-REAL-AUTHENTICATION'
DEV_SEED=730127;TEST_SEED=830129
KINDS=('clean','legitimate_stress','legitimate_periodic_change','weak_tone','strong_tone','off_bin_weak','dc_shift','forged_context','missing_context','signed_wrong_context')

def dataset(seed,n,kinds):
 rng=np.random.default_rng(seed);t=np.arange(128);tone=np.sin(2*np.pi*15*t/128);out={}
 for kind in kinds:
    sigma=np.full(n,.25);expected=np.full(n,.25);actual=np.full(n,.25)
    if kind=='legitimate_stress':sigma=np.where(np.arange(n)%10==0,1.7,.9);actual[:]=0;expected[:]=0
    if kind=='legitimate_periodic_change':actual[:]=.35;expected[:]=.35
    if kind in ('weak_tone','forged_context','missing_context','signed_wrong_context'):actual[:]=.35
    if kind=='strong_tone':actual[:]=3.05
    if kind in ('forged_context','signed_wrong_context'):expected[:]=.35
    x=rng.normal(size=(n,128))*sigma[:,None]+actual[:,None]*tone
    if kind=='off_bin_weak':x+=.1*np.sin(2*np.pi*15.5*t/128)
    if kind=='dc_shift':x+=.8
    rms=np.sqrt((x*x).mean(axis=1));mean=np.abs(x.mean(axis=1));energy=np.abs(np.fft.rfft(x-x.mean(axis=1,keepdims=True),axis=1))**2
    no_context=flags((rms,mean,energy.max(axis=1)/energy.sum(axis=1)),.485)
    # Known phase/bin and calibrated noise are privileged synthetic context.
    amplitude=2*(x*tone).mean(axis=1)
    score=np.maximum(np.abs(amplitude-expected)/(sigma*np.sqrt(2/128)),mean/(sigma/np.sqrt(128)))
    validity=[]
    for i in range(n):
        body={'id':f'{kind}-{i}','expected_amplitude':float(expected[i]),'noise_std':float(sigma[i]),'bin':15}
        digest=hmac.new(KEY,canonical(body),hashlib.sha256).hexdigest()
        supplied='0'*64 if kind=='forged_context' else digest
        validity.append(kind!='missing_context' and hmac.compare_digest(supplied,digest))
    out[kind]=(score,np.array(validity),no_context)
 return out

def develop():
 data=dataset(DEV_SEED,3000,KINDS[:3])
 threshold=max(float(np.quantile(s,.995,method='higher')) for s,_,_ in data.values())
 return {'scope':'Synthetic rule development, not independent context verification','development_seed':DEV_SEED,'development_n':9000,'threshold':threshold,'selection':'Maximum per-benign-slice 99.5th percentile of normalized known-phase amplitude/mean residual; no adverse examples used for tuning',
 'test_plan':{'seed':TEST_SEED,'n_per_slice':4000,'benign_false_alarm_max':.01,'weak_recall_min':.5,'strong_recall_min':.99,'forged_or_missing_context_review_min':1.0,'signed_wrong_context_recall_min':.5},
 'assumptions':['Expected phase/bin and noise scale supplied before observation','Context signer uses public simulation key','Valid context can still be wrong']}

def evaluate(config):
 data=dataset(TEST_SEED,4000,KINDS);detail={};trace={}
 for k,(score,valid,old) in data.items():
    review=(~valid)|(score>config['threshold'])
    detail[k]={'n':len(review),'without_context_flagged':int(old.sum()),'context_reviewed':int(review.sum()),'without_context_rate':float(old.mean()),'context_review_rate':float(review.mean()),'unusable_context':int((~valid).sum()),'target':'benign' if k in KINDS[:3] else 'review'}
    trace[k]=review.astype(int).tolist()
 rates={k:v['context_review_rate'] for k,v in detail.items()}
 gates={k+'_false_alarm':rates[k]<=.01 for k in KINDS[:3]}
 gates.update(weak_recall=rates['weak_tone']>=.5,strong_recall=rates['strong_tone']>=.99,forged_context_review=rates['forged_context']==1,missing_context_review=rates['missing_context']==1,signed_wrong_context_recall=rates['signed_wrong_context']>=.5)
 return {'scope':'Frozen synthetic context study; no RF measurements or external context authentication','n':40000,'test_seed':TEST_SEED,'slices':detail,'gates':gates,'overall_pass':all(gates.values()),'configuration_sha256':hashlib.sha256(canonical(config)).hexdigest(),'decision_trace_sha256':hashlib.sha256(canonical(trace)).hexdigest(),
 'note':'Missing/invalid context routes to review, not a finding of attack. Signed-wrong context is deliberately indistinguishable from authorized change given these inputs.'}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['develop','evaluate']);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.stage=='develop':
    r=develop();dest=a.config
 else:
    if a.output is None:p.error('--output required')
    r=evaluate(json.loads(a.config.read_text()));dest=a.output
 with dest.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(r,indent=2))
