# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


import unittest

from ptc.seqnum import SequenceNumber


class SequenceNumberTest(unittest.TestCase):
    
    DEFAULT_MODULUS = 100
    
    def get_seqnum(self, value, modulus=None):
        if modulus is None:
            modulus = self.DEFAULT_MODULUS
        return SequenceNumber(value, modulus=modulus)
    
    def setUp(self):
        self.n = self.get_seqnum(10)
        self.m = self.get_seqnum(50)
        self.l = self.get_seqnum(99)
    
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
        self.assertLess(self.n, self.m)
        self.assertLess(50, self.l)
        self.assertLessEqual(self.m, 50)
        self.assertGreater(self.m, self.n)
        self.assertGreater(self.l, 50)
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