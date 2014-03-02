# -*- coding: utf-8 -*- 

import threading
import random

import buffers
import constants
import packet_utils
import soquete
import thread

from packet import ACKFlag, FINFlag, SYNFlag
from constants import MIN_PACKET_SIZE, MAX_PACKET_SIZE, CLOSED, SYN_RCVD,\
                      ESTABLISHED, FIN_SENT, SYN_SENT, MAX_SEQ, LISTEN,\
                      SEND_WINDOW, MAX_RETRANSMISSION_ATTEMPTS, RECV_WINDOW


class PTCControlBlock(object):
    
    def __init__(self, send_seq, receive_seq, window_size):
        self.iss = send_seq
        self.irs = receive_seq
        self.snd_wnd = window_size
        self.snd_nxt = self.iss
        self.snd_una = self.iss
        self.rcv_nxt = self.irs
        self.rcv_wnd = constants.RECEIVE_BUFFER_SIZE
        self.snd_wl1 = self.irs
        self.snd_wl2 = self.iss
        self.in_buffer = buffers.DataBuffer(start_index=self.irs)
        self.out_buffer = buffers.DataBuffer(start_index=self.iss)
        
    def modular_sum(self, a, b):
        return (a + b) % (self.modulus + 1)
    
    def modular_increment(self, a):
        return self.modular_sum(a, 1)        
        
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
        
    def process_incoming(self, packet):
        self.process_payload(packet)
        self.process_ack(packet)
        
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
            self.snd_una = ack_number
            # TODO: Remove from retransmission queue
            self.update_window(packet)
        
    def ack_is_accepted(self, ack_number):
        # TODO: modular arithmetic
        return self.snd_una <= ack_number <= self.snd_nxt
    
    def payload_is_accepted(self, packet):
        first_byte = packet.get_seq_number()
        last_byte = first_byte + len(packet.get_payload()) - 1
        first_ok =  self.rcv_nxt <= first_byte <= self.rcv_nxt + self.rcv_wnd
        last_ok = self.rcv_nxt <= last_byte <= self.rcv_nxt + self.rcv_wnd
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

    def to_out_buffer(self, data):
        self.out_buffer.put(data)    
    
    def from_in_buffer(self, size):
        return self.in_buffer.get(size)
    
    def extract_from_out_buffer(self, size):
        data = self.out_buffer.get(size)
        self.snd_nxt += len(data)
        return data
    
        

class PTCProtocol(object):
    
    def __init__(self):
        self.state = CLOSED
        self.packet_builder = packet_utils.PacketBuilder()
        self.socket = soquete.Soquete()
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
        window_size = packet.get_window_size()
        send_seq = iss if iss is not None else self.compute_iss()
        self.control_block = PTCControlBlock(send_seq, receive_seq,
                                             window_size)
    
    def is_connected(self):
        return self.state == ESTABLISHED
        
    def build_packet(self, seq=None, payload=None, flags=None):
        if seq is None:
            seq = self.control_block.get_snd_nxt()
        if payload is not None:
            self.control_block.increment_send_seq()
        packet = self.packet_builder.build(payload=payload, flags=flags,
                                           seq=seq)
        return packet
        
    def send_packet(self, packet):
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
        self.iss = self.compute_iss()
        syn_packet = self.build_packet(seq=self.iss, flags=[SYNFlag])
        self.state = SYN_SENT
        self.send_packet(syn_packet)
        
        self.connected_event.wait()

    def accept(self):
        if self.state != LISTEN:
            raise Exception('should listen first')
        self.connected_event = threading.Event()
        self.start_threads()
        # No hay mucho por hacer... simplemente esperar a que caiga el SYN del cliente
        self.connected_event.wait()        
        
    def send(self, data):
        self.control_block.to_out_buffer(data)
        self.packet_sender.notify()
        
    def receive(self, size):
        pass
    
    def tick(self):
        pass
    
    def handle_outgoing(self):
        pass
    
    def handle_incoming(self, packet):
        if self.state == LISTEN:
            self.handle_incoming_on_listen(packet)
        else:
            if ACKFlag not in packet:
                return
            if self.state == SYN_SENT:
                self.handle_incoming_on_syn_sent(packet)
            elif self.state == SYN_RCVD:
                self.handle_incoming_on_syn_rcvd(packet)
            elif self.state == ESTABLISHED:
                self.handle_incoming_on_established(packet)
            else:
                raise Exception('not handled yet')                                    
    
    def handle_incoming_on_listen(self, packet):
        if SYNFlag in packet:
            self.state = SYN_RCVD
            self.initialize_control_block_from(packet)
            self.set_destination_on_packet_builder(packet.get_source_ip(),
                                                   packet.get_source_port())
            syn_ack_packet = self.build_packet(flags=[SYNFlag, ACKFlag])
            syn_ack_packet.set_ack_number(packet.get_seq_number())
            self.send_packet(syn_ack_packet)
            
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
            self.send_packet(ack_packet)            
            #self.retransmission_queue.acknowledge(packet)
            self.connected_event.set()
            
    def handle_incoming_on_syn_rcvd(self, packet):
        ack_number = packet.get_ack_number()
        expected_ack = self.control_block.get_snd_nxt()
        if expected_ack == ack_number:
            self.state = ESTABLISHED
            self.connected_event.set()            
            
    def handle_incoming_on_established(self, packet):       
        pass
        
    def close(self):
        self.stop_threads()
        # Esto es por si falló el establecimiento de conexión (para destrabar al thread principal)
        self.connected_event.set()
        self.state = CLOSED