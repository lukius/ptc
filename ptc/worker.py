import threading
import Queue
import time
import socket

from constants import SERVER_CONNECTION_TIMEOUT
from event import TimeoutEvent, IncomingPacketEvent, PendingDataEvent,\
                  CloseConnectionEvent, NullEvent


class Worker(object):
    
    def __init__(self, parent):
        self.parent = parent
        self.children = list()
        self.start_working_event = threading.Event()
        
    def start(self):
        self.keep_working = True
        map(lambda child: child.start(), self.children)
        self.start_working_event.set()
    
    def work(self):
        self.start_working_event.wait()
        self.pre_work()
        while self.should_work():
            self.do_work()
        self.post_work()
        
    def should_work(self):
        return self.keep_working is True
    
    def pre_work(self):
        pass
    
    def post_work(self):
        pass
    
    def stop(self):
        self.keep_working = False
        map(lambda child: child.stop(), self.children)
        
    def spawn_thread(self):
        self.worker_thread = threading.Thread(target=self.work)
        self.worker_thread.setDaemon(False) # En False para los tests.
        self.worker_thread.start()
        self.spawn_children_threads()
        
    def spawn_children_threads(self):
        for child in self.children:
            child.spawn_thread()
            
    def join(self):
        map(lambda child: child.join(), self.children)
        self.worker_thread.join()

    def do_work(self):
        raise NotImplementedError('Subclass responsibility')


class ProtocolWorker(Worker):

    EVENT_TIMEOUT = 0.5
    
    @classmethod
    def spawn_for(cls, parent):
        worker = cls(parent)
        worker.spawn_thread()
        return worker    
    
    def __init__(self, parent):
        Worker.__init__(self, parent)
        self.children = [SocketListener(self)]
        self.event_queue = Queue.Queue()
        
    def should_work(self):
        return Worker.should_work(self)
    
    def do_work(self):
        event = self.wait_for_event()

        if event.is_timeout_event():
            self.handle_timeout(event)
        elif event.is_pending_data_event():
            self.handle_pending_data(event)
        elif event.is_incoming_packet_event():
            self.handle_incoming(event)
        elif event.is_close_connection_event():
            self.handle_close_connection(event)            
        
    def receive(self, timeout = None):
        packet = self.parent.socket.receive(timeout)
        self.signal_event(IncomingPacketEvent(packet))
    
    def handle_incoming(self, event):
        packet = event.get_packet()
        self.parent.handle_incoming(packet)       
        
    def wait_for_event(self):
        try:
            event = self.event_queue.get(timeout=self.EVENT_TIMEOUT)
        except Queue.Empty:
            event = NullEvent()
        return event
    
    def signal_event(self, event):
        self.event_queue.put(event)
        
        
class ClientProtocolWorker(ProtocolWorker):
    
    def should_work(self):
        return ProtocolWorker.should_work(self) or\
            not self.parent.outgoing_buffer.empty() or\
            not self.parent.retransmission_queue.empty()    
    
    def send(self, data):
        self.parent.outgoing_buffer.put(data)
        self.signal_pending_data()    
    
    def signal_timeout(self):
        self.signal_event(TimeoutEvent())
        
    def signal_pending_data(self):
        self.signal_event(PendingDataEvent())
            
    def signal_close_connection(self):
        self.signal_event(CloseConnectionEvent())    
    
    def handle_timeout(self, event):
        self.parent.handle_timeout()
    
    def handle_pending_data(self, event):
        self.parent.handle_pending_data()
        
    def handle_close_connection(self, event):
        self.parent.handle_close_connection()
        
     
class ServerProtocolWorker(ProtocolWorker):
        
    def start_connection_timer(self):
        self.connection_timer = threading.Timer(SERVER_CONNECTION_TIMEOUT, self.handle_connection_timeout)
        self.connection_timer.start()
        
    def pre_work(self):
        self.start_connection_timer()
        
    def handle_incoming(self, event):
        self.client_still_connected()
        ProtocolWorker.handle_incoming(self, event)
    
    def client_still_connected(self):
        self.connection_timer.cancel()
        self.start_connection_timer()
    
    def handle_connection_timeout(self):
        self.parent.close()
        self.parent.shutdown()
        self.parent.error = 'connection timed out'
        
        
class SocketListener(Worker):
    
    SLEEP_TIME = 0.1
    TIMEOUT = 0.5
    
    def do_work(self):
        try:
            self.parent.receive(timeout = self.TIMEOUT)
        except socket.timeout:
            pass
        time.sleep(self.SLEEP_TIME)
        
    def should_work(self):
        return self.parent.should_work()   
