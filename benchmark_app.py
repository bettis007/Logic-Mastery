"""Measure cached versus rebuilt canonical inference on this host."""
import json,time,statistics,resource,platform
from pathlib import Path
from claim_app import predict,model_bundle,m
ROOT=Path(__file__).resolve().parent

def request(n):
    data=m._make_dataset(104729,n,20260916)
    return {'examples':[{'id':f'bench-{i}','features':dict(zip(m.FEATURES,map(float,row)))} for i,row in enumerate(data.x)]}

def timing(fn,repeats):
    samples=[];value=None
    for _ in range(repeats):
        start=time.perf_counter();value=fn();samples.append((time.perf_counter()-start)*1000)
    return value,{'median_ms':statistics.median(samples),'min_ms':min(samples),'max_ms':max(samples),'samples_ms':samples}

def main():
    results=[]
    for n in (13,100,1000):
        data=request(n)
        before,cold=timing(lambda:predict(data,reuse_model=False),5)
        model_bundle.cache_clear();start=time.perf_counter();first=predict(data);initial_ms=(time.perf_counter()-start)*1000
        after,warm=timing(lambda:predict(data),9)
        assert before==first==after
        _,serialization=timing(lambda:json.dumps(after,sort_keys=True),9)
        results.append({'cases':n,'rebuild_each_request':cold,'cached_request':warm,'first_cached_request_ms':initial_ms,
                        'serialization':serialization,'identical_records':True,'median_speedup':cold['median_ms']/warm['median_ms']})
    out={'scope':'Measured local CPU wall-clock timings; synthetic inputs; not Google Cloud or Jetson performance.',
         'python':platform.python_version(),'numpy':m.np.__version__,'scikit_learn':m.sklearn.__version__,
         'machine':platform.machine(),'peak_process_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
         'note':'RSS is whole-process high-water mark on Linux; warm cache retains one model; timing samples are not independent population estimates.',
         'results':results}
    (ROOT/'results').mkdir(exist_ok=True)
    (ROOT/'results/performance.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({str(r['cases']):{'rebuild_ms':r['rebuild_each_request']['median_ms'],'cached_ms':r['cached_request']['median_ms'],'speedup':r['median_speedup']} for r in results},indent=2))

if __name__=='__main__':main()
