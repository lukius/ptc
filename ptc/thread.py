import threading
import socket

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
        self.timer = None
        self.condition = threading.Condition()
        PTCThread.__init__(self, protocol)
        
    def stop(self):
        PTCThread.stop(self)
        # Unlock clock thread if the stop call is issued inside
        # self.protocol.tick().
        self.end_timer()

    def wait_until_previous_timer_ends(self):
        with self.condition:
            if self.timer is not None:
                self.condition.wait()

    def end_timer(self):
        with self.condition:
            self.timer = None
            self.condition.notify()

    def do_run(self):
        self.wait_until_previous_timer_ends()
        self.timer = threading.Timer(CLOCK_TICK, self.tick)
        self.timer.start()
        
    def tick(self):
        if self.should_run():
            # Avoid doing anything if we were told to stop just after this
            # timer was created.
            self.protocol.tick()
        self.end_timer()
    
        
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
        self.condition = threading.Condition()
        self.notified = False
        PTCThread.__init__(self, protocol)
    
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