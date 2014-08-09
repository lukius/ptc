import threading


class RetransmissionQueue(object):
    
    def __init__(self):
        self.queue = list()
        self.lock = threading.RLock()
        
    def empty(self):
        with self.lock:
            return len(self.queue) == 0

    def head(self):
        with self.lock:
            if self.empty():
                raise RuntimeError('retransmission queue is empty')
            return self.queue[0]

    def put(self, packet):
        with self.lock:
            self.queue.append(packet)

    def remove_acknowledged_by(self, ack_packet, snd_una, snd_nxt):
        with self.lock:
            new_queue = list()
            acknowledged_packets = list()
            for packet in self.queue:
                ack = ack_packet.get_ack_number()
                # Check that ack >= seq_lo and ack >= seq_hi simultaneously,
                # considering that any of these values may have wrapped.
                if self.ack_covers_packet(ack, packet, snd_una, snd_nxt):
                    acknowledged_packets.append(packet)
                else:
                    new_queue.append(packet)
            self.queue = new_queue
            return acknowledged_packets
        
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