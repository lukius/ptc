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
        self.snd_una = self.DEFAULT_SEQ
        self.snd_nxt = self.snd_una + 2*len(self.DEFAULT_DATA) 
        packet1 = self.packet_builder.build(seq=self.DEFAULT_SEQ,
                                            payload=self.DEFAULT_DATA)
        packet2 = self.packet_builder.build(seq=self.DEFAULT_SEQ+\
                                            len(self.DEFAULT_DATA),
                                            payload=self.DEFAULT_DATA)        
        self.packets = [packet1, packet2]
        
    def get_packet_for_seqs(self, seq_lo, seq_hi):
        if seq_hi < seq_lo:
            seq_hi = MAX_SEQ + seq_hi 
        payload = 'x' * int(seq_hi - seq_lo + 1)
        packet = self.packet_builder.build(seq=seq_lo,
                                           payload=payload)
        return packet        
    
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
        self.queue.remove_acknowledged_by(ack_packet, self.snd_una,
                                          self.snd_nxt)
        
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
        self.queue.remove_acknowledged_by(ack_packet, self.snd_una,
                                          self.snd_nxt)
        
        time.sleep(time_to_wait)
        self.queue.tick()
        packets_to_retransmit = self.queue.get_packets_to_retransmit()
        
        self.assertEquals(1, len(packets_to_retransmit))
        packet = packets_to_retransmit[0]
        self.assertEquals(packet.get_seq_number(), packet.get_seq_number())
        
    def test_ack_covers_packet_without_wraparound(self):
        # Case 1: snd_una < seq_lo < seq_hi < ack < snd_nxt
        # Should be true.
        snd_una = SequenceNumber(75)
        snd_nxt = snd_una + 20
        seq_lo = SequenceNumber(80)
        seq_hi = SequenceNumber(85)
        ack = SequenceNumber(90)
        packet = self.get_packet_for_seqs(seq_lo, seq_hi)
 
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertTrue(result)
         
        # Case 2: snd_una < ack < seq_lo < seq_hi < snd_nxt
        # Should be false.
        ack = seq_lo - 1
        snd_una = ack - 1
  
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)
          
        # Case 3: snd_una < seq_lo < ack < seq_hi < snd_nxt
        # Should be false.
        ack = seq_hi - 1
        snd_una = seq_lo - 1
          
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)

    def test_ack_covers_packet_with_wraparound(self):
        # Case 1: seq_hi < ack < snd_nxt < snd_una < seq_lo
        # Should be true.
        seq_hi = SequenceNumber(10)
        ack = seq_hi + 5
        snd_nxt = ack + 1
        snd_una = snd_nxt + 10
        seq_lo = SequenceNumber(MAX_SEQ - 10)
        packet = self.get_packet_for_seqs(seq_lo, seq_hi)
        
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertTrue(result)
        
        # Case 2: ack < seq_hi < snd_nxt < snd_una < seq_lo
        # Should be false.
        ack = seq_hi - 1
        snd_nxt = seq_hi + 1
        
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)
        
        # Case 3: seq_hi < snd_nxt < snd_una < seq_lo < ack
        # Should be false.
        ack = seq_lo + 1
        
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)
        
        # Case 4: seq_hi < snd_nxt < snd_una < ack < seq_lo
        # Should be false.
        ack = seq_lo - 1
        
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)        