# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


import random
import struct
import socket

from constants import PROTOCOL_NUMBER, MAX_WND
from seqnum import SequenceNumber


class IPChecksumAlgorithm(object):
    # Implementación naive, ineficiente, del algorimo de checksum de Internet.
    
    @classmethod
    def for_bytes(cls, message):
        return cls(message)
        
    def __init__(self, message):
        self.message = message
        
    def has_odd_length(self, message):
        return len(message) % 2 == 1
        
    def value(self):
        message = self.message
        value = 0
        
        if self.has_odd_length(message):
            message += '\0'
        
        for i in range(0, len(message), 2):
            word = (ord(message[i]) << 8) + (ord(message[i+1]))
            value += word
        
        high_part = value >> 16
        low_part = value & 0xffff
        while high_part > 0:
            value = high_part + low_part
            high_part = value >> 16
            low_part = value & 0xffff
        
        value = ~value & 0xffff
        
        return value


class PTCNetworkPacket(object):
    
    def __init__(self):
        self.source_ip = '0.0.0.0'
        self.destination_ip = '0.0.0.0'
        self.version = 4
        self.header_length = 5
        self.type_of_service = 0
        self.total_length = 4*self.header_length
        self.id_number = random.randint(0, 2**16 - 1)
        dont_fragment = 1
        self.fragmentation_word = (dont_fragment << 14)
        self.time_to_live = 255
        self.protocol = PROTOCOL_NUMBER
        self.payload = None
        self.update_checksum()
        
    def get_source_ip(self):
        return self.source_ip
    
    def get_destination_ip(self):
        return self.destination_ip    
    
    def get_version(self):
        return self.version
    
    def get_header_length(self):
        return self.header_length
    
    def get_type_of_service(self):
        return self.type_of_service
    
    def get_total_length(self):
        return self.total_length
    
    def get_id_number(self):
        return self.id_number
    
    def get_time_to_live(self):
        return self.time_to_live
    
    def get_protocol(self):
        return self.protocol
    
    def get_checksum(self):
        return self.checksum
    
    def get_fragmentation_word(self):
        return self.fragmentation_word
    
    def get_payload(self):
        return self.payload
    
    def set_source_ip(self, ip):
        self.source_ip = ip
        self.update_checksum()
        
    def set_destination_ip(self, ip):
        self.destination_ip = ip
        self.update_checksum()
    
    def set_version(self, version):
        self.version = version
        self.update_checksum()
    
    def set_header_length(self, length):
        self.header_length = length
        self.update_checksum()
    
    def set_type_of_service(self, type_of_service):
        self.type_of_service = type_of_service
        self.update_checksum()
    
    def add_length(self, length):
        self.total_length += length
        self.update_checksum()
    
    def set_id_number(self, id_number):
        self.id_number = id_number
        self.update_checksum()
    
    def set_time_to_live(self, time_to_live):
        self.time_to_live = time_to_live
        self.update_checksum()
    
    def set_protocol(self, protocol):
        self.protocol = protocol
        self.update_checksum()
    
    def set_fragmentation_word(self, fragmentation_word):
        self.fragmentation_word = fragmentation_word
        self.update_checksum()
        
    def set_payload(self, payload):
        self.payload = payload
        length = len(payload.get_bytes())
        self.add_length(length)
        self.payload.set_parent(self)
    
    def update_checksum(self):
        self.checksum = 0
        header_bytes = self.get_bytes()
        updated_checksum = IPChecksumAlgorithm.for_bytes(header_bytes).value()
        self.checksum = updated_checksum
        
    def get_bytes(self):
        source_ip = socket.inet_aton(self.source_ip)
        destination_ip = socket.inet_aton(self.destination_ip)        
        header_length_plus_version = (self.version << 4) + self.header_length
        payload_bytes = str()
        if self.payload is not None:
            payload_bytes = self.payload.get_bytes()
        header_bytes = struct.pack('!BBHHHBBH4s4s', header_length_plus_version,
                            self.type_of_service, self.total_length,
                            self.id_number, self.fragmentation_word,
                            self.time_to_live, self.protocol, self.checksum,
                            source_ip, destination_ip)
        return header_bytes + payload_bytes
    

