# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


from base import PTCTestCase
from ptc.constants import MAX_SEQ
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
    
    def test_empty_queue(self):
        self.assertTrue(self.queue.empty())
        
        self.queue.put(self.packets[0])
        self.assertFalse(self.queue.empty())
        
    def test_queue_head(self):
        self.assertRaises(RuntimeError, self.queue.head)
        
        self.queue.put(self.packets[0])
        self.queue.put(self.packets[1])
        head = self.queue.head()
        expected_seq = self.packets[0].get_seq_number()
        
        self.assertEquals(expected_seq, head.get_seq_number())
        
    def test_acked_packet_removed_from_queue(self):
        self.queue.put(self.packets[0])
        self.queue.put(self.packets[1])
        expected_seq, target_ack = self.packets[0].get_seq_interval()
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               ack=target_ack + 10)
        packets = self.queue.remove_acknowledged_by(ack_packet, self.snd_una,
                                                    self.snd_nxt)
        
        self.assertEquals(1, len(packets))
        self.assertEquals(expected_seq, packets[0].get_seq_number())
        
    def test_partially_acked_packet_not_removed_from_queue(self):
        self.queue.put(self.packets[0])
        expected_seq = self.packets[0].get_seq_number()
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               ack=expected_seq + 10)
        packets = self.queue.remove_acknowledged_by(ack_packet, self.snd_una,
                                                    self.snd_nxt)
        
        self.assertEquals(0, len(packets))
        
    def test_ack_covers_packet_without_wraparound(self):
        # Caso 1: snd_una < seq_lo < seq_hi < ack < snd_nxt
        # Debería dar verdadero.
        snd_una = SequenceNumber(75)
        snd_nxt = snd_una + 20
        seq_lo = SequenceNumber(80)
        seq_hi = SequenceNumber(85)
        ack = SequenceNumber(90)
        packet = self.get_packet_for_seqs(seq_lo, seq_hi)
 
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertTrue(result)
         
        # Caso 2: snd_una < ack < seq_lo < seq_hi < snd_nxt
        # Debería dar falso.
        ack = seq_lo - 1
        snd_una = ack - 1
  
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)
          
        # Caso 3: snd_una < seq_lo < ack < seq_hi < snd_nxt
        # Debería dar falso.
        ack = seq_hi - 1
        snd_una = seq_lo - 1
          
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)

    def test_ack_covers_packet_with_wraparound(self):
        # Caso 1: seq_hi < ack < snd_nxt < snd_una < seq_lo
        # Debería dar verdadero.
        seq_hi = SequenceNumber(10)
        ack = seq_hi + 5
        snd_nxt = ack + 1
        snd_una = snd_nxt + 10
        seq_lo = SequenceNumber(MAX_SEQ - 10)
        packet = self.get_packet_for_seqs(seq_lo, seq_hi)
        
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertTrue(result)
        
        # Caso 2: ack < seq_hi < snd_nxt < snd_una < seq_lo
        # Debería dar falso.
        ack = seq_hi - 1
        snd_nxt = seq_hi + 1
        
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)
        
        # Caso 3: seq_hi < snd_nxt < snd_una < seq_lo < ack
        # Debería dar falso.
        ack = seq_lo + 1
        
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)
        
        # Caso 4: seq_hi < snd_nxt < snd_una < ack < seq_lo
        # Debería dar falso.
        ack = seq_lo - 1
        
        result = self.queue.ack_covers_packet(ack, packet, snd_una, snd_nxt)
        self.assertFalse(result)       