import time

from base import PTCTestCase
from ptc.constants import RETRANSMISSION_TIMEOUT
from ptc.packet import ACKFlag
from ptc.rqueue import RetransmissionQueue


# TODO: tests with multiple packets.
class RetransmissionQueueTest(PTCTestCase):
    
    DEFAULT_SEQ = 10000
    DEFAULT_DATA = 'data' * 50
    
    def set_up(self):
        self.queue = RetransmissionQueue()
        self.packet = self.packet_builder.build(seq=self.DEFAULT_SEQ,
                                                payload=self.DEFAULT_DATA)
    
    def test_nothing_to_retransmit_if_timeout_has_not_expired(self):
        time_to_wait = RETRANSMISSION_TIMEOUT / 2
        self.queue.put(self.packet)
        
        time.sleep(time_to_wait)
        self.queue.tick()
        packets_to_retransmit = self.queue.get_packets_to_retransmit()
        
        self.assertEquals(0, len(packets_to_retransmit))
    
    def test_packet_ready_to_retransmit_after_timeout(self):
        time_to_wait = RETRANSMISSION_TIMEOUT
        self.queue.put(self.packet)
        
        time.sleep(time_to_wait)
        self.queue.tick()
        packets_to_retransmit = self.queue.get_packets_to_retransmit()
        
        self.assertEquals(1, len(packets_to_retransmit))
        packet = packets_to_retransmit[0]
        self.assertEquals(self.packet.get_seq_number(), packet.get_seq_number())
    
    def test_acknowledged_packet_should_not_be_retransmited(self):
        time_to_wait = RETRANSMISSION_TIMEOUT
        ack_number = self.DEFAULT_SEQ + len(self.DEFAULT_DATA) + 5
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               ack=ack_number)
        self.queue.put(self.packet)
        self.queue.remove_acknowledged_by(ack_packet)
        
        time.sleep(time_to_wait)
        self.queue.tick()
        packets_to_retransmit = self.queue.get_packets_to_retransmit()
        
        self.assertEquals(0, len(packets_to_retransmit))
        
    def test_packet_not_removed_from_queue_when_partially_acked(self):
        time_to_wait = RETRANSMISSION_TIMEOUT
        ack_number = self.DEFAULT_SEQ + len(self.DEFAULT_DATA) - 10
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               ack=ack_number)
        self.queue.put(self.packet)
        self.queue.remove_acknowledged_by(ack_packet)
        
        time.sleep(time_to_wait)
        self.queue.tick()
        packets_to_retransmit = self.queue.get_packets_to_retransmit()
        
        self.assertEquals(1, len(packets_to_retransmit))
        packet = packets_to_retransmit[0]
        self.assertEquals(self.packet.get_seq_number(), packet.get_seq_number())    