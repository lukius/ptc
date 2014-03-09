import unittest

from ptc.seqnum import SequenceNumber


class SequenceNumberTest(unittest.TestCase):
    
    DEFAULT_MODULUS = 100
    
    def setUp(self):
        self.n = SequenceNumber(10, modulus=self.DEFAULT_MODULUS, wrapped=True)
        self.m = SequenceNumber(50, modulus=self.DEFAULT_MODULUS)
        self.l = SequenceNumber(99, modulus=self.DEFAULT_MODULUS)
    
    def test_addition(self):
        self.assertEqual(int(self.n + self.m), 60)
        self.assertEqual(int(self.n + self.l), 9)
        self.assertEqual(int(self.n + 99), 9)
        self.assertEqual(int(99 + self.n), 9)
        
        self.n += 92
        self.assertEqual(int(self.n), 2)
        
    def test_subtraction(self):
        self.assertEqual(int(self.n - self.m), 60)
        self.assertEqual(int(self.l - self.n), 89)
        self.assertEqual(int(self.n - 50), 60)
        self.assertEqual(int(50 - self.m), 0)

        self.n -= 11
        self.assertEqual(int(self.n), 99)
        
    def test_comparison(self):
        self.assertLess(self.m, self.n)
        self.assertLess(50, self.n)
        self.assertLessEqual(self.m, 50)
        self.assertGreater(self.n, self.m)
        self.assertGreater(self.n, 50)
        self.assertGreaterEqual(self.m, 50)
        
        result = SequenceNumber.a_lt_b_lt_c(self.m, 70, self.l)
        self.assertTrue(result)
        
        result = SequenceNumber.a_lt_b_lt_c(self.m, 10, self.n)
        self.assertFalse(result)
        
        result =  SequenceNumber.a_lt_b_lt_c(self.m, 50, self.n)
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