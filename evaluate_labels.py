"""Score frozen prediction receipts against a separately supplied label file.

Provenance declarations are recorded, not authenticated. No external validation
claim follows merely from a supplied dataset_kind or annotation_author field.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
LABELS=('ACCEPT','QUALIFY','SIMULATED','NARRATIVE','QUARANTINE')

def unique(rows):
    ids=[r['id'] for r in rows]
    if not all(isinstance(i,str) and i for i in ids) or len(ids)!=len(set(ids)):raise ValueError('Invalid or duplicate IDs.')
    return {r['id']:r for r in rows}

def score(predictions, labels):
    meta=labels['provenance']
    for k in ('dataset_kind','annotation_author','annotation_protocol','label_target'):
        if not isinstance(meta.get(k),str) or not meta[k].strip():raise ValueError('Missing provenance: '+k)
    if meta['label_target']!='epistemic_category':raise ValueError('Use separate action-appropriateness evaluation; do not mix target definitions.')
    p=unique(predictions['records']);y=unique(labels['labels'])
    if not y or set(p)!=set(y):raise ValueError('Prediction and label IDs must match exactly and be nonempty.')
    truth=[];pred=[];conf=[];families={}
    for i in sorted(y):
        row=y[i]
        if row['expected'] not in LABELS or p[i]['final_policy_label'] not in LABELS:raise ValueError('Unknown category.')
        if not isinstance(row.get('source_family'),str) or not row['source_family']:raise ValueError('Missing source family.')
        probability=p[i]['classifier_probability_for_final_label']
        if isinstance(probability,bool) or not isinstance(probability,(int,float)):
            raise ValueError('Probabilities must be JSON numbers, not strings or booleans.')
        truth.append(row['expected']);pred.append(p[i]['final_policy_label']);conf.append(probability)
        families.setdefault(row['source_family'],[]).append(len(truth)-1)
    truth=np.asarray(truth);pred=np.asarray(pred);conf=np.asarray(conf,dtype=float)
    if not np.all(np.isfinite(conf)) or np.any((conf<0)|(conf>1)):raise ValueError('Invalid probabilities.')
    correct=truth==pred;ece=0.0;bins=[]
    for i in range(15):
        mask=(conf>=i/15)&((conf<(i+1)/15) if i<14 else (conf<=1))
        if mask.any():
            gap=abs(float(correct[mask].mean()-conf[mask].mean()));ece+=float(mask.mean())*gap
            bins.append({'bin':i,'n':int(mask.sum()),'accuracy':float(correct[mask].mean()),'mean_probability':float(conf[mask].mean())})
    def rate(category):
        mask=truth==category
        return float(np.mean(pred[mask]=='ACCEPT')) if mask.any() else None
    return {'scope':'Evaluation of supplied labeled feature examples; external provenance is user-declared and unverified.',
        'provenance_declaration':meta,'independent_provenance_verified':False,'n':len(truth),
        'accuracy':float(accuracy_score(truth,pred)),
        'macro_f1_fixed_five_classes':float(f1_score(truth,pred,labels=LABELS,average='macro',zero_division=0)),
        'class_support':{k:int((truth==k).sum()) for k in LABELS},
        'false_factual_promotion_all_examples':float(np.mean((truth!='ACCEPT')&(pred=='ACCEPT'))),
        'simulation_to_fact':rate('SIMULATED'),'narrative_to_fact':rate('NARRATIVE'),
        'final_label_probability_binary_brier':float(np.mean((conf-correct)**2)),
        'final_label_probability_ece_15':ece,'bins':bins,
        'confusion_matrix':confusion_matrix(truth,pred,labels=LABELS).tolist(),'label_order':list(LABELS),
        'source_family_accuracy':{k:float(correct[v].mean()) for k,v in families.items()},
        'complete_class_coverage':all((truth==k).any() for k in LABELS),
        'warning':'No production certification. Repeated or templated examples do not establish statistical independence.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('predictions',type=Path);parser.add_argument('labels',type=Path);parser.add_argument('output',type=Path);a=parser.parse_args()
    result=score(json.loads(a.predictions.read_text()),json.loads(a.labels.read_text()))
    result['prediction_receipt_sha256']=hashlib.sha256(a.predictions.read_bytes()).hexdigest();result['labels_sha256']=hashlib.sha256(a.labels.read_bytes()).hexdigest()
    with a.output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
