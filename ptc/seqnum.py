class SequenceNumber(object):
    
    @classmethod  
    def validate_moduli(cls, a, b):
        if a.modulus != b.modulus:
            raise Exception    
    
    @classmethod
    def a_lt_b_lt_c(cls, a, b, c):
        cls.validate_moduli(a, c)
        if a > c:
            return (b > a and b < a.modulus) or b < c
        else:
            return a < b < c
    
    @classmethod
    def a_leq_b_lt_c(cls, a, b, c):
        cls.validate_moduli(a, c)
        if a > c:
            return (b >= a and b < a.modulus) or b < c
        else:
            return a <= b < c
    
    @classmethod
    def a_lt_b_leq_c(cls, a, b, c):
        cls.validate_moduli(a, c)
        if a > c:
            return (b > a and b < a.modulus) or b <= c
        else:
            return a < b <= c
    
    @classmethod
    def a_leq_b_leq_c(cls, a, b, c):
        cls.validate_moduli(a, c)
        if a > c:
            return (b >= a and b < a.modulus) or b <= c
        else:
            return a < b <= c
    
    def __init__(self, value, modulus=None):
        self.modulus = modulus if modulus is not None else 2**32
        self.value = value % self.modulus
        
    def __add__(self, other):
        def addition(a, b):
            return a + b
        return self.operate_with(other, addition)
    
    def __sub__(self, other):
        def subtraction(a, b):
            return a - b
        return self.operate_with(other, subtraction)
            
    def __mul__(self, other):
        def multiplication(a, b):
            return a * b
        return self.operate_with(other, multiplication)
    
    def __mod__(self, number):
        return self.value % number
            
    def __radd__(self, other):
        return self.__add__(other)
        
    def __rsub__(self, other):
        return -1 * self.__sub__(other)
    
    def __rmul__(self, other):
        return self.__mul__(other)
        
    def __eq__(self, other):
        def equals(a, b):
            return a == b
        return self.compare_with(other, equals)

    def __lt__(self, other):
        def less_than(a, b):
            return a < b
        return self.compare_with(other, less_than)
    
    def __gt__(self, other):
        def greater_than(a, b):
            return a > b
        return self.compare_with(other, greater_than)
    
    def __le__(self, other):
        def leq(a, b):
            return a <= b
        return self.compare_with(other, leq)
    
    def __ge__(self, other):
        def geq(a, b):
            return a >= b
        return self.compare_with(other, geq)            
        
    def __ne__(self, other):
        def not_equals(a, b):
            return a != b
        return self.compare_with(other, not_equals)        
        
    def __hash__(self):
        return hash(self.value)
        
    def __repr__(self):
        return repr(self.value)
    
    def __int__(self):
        return self.value
    
    def __index__(self):
        return self.value
    
    def operate_with(self, other, operation):
        arg = self.get_value_from(other)
        value = operation(self.value, arg)
        value %= self.modulus
        return self.__class__(value, modulus=self.modulus)
    
    def compare_with(self, other, comparison):
        arg = self.get_value_from(other)
        return comparison(self.value, arg)
    
    def get_value_from(self, other):        
        if isinstance(other, self.__class__):
            self.validate_moduli(self, other)
            value = other.value
        else:
            value = other
        return value    