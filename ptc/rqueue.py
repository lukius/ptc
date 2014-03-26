import threading
import time

from constants import RETRANSMISSION_TIMEOUT


class RetransmissionQueue(object):
    
    def __init__(self):
        self.queue = list()
        self.packets_to_retransmit = list()
        self.lock = threading.Lock()
        
    def tick(self):
        with self.lock:
            to_remove = list()
            for index, packet_tuple in enumerate(self.queue):
                packet, enqueued_at, remaining_time = packet_tuple
                now = time.time()
                if now - enqueued_at >= remaining_time:
                    to_remove.append(index)
            for index in to_remove:
                packet = self.queue[index][0]
                self.packets_to_retransmit.append(packet)
                del self.queue[index]
            
    def remove_acknowledged_by(self, ack_packet):
        with self.lock:
            to_remove = list()
            for index, packet_tuple in enumerate(self.queue):
                packet = packet_tuple[0]
                ack = ack_packet.get_ack_number()
                seq_lo = packet.get_seq_number()
                seq_hi = seq_lo + len(packet.get_payload())
                # TODO: won't work for wrapped ACK numbers.
                if seq_lo <= ack and seq_hi <= ack:
                    to_remove.append(index)
            for index in to_remove:
                del self.queue[index]
        
    def put(self, packet):
        with self.lock:
            enqueued_at = time.time()
            remaining_time = RETRANSMISSION_TIMEOUT
            packet_tuple = (packet, enqueued_at, remaining_time)
            self.queue.append(packet_tuple)
            
    def get_packets_to_retransmit(self):
        with self.lock:
            packets = list(self.packets_to_retransmit)
            self.packets_to_retransmit = list()
            return packets