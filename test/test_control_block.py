from base import PTCTestCase
from ptc.protocol import PTCControlBlock


class ControlBlockTest(PTCTestCase):
    
    DEFAULT_ISS = 20000
    DEFAULT_IRS = 10000
    DEFAULT_IW = 64000
    
    def set_up(self):
        self.control_block = PTCControlBlock(self.DEFAULT_ISS,
                                             self.DEFAULT_IRS,
                                             self.DEFAULT_IW)
    
    def test_creation(self):
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        rcv_nxt = self.control_block.get_rcv_nxt()
        bytes_allowed = self.control_block.bytes_allowed()
        
        self.assertEqual(snd_nxt, snd_una)
        self.assertEqual(snd_nxt, self.DEFAULT_ISS)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS)
        self.assertEqual(len(bytes_allowed), 0)
        
        