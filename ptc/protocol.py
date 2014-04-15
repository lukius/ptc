# -*- coding: utf-8 -*- 

import threading
import random

import buffer
import constants
import packet_utils
import rqueue
import seqnum
import soquete
import thread

from constants import MSS, CLOSED, SYN_RCVD, ESTABLISHED, SYN_SENT,\
                      LISTEN, FIN_WAIT1, FIN_WAIT2, MAX_SEQ,\
                      MAX_RETRANSMISSION_ATTEMPTS, SHUT_RD, SHUT_WR
from exceptions import WriteStreamClosedException
from packet import ACKFlag, FINFlag, SYNFlag


class PTCControlBlock(object):
    
    def __init__(self, send_seq, receive_seq, send_window, receive_window):
        self.iss = seqnum.SequenceNumber(send_seq)
        self.irs = seqnum.SequenceNumber(receive_seq)
        self.snd_wnd = send_window
        self.snd_nxt = seqnum.SequenceNumber(send_seq)
        self.snd_una = seqnum.SequenceNumber(send_seq)
        self.rcv_nxt = seqnum.SequenceNumber(receive_seq)
        self.rcv_wnd = receive_window
        self.snd_wl1 = seqnum.SequenceNumber(receive_seq)
        self.snd_wl2 = seqnum.SequenceNumber(send_seq)
        self.in_buffer = buffer.DataBuffer(start_index=self.irs)
        self.out_buffer = buffer.DataBuffer(start_index=self.iss)
        
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
    
    def get_iss(self):
        return self.iss
    
    def get_irs(self):
        return self.irs
        
    def process_incoming(self, packet, ignore_payload=False):
        self.process_ack(packet)
        if not ignore_payload:
            self.process_payload(packet)
        
    def process_payload(self, packet):    
        if self.payload_is_accepted(packet):
            seq_number = packet.get_seq_number()
            payload = packet.get_payload()
            lower = max(self.rcv_nxt, seq_number)
            self.in_buffer.add_chunk(lower, payload)
            if lower == self.rcv_nxt:
                # We should advance rcv_nxt since the lower end of the chunk
                # just added matches its old value. The buffer tracks this
                # value as data is inserted and removed.
                self.rcv_nxt = self.in_buffer.get_last_index()
    
    def process_ack(self, packet):
        ack_number = packet.get_ack_number()
        if self.ack_is_accepted(ack_number):
            self.snd_una = seqnum.SequenceNumber(ack_number)
            self.update_window(packet)
        
    def ack_is_accepted(self, ack_number):
        return seqnum.SequenceNumber.a_leq_b_leq_c(self.snd_una, ack_number,
                                                   self.snd_nxt)
    
    def payload_is_accepted(self, packet):
        first_byte = packet.get_seq_number()
        last_byte = first_byte + len(packet.get_payload()) - 1
        first_ok = seqnum.SequenceNumber.a_leq_b_leq_c(self.rcv_nxt,
                                                       first_byte,
                                                       self.rcv_nxt+self.rcv_wnd)
        last_ok = seqnum.SequenceNumber.a_leq_b_leq_c(self.rcv_nxt, last_byte,
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
        return self.in_buffer.get(size)
    
    def extract_from_out_buffer(self, size):
        usable_window = self.usable_window_size()
        size = min(size, usable_window)
        data = self.out_buffer.get(size)
        self.snd_nxt += len(data)
        return data
    
    def flush_buffers(self):
        self.in_buffer.flush()
        self.out_buffer.flush()
    

class PTCProtocol(object):
    
    def __init__(self):
        self.state = CLOSED
        self.packet_builder = packet_utils.PacketBuilder()
        self.socket = soquete.Soquete()
        self.rcv_wnd = constants.RECEIVE_BUFFER_SIZE        
        self.iss = self.compute_iss()
        self.rqueue = rqueue.RetransmissionQueue()
        self.retransmission_attempts = dict()
        self.read_stream_open = True
        self.write_stream_open = True
        self.initialize_threads()
        
    def initialize_threads(self):
        self.packet_sender = thread.PacketSender(self)
        self.packet_receiver = thread.PacketReceiver(self)
        self.clock = thread.Clock(self)
        
    def start_threads(self):
        self.packet_receiver.start()
        self.packet_sender.start()
        self.clock.start()
        
    def stop_threads(self):
        self.packet_receiver.stop()
        self.packet_sender.stop()
        self.packet_sender.notify()
        self.clock.stop()
    
    def compute_iss(self):
        return random.randint(0, MAX_SEQ)
        
    def initialize_control_block_from(self, packet, iss=None):
        receive_seq = packet.get_seq_number()
        send_seq = self.iss
        send_window = packet.get_window_size()
        receive_window = self.rcv_wnd
        self.control_block = PTCControlBlock(send_seq, receive_seq,
                                             send_window, receive_window)
    
    def is_connected(self):
        connected_states = [ESTABLISHED, FIN_WAIT1, FIN_WAIT2]
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
            # TODO: fix rcv_wnd calculation (when updating rcv_nxt).
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
        self.state = LISTEN
        
    def connect_to(self, address, port):
        self.connected_event = threading.Event()
        self.set_destination_on_packet_builder(address, port)
        self.start_threads()
        
        # Mandamos el SYN y luego hay que aguardar por el ACK
        syn_packet = self.build_packet(seq=self.iss, flags=[SYNFlag],
                                       window=self.rcv_wnd)
        self.state = SYN_SENT
        self.send_and_queue(syn_packet)
        
        self.connected_event.wait()

    def accept(self):
        if self.state != LISTEN:
            raise Exception('should listen first')
        self.connected_event = threading.Event()
        self.start_threads()
        # No hay mucho por hacer... simplemente esperar a que caiga el SYN del cliente
        self.connected_event.wait()        
        
    def send(self, data):
        if not self.write_stream_open:
            raise WriteStreamClosedException
        self.control_block.to_out_buffer(data)
        self.packet_sender.notify()
        
    def receive(self, size):
        return self.control_block.from_in_buffer(size)
    
    def tick(self):
        self.rqueue.tick()
        self.retransmit_packets_if_needed()
        
    def retransmit_packets_if_needed(self):
        to_retransmit = self.rqueue.get_packets_to_retransmit()
        for packet in to_retransmit:
            attempts = self.update_retransmission_attempts_for(packet)
            if attempts > MAX_RETRANSMISSION_ATTEMPTS:
                # Give up. Maximum number of retransmissions exceeded for this
                # packet.
                self.close()
            else:
                self.send_and_queue(packet)
    
    def update_retransmission_attempts_for(self, packet):
        seq_number = packet.get_seq_number()
        attempts = 1 + self.retransmission_attempts.setdefault(seq_number, 0)
        self.retransmission_attempts[seq_number] = attempts
        return attempts
    
    def acknowledge_packets_on_retransmission_queue_with(self, packet):
        removed_packets = self.rqueue.remove_acknowledged_by(packet)
        for removed_packet in removed_packets:
            seq_number = removed_packet.get_seq_number()
            if seq_number in self.retransmission_attempts:
                del self.retransmission_attempts[seq_number]
        
    def handle_outgoing(self):
        if self.write_stream_open or self.control_block.has_data_to_send():
            self.attempt_to_send_data()
        else:
            # Send FIN when:
            #   * Write stream is closed,
            #   * State is ESTABLISHED (i.e., FIN was not yet sent), and
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
        if self.state == ESTABLISHED and self.rqueue.empty():
            fin_packet = self.build_packet(flags=[ACKFlag, FINFlag])
            self.state = FIN_WAIT1
            self.send_and_queue(fin_packet)
    
    def handle_incoming(self, packet):
        if self.state == LISTEN:
            self.handle_incoming_on_listen(packet)
        else:
            if ACKFlag not in packet:
                # Ignore packets not following protocol specification.
                return
            if self.state == SYN_SENT:
                self.handle_incoming_on_syn_sent(packet)
            elif self.state == SYN_RCVD:
                self.handle_incoming_on_syn_rcvd(packet)
            elif self.state == ESTABLISHED:
                self.handle_incoming_on_established(packet)
            elif self.state == FIN_WAIT1:
                self.handle_incoming_on_fin_wait1(packet)
            elif self.state == FIN_WAIT2:
                self.handle_incoming_on_fin_wait2(packet)                
            else:
                raise Exception('not handled yet')
            self.acknowledge_packets_on_retransmission_queue_with(packet)
    
    def handle_incoming_on_listen(self, packet):
        if SYNFlag in packet:
            self.state = SYN_RCVD
            self.initialize_control_block_from(packet)
            self.set_destination_on_packet_builder(packet.get_source_ip(),
                                                   packet.get_source_port())
            syn_ack_packet = self.build_packet(flags=[SYNFlag, ACKFlag],
                                               window=self.rcv_wnd)
            syn_ack_packet.set_ack_number(packet.get_seq_number())
            self.socket.send(syn_ack_packet)
            
    def handle_incoming_on_syn_sent(self, packet):
        if SYNFlag not in packet:
            return
        ack_number = packet.get_ack_number()
        expected_ack = self.iss
        if expected_ack == ack_number:
            self.state = ESTABLISHED
            self.initialize_control_block_from(packet, iss=self.iss)
            self.dst_port = packet.get_source_port()
            self.dst_address = packet.get_source_ip()
            ack_packet = self.build_packet(flags=[ACKFlag])
            ack_packet.set_ack_number(packet.get_seq_number())
            self.socket.send(ack_packet)            
            #self.retransmission_queue.acknowledge(packet)
            self.connected_event.set()
            
    def handle_incoming_on_syn_rcvd(self, packet):
        ack_number = packet.get_ack_number()
        expected_ack = self.control_block.get_snd_nxt()
        if expected_ack == ack_number:
            self.state = ESTABLISHED
            self.connected_event.set()            
            
    def handle_incoming_on_established(self, packet):
        ignore_payload = not self.read_stream_open
        self.control_block.process_incoming(packet,
                                            ignore_payload=ignore_payload)
        if not self.control_block.has_data_to_send():
            # If some data is about to be sent, then just piggyback the ACK
            # there. It is not necessary to manually send an ACK.
            if len(packet.get_payload()) > 0:
                # Do not send ACKs for plain ACK segments.
                ack_packet = self.build_packet()
                self.socket.send(ack_packet)
        self.packet_sender.notify()
        
    def handle_incoming_on_fin_wait1(self, packet):
        # TODO: remove duplicate code.
        ignore_payload = not self.read_stream_open
        self.control_block.process_incoming(packet,
                                            ignore_payload=ignore_payload)
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            # It can only be the ACK to our FIN packet previously sent.
            self.state = FIN_WAIT2
            
    def handle_incoming_on_fin_wait2(self, packet):
        # TODO: remove duplicate code.
        # TODO: what if read stream is closed here?
        should_send_ack = False
        ack_number = packet.get_ack_number()
        if FINFlag in packet and\
           self.control_block.ack_is_accepted(ack_number):
            self.state = CLOSED
            should_send_ack = True
        elif self.control_block.ack_is_accepted(ack_number):
            ignore_payload = not self.read_stream_open
            self.control_block.process_incoming(packet,
                                                ignore_payload=ignore_payload)
            if len(packet.get_payload()) > 0:
                should_send_ack = True
        if should_send_ack:
            ack_packet = self.build_packet()
            self.socket.send(ack_packet)            
        
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
        self.control_block.flush_buffers()
        self.stop_threads()
        # Esto es por si falló el establecimiento de conexión (para destrabar al thread principal)
        self.connected_event.set()
        self.state = CLOSED