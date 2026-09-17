"""Delivery liveness and strict-context regression tests on disposable fixtures."""
import copy,json,secrets,sqlite3,tempfile,unittest
from pathlib import Path
from transactional_delivery import DeliveryGuard,initialize_sink,deliver_one
from signal_guard_sim import sign
from corroborated_context_study import attest,check_context

class Delivery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.key=secrets.token_bytes(32)
        self.path=self.root/'queue.sqlite';self.sink=self.root/'sink.sqlite'
        initialize_sink(self.sink);self.g=DeliveryGuard(self.path,self.key,initialize=True,max_attempts=2,max_rows=8)
    def tearDown(self):self.g.close();self.temp.cleanup()
    def put(self,seq):return self.g.inspect(sign(seq,[0]*128),seq)
    def test_delayed_item_does_not_block_ready_item(self):
        self.put(0);self.put(1);self.assertEqual(deliver_one(self.g,self.sink,0,fail=True),'retry_scheduled')
        self.assertEqual(deliver_one(self.g,self.sink,.5),'delivered')
        self.assertEqual(self.g.db.execute('SELECT status FROM outbox WHERE seq=0').fetchone()[0],'pending')
        self.assertEqual(self.g.db.execute('SELECT status FROM outbox WHERE seq=1').fetchone()[0],'delivered')
    def test_exhausted_item_does_not_block_after_restart(self):
        self.put(0);deliver_one(self.g,self.sink,0,fail=True);deliver_one(self.g,self.sink,1,fail=True)
        self.assertEqual(deliver_one(self.g,self.sink,3),'exhausted');self.put(1);self.g.close();self.g=DeliveryGuard(self.path,self.key)
        self.assertEqual(deliver_one(self.g,self.sink,4),'delivered')
        self.assertEqual(self.g.queue_status(),{'delivered':1,'exhausted':1})
        self.assertEqual(self.g.db.execute('SELECT attempts FROM outbox WHERE seq=0').fetchone()[0],2)
    def test_retry_policy_cannot_change_on_reopen(self):
        with self.assertRaises(ValueError):DeliveryGuard(self.path,self.key,max_attempts=8)
        with self.assertRaises(ValueError):deliver_one(self.g,self.sink,0,max_attempts=8)
    def test_policy_byte_alteration_rejected(self):
        self.g.db.execute("UPDATE delivery_policy SET body='{}'")
        with self.assertRaises(ValueError):deliver_one(self.g,self.sink,0)
    def test_capacity_rolls_back_receipt_and_sequence(self):
        p=self.root/'tiny.sqlite';g=DeliveryGuard(p,self.key,initialize=True,max_rows=1)
        try:
            g.inspect(sign(0,[0]*128),0)
            with self.assertRaises(ValueError):g.inspect(sign(1,[0]*128),1)
            self.assertEqual(g.read_state()['last'],0)
            self.assertEqual(g.db.execute('SELECT count(*) FROM receipts').fetchone()[0],1)
        finally:g.close()
    def test_invalid_clock_rejected(self):
        for clock in (True,float('nan'),float('inf'),-1):
            with self.assertRaises(ValueError):deliver_one(self.g,self.sink,clock)

class Context(unittest.TestCase):
    def setUp(self):self.body={'id':'case','expected_amplitude':.25,'noise_std':.25,'bin':15,'issued_at':0,'expires_at':10}
    def valid(self,body=None,now=1):
        b=self.body if body is None else body
        return check_context(attest('producer',b),attest('registry',b),'case',now)
    def test_valid_and_expiry_boundaries(self):
        self.assertTrue(self.valid(now=0));self.assertTrue(self.valid(now=10));self.assertFalse(self.valid(now=11))
    def test_malformed_envelopes_request_review(self):
        b=attest('registry',self.body)
        for obj in (None,[],{},'text',{'body':self.body},{'body':[], 'mac':'0'*64},{'body':self.body,'mac':'é'*64}):
            self.assertFalse(check_context(obj,b,'case',1))
    def test_invalid_signed_fields_request_review(self):
        mutations=[('noise_std',0),('noise_std',-1),('noise_std',True),('bin',True),('bin',16),('expected_amplitude','0.25'),('expected_amplitude',10**1000),('expires_at',1000),('issued_at',-1)]
        for k,v in mutations:
            b={**self.body,k:v};self.assertFalse(self.valid(b))
        b={**self.body,'extra':'unexpected'};self.assertFalse(self.valid(b))
    def test_nonfinite_fields_and_clock_request_review(self):
        for k in ('noise_std','expected_amplitude','issued_at','expires_at'):
            for v in (float('nan'),float('inf')):
                obj={'body':{**self.body,k:v},'mac':'0'*64}
                self.assertFalse(check_context(obj,attest('registry',self.body),'case',1))
        self.assertFalse(self.valid(now=True))
    def test_wrong_roles_and_disagreement_request_review(self):
        a=attest('producer',self.body);b=attest('registry',self.body)
        self.assertFalse(check_context(b,a,'case',1))
        self.assertFalse(check_context(a,attest('registry',{**self.body,'expected_amplitude':.5}),'case',1))
    def test_agreement_still_does_not_prove_truth(self):
        self.assertTrue(self.valid({**self.body,'expected_amplitude':.35}))

if __name__=='__main__':unittest.main()
