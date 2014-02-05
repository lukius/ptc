class Event(object):
    
    def is_timeout_event(self):
        return False
    
    def is_incoming_packet_event(self):
        return False 
        
    def is_pending_data_event(self):
        return False
    
    def is_close_connection_event(self):
        return False


class IncomingPacketEvent(Event):
    
    def __init__(self, packet):
        Event.__init__(self)
        self.packet = packet
    
    def get_packet(self):
        return self.packet
    
    def is_incoming_packet_event(self):
        return True 


class TimeoutEvent(Event):
    
    def is_timeout_event(self):
        return True


class PendingDataEvent(Event):
    
    def is_pending_data_event(self):
        return True
    
    
class CloseConnectionEvent(Event):
    
    def is_close_connection_event(self):
        return True

    
class NullEvent(Event):
    
    pass
