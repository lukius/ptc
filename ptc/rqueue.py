import threading
import time

from constants import RETRANSMISSION_TIMEOUT


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
            
    def remove_acknowledged_by(self, ack_packet, snd_una, snd_nxt):
        with self.lock:
            new_queue = list()
            acknowledged_packets = list()
            for packet_tuple in self.queue:
                packet = packet_tuple[0]
                ack = ack_packet.get_ack_number()
                # Check that ack >= seq_lo and ack >= seq_hi simultaneously,
                # considering that any of these values may have wrapped.
                if self.ack_covers_packet(ack, packet, snd_una, snd_nxt):
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
            
    def ack_covers_packet(self, ack, packet, snd_una, snd_nxt):
        # Private method to correctly compare the ACK against the SEQs.
        _, seq_hi = packet.get_seq_interval()
        if snd_nxt > snd_una:
            # When SND_NXT > SND_UNA, there is no wrap-around.
            # Thus, the ACK provided covers the packet iff
            # ack > seq_hi = sequence number of the last byte.
            return ack >= seq_hi
        else:
            # When SND_NXT <= SND_UNA, SND_NXT has wrapped around.
            # So, we have two possibilities:
            #   * seq_hi and ack have also wrapped around, and thus
            #     we should have seq_hi <= ack <= snd_nxt
            #   * or just ack wrapped around, which means that it is
            #     already greater than seq_hi. 
            return (seq_hi <= ack <= snd_nxt) or\
                    snd_nxt < seq_hi
            
    def __enter__(self, *args, **kwargs):
        return self.lock.__enter__(*args, **kwargs)
    
    def __exit__(self, *args, **kwargs):
        return self.lock.__exit__(*args, **kwargs)