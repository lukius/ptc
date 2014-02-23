import struct
import socket

from packet import PTCPacket, PTCFlag


class PacketParser(object):
    
    SOURCE_IP_OFFSET = 12
    DESTINATION_IP_OFFSET = 16
    IP_HEADER_LENGTH_OFFSET = 0
    
    SOURCE_PORT_OFFSET = 0
    DESTINATION_PORT_OFFSET = 2
    SEQ_NUMBER_OFFSET = 4
    ACK_NUMBER_OFFSET = 8
    FLAGS_OFFSET = 12
    WINDOW_SIZE_OFFSET = 14
    
    PTC_HEADER_DWORDS = 4
    
    def parse_from(self, packet_bytes):
        packet = PTCPacket()        
        source_ip = self.parse_source_ip_on(packet_bytes)
        destination_ip = self.parse_destination_ip_on(packet_bytes)
        
        transport_packet_bytes = self.get_transport_packet_bytes_from(packet_bytes)
        source_port = self.parse_source_port_on(transport_packet_bytes)
        destination_port = self.parse_destination_port_on(transport_packet_bytes)
        seq_number = self.parse_seq_number_on(transport_packet_bytes)
        ack_number = self.parse_ack_number_on(transport_packet_bytes)
        flags = self.parse_flags_on(transport_packet_bytes)
        window_size = self.parse_window_size_on(transport_packet_bytes)
        data = self.parse_data_on(transport_packet_bytes)

        packet.set_source_ip(source_ip)
        packet.set_destination_ip(destination_ip)        
        packet.set_source_port(source_port)
        packet.set_destination_port(destination_port)
        packet.set_seq_number(seq_number)
        packet.set_ack_number(ack_number)
        packet.add_flags(flags)
        packet.set_window_size(window_size)
        packet.set_payload(data)
        
        return packet
    
    def parse_source_ip_on(self, packet_bytes):
        return self.parse_ip_from_offset(packet_bytes, self.SOURCE_IP_OFFSET)
    
    def parse_destination_ip_on(self, packet_bytes):
        return self.parse_ip_from_offset(packet_bytes,
                                         self.DESTINATION_IP_OFFSET)
        
    def parse_ip_from_offset(self, packet_bytes, ip_offset):
        ip_bytes = packet_bytes[ip_offset:ip_offset+4]
        return socket.inet_ntoa(ip_bytes)
    
    def get_transport_packet_bytes_from(self, packet_bytes):
        ip_header_length = self.parse_ip_header_length_on(packet_bytes)
        return packet_bytes[4*ip_header_length:]
    
    def parse_source_port_on(self, packet_bytes):
        return self.parse_short_from_offset(packet_bytes,
                                            self.SOURCE_PORT_OFFSET)
    
    def parse_destination_port_on(self, packet_bytes):
        return self.parse_short_from_offset(packet_bytes,
                                           self.DESTINATION_PORT_OFFSET)
        
    def parse_seq_number_on(self, packet_bytes):
        return self.parse_long_from_offset(packet_bytes,
                                           self.SEQ_NUMBER_OFFSET)
        
    def parse_ack_number_on(self, packet_bytes):
        return self.parse_long_from_offset(packet_bytes,
                                           self.ACK_NUMBER_OFFSET)
        
    def parse_window_size_on(self, packet_bytes):
        return self.parse_short_from_offset(packet_bytes,
                                            self.WINDOW_SIZE_OFFSET)
        
    def parse_flags_on(self, packet_bytes):
        flags_bits = self.get_flags_bits_on(packet_bytes)
        flags = PTCFlag.__subclasses__()
        packet_flags = filter(lambda flag: flag.get_bits() & flags_bits > 0,
                              flags)
        return packet_flags
    
    def get_flags_bits_on(self, packet_bytes):
        return self.parse_short_from_offset(packet_bytes,
                                            self.FLAGS_OFFSET)
    
    def parse_data_on(self, packet_bytes):
        return packet_bytes[4*self.PTC_HEADER_DWORDS:]
    
    def parse_ip_header_length_on(self, packet_bytes):
        ihl_byte = packet_bytes[self.IP_HEADER_LENGTH_OFFSET]
        header_length = struct.unpack('!B', ihl_byte)[0] & 0x0f
        return header_length
    
    def parse_short_from_offset(self, packet_bytes, offset):
        number_bytes = packet_bytes[offset:offset+2]
        number = struct.unpack('!H', number_bytes)[0]
        return number    
    
    def parse_long_from_offset(self, packet_bytes, offset):
        number_bytes = packet_bytes[offset:offset+4]
        number = struct.unpack('!L', number_bytes)[0]
        return number