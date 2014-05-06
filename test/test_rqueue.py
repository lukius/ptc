import time

from base import PTCTestCase
from ptc.constants import RETRANSMISSION_TIMEOUT, MAX_SEQ
from ptc.packet import ACKFlag
from ptc.rqueue import RetransmissionQueue
from ptc.seqnum import SequenceNumber


class RetransmissionQueueTest(PTCTestCase):
    
    DEFAULT_SEQ = 10000
    DEFAULT_DATA = 'data' * 50
    
    def set_up(self):
        self.queue = RetransmissionQueue()
        packet1 = self.packet_builder.build(seq=self.DEFAULT_SEQ,
                                            payload=self.DEFAULT_DATA)
        packet2 = self.packet_builder.build(seq=self.DEFAULT_SEQ+\
                                            len(self.DEFAULT_DATA),
                                            payload=self.DEFAULT_DATA)        
        self.packets = [packet1, packet2]
    
    def test_nothing_to_retransmit_if_timeout_has_not_expired(self):
        time_to_wait = RETRANSMISSION_TIMEOUT / 2
        packet = self.packets[0]
        self.queue.put(packet)
        
        time.sleep(time_to_wait)
        self.queue.tick()
        packets_to_retransmit = self.queue.get_packets_to_retransmit()
        
        self.assertEquals(0, len(packets_to_retransmit))
    
    def test_packets_ready_to_retransmit_after_timeout(self):
        time_to_wait = RETRANSMISSION_TIMEOUT
        packet1, packet2 = self.packets
        self.queue.put(packet1)
        self.queue.put(packet2)
        
        time.sleep(time_to_wait)
        self.queue.tick()
        packets_to_retransmit = self.queue.get_packets_to_retransmit()
        
        self.assertEquals(2, len(packets_to_retransmit))
        to_retransmit1, to_retransmit2 = packets_to_retransmit
        self.assertEquals(packet1.get_seq_number(),
                          to_retransmit1.get_seq_number())
        self.assertEquals(packet2.get_seq_number(),
                          to_retransmit2.get_seq_number())        
    
    def test_acknowledged_packet_should_not_be_retransmited(self):
        time_to_wait = RETRANSMISSION_TIMEOUT
        packet1, packet2 = self.packets
        ack_number = self.DEFAULT_SEQ + len(self.DEFAULT_DATA) + 5
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               ack=ack_number)
        self.queue.put(packet1)
        self.queue.put(packet2)
        self.queue.remove_acknowledged_by(ack_packet)
        
        time.sleep(time_to_wait)
        self.queue.tick()
        packets_to_retransmit = self.queue.get_packets_to_retransmit()
        
        self.assertEquals(1, len(packets_to_retransmit))
        to_retransmit = packets_to_retransmit[0]
        self.assertEquals(packet2.get_seq_number(),
                          to_retransmit.get_seq_number())        
        
    def test_packet_not_removed_from_queue_when_partially_acked(self):
        time_to_wait = RETRANSMISSION_TIMEOUT
        ack_number = self.DEFAULT_SEQ + len(self.DEFAULT_DATA) - 10
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               ack=ack_number)
        packet = self.packets[0]
        self.queue.put(packet)
        self.queue.remove_acknowledged_by(ack_packet)
        
        time.sleep(time_to_wait)
        self.queue.tick()
        packets_to_retransmit = self.queue.get_packets_to_retransmit()
        
        self.assertEquals(1, len(packets_to_retransmit))
        packet = packets_to_retransmit[0]
        self.assertEquals(packet.get_seq_number(), packet.get_seq_number())
        
    def test_ack_greater_than_seq_lo_and_seq_hi(self):
        # Case 1: a=80 < b=85 < c=MAX_SEQ - 10
        a = SequenceNumber(80)
        b = SequenceNumber(85)
        c = SequenceNumber(MAX_SEQ-10)
 
        result = self.queue.geq_than_both(c, a, b)
        self.assertTrue(result)
         
        # Case 2: c=5 < a=80 < b=98 (c has wrapped around)
        c = SequenceNumber(5)
 
        result = self.queue.geq_than_both(c, a, b)
        self.assertTrue(result)        
         
        # Case 3: b=5 < c=10 < a=80 (b and c have wrapped around)
        b = SequenceNumber(5)
        c = SequenceNumber(10)
         
        result = self.queue.geq_than_both(c, a, b)
        self.assertTrue(result)     
         
        # When c=1 < b=5 < a=80 (b and c have wrapped around, but c is not
        # greater than b), it should be false.
        c = SequenceNumber(1)
         
        result = self.queue.geq_than_both(c, a, b)
        self.assertFalse(result)      
         
        # Same when a=80 < c=85 < b=90 (b and c have wrapped around)
        c = SequenceNumber(85)
        b = SequenceNumber(90)
         
        result = self.queue.geq_than_both(c, a, b)
        self.assertFalse(result)        