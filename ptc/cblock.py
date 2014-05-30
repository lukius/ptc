import threading

from buffer import DataBuffer
from seqnum import SequenceNumber


class PTCControlBlock(object):
    
    def __init__(self, send_seq, receive_seq, send_window, receive_window):
        self.snd_wnd = send_window
        self.snd_nxt = send_seq.clone()
        self.snd_una = send_seq.clone()
        self.rcv_nxt = receive_seq.clone()
        self.rcv_wnd = receive_window
        self.snd_wl1 = receive_seq.clone()
        self.snd_wl2 = send_seq.clone()
        self.in_buffer = DataBuffer(start_index=receive_seq.clone())
        self.out_buffer = DataBuffer(start_index=send_seq.clone())
        self.lock = threading.RLock()
        
    def get_snd_nxt(self):
        return self.snd_nxt
    
    def get_snd_una(self):
        return self.snd_una    
    
    def get_snd_wnd(self):
        return self.snd_wnd
    
    def get_snd_wl1(self):
        return self.snd_wl1

    def get_snd_wl2(self):
        return self.snd_wl2        
    
    def get_rcv_nxt(self):
        return self.rcv_nxt
    
    def get_rcv_wnd(self):
        return self.rcv_wnd
    
    def increment_snd_nxt(self):
        with self:
            self.snd_nxt += 1
            
    def increment_snd_una(self):
        with self:
            self.snd_una += 1
            
    def increment_rcv_nxt(self):
        with self:
            self.rcv_nxt += 1
        
    def process_incoming(self, packet, ignore_payload=False):
        self.process_ack(packet)
        if not ignore_payload:
            self.process_payload(packet)
        
    def process_payload(self, packet):    
        if self.payload_is_accepted(packet):
            seq_lo, seq_hi = packet.get_seq_interval()
            payload = packet.get_payload()
            lower = max(self.rcv_nxt, seq_lo)
            upper = min(self.rcv_nxt + self.rcv_wnd, seq_hi)
            # Honor RCV_WND by dropping those bytes that go below it
            # or beyond it.
            effective_payload = payload[lower-seq_lo:upper-seq_lo]
            self.in_buffer.add_chunk(lower, effective_payload)
            if lower == self.rcv_nxt:
                # We should advance rcv_nxt since the lower end of the chunk
                # just added matches its old value. The buffer tracks this
                # value as data is inserted and removed.
                self.rcv_nxt = self.in_buffer.get_last_index()
                # Decrease window until data is removed from the buffer.
                self.rcv_wnd = self.rcv_wnd - len(effective_payload)
    
    def process_ack(self, packet):
        ack_number = packet.get_ack_number()
        if self.ack_is_accepted(ack_number):
            self.snd_una = ack_number
        if self.should_update_window(ack_number):
            self.update_window(packet)
        
    def ack_is_accepted(self, ack_number):
        # Accept only if  SND_UNA < ACK <= SND_NXT
        return SequenceNumber.a_lt_b_leq_c(self.snd_una, ack_number,
                                           self.snd_nxt)
    
    def payload_is_accepted(self, packet):
        seq_lo, seq_hi = packet.get_seq_interval()
        first_byte, last_byte = seq_lo, seq_hi-1
        first_ok = SequenceNumber.a_leq_b_leq_c(self.rcv_nxt,
                                                first_byte,
                                                self.rcv_nxt+self.rcv_wnd)
        last_ok = SequenceNumber.a_leq_b_leq_c(self.rcv_nxt, last_byte,
                                               self.rcv_nxt+self.rcv_wnd)
        return last_byte >= first_byte and (first_ok or last_ok)
    
    def should_update_window(self, ack_number):
        # TODO: add tests for this.
        # RFC 1122, p.94 (correction to RFC 793).
        return SequenceNumber.a_leq_b_leq_c(self.snd_una, ack_number,
                                            self.snd_nxt)
    
    def update_window(self, packet):
        seq_number = packet.get_seq_number()
        ack_number = packet.get_ack_number()
        if self.snd_wl1 < seq_number or \
           (self.snd_wl1 == seq_number and self.snd_wl2 <= ack_number):
            self.snd_wnd = packet.get_window_size()
            self.snd_wl1 = seq_number
            self.snd_wl2 = ack_number
            
    def usable_window_size(self):
        return self.snd_una + self.snd_wnd - self.snd_nxt
    
    def has_data_to_send(self):
        return not self.out_buffer.empty()

    def to_out_buffer(self, data):
        self.out_buffer.put(data)    
    
    def from_in_buffer(self, size):
        data = self.in_buffer.get(size)
        # Window should grow now, since data has been consumed.
        with self:
            self.rcv_wnd += len(data)
        return data
    
    def extract_from_out_buffer(self, size):
        usable_window = self.usable_window_size()
        size = min(size, usable_window)
        data = self.out_buffer.get(size)
        self.snd_nxt += len(data)
        return data
    
    def flush_buffers(self):
        self.in_buffer.flush()
        self.out_buffer.flush()
        
    def __enter__(self, *args, **kwargs):
        return self.lock.__enter__(*args, **kwargs)
    
    def __exit__(self, *args, **kwargs):
        return self.lock.__exit__(*args, **kwargs)