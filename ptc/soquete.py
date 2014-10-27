import socket

from constants import PROTOCOL_NUMBER
from packet_utils import PacketDecoder


class Soquete(object):
    
    MAX_SIZE = 65535
    
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                    PROTOCOL_NUMBER)
        
    def close(self):
        self.socket.close()  
        
    def bind(self, address, port):
        self.address = address
        self.port = port
        self.socket.bind((self.address, self.port))
        
    def send(self, packet):
        data = packet.get_bytes()
        dst_address = packet.get_destination_ip()
        dst_port = packet.get_destination_port()
        self.socket.sendto(data, (dst_address, dst_port))
        
    def receive(self, timeout=None):
        should_stop = False
        if timeout is not None and timeout > 0:
            self.socket.settimeout(timeout)
        else:
            self.socket.settimeout(None)
        while not should_stop:
            packet_bytes, _ = self.socket.recvfrom(self.MAX_SIZE)
            packet = PacketDecoder().decode(packet_bytes)
            if self.is_for_me(packet):
                should_stop = True
        return packet
                
    def is_for_me(self, packet):
        from ptc_socket import Socket
        address = packet.get_destination_ip()
        port = packet.get_destination_port()
        address_is_null = self.address == Socket.NULL_ADDRESS
        return (address_is_null or address == self.address) and\
                port == self.port