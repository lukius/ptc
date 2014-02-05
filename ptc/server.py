# -*- coding: utf-8 -*- 

import threading

from common import PacketBuilder, ProtocolControlBlock
from soquete import Soquete
from packet import ACKFlag, FINFlag, SYNFlag
from worker import ServerProtocolWorker
from buffers import DataBuffer
from constants import MIN_PACKET_SIZE, CLOSED,\
                      ESTABLISHED,\
                      FIN_RECEIVED, RECV_WINDOW


class ServerControlBlock(ProtocolControlBlock):
    
    def __init__(self, address, port):
        ProtocolControlBlock.__init__(self, address, port)
        self.receive_seq = 0
        self.receive_window = RECV_WINDOW   
    
    def get_receive_seq(self):
        return self.receive_seq
    
    def get_receive_window(self):
        return self.receive_window
    
    def set_receive_seq(self, seq_number):
        self.receive_seq = seq_number
        
    def increment_receive_seq(self):
        self.receive_seq = self.modular_increment(self.receive_seq)
    
    # Devuelte True sii seq_number es el siguiente paquete esperado
    def accepts(self, seq_number):
        return seq_number == self.receive_seq


class PTCServerProtocol(object):
    
    def __init__(self, address, port):
        self.state = CLOSED
        self.control_block = ServerControlBlock(address, port)
        self.socket = Soquete(address, port)
        self.packet_builder = PacketBuilder(self)
        self.connection_closed_event = threading.Event()
    
    def is_connected(self):
        return self.state == ESTABLISHED
    
    def is_closed(self):
        return self.state == CLOSED
        
    def build_packet(self, flags=None):
        ack = self.control_block.get_receive_seq()
        packet = self.packet_builder.build(flags=flags, ack=ack)
        return packet      
        
    def send_packet(self, packet):
        self.socket.send(packet)
    
    def receive(self, size):
        if self.is_closed() and self.incoming_buffer.empty():
            raise Exception('cannot receive: connection ended and no more pending data buffered')
        elif self.incoming_buffer.empty() and not self.is_connected():
            raise Exception('cannot receive: connection not established')        
        if size < MIN_PACKET_SIZE:
            size = MIN_PACKET_SIZE
        data = self.incoming_buffer.sync_get(MIN_PACKET_SIZE, size)
        return data
    
    def accept(self):
        self.incoming_buffer = DataBuffer()
        self.state = CLOSED
        self.worker = ServerProtocolWorker.spawn_for(self)
        self.worker.start()
        # No hay mucho por hacer... simplemente esperar a que caiga el SYN del cliente
        self.connected_event = threading.Event()
        self.connected_event.wait()     
        
    def handle_incoming(self, packet):
        seq_number = packet.get_seq_number()
        if SYNFlag in packet:
            self.control_block.set_destination_address(packet.get_source_ip())
            self.control_block.set_destination_port(packet.get_source_port())
            self.control_block.set_receive_seq(seq_number)
            ack_packet = self.build_packet(flags=[ACKFlag])
            self.send_packet(ack_packet)
            self.control_block.set_receive_seq(seq_number)
            self.control_block.increment_receive_seq()            
            self.state = ESTABLISHED
            self.connected_event.set()
        if FINFlag in packet:
            if self.control_block.accepts(seq_number):
                self.state = FIN_RECEIVED
                self.send_ack()
                self.close()
        else:
            data = packet.get_payload()
            if self.control_block.accepts(seq_number) and data:
                self.incoming_buffer.put(data)
                if self.state != FIN_RECEIVED:
                    self.send_ack()
                self.control_block.increment_receive_seq()
            
    def send_ack(self):
        ack_packet = self.build_packet(flags=[ACKFlag])
        self.send_packet(ack_packet)
        
    def shutdown(self):
        self.worker.stop()
        # Esto es por si falló el establecimiento de conexión (para destrabar al thread principal)
        self.connected_event.set()

    def close(self):
        self.state = CLOSED
        self.connection_closed_event.set()
        
    def wait_for_close(self):
        self.connection_closed_event.wait()