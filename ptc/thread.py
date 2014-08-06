import threading
import socket
import time

from constants import CLOCK_TICK


class PTCThread(threading.Thread):
    
    def __init__(self, protocol):
        threading.Thread.__init__(self)
        self.protocol = protocol
        self.setDaemon(False)
        self.keep_running = True
        
    def run(self):
        while self.should_run():
            self.do_run()
            
    def should_run(self):
        return self.keep_running
    
    def stop(self):
        self.keep_running = False
        
    def do_run(self):
        raise NotImplementedError
    
    
class Clock(PTCThread):
    
    def __init__(self, protocol):
        PTCThread.__init__(self, protocol)
        self.subscribers = set()
        self.lock = threading.RLock()
        
    def do_run(self):
        self.wait()
        self.tick()
        
    def register(self, obj):
        with self.lock:
            self.subscribers.add(obj)
        
    def unregister(self, obj):
        with self.lock:
            self.subscribers.remove(obj)
        
    def is_registered(self, obj):
        with self.lock:
            return obj in self.subscribers
        
    def wait(self):
        time.sleep(CLOCK_TICK)
        
    def tick(self):
        with self.lock:
            # Make a copy of the set since the tick call below might unregister
            # the subscriber.
            subscribers = list(self.subscribers)
        # TODO: this line might be removed soon
        self.protocol.tick()
        for obj in subscribers:
            obj.tick()
    
        
class PacketReceiver(PTCThread):
    
    TIMEOUT = 0.5
    
    def do_run(self):
        try:
            packet = self.protocol.socket.receive(timeout=self.TIMEOUT)
            self.protocol.handle_incoming(packet)
        except socket.timeout:
            pass
        
        
class PacketSender(PTCThread):
    
    def __init__(self, protocol):
        PTCThread.__init__(self, protocol)
        self.condition = threading.Condition()
        self.notified = False
    
    def wait(self):
        with self.condition:
            if not self.notified:
                self.condition.wait()
            self.notified = False
    
    def notify(self):
        with self.condition:
            self.condition.notify()
            self.notified = True
    
    def do_run(self):
        self.wait()
        self.protocol.handle_outgoing()
