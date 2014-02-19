from packet import PTCPacket


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