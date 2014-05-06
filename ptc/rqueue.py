import threading
import time

from constants import RETRANSMISSION_TIMEOUT
from seqnum import SequenceNumber


class RetransmissionQueue(object):
    
    def __init__(self):
        self.queue = list()
        self.packets_to_retransmit = list()
        self.lock = threading.RLock()
        
    def empty(self):
        with self.lock:
            return len(self.queue) == 0 and\
                   len(self.packets_to_retransmit) == 0
        
    def tick(self):
        with self.lock:
            new_queue = list()
            for packet_tuple in self.queue:
                packet, enqueued_at, remaining_time = packet_tuple
                now = time.time()
                if now - enqueued_at >= remaining_time:
                    self.packets_to_retransmit.append(packet)
                else:
                    new_queue.append(packet_tuple)
            self.queue = new_queue
            
    def remove_acknowledged_by(self, ack_packet):
        with self.lock:
            new_queue = list()
            acknowledged_packets = list()
            for packet_tuple in self.queue:
                packet = packet_tuple[0]
                ack = ack_packet.get_ack_number()
                seq_lo, seq_hi = packet.get_seq_interval()
                # Check that ack >= seq_lo and ack >= seq_hi simultaneously,
                # considering that any of these values may have wrapped.
                if self.geq_than_both(ack, seq_lo, seq_hi):
                    acknowledged_packets.append(packet)
                    self.remove_packet_from_packets_to_retransmit(packet)
                else:
                    new_queue.append(packet_tuple)
            self.queue = new_queue
            return acknowledged_packets
        
    def put(self, packet):
        with self.lock:
            enqueued_at = time.time()
            remaining_time = RETRANSMISSION_TIMEOUT
            packet_tuple = (packet, enqueued_at, remaining_time)
            self.queue.append(packet_tuple)
            self.remove_packet_from_packets_to_retransmit(packet)
            
    def get_packets_to_retransmit(self):
        with self.lock:
            return list(self.packets_to_retransmit)
        
    def remove_packet_from_packets_to_retransmit(self, packet):
        # Private method. Lock already taken.
        seq_numbers = map(lambda packet: packet.get_seq_number(),
                          self.packets_to_retransmit)
        try:
            index = seq_numbers.index(packet.get_seq_number())
        except ValueError:
            index = None
        if index is not None:
            del self.packets_to_retransmit[index]
            
    def geq_than_both(self, ack, seq_lo, seq_hi):
        # Private method to correctly compare the ACK against the SEQs.
        if seq_lo < seq_hi and seq_lo < ack < seq_hi:
            result = False
        elif seq_hi < seq_lo and ack < seq_hi:
            result = False
        else:
            # Case 1: seq_lo < seq_hi < ack
            # Case 2: seq_hi < seq_lo but ack > seq_hi (here, seq_hi and ack
            #         wrapped around)
            # Case 3: ack < seq_lo < seq_hi (here, ack wrapped around)
            # This last case is valid since this comparison only holds
            # whenever ack < SND_NXT, and of course SND_NXT is greater tan both
            # seq_lo and seq_hi, which represent sequenced bytes already sent
            # by the protocol.
            result = True
        return result        
            
    def __enter__(self, *args, **kwargs):
        return self.lock.__enter__(*args, **kwargs)
    
    def __exit__(self, *args, **kwargs):
        return self.lock.__exit__(*args, **kwargs)