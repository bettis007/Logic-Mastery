"""Fictional reviewer fixtures test workflow logic, not independent review."""
import copy
import hashlib
import json
import unittest
from pathlib import Path
from review_audit import audit
from claim_identity import claim_digest


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.rubric = json.loads((Path(__file__).parent/'docs/waveform_review_rubric.json').read_text())
        self.rubric.update(status='approved', approval_reference='synthetic test only')
        self.template = {'status':'unannotated','items':[{'id':'case', 'source_sha256':'a'*64,
                         'source_family':'fixture','reference_label':None,'evidence_category':None,'handling_action':None}]}
        digest = hashlib.sha256(json.dumps(self.rubric,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        row = {**self.template['items'][0], 'reference_label':self.rubric['reference_labels'][0],
               'evidence_category':self.rubric['evidence_categories'][0], 'handling_action':self.rubric['handling_actions'][0],
               'evidence_references':['synthetic-context'], 'uncertainty':'Synthetic fixture only',
               'rationale':'Known contract fixture', 'exclusion_reason':None}
        self.reviews = [{'role':role,'status':'complete','reviewer_id':role+'-fictional',
                         'protocol_reference':digest,'items':[copy.deepcopy(row)]}
                        for role in ('reviewer_a','reviewer_b')]

    def result(self):return audit(self.template,self.reviews,self.rubric)

    def test_agreement_is_not_independence_or_accuracy(self):
        result=self.result()
        self.assertTrue(result['ready_for_adjudication'])
        self.assertEqual(result['joint_label_agreement_rate'],1)
        self.assertFalse(result['independence_verified'])
        self.assertIsNone(result['external_accuracy'])

    def test_disagreement_is_retained_without_auto_label(self):
        self.reviews[1]['items'][0]['reference_label']=self.rubric['reference_labels'][1]
        result=self.result()
        self.assertEqual(result['disagreements'],['case'])
        self.assertEqual(result['joint_label_agreement_rate'],0)
        self.assertNotIn('adjudicated_label',result)

    def test_incomplete_and_all_excluded_are_not_approved(self):
        self.reviews[0]['items'][0]['rationale']=None
        self.assertFalse(self.result()['ready_for_adjudication'])
        for review in self.reviews:
            review['items'][0].update(reference_label=None,evidence_category=None,handling_action=None,exclusion_reason='Missing context')
        result=self.result()
        self.assertEqual(result['joint_exclusions'],['case'])
        self.assertIsNone(result['joint_label_agreement_rate'])
        self.assertFalse(result['ready_for_adjudication'])

    def test_source_mutation_missing_items_and_duplicate_items_rejected(self):
        for change in ('source','missing','duplicate'):
            self.setUp()
            if change=='source':self.reviews[0]['items'][0]['source_sha256']='b'*64
            elif change=='missing':self.reviews[0]['items']=[]
            else:self.reviews[0]['items']*=2
            self.assertFalse(self.result()['technical_review_complete'])

    def test_same_identity_and_wrong_protocol_rejected(self):
        self.reviews[1]['reviewer_id']=self.reviews[0]['reviewer_id']
        self.assertFalse(self.result()['technical_review_complete'])
        self.setUp();self.reviews[0]['protocol_reference']='b'*64
        self.assertFalse(self.result()['technical_review_complete'])

    def test_blank_packet_and_draft_rubric_remain_blocked(self):
        self.reviews[0].update(status='unannotated',reviewer_id=None)
        self.assertFalse(self.result()['ready_for_adjudication'])
        self.setUp();self.rubric['status']='draft'
        digest=hashlib.sha256(json.dumps(self.rubric,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        for review in self.reviews:review['protocol_reference']=digest
        result=self.result()
        self.assertTrue(result['technical_review_complete'])
        self.assertFalse(result['ready_for_adjudication'])

    def test_claim_rubric_uses_separate_target(self):
        self.rubric=json.loads((Path(__file__).parent/'docs/claim_review_rubric.json').read_text())
        self.assertEqual(self.rubric['target'],'claim_evidence')
        self.assertFalse(self.result()['ready_for_adjudication'])
        self.rubric.update(status='approved',approval_reference='Fictional claim rubric test')
        self.template['items'][0].update(claim_text='A synthetic report contains this example.',
            source_references=[{'document':'synthetic.json','sha256':'b'*64,'locator':'/example'}])
        self.template['items'][0]['source_sha256']=claim_digest(self.template['items'][0])
        digest=hashlib.sha256(json.dumps(self.rubric,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        for review in self.reviews:
            review['protocol_reference']=digest
            for key in ('claim_text','source_references','source_sha256'):
                review['items'][0][key]=copy.deepcopy(self.template['items'][0][key])
            review['items'][0].update(reference_label='supported_in_supplied_context',
                                     evidence_category='simulated',handling_action='retain_with_attribution')
        self.assertTrue(self.result()['ready_for_adjudication'])
        self.assertIsNone(self.result()['external_accuracy'])

    def test_claim_text_and_reference_edits_cannot_keep_old_identity(self):
        self.test_claim_rubric_uses_separate_target()
        original=copy.deepcopy(self.reviews)
        for field in ('claim_text','document','locator','sha256'):
            self.reviews=copy.deepcopy(original)
            if field=='claim_text':self.reviews[0]['items'][0]['claim_text']='A different claim.'
            else:self.reviews[0]['items'][0]['source_references'][0][field]='c'*64 if field=='sha256' else 'different'
            self.assertFalse(self.result()['technical_review_complete'])


if __name__=='__main__':unittest.main()
