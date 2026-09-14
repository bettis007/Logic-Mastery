"""Explicit confidence reporting around the unchanged frozen decision policy.

No field is named final_confidence: classifier support and policy action are
different quantities. No post-policy correctness calibrator is claimed.
"""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent/'originals'))
import pure_intelligence_logic_mastery as frozen

def decisions(probabilities, features, minimum_confidence, accept_evidence_gate):
    p=np.asarray(probabilities,dtype=float)
    x=np.asarray(features,dtype=float)
    if p.ndim!=2 or p.shape[1]!=len(frozen.LABELS):
        raise ValueError('probabilities must have five columns in frozen LABELS order')
    if x.shape!=(len(p),len(frozen.FEATURES)):
        raise ValueError('features must match probability rows and frozen FEATURES order')
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(x)):
        raise ValueError('nonfinite inputs are invalid')
    if np.any((p<0)|(p>1)) or np.any((x<0)|(x>1)):
        raise ValueError('probabilities and features must lie in [0,1]')
    if not np.allclose(p.sum(axis=1),1.0,rtol=0,atol=1e-10):
        raise ValueError('probability rows must sum to one')
    if not all(np.isfinite(t) and 0<=t<=1 for t in (minimum_confidence,accept_evidence_gate)):
        raise ValueError('policy thresholds must be finite values in [0,1]')
    if not len(p):
        return []
    final=frozen._apply_logic_gates(p,x,minimum_confidence,accept_evidence_gate)
    top=np.argmax(p,axis=1)
    return [{
        'schema_version':'2.1.0',
        'evidence_category':None,
        'evidence_category_status':'Not independently assessed; legacy classifier labels mix categories and actions.',
        'handling_action':{'ACCEPT':'accept_under_policy','QUALIFY':'review_with_qualification','SIMULATED':'retain_simulation_label','NARRATIVE':'retain_narrative_label','QUARANTINE':'quarantine_for_review'}[frozen.LABELS[int(final[i])]],
        'classifier_top_label':frozen.LABELS[int(top[i])],
        'classifier_top_label_probability':float(p[i,top[i]]),
        'final_policy_label':frozen.LABELS[int(final[i])],
        'classifier_probability_for_final_label':float(p[i,final[i]]),
        'policy_override':bool(final[i]!=top[i]),
        'post_policy_correctness_probability':None,
        'probability_scope':'Classifier category probabilities; not certainty that a policy action or real-world claim is correct.',
        'evidence_scope':'Supplied feature vector; not independent verification of source claims.',
    } for i in range(len(p))]
