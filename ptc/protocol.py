# -*- coding: utf-8 -*- 

import threading
import random

import buffers
import packet_utils
import soquete
import thread

from packet import ACKFlag, FINFlag, SYNFlag
from constants import MIN_PACKET_SIZE, MAX_PACKET_SIZE, CLOSED, SYN_RCVD,\
                      ESTABLISHED, FIN_SENT, SYN_SENT, MAX_SEQ, LISTEN,\
                      SEND_WINDOW, MAX_RETRANSMISSION_ATTEMPTS, RECV_WINDOW,\
                      RECEIVE_BUFFER_SIZE


class PTCControlBlock(object):
    
    def __init__(self, send_seq, receive_seq, window_size):
        self.iss = send_seq
        self.irs = receive_seq
        self.snd_wnd = window_size
        self.snd_nxt = self.iss
        self.snd_una = self.iss
        self.rcv_nxt = self.irs
        self.rcv_wnd = RECEIVE_BUFFER_SIZE
        self.snd_wl1 = self.irs
        self.snd_wl2 = self.iss
        
        self.in_buffer = buffers.DataBuffer(size=RECEIVE_BUFFER_SIZE)
        self.out_buffer = buffers.DataBuffer()
        
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
            higher = min(self.rcv_nxt + self.rcv_wnd, seq_number + len(payload))
            self.in_buffer[lower:higher] = payload
    
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
            self.wl1 = seq_number
            self.wl2 = ack_number
    
    def bytes_allowed(self):
        lower = 0
        higher = self.snd_una + self.snd_wnd - self.snd_nxt
        return self.out_buffer[lower:higher]
    
    def to_out_buffer(self, data):
        self.out_buffer.put(data)    
    
    def from_in_buffer(self, size):
        pass
    
        

class PTCProtocol(object):
    
    def __init__(self):
        self.retransmission_attempts = dict()
        self.outgoing_buffer = buffers.DataBuffer()
        self.incoming_buffer = buffers.DataBuffer()
        self.state = CLOSED
        self.control_block = PTCControlBlock()
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
    
    def is_connected(self):
        return self.state == ESTABLISHED
        
    def build_packet(self, payload=None, flags=None):
        seq = self.control_block.get_send_seq()
        if payload is not None:
            self.control_block.increment_send_seq()
        packet = self.packet_builder.build(payload=payload, flags=flags, seq=seq)
        return packet
        
    def send_packet(self, packet):
        self.socket.send(packet)
        
    def send_and_queue_packet(self, packet):
        self.send_packet(packet)
        #self.retransmission_queue.put(packet)
        
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
        syn_packet = self.build_packet(flags=[SYNFlag])
        self.state = SYN_SENT
        self.send_and_queue_packet(syn_packet)
        
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
        if self.is_closed() and self.incoming_buffer.empty():
            raise Exception('cannot receive: connection ended and no more pending data buffered')
        elif self.incoming_buffer.empty() and not self.is_connected():
            raise Exception('cannot receive: connection not established')        
        if size < MIN_PACKET_SIZE:
            size = MIN_PACKET_SIZE
        data = self.incoming_buffer.sync_get(MIN_PACKET_SIZE, size)
        return data
    
    def tick(self):
        pass
    
    def handle_outgoing(self):
        while self.control_block.send_allowed():
            try:
                data = self.outgoing_buffer.get(MIN_PACKET_SIZE, MAX_PACKET_SIZE)
            except buffers.NotEnoughDataException:
                break
            else:
                packet = self.build_packet(payload=data)
                # Ajustar variables en el bloque de control
                self.send_packet(packet)
                #self.retransmission_queue.put(packet)
    
    def handle_incoming(self, packet):
        if self.state == LISTEN:
            self.handle_incoming_on_listen(packet)
        else:
            if ACKFlag not in packet:
                # packet should have ack flag
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
        seq_number = packet.get_seq_number()
        if SYNFlag in packet:
            self.state = SYN_RCVD
            self.set_destination_on_packet_builder(packet.get_source_ip(),
                                                   packet.get_source_port())
            self.control_block.set_receive_seq(seq_number)
            syn_ack_packet = self.build_packet(flags=[SYNFlag, ACKFlag])
            syn_ack_packet.set_ack_number(packet.get_seq_number())
            self.send_packet(syn_ack_packet)
            self.control_block.set_receive_seq(seq_number)
            self.control_block.increment_receive_seq()            
            
    def handle_incoming_on_syn_sent(self, packet):
        if SYNFlag not in packet:
            return
        ack_number = packet.get_ack_number()
        expected_ack = self.control_block.get_send_seq()
        if expected_ack == ack_number:
            self.state = ESTABLISHED
            self.dst_port = packet.get_source_port()
            self.dst_address = packet.get_source_ip()
            self.control_block.adjust_window_with(ack_number)
            ack_packet = self.build_packet(flags=[ACKFlag])
            ack_packet.set_ack_number(packet.get_seq_number())
            self.send_packet(ack_packet)            
            #self.retransmission_queue.acknowledge(packet)
            self.control_block.increment_send_seq()
            self.connected_event.set()
            
    def handle_incoming_on_syn_rcvd(self, packet):
        ack_number = packet.get_ack_number()
        expected_ack = self.control_block.get_send_seq()
        if expected_ack == ack_number:
            self.state = ESTABLISHED
            self.control_block.adjust_window_with(ack_number)
            self.control_block.increment_send_seq()
            self.connected_event.set()            
            
    def handle_incoming_on_established(self, packet):       
        ack_number = packet.get_ack_number()
        accepted = self.control_block.accepts(ack_number)
        if accepted:
            self.control_block.adjust_window_with(ack_number)
            #self.retransmission_queue.acknowledge(packet)
            
    def handle_close_connection(self):
        if not self.outgoing_buffer.empty():
            self.worker.signal_pending_data()
            self.worker.signal_close_connection()
        elif not self.retransmission_queue.empty():
            self.worker.signal_close_connection()
        else:
            fin_packet = self.build_packet(flags=[FINFlag])
            self.send_and_queue_packet(fin_packet)
            self.state = FIN_SENT
        
    def close(self):
        self.incoming_buffer.clear()
        self.outgoing_buffer.clear()
        self.retransmission_queue.clear()
        self.retransmission_attempts.clear()
        self.stop_threads()
        # Esto es por si falló el establecimiento de conexión (para destrabar al thread principal)
        self.connected_event.set()
        self.state = CLOSED