import threading

from exceptions import PTCError


class PTCTimer(object):

    def __init__(self, protocol):
        self.protocol = protocol
        self.current_ticks = None
        self.target_ticks = None
        self.running = False
        self.lock = threading.RLock()
        
    def on_expired(self):
        raise NotImplementedError
        
    def is_running(self):
        with self.lock:
            return self.running
        
    def has_expired(self):
        with self.lock:
            return self.current_ticks is not None and\
                   self.target_ticks is not None and\
                   self.current_ticks >= self.target_ticks
        
    def start(self, target_ticks):
        with self.lock:
            if self.is_running():
                raise PTCError('timer already running')
            self.target_ticks = target_ticks
            self.current_ticks = 0
            self.running = True
    
    def stop(self):
        with self.lock:
            self.running = False

    def restart(self, target_ticks):
        with self.lock:
            self.stop()
            self.start(target_ticks)

    def tick(self):
        with self.lock:
            if not self.is_running():
                return
            self.current_ticks += 1
            if self.has_expired():
                self.on_expired()
                self.stop()
    
    def __eq__(self, other):
        # Equality based on classname since we will not need more than one
        # timer of each kind.
        other_classname = other.__class__.__name__
        return self.__class__.__name__ == other_classname

    def __hash__(self):
        return hash(self.__class__.__name__)
    

class RetransmissionTimer(PTCTimer):
    
    def on_expired(self):
        # Awake the packet sender. It will take care of the retransmission.
        self.protocol.packet_sender.notify()