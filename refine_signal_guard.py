"""Development-only threshold selection and frozen synthetic holdout comparison."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from signal_guard_sim import canonical
DEV_SEED=610201;TEST_SEED=910301
KINDS=('clean','legitimate_stress','strong_tone','weak_tone','off_bin_weak','dc_shift','legitimate_periodic_change')

def features(seed,n,kinds):
 rng=np.random.default_rng(seed);t=np.arange(128);base=np.sin(2*np.pi*15*t/128);out={}
 for k in kinds:
    x=rng.normal(0,.25,(n,128))+.25*base
    if k=='legitimate_stress':
        std=np.where(np.arange(n)%10==0,1.7,.9);x=rng.normal(size=(n,128))*std[:,None]
    elif k=='strong_tone':x+=2.8*base
    elif k in ('weak_tone','legitimate_periodic_change'):x+=.1*base
    elif k=='off_bin_weak':x+=.1*np.sin(2*np.pi*15.5*t/128)
    elif k=='dc_shift':x+=.8
    rms=np.sqrt(np.mean(x*x,axis=1));mean=np.abs(x.mean(axis=1));energy=np.abs(np.fft.rfft(x-x.mean(axis=1,keepdims=True),axis=1))**2
    out[k]=(rms,mean,energy.max(axis=1)/energy.sum(axis=1))
 return out

def flags(f,threshold,baseline=False):
 rms,mean,peak=f
 return (peak>threshold)|(mean>.5)|((rms>1.5) if baseline else False)

def develop():
 data=features(DEV_SEED,2000,KINDS[:4]);candidates=[]
 for threshold in np.linspace(.3,.7,81):
    rates={k:float(flags(f,threshold).mean()) for k,f in data.items()}
    if rates['clean']<=.01 and rates['legitimate_stress']<=.01:
        candidates.append((rates['weak_tone'],float(threshold),rates))
 if not candidates:raise ValueError('No candidate meets development false-alarm bounds')
 best=max(candidates,key=lambda x:(x[0],x[1]))
 return {'scope':'Synthetic development-selected spectral/mean review rule; no automatic blocking','development_seed':DEV_SEED,'development_n_per_slice':2000,'spectral_threshold':best[1],'mean_limit':.5,'rms_rule_removed':True,'development_rates':best[2],
 'test_plan':{'seed':TEST_SEED,'n_per_slice':4000,'core_benign_false_alarm_max':.01,'strong_recall_min':.99,'weak_recall_min':.5,'expanded_benign_false_alarm_max':.01,'baseline_spectral_threshold':.6},
 'selection':'Maximum weak-tone recall subject to <=1% false alarms in each clean/stress development slice; ties choose higher threshold. Test seed unused until configuration is written.'}

def evaluate(config):
 data=features(TEST_SEED,4000,KINDS);out={};traces={}
 for name,threshold,baseline in [('baseline',.6,True),('refined',config['spectral_threshold'],False)]:
    detail={};traces[name]={};tp=fp=fn=tn=0
    for k,f in data.items():
        v=flags(f,threshold,baseline);count=int(v.sum());benign=k in ('clean','legitimate_stress','legitimate_periodic_change')
        detail[k]={'n':len(v),'flagged':count,'flag_rate':count/len(v),'target':'benign' if benign else 'injected_anomaly'};traces[name][k]=v.astype(int).tolist()
        if benign:fp+=count;tn+=len(v)-count
        else:tp+=count;fn+=len(v)-count
    rates={k:v['flag_rate'] for k,v in detail.items()}
    gates={'core_clean_false_alarm':rates['clean']<=.01,'core_stress_false_alarm':rates['legitimate_stress']<=.01,'strong_recall':rates['strong_tone']>=.99,'weak_recall':rates['weak_tone']>=.5,'expanded_periodic_false_alarm':rates['legitimate_periodic_change']<=.01}
    out[name]={'slices':detail,'gates':gates,'overall_gate_pass':all(gates.values()),'confusion':{'tp':tp,'fp':fp,'fn':fn,'tn':tn},'accuracy':(tp+tn)/(tp+fp+fn+tn),'precision':tp/(tp+fp),'recall':tp/(tp+fn),'benign_false_alarm_rate':fp/(fp+tn)}
 return {'scope':'Synthetic heldout waveform review only; not external data or message authentication','test_seed':TEST_SEED,'n_per_variant':28000,'configuration_sha256':hashlib.sha256(canonical(config)).hexdigest(),'variants':out,'decision_trace_sha256':hashlib.sha256(canonical(traces)).hexdigest(),'limitations':['Same generator family with different seeds, not independent external validation','Legitimate periodic changes and weak injected tones deliberately overlap in distribution','No RF sensing or physical frequency attribution','No test-label tuning; failed gates are reported']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['develop','evaluate']);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.stage=='develop':
    result=develop()
    with a.config.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 else:
    if a.output is None:p.error('--output required for evaluate')
    result=evaluate(json.loads(a.config.read_text()))
    with a.output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(result,indent=2))
