# -*- coding: utf-8 -*- 

import threading
import random

from common import PacketBuilder, ProtocolControlBlock
from soquete import Soquete
from packet import ACKFlag, FINFlag, SYNFlag
from worker import ClientProtocolWorker
from buffers import DataBuffer, RetransmissionQueue, NotEnoughDataException
from constants import MIN_PACKET_SIZE, MAX_PACKET_SIZE, CLOSED,\
                      ESTABLISHED, FIN_SENT, SYN_SENT, MAX_SEQ,\
                      SEND_WINDOW, MAX_RETRANSMISSION_ATTEMPTS


class ClientControlBlock(ProtocolControlBlock):
    
    def __init__(self, address, port):
        ProtocolControlBlock.__init__(self, address, port)
        # Próximo SEQ a enviar
        self.send_seq = random.randint(1, MAX_SEQ)
        # Tamaño de la ventana de emisión
        self.send_window = SEND_WINDOW
        # Límite inferior de la ventana (i.e., unacknowledged)
        self.window_lo = self.send_seq
        # Límite superior de la ventana
        self.window_hi = self.modular_sum(self.window_lo, self.send_window)
        
    def get_send_seq(self):
        return self.send_seq
    
    def get_send_window(self):
        return self.send_window
        
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
        

class PTCClientProtocol(object):
    
    def __init__(self, address, port):
        self.retransmission_queue = RetransmissionQueue(self)
        self.retransmission_attempts = dict()
        self.outgoing_buffer = DataBuffer()
        self.state = CLOSED
        self.control_block = ClientControlBlock(address, port)
        self.socket = Soquete(address, port)
        self.packet_builder = PacketBuilder(self)
    
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
        self.retransmission_queue.put(packet)
        
    def send(self, data):
        if not self.is_connected():
            raise Exception('cannot send data: connection not established')
        self.worker.send(data)

    ### Métodos a definir por los alumnos ###
    def connect_to(self, address, port):
        self.worker = ClientProtocolWorker.spawn_for(self)
        self.worker.start()
        self.connected_event = threading.Event()
        self.control_block.set_destination_address(address)
        self.control_block.set_destination_port(port)
        
        # Mandamos el SYN y luego hay que aguardar por el ACK
        syn_packet = self.build_packet(flags=[SYNFlag])
        self.send_and_queue_packet(syn_packet)
        self.state = SYN_SENT
        
        self.connected_event.wait()
    
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
    
    def handle_pending_data(self):
        more_data_pending = False
        
        if self.control_block.send_allowed():
            try:
                data = self.outgoing_buffer.get(MIN_PACKET_SIZE, MAX_PACKET_SIZE)
            except NotEnoughDataException:
                pass
            else:
                packet = self.build_packet(payload=data)
                self.send_and_queue_packet(packet)
                
            if not self.outgoing_buffer.empty():
                more_data_pending = True
        else:
            more_data_pending = True
        
        if more_data_pending:
            self.worker.signal_pending_data()
    
    def handle_incoming(self, packet):
        if ACKFlag in packet:
            ack_number = packet.get_ack_number()
            if self.state == SYN_SENT:
                expected_ack = self.control_block.get_send_seq()
                if expected_ack == ack_number:
                    self.state = ESTABLISHED
                    self.dst_port = packet.get_source_port()
                    self.dst_address = packet.get_source_ip()
                    self.control_block.increment_send_seq()
                    self.control_block.adjust_window_with(ack_number)
                    self.retransmission_queue.acknowledge(packet)
                    self.connected_event.set()
            else:
                accepted = self.control_block.accepts(ack_number)
                if accepted:
                    if self.state == FIN_SENT:
                        self.shutdown()
                    else:
                        self.control_block.adjust_window_with(ack_number)
                        self.retransmission_queue.acknowledge(packet)
            
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
        if self.is_connected():
            self.worker.signal_close_connection()
        
    def shutdown(self):
        self.outgoing_buffer.clear()
        self.retransmission_queue.clear()
        self.retransmission_attempts.clear()
        self.worker.stop()
        # Esto es por si falló el establecimiento de conexión (para destrabar al thread principal)
        self.connected_event.set()
        self.state = CLOSED