"""Synthetic software signal/message guard. No device, RF, biological or network access."""
import argparse,hashlib,hmac,json,math,platform,time
from collections import Counter,deque
from pathlib import Path
import numpy as np

# Public fixture key only. Never use for deployment or real authentication.
FIXTURE_KEY=b'PUBLIC-NONSECRET-SIMULATION-FIXTURE-ONLY'
CONFIG={'sample_count':128,'max_bytes':16384,'requests_per_second':20,'rms_limit':1.5,'mean_limit':0.5,'spectral_fraction_limit':0.6}

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sign(seq,samples):
    payload={'sender':'fixture','seq':seq,'samples':list(map(float,samples))}
    return {'payload':payload,'mac':hmac.new(FIXTURE_KEY,canonical(payload),hashlib.sha256).hexdigest()}

class Guard:
    def __init__(self):self.last=-1;self.arrivals=deque();self.last_time=-math.inf
    def inspect(self,message,now):
        try:
            if len(canonical(message))>CONFIG['max_bytes']:return 'reject_size'
            if set(message)!={'payload','mac'}:return 'reject_schema'
            p=message['payload']
            if set(p)!={'sender','seq','samples'} or p['sender']!='fixture':return 'reject_schema'
            if type(p['seq']) is not int or p['seq']<0:return 'reject_schema'
            if not isinstance(message['mac'],str) or not hmac.compare_digest(message['mac'],hmac.new(FIXTURE_KEY,canonical(p),hashlib.sha256).hexdigest()):return 'reject_authentication'
            if not isinstance(p['samples'],list) or len(p['samples'])!=CONFIG['sample_count']:return 'reject_schema'
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in p['samples']):return 'reject_schema'
            if not math.isfinite(now) or now<self.last_time:return 'reject_clock'
            self.last_time=now
            if p['seq']<=self.last:return 'reject_replay'
            self.last=p['seq']
            while self.arrivals and self.arrivals[0]<=now-1:self.arrivals.popleft()
            if len(self.arrivals)>=CONFIG['requests_per_second']:return 'reject_rate'
            self.arrivals.append(now)
            x=np.asarray(p['samples'],dtype=float)
            with np.errstate(over='ignore',invalid='ignore'):
                rms=float(np.sqrt(np.mean(x*x)));mean=float(abs(x.mean()))
                energy=np.abs(np.fft.rfft(x-x.mean()))**2
                fraction=float(energy.max()/energy.sum()) if energy.sum()>0 else 0.0
            if not all(map(math.isfinite,(rms,mean,fraction))):return 'reject_numeric'
            if rms>CONFIG['rms_limit'] or mean>CONFIG['mean_limit'] or fraction>CONFIG['spectral_fraction_limit']:return 'review_signal'
            return 'allow'
        except (ValueError,TypeError,KeyError,OverflowError):return 'reject_schema'

def run(seed=20260914):
    rng=np.random.default_rng(seed);tone=np.sin(2*np.pi*15*np.arange(128)/128)
    rows=[];latencies=[]
    counts={'clean':2000,'legitimate_stress':1000,'modified_payload':1000,'replay':1000,'oversize':500,'overflow_burst':500,'strong_tone':1000,'weak_tone':1000,'validly_signed_false_content':1000}
    for kind,n in counts.items():
        g=Guard()
        if kind=='overflow_burst':
            for seq in range(20):assert g.inspect(sign(seq,np.zeros(128)),seq*.001)=='allow'
        for i in range(n):
            x=rng.normal(0,.25,128)+.25*tone
            if kind=='legitimate_stress':x=rng.normal(0,1.7 if i%10==0 else .9,128)
            elif kind=='strong_tone':x=x+2.8*tone
            elif kind=='weak_tone':x=x+.10*tone
            seq=i+20 if kind=='overflow_burst' else i
            msg=sign(seq,x);now=i*2.0
            if kind=='modified_payload':msg['payload']['samples'][0]+=1
            elif kind=='oversize':msg['payload']['samples']=[0.0]*10000
            elif kind=='replay':
                assert g.inspect(msg,now)=='allow'
                now+=.1
            elif kind=='overflow_burst':now=.1+i*.001
            # False content has no waveform signature and a valid fixture MAC.
            t=time.perf_counter_ns();out=g.inspect(msg,now);latencies.append(time.perf_counter_ns()-t)
            rows.append({'slice':kind,'index':i,'outcome':out,'target':'allow' if kind in ('clean','legitimate_stress') else 'flag'})
    slices={}
    for kind in counts:
        r=[x for x in rows if x['slice']==kind];flag=sum(x['outcome']!='allow' for x in r)
        slices[kind]={'n':len(r),'flagged':flag,'allowed':len(r)-flag,'flag_rate':flag/len(r),'outcomes':dict(Counter(x['outcome'] for x in r))}
    tp=sum(r['target']=='flag' and r['outcome']!='allow' for r in rows);fp=sum(r['target']=='allow' and r['outcome']!='allow' for r in rows)
    fn=sum(r['target']=='flag' and r['outcome']=='allow' for r in rows);tn=len(rows)-tp-fp-fn
    summary={'scope':'Synthetic software-message and numeric-waveform experiment only','seed':seed,'config':CONFIG,'n':len(rows),'slices':slices,
        'confusion':{'tp':tp,'fp':fp,'fn':fn,'tn':tn},'accuracy':(tp+tn)/len(rows),'flag_precision':tp/(tp+fp),'flag_recall':tp/(tp+fn),'benign_false_alarm_rate':fp/(fp+tn),
        'decision_trace_sha256':hashlib.sha256(canonical(rows)).hexdigest(),
        'excluded_setup_events':1020,
        'limitations':['Public fixture key; no real authentication deployment','Review flags are anomalies, not attack attribution','Signal classes and sample mix are artificial','No encryption or protection against authenticated data theft','No biological model or RF measurements','State is process-local; restart/reordering recovery untested']}
    timing={'python':platform.python_version(),'numpy':np.__version__,'machine':platform.machine(),'median_us':float(np.median(latencies)/1000),'p95_us':float(np.percentile(latencies,95)/1000),'includes':'inspection only; excludes signing, generation and setup; one measured process'}
    return summary,timing

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    summary,timing=run()
    result={'deterministic':summary,'timing':timing,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with a.output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(summary,indent=2))