class PTCTransportPacket(object):
    
    def __init__(self):
        self.source_port = 0
        self.destination_port = 0
        self.seq_number = SequenceNumber(0)
        self.ack_number = SequenceNumber(0)
        self.window_size = 0
        self.flags = set()
        self.payload = str()
        self.parent = None
        
    def __contains__(self, element):
        flag_contained = element in PTCFlag.__subclasses__() and\
                         element in self.get_flags()

        return flag_contained   
        
    def get_source_port(self):
        return self.source_port
    
    def get_destination_port(self):
        return self.destination_port
        
    def get_seq_number(self):
        return self.seq_number
    
    def get_seq_interval(self):
        seq_lo = self.seq_number.clone()
        seq_hi = seq_lo + len(self.payload)
        return seq_lo, seq_hi

    def get_ack_number(self):
        return self.ack_number
    
    def get_window_size(self):
        return self.window_size
    
    def get_payload(self):
        return self.payload
    
    def get_parent(self):
        return self.parent
    
    def get_flags(self):
        return self.flags
    
    def add_flag(self, flag):
        self.flags.add(flag)
        
    def add_flags(self, flags):
        self.flags.update(flags)
    
    def set_source_port(self, port):
        self.source_port = port
        
    def set_destination_port(self, port):
        self.destination_port = port          
    
    def set_seq_number(self, seq_number):
        self.seq_number = SequenceNumber(seq_number)
        
    def set_ack_number(self, ack_number):
        self.ack_number = SequenceNumber(ack_number)
        
    def set_window_size(self, window_size):
        self.window_size = window_size % (MAX_WND+1)
        
    def set_payload(self, data):
        self.payload = data
        if self.parent is not None:
            length_difference = len(data) - len(self.payload)
            self.parent.add_length(length_difference)
        
    def set_parent(self, parent):
        self.parent = parent
        
    def has_payload(self):
        return len(self.payload) > 0        
        
    def get_bytes(self):
        flags_bytes = reduce(lambda value, flag: value ^ flag.get_bits(),
                             self.flags, 0)
        header_bytes = struct.pack('!HHLLHH', self.source_port,
                                              self.destination_port, 
                                              self.seq_number,
                                              self.ack_number,
                                              flags_bytes,
                                              self.window_size)
        
        
        return header_bytes + self.payload
    
    
class PTCPacket(object):
    
    SEQ_SIZE = 2
    ACK_SIZE = 2
    
    def __init__(self):
        self.transport_packet = PTCTransportPacket()
        self.network_packet = PTCNetworkPacket()
        self.network_packet.set_payload(self.transport_packet)
        
    def __contains__(self, element):
        return self.transport_packet.__contains__(element)
    
    def get_source_ip(self):
        return self.network_packet.get_source_ip()
    
    def get_destination_ip(self):
        return self.network_packet.get_destination_ip()
    
    def get_length(self):
        return self.network_packet.get_total_length()
        
    def get_source_port(self):
        return self.transport_packet.get_source_port()
    
    def get_destination_port(self):
        return self.transport_packet.get_destination_port()
        
    def get_seq_number(self):
        return self.transport_packet.get_seq_number()
    
    def get_seq_interval(self):
        return self.transport_packet.get_seq_interval()
    
    def get_ack_number(self):
        return self.transport_packet.get_ack_number()
    
    def get_window_size(self):
        return self.transport_packet.get_window_size()
    
    def get_payload(self):
        return self.transport_packet.get_payload()
    
    def get_flags(self):
        return self.transport_packet.get_flags()
    
    def add_flag(self, flag):
        self.transport_packet.add_flag(flag)
        
    def add_flags(self, flags):
        self.transport_packet.add_flags(flags)
        
    def set_source_ip(self, ip):
        self.network_packet.set_source_ip(ip)
        
    def set_destination_ip(self, ip):
        self.network_packet.set_destination_ip(ip)          
    
    def set_source_port(self, port):
        self.transport_packet.set_source_port(port)
        
    def set_destination_port(self, port):
        self.transport_packet.set_destination_port(port)
    
    def set_seq_number(self, seq_number):
        self.transport_packet.set_seq_number(seq_number)
        
    def set_ack_number(self, ack_number):
        self.transport_packet.set_ack_number(ack_number)
        
    def set_window_size(self, window_size):
        self.transport_packet.set_window_size(window_size)
    
    def set_payload(self, data):
        self.transport_packet.set_payload(data)
        
    def get_bytes(self):
        return self.network_packet.get_bytes()
    
    def has_payload(self):
        return self.transport_packet.has_payload()    
    
    def __repr__(self):
        template = 'From: %s\nTo: %s\nSeq: %d\nAck: %d\nFlags: %s\nWindow: %s\nPayload: %s'
        from_field = '(%s, %d)' % (self.get_source_ip(),
                                   self.get_source_port())
        destination_field = '(%s, %d)' % (self.get_destination_ip(),
                                          self.get_destination_port())
        flags = ', '.join(map(lambda flag: flag.name(), self.get_flags()))
        if not flags:
            flags = '<none>'
        seq = self.get_seq_number()
        ack = self.get_ack_number()
        window = self.get_window_size()
        payload = self.get_payload()
        if not payload:
            payload = '<none>'
        return template % (from_field, destination_field, seq, ack, flags,
                           window, payload)
    
    
class PTCFlag(object):
    
    @classmethod
    def get_bits(self):
        raise NotImplementedError
    
    @classmethod
    def __hash__(self):
        return hash(self.get_bits())
    
    @classmethod
    def __eq__(self, flag):
        return self.get_bits() == flag.get_bits()

    @classmethod
    def name(cls):
        return cls.__name__[:-4]   
    

class FINFlag(PTCFlag):
    
    @classmethod
    def get_bits(self):
        return 0x1
    

class SYNFlag(PTCFlag):
    
    @classmethod
    def get_bits(self):
        return 0x2


class RSTFlag(PTCFlag):
    
    @classmethod
    def get_bits(self):
        return 0x4
    
    
class NDTFlag(PTCFlag):
    
    @classmethod
    def get_bits(self):
        return 0x8
    
    
class ACKFlag(PTCFlag):
    
    @classmethod
    def get_bits(self):
        return 0x10            