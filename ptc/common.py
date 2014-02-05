from packet import PTCPacket
from constants import MAX_SEQ


class PacketBuilder(object):
    
    def __init__(self, protocol):
        self.control_block = protocol.control_block
        
    def build(self, payload=None, flags=None, seq=None, ack=None):
        packet = PTCPacket()

        source_address = self.control_block.get_source_address()
        source_port = self.control_block.get_source_port()
        dst_address = self.control_block.get_destination_address()
        dst_port = self.control_block.get_destination_port()
        
        packet.set_source_ip(source_address)
        packet.set_destination_ip(dst_address)
        packet.set_source_port(source_port)
        packet.set_destination_port(dst_port)
        
        if payload is not None:
            packet.set_payload(payload)
        if flags is not None:
            packet.add_flags(flags)
        if seq is not None:
            packet.set_seq_number(seq)
        if ack is not None:
            packet.set_ack_number(ack)            
        
        return packet        
        
        
class ProtocolControlBlock(object):
    
    def __init__(self, address, port):
        self.src_address = address
        self.src_port = port
        self.dst_address = None
        self.dst_port = None
        self.modulus = MAX_SEQ
        
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
    
    def set_destination_address(self, address):
        self.dst_address = address
        
    def set_destination_port(self, port):
        self.dst_port = port    