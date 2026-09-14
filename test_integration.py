"""Deterministic integration checks; the fixtures are synthetic, not external."""
import copy,json
from pathlib import Path
import numpy as np
from claim_app import predict
from evaluate_labels import score,LABELS
ROOT=Path(__file__).resolve().parent
request=json.loads((ROOT/'demo/features.json').read_text())
baseline=json.loads((ROOT/'originals/frozen_2026-09-03.json').read_text())
first=predict(request);second=predict(request)
assert first==second
assert all(r['evidence_category'] is None and r['handling_action'] for r in first['records'])
expected=baseline['corpus_summary']['canonical_traces']
for actual,old in zip(first['records'],expected):
    assert actual['id']==old['fixture_id']
    assert actual['final_policy_label']==old['predicted']
    assert actual['classifier_top_label_probability']==old['model_top_probability']
    assert actual['classifier_probability_for_final_label']==old['final_label_model_probability']
checks={'replay_exact':True,'all_13_records_match_canonical':len(first['records'])==13}
bad=copy.deepcopy(request);bad['examples'][0]['expected']='ACCEPT'
try:predict(bad);raise AssertionError('label contamination accepted')
except ValueError:checks['labels_rejected_by_prediction']=True
bad=copy.deepcopy(request);bad['examples'].append(bad['examples'][0])
try:predict(bad);raise AssertionError('duplicate ID accepted')
except ValueError:checks['duplicate_prediction_id_rejected']=True
gold={'provenance':{'dataset_kind':'synthetic_metric_unit_test','annotation_author':'test author','annotation_protocol':'five known labels with one deliberate mistake','label_target':'epistemic_category'},
      'labels':[{'id':str(i),'expected':k,'source_family':'synthetic'} for i,k in enumerate(LABELS)]}
receipt={'records':[{'id':str(i),'final_policy_label':('ACCEPT' if k=='SIMULATED' else k),'classifier_probability_for_final_label':.9} for i,k in enumerate(LABELS)]}
s=score(receipt,gold)
assert s['accuracy']==.8 and s['false_factual_promotion_all_examples']==.2
assert s['simulation_to_fact']==1 and s['narrative_to_fact']==0
assert np.isclose(s['final_label_probability_ece_15'],.1)
assert np.isclose(s['final_label_probability_binary_brier'],.17)
assert np.isclose(s['macro_f1_fixed_five_classes'],11/15)
checks['hand_computed_metrics_match']=True
bad=copy.deepcopy(gold);bad['labels'].pop()
try:score(receipt,bad);raise AssertionError('missing label accepted')
except ValueError:checks['missing_label_rejected']=True
bad=copy.deepcopy(gold);bad['labels'].append(bad['labels'][0])
try:score(receipt,bad);raise AssertionError('duplicate label accepted')
except ValueError:checks['duplicate_label_rejected']=True
bad=copy.deepcopy(gold);bad['provenance']['label_target']='action_appropriateness'
try:score(receipt,bad);raise AssertionError('mixed target accepted')
except ValueError:checks['mixed_target_rejected']=True
assert not s['independent_provenance_verified'];checks['provenance_not_self_certified']=True
(ROOT/'results/integration_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
