"""Synthetic message-boundary tests, not field security validation."""
import unittest
import numpy as np
from signal_guard_sim import Guard,sign

class Boundaries(unittest.TestCase):
    def test_replay(self):
        g=Guard();m=sign(0,np.zeros(128));self.assertEqual(g.inspect(m,0),'allow');self.assertEqual(g.inspect(m,.1),'reject_replay')
    def test_clock(self):
        g=Guard();g.inspect(sign(0,np.zeros(128)),1);self.assertEqual(g.inspect(sign(1,np.zeros(128)),0),'reject_clock')
    def test_forgery_does_not_advance_sequence(self):
        g=Guard();m=sign(0,np.zeros(128));m['payload']['samples'][0]=1
        self.assertEqual(g.inspect(m,0),'reject_authentication');self.assertEqual(g.inspect(sign(0,np.zeros(128)),0),'allow')
    def test_quota_expiry(self):
        g=Guard()
        for i in range(20):self.assertEqual(g.inspect(sign(i,np.zeros(128)),0),'allow')
        self.assertEqual(g.inspect(sign(20,np.zeros(128)),.5),'reject_rate')
        self.assertEqual(g.inspect(sign(21,np.zeros(128)),1),'allow')
    def test_shape(self):self.assertEqual(Guard().inspect(sign(0,[]),0),'reject_schema')
    def test_numeric_overflow(self):self.assertEqual(Guard().inspect(sign(0,np.full(128,1e308)),0),'reject_numeric')

if __name__=='__main__':unittest.main()
