# -*- coding: utf-8 -*- 

import threading
import random

import thread
from common import PacketBuilder
from packet import ACKFlag, FINFlag, SYNFlag
from buffers import DataBuffer, RetransmissionQueue, NotEnoughDataException
from constants import MIN_PACKET_SIZE, MAX_PACKET_SIZE, CLOSED, SYN_RCVD,\
                      ESTABLISHED, FIN_SENT, SYN_SENT, MAX_SEQ, LISTEN,\
                      SEND_WINDOW, MAX_RETRANSMISSION_ATTEMPTS, RECV_WINDOW
from soquete import Soquete


class PTCControlBlock(object):
    
    def __init__(self):
        self.dst_address = None
        self.dst_port = None
        self.modulus = MAX_SEQ
        # Próximo SEQ a enviar
        self.send_seq = random.randint(1, MAX_SEQ)
        # Tamaño de la ventana de emisión
        self.send_window = SEND_WINDOW
        # Límite inferior de la ventana (i.e., unacknowledged)
        self.window_lo = self.send_seq
        # Límite superior de la ventana
        self.window_hi = self.modular_sum(self.window_lo, self.send_window)
        self.receive_seq = 0
        self.receive_window = RECV_WINDOW        
        
    def modular_sum(self, a, b):
        return (a + b) % (self.modulus + 1)
    
    def modular_increment(self, a):
        return self.modular_sum(a, 1)        
        
    def get_source_address(self):
        return self.src_address
    
    def get_source_port(self):
        return self.src_port
    
    def get_destination_address(self):
        return self.dst_address
    
    def get_destination_port(self):
        return self.dst_port
    
    def set_source_address(self, address):
        self.src_address = address
        
    def set_source_port(self, port):
        self.src_port = port
    
    def set_destination_address(self, address):
        self.dst_address = address
        
    def set_destination_port(self, port):
        self.dst_port = port    
    
    def get_send_seq(self):
        return self.send_seq
    
    def get_send_window(self):
        return self.send_window
    
    def get_receive_seq(self):
        return self.receive_seq
    
    def get_receive_window(self):
        return self.receive_window
    
    def set_receive_seq(self, seq_number):
        self.receive_seq = seq_number
        
    def increment_receive_seq(self):
        self.receive_seq = self.modular_increment(self.receive_seq)    
        
    def increment_send_seq(self):
        self.send_seq = self.modular_increment(self.send_seq)
    
    # Responde True sii ack_number cae dentro de la ventana deslizante.    
    def accepts(self, ack_number):
        if ack_number >= self.window_lo and ack_number <= self.window_hi:
            return True
        if self.window_hi < self.window_lo and\
           (ack_number >= self.window_lo or ack_number <= self.window_hi):
            return True
        return False
    
    # A partir de un ack_number aceptado, ajusta los límites de la ventana
    def adjust_window_with(self, ack_number):
        if self.accepts(ack_number):
            self.window_lo = self.modular_increment(ack_number)
            self.window_hi = self.modular_sum(self.window_lo, self.send_window)
    
    # Responde True sii la ventana de emisión no está saturada.
    def send_allowed(self):
        if self.window_lo <= self.window_hi:
            return self.send_seq < self.window_hi
        else:
            return self.send_seq >= self.window_lo or\
                   self.send_seq < self.window_hi
        

class PTCProtocol(object):
    
    def __init__(self):
        self.retransmission_queue = RetransmissionQueue(self)
        self.retransmission_attempts = dict()
        self.outgoing_buffer = DataBuffer()
        self.incoming_buffer = DataBuffer()
        self.state = CLOSED
        self.control_block = PTCControlBlock()
        self.packet_builder = PacketBuilder(self)
        self.socket = Soquete()
        self.initialize_threads()
        
    def initialize_threads(self):
        self.packet_sender = thread.PacketSender(self)
        self.packet_receiver = thread.PacketReceiver(self)
        self.clock = thread.Clock(self)
    
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
        
    def bind(self, address, port):
        self.socket.bind(address, port)
        self.control_block.set_source_address(address)
        self.control_block.set_source_port(port)
    
    def listen(self):
        self.state = LISTEN
        
    def connect_to(self, address, port):
        self.connected_event = threading.Event()
        self.control_block.set_destination_address(address)
        self.control_block.set_destination_port(port)
        
        # Mandamos el SYN y luego hay que aguardar por el ACK
        syn_packet = self.build_packet(flags=[SYNFlag])
        self.state = SYN_SENT
        self.send_and_queue_packet(syn_packet)
        
        self.connected_event.wait()

    def accept(self):
        if self.state != LISTEN:
            raise Exception('should listen first')
        self.connected_event = threading.Event()
        # No hay mucho por hacer... simplemente esperar a que caiga el SYN del cliente
        self.connected_event.wait()        
        
    def send(self, data):
        self.outgoing_buffer.put(data)
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
            except NotEnoughDataException:
                break
            else:
                packet = self.build_packet(payload=data)
                # Ajustar variables en el bloque de control
                self.send_packet(packet)
                #self.retransmission_queue.put(packet)
                
    def handle_timeout(self):
        new_queue = RetransmissionQueue(self)
        for packet in self.retransmission_queue:
            seq_number = packet.get_seq_number()
            attempts = 1 + self.retransmission_attempts.setdefault(seq_number, 0)
            if attempts > MAX_RETRANSMISSION_ATTEMPTS:
                self.error = 'a packet exceeded maximum number of retransmissions'
                self.shutdown()
                return
            self.retransmission_attempts[seq_number] = attempts
            self.send_packet(packet)
            new_queue.put(packet)
        self.retransmission_queue = new_queue
    
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
            self.control_block.set_destination_address(packet.get_source_ip())
            self.control_block.set_destination_port(packet.get_source_port())
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
        
    def stop_threads(self):
        self.packet_receiver.stop()
        self.packet_sender.stop()
        self.packet_sender.notify()
        self.clock.stop()