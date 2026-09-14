"""Synthetic malformed-probability checks with a known one-case oracle."""
import copy
from evaluate_labels import score
labels={'provenance':{'dataset_kind':'synthetic','annotation_author':'test','annotation_protocol':'one known ACCEPT','label_target':'epistemic_category'},'labels':[{'id':'a','expected':'ACCEPT','source_family':'synthetic'}]}
receipt={'records':[{'id':'a','final_policy_label':'ACCEPT','classifier_probability_for_final_label':1}]}
for value in (True,False,'0.9',None,[],{},float('nan'),float('inf'),-0.1,1.1):
    bad=copy.deepcopy(receipt);bad['records'][0]['classifier_probability_for_final_label']=value
    try:score(bad,labels)
    except (ValueError,TypeError):pass
    else:raise AssertionError(f'Accepted malformed probability: {value!r}')
assert score(receipt,labels)['final_label_probability_binary_brier']==0
receipt['records'][0]['classifier_probability_for_final_label']=0
assert score(receipt,labels)['final_label_probability_binary_brier']==1
print('PASS: 10 malformed probability cases rejected; both numeric endpoints correct.')
