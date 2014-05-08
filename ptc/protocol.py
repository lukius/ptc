import threading
import random


from buffer import DataBuffer
from constants import MSS, CLOSED, SYN_RCVD, ESTABLISHED, SYN_SENT,\
                      LISTEN, FIN_WAIT1, FIN_WAIT2, MAX_SEQ,\
                      MAX_RETRANSMISSION_ATTEMPTS, SHUT_RD, SHUT_WR,\
                      SHUT_RDWR, CLOSE_WAIT, LAST_ACK, CLOSING,\
                      RECEIVE_BUFFER_SIZE
from exceptions import WriteStreamClosedException
from packet import ACKFlag, FINFlag, SYNFlag
from packet_utils import PacketBuilder
from rqueue import RetransmissionQueue
from seqnum import SequenceNumber
from soquete import Soquete
from thread import Clock, PacketSender, PacketReceiver


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
            self.update_window(packet)
        
    def ack_is_accepted(self, ack_number):
        return SequenceNumber.a_leq_b_leq_c(self.snd_una, ack_number,
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
    

class PTCProtocol(object):
    
    def __init__(self):
        self.state = CLOSED
        self.control_block = None
        self.packet_builder = PacketBuilder()
        self.socket = Soquete()
        self.rcv_wnd = RECEIVE_BUFFER_SIZE        
        self.iss = self.compute_iss()
        self.rqueue = RetransmissionQueue()
        self.retransmission_attempts = dict()
        self.read_stream_open = True
        self.write_stream_open = True
        self.close_event = threading.Event()
        self.initialize_threads()
        
    def initialize_threads(self):
        self.packet_sender = PacketSender(self)
        self.packet_receiver = PacketReceiver(self)
        self.clock = Clock(self)
        
    def start_threads(self):
        self.packet_receiver.start()
        self.packet_sender.start()
        self.clock.start()
        
    def stop_threads(self):
        self.packet_receiver.stop()
        self.packet_sender.stop()
        self.packet_sender.notify()
        self.clock.stop()
        
    def join_threads(self):
        self.packet_receiver.join()
        self.packet_sender.join()
        self.clock.join()
        
    def set_state(self, state):
        self.state = state
        if state == CLOSED or state == FIN_WAIT2:
            self.close_event.set()
        if state == ESTABLISHED:
            self.connected_event.set()
    
    def compute_iss(self):
        value = random.randint(0, MAX_SEQ)
        return SequenceNumber(value)
        
    def initialize_control_block_from(self, packet):
        # +1 since the SYN flag is also sequenced. 
        receive_seq = 1 + packet.get_seq_number()
        send_seq = 1 + self.iss
        send_window = packet.get_window_size()
        receive_window = self.rcv_wnd
        self.control_block = PTCControlBlock(send_seq, receive_seq,
                                             send_window, receive_window)
    
    def is_connected(self):
        connected_states = [ESTABLISHED, FIN_WAIT1, FIN_WAIT2, CLOSE_WAIT,
                            CLOSING, LAST_ACK]
        return self.state in connected_states
        
    def build_packet(self, seq=None, ack=None, payload=None, flags=None,
                     window=None):
        if seq is None:
            seq = self.control_block.get_snd_nxt()
        if flags is None:
            flags = [ACKFlag]
        if ack is None and ACKFlag in flags:
            ack = self.control_block.get_rcv_nxt()
        if window is None:
            window = self.control_block.get_rcv_wnd()
        packet = self.packet_builder.build(payload=payload, flags=flags,
                                           seq=seq, ack=ack, window=window)
        return packet
        
    def send_and_queue(self, packet):
        self.rqueue.put(packet)
        self.socket.send(packet)
        
    def set_destination_on_packet_builder(self, address, port):
        self.packet_builder.set_destination_address(address)
        self.packet_builder.set_destination_port(port)        
        
    def bind(self, address, port):
        self.socket.bind(address, port)
        self.packet_builder.set_source_address(address)
        self.packet_builder.set_source_port(port)
    
    def listen(self):
        self.set_state(LISTEN)
        
    def connect_to(self, address, port):
        self.connected_event = threading.Event()
        self.set_destination_on_packet_builder(address, port)
        self.start_threads()
        
        syn_packet = self.build_packet(seq=self.iss, flags=[SYNFlag],
                                       window=self.rcv_wnd)
        self.set_state(SYN_SENT)
        self.send_and_queue(syn_packet)
        
        self.connected_event.wait()

    def accept(self):
        if self.state != LISTEN:
            raise Exception('should listen first')
        self.connected_event = threading.Event()
        self.start_threads()
        # Wait until client attempts to connect.
        self.connected_event.wait()        
        
    def send(self, data):
        with self.control_block:
            if not self.write_stream_open:
                raise WriteStreamClosedException
            self.control_block.to_out_buffer(data)
            self.packet_sender.notify()
        
    def receive(self, size):
        data = self.control_block.from_in_buffer(size)
        updated_rcv_wnd = self.control_block.get_rcv_wnd()
        if updated_rcv_wnd > 0:
            wnd_packet = self.build_packet(window=updated_rcv_wnd)
            self.socket.send(wnd_packet)
        return data
    
    def tick(self):
        with self.rqueue:
            self.rqueue.tick()
            self.retransmit_packets_if_needed()
        
    def retransmit_packets_if_needed(self):
        to_retransmit = self.rqueue.get_packets_to_retransmit()
        for packet in to_retransmit:
            attempts = self.update_retransmission_attempts_for(packet)
            if attempts > MAX_RETRANSMISSION_ATTEMPTS:
                # Give up. Maximum number of retransmissions exceeded for this
                # packet.
                self.free()
            else:
                self.send_and_queue(packet)
    
    def update_retransmission_attempts_for(self, packet):
        seq_number = packet.get_seq_number()
        attempts = 1 + self.retransmission_attempts.setdefault(seq_number, 0)
        self.retransmission_attempts[seq_number] = attempts
        return attempts
    
    def acknowledge_packets_on_retransmission_queue_with(self, packet):
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            # Only ACK numbers greater than SND_UNA and less than SND_NXT are
            # valid here.
            with self.rqueue:
                snd_una = self.control_block.get_snd_una()
                snd_nxt = self.control_block.get_snd_nxt()
                # See which packets already enqueued are acknowledged by this
                # packet. SND_UNA and SND_NXT are needed for properly comparing
                # SEQs and ACKs.
                removed_packets = self.rqueue.remove_acknowledged_by(packet,
                                                                     snd_una,
                                                                     snd_nxt)
                for removed_packet in removed_packets:
                    seq_number = removed_packet.get_seq_number()
                    if seq_number in self.retransmission_attempts:
                        del self.retransmission_attempts[seq_number]
        
    def handle_outgoing(self):
        if self.control_block is None:
            # When connection is still not established, we don't have 
            # anything to send.
            return
        with self.control_block:
            if self.write_stream_open or self.control_block.has_data_to_send():
                self.attempt_to_send_data()
            else:
                # Send FIN when:
                #   * Write stream is closed,
                #   * State is ESTABLISHED/CLOSE_WAIT
                #     (i.e., FIN was not yet sent), and
                #   * Every outgoing byte was successfully acknowledged.
                self.attempt_to_send_FIN()
            
    def attempt_to_send_data(self):
        window_closed = False
        while self.control_block.has_data_to_send() and not window_closed:
            seq_number = self.control_block.get_snd_nxt()
            to_send = self.control_block.extract_from_out_buffer(MSS)
            if not to_send:
                # Control block returned nothing, which hints that the window
                # is closed. Thus, we have nothing else to do until further
                # ACKs arrive.
                window_closed = True
            else:
                packet = self.build_packet(payload=to_send, seq=seq_number)
                self.send_and_queue(packet)
                
    def attempt_to_send_FIN(self):
        state_allows_closing = self.state in [ESTABLISHED, CLOSE_WAIT]
        if state_allows_closing and self.rqueue.empty():
            fin_packet = self.build_packet(flags=[ACKFlag, FINFlag])
            # We are sending a FIN packet, and this flag is sequenced. Move
            # forward the next byte sequence to be sent.
            self.control_block.increment_snd_nxt()
            self.control_block.increment_snd_una()
            new_state = FIN_WAIT1 if self.state == ESTABLISHED else LAST_ACK
            self.set_state(new_state)
            self.send_and_queue(fin_packet)
    
    def handle_incoming(self, packet):
        if self.state == LISTEN:
            self.handle_incoming_on_listen(packet)
        elif self.state == SYN_SENT:
            self.handle_incoming_on_syn_sent(packet)
        else:
            if ACKFlag not in packet:
                # Ignore packets not following protocol specification.
                return
            with self.control_block:
                if self.state == SYN_RCVD:
                    self.handle_incoming_on_syn_rcvd(packet)
                elif self.state == ESTABLISHED:
                    self.handle_incoming_on_established(packet)
                elif self.state == FIN_WAIT1:
                    self.handle_incoming_on_fin_wait1(packet)
                elif self.state == FIN_WAIT2:
                    self.handle_incoming_on_fin_wait2(packet)  
                elif self.state == CLOSE_WAIT:
                    self.handle_incoming_on_close_wait(packet)
                elif self.state == LAST_ACK:
                    self.handle_incoming_on_last_ack(packet)
                elif self.state == CLOSING:
                    self.handle_incoming_on_closing(packet)                    
                self.acknowledge_packets_on_retransmission_queue_with(packet)
    
    def handle_incoming_on_listen(self, packet):
        if SYNFlag in packet:
            self.set_state(SYN_RCVD)
            self.initialize_control_block_from(packet)
            self.set_destination_on_packet_builder(packet.get_source_ip(),
                                                   packet.get_source_port())
            syn_ack_packet = self.build_packet(flags=[SYNFlag, ACKFlag])
            # The next byte we send should be sequenced after the SYN flag.
            self.control_block.increment_snd_nxt()
            self.socket.send(syn_ack_packet)
            
    def handle_incoming_on_syn_sent(self, packet):
        if SYNFlag not in packet or ACKFlag not in packet:
            return
        ack_number = packet.get_ack_number()
        # +1 since the SYN flag is also sequenced.
        expected_ack = 1 + self.iss
        if expected_ack == ack_number:
            self.initialize_control_block_from(packet)
            self.dst_port = packet.get_source_port()
            self.dst_address = packet.get_source_ip()
            ack_packet = self.build_packet(flags=[ACKFlag])
            self.set_state(ESTABLISHED)
            self.socket.send(ack_packet)            
            
    def handle_incoming_on_syn_rcvd(self, packet):
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            self.set_state(ESTABLISHED)
            # This packet is acknowledging our SYN. We must increment SND_UNA
            # in order to reflect this.
            self.control_block.increment_snd_una()
            
    def handle_incoming_fin(self, packet, next_state):
        seq_number = packet.get_seq_number()
        # SEQ number should be the one we are expecting.        
        if seq_number == self.control_block.get_rcv_nxt():
            self.set_state(next_state)
            self.read_stream_open = False
            # The FIN flag is also sequenced, and so we must increment the next
            # byte we expect to receive.
            self.control_block.increment_rcv_nxt()
        # Send ACK (if the previous check fails, the ACK number will be
        # automatically set to the proper one).
        ack_packet = self.build_packet()
        self.socket.send(ack_packet)
        
    def process_on_control_block(self, packet):
        ignore_payload = not self.read_stream_open
        self.control_block.process_incoming(packet,
                                            ignore_payload=ignore_payload)
        
    def send_ack_for_packet_only_if_it_has_payload(self, packet):
        # This is to avoid sending ACKs for plain ACK segments.
        if len(packet.get_payload()) > 0:
            ack_packet = self.build_packet()
            self.socket.send(ack_packet)        
            
    def handle_incoming_on_established(self, packet):
        if FINFlag in packet:
            self.handle_incoming_fin(packet, next_state=CLOSE_WAIT)
        else:
            self.process_on_control_block(packet)
            if not self.control_block.has_data_to_send():
                # If some data is about to be sent, then just piggyback the ACK
                # there. It is not necessary to manually send an ACK.
                self.send_ack_for_packet_only_if_it_has_payload(packet)
            self.packet_sender.notify()
        
    def handle_incoming_on_fin_wait1(self, packet):
        # We might receive data, so we must process the packet accordingly.
        self.process_on_control_block(packet)
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            # It can only be the ACK to our FIN packet previously sent.
            self.set_state(FIN_WAIT2)
            if FINFlag in packet:
                self.handle_incoming_fin(packet, next_state=CLOSED)
        else:
            # Check if it is a FIN packet, meaning that our peer closed
            # its write stream simultaneously.
            if FINFlag in packet:
                self.handle_incoming_fin(packet, next_state=CLOSING)
            
    def handle_incoming_on_fin_wait2(self, packet):
        # TODO: what if read stream is closed here?
        if FINFlag in packet:
            self.handle_incoming_fin(packet, next_state=CLOSED)
        else:
            self.process_on_control_block(packet)
            self.send_ack_for_packet_only_if_it_has_payload(packet)
            
    def handle_incoming_on_close_wait(self, packet):
        # We should ignore everything here since the other side has closed its
        # write stream.
        # TODO: revisar (ACKs?)
        pass
    
    def set_closed_if_packet_acknowledges_fin(self, packet):
        # Move to CLOSED only if this packet ACKs the FIN we sent before.
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            self.set_state(CLOSED)
    
    def handle_incoming_on_last_ack(self, packet):
        self.set_closed_if_packet_acknowledges_fin(packet)
            
    def handle_incoming_on_closing(self, packet):
        self.set_closed_if_packet_acknowledges_fin(packet)
        
    def shutdown(self, how):
        if how == SHUT_RD:
            self.shutdown_read_stream()
        elif how == SHUT_WR:
            self.shutdown_write_stream()
        else:
            self.shutdown_read_stream()
            self.shutdown_write_stream()
            
    def shutdown_read_stream(self):
        self.read_stream_open = False
    
    def shutdown_write_stream(self):
        self.write_stream_open = False
        self.packet_sender.notify()
        
    def close(self):
        if self.state != CLOSED:
            self.shutdown(SHUT_RDWR)
            self.close_event.wait()
        self.free()
        self.join_threads()
            
    def free(self):
        if self.control_block is not None:
            self.control_block.flush_buffers()
        self.stop_threads()
        # In case connection establishment failed, this will unlock the main
        # thread.
        self.connected_event.set()
        # And, similarly, this will unlock the main thread if close is called
        # and free is later invoked by some other thread, for whatever reason.
        self.close_event.set()
        self.set_state(CLOSED)