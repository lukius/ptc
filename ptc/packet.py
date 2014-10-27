import struct

from constants import MAX_WND
from seqnum import SequenceNumber


class PTCPacket(object):
    
    def __init__(self):
        from ptc_socket import Socket
        self.source_port = 0
        self.destination_port = 0
        self.seq_number = SequenceNumber(0)
        self.ack_number = SequenceNumber(0)
        self.window_size = 0
        self.flags = set()
        self.payload = str()
        self.source_ip = Socket.NULL_ADDRESS
        self.destination_ip = Socket.NULL_ADDRESS
        self.parent = None
        
    def __contains__(self, element):
        flag_contained = element in PTCFlag.__subclasses__() and\
                         element in self.get_flags()

        return flag_contained   

    def get_source_ip(self):
        return self.source_ip
        
    def get_source_port(self):
        return self.source_port
    
    def get_destination_port(self):
        return self.destination_port

    def get_destination_ip(self):
        return self.destination_ip
        
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

    def set_source_ip(self, ip):
        self.source_ip = ip
    
    def set_source_port(self, port):
        self.source_port = port

    def set_destination_ip(self, ip):
        self.destination_ip = ip
        
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
    
    def __repr__(self):
        template = 'Source port: %s\nDestination port: %s\nSeq: %d\n' +\
                   'Ack: %d\nFlags: %s\nWindow: %s\nPayload: %s'
        from_field = '%d' % self.get_source_port()
        destination_field = '%d' % self.get_destination_port()
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