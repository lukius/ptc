import unittest

from ptc.seqnum import SequenceNumber


class SequenceNumberTest(unittest.TestCase):
    
    DEFAULT_MODULUS = 100
    
    def setUp(self):
        self.n = SequenceNumber(10, modulus=self.DEFAULT_MODULUS)
        self.m = SequenceNumber(50, modulus=self.DEFAULT_MODULUS)
        self.l = SequenceNumber(99, modulus=self.DEFAULT_MODULUS)
    
    def test_addition(self):
        self.assertEqual(self.n + self.m, 60)
        self.assertEqual(self.n + self.l, 9)
        self.assertEqual(self.n + 99, 9)
        self.assertEqual(99 + self.n, 9)
        
        self.n += 92
        self.assertEqual(self.n, 2)
        
    def test_subtraction(self):
        self.assertEqual(self.n - self.m, 60)
        self.assertEqual(self.l - self.n, 89)
        self.assertEqual(self.n - 50, 60)
        self.assertEqual(50 - self.n, 40)

        self.n -= 11
        self.assertEqual(self.n, 99)
        
    def test_comparison(self):
        self.assertLess(self.n, self.m)
        self.assertLess(self.n, 50)
        self.assertLessEqual(self.n, 10)
        self.assertGreater(self.m, self.n)
        self.assertGreater(50, self.n)
        self.assertGreaterEqual(10, self.n)
        
        result = SequenceNumber.a_lt_b_lt_c(self.n, 40, self.m)
        self.assertTrue(result)
        
        result = SequenceNumber.a_lt_b_lt_c(self.m, 10, self.n)
        self.assertFalse(result)
        
        result = SequenceNumber.a_lt_b_lt_c(self.m, 50, self.n)
        self.assertFalse(result)    

        result = SequenceNumber.a_lt_b_lt_c(self.m, 2, self.n)
        self.assertTrue(result)
        
        result = SequenceNumber.a_lt_b_lt_c(self.m, 99, self.n)
        self.assertTrue(result)
        
        result = SequenceNumber.a_lt_b_leq_c(self.m, 10, self.n)
        self.assertTrue(result)
        
        result = SequenceNumber.a_leq_b_lt_c(self.m, 50, self.n)
        self.assertTrue(result)
        
        result = SequenceNumber.a_leq_b_leq_c(self.m, 10, self.n)
        self.assertTrue(result)
        
        result = SequenceNumber.a_leq_b_leq_c(self.m, 50, self.n)
        self.assertTrue(result)        