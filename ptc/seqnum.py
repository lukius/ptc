class SequenceNumber(object):

    @classmethod  
    def validate_moduli(cls, a, b):
        if a.modulus != b.modulus:
            raise Exception    
    
    @classmethod
    def a_lt_b_lt_c(cls, a, b, c):
        cls.validate_moduli(a, c)
        if c.wrapped and not a.wrapped:
            return (b > a.value and b < a.modulus) or b < c.value
        elif not c.wrapped and a.wrapped:
            return False
        else:
            return a < b < c
    
    @classmethod
    def a_leq_b_lt_c(cls, a, b, c):
        cls.validate_moduli(a, c)
        if c.wrapped and not a.wrapped:
            return (b >= a.value and b < a.modulus) or b < c.value
        elif not c.wrapped and a.wrapped:
            return False        
        else:
            return a <= b < c
    
    @classmethod
    def a_lt_b_leq_c(cls, a, b, c):
        cls.validate_moduli(a, c)
        if c.wrapped and not a.wrapped:
            return (b > a.value and b < a.modulus) or b <= c.value
        elif not c.wrapped and a.wrapped:
            return False        
        else:
            return a < b <= c
    
    @classmethod
    def a_leq_b_leq_c(cls, a, b, c):
        cls.validate_moduli(a, c)
        if c.wrapped and not a.wrapped:
            return (b >= a.value and b < a.modulus) or b <= c.value
        elif not c.wrapped and a.wrapped:
            return False        
        else:
            return a < b <= c
    
    def __init__(self, value, modulus=None, wrapped=False):
        self.modulus = modulus if modulus is not None else 2**32
        self.value = value % self.modulus
        self.wrapped = wrapped
        
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
        other = self.get_seqnum_from(other)
        if self.wrapped and not other.wrapped:
            return False
        elif not self.wrapped and other.wrapped:
            return False
        else:
            return self.value == other.value

    def __lt__(self, other):
        other = self.get_seqnum_from(other)
        if self.wrapped and not other.wrapped:
            return False
        elif not self.wrapped and other.wrapped:
            return True
        else:
            return self.value < other.value
            
    def __gt__(self, other):
        other = self.get_seqnum_from(other)
        if self.wrapped and not other.wrapped:
            return True
        elif not self.wrapped and other.wrapped:
            return False
        else:
            return self.value > other.value
    
    def __le__(self, other):
        return self < other or self == other
    
    def __ge__(self, other):
        return self > other or self == other
        
    def __ne__(self, other):
        return not self == other       
        
    def __hash__(self):
        return hash(self.value)
        
    def __repr__(self):
        return repr(self.value)
    
    def __int__(self):
        return self.value
    
    def __index__(self):
        return self.value
    
    def operate_with(self, other, operation):
        other = self.get_seqnum_from(other)
        value = operation(self.value, other.value)
        wrapped = self.wrapped or value >= self.modulus
        value %= self.modulus
        return self.__class__(value, modulus=self.modulus, wrapped=wrapped)
    
    def get_seqnum_from(self, other):        
        if not isinstance(other, self.__class__):
            other = self.__class__(other, modulus=self.modulus, wrapped=False)
        self.validate_moduli(self, other)
        return other