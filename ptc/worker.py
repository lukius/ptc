import threading
import socket

from soquete import Soquete                  


class Kernel(object):
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.socket = Soquete()
        self.condition = threading.Condition()
        self.workers_lock = threading.Lock()
        self.initialize_workers()
    
    def initialize_workers(self):
        self.workers = set()
        self.add_worker(PacketReceiver)
        self.add_worker(PacketSender)
        
    def get_socket(self):
        return self.socket
        
    def add_worker(self, worker_class):
        with self.workers_lock:
            worker = worker_class(self)
            self.workers.add(worker)
        
    def remove_worker(self, worker):
        with self.workers_lock:
            self.workers.remove(worker)
        
    def bind(self, address, port):
        self.socket.bind(address, port)
        
    def dispatch_incoming_packet(self, packet):
        self.protocol.handle_incoming(packet)
        self.notify()
        
    def dispatch_outgoing_packet(self, packet):
        self.socket.send(packet)
        
    def notify(self):
        with self.condition:
            self.condition.notifyAll()
            
    def wait(self):
        with self.condition:
            self.condition.wait()
        
    def start(self):
        map(lambda worker: worker.start(), self.workers)
        
    def stop(self):
        map(lambda worker: worker.stop(), self.workers)
        self.notify()


class PTCThread(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        
    def run(self):
        raise NotImplementedError


class Worker(object): 
    
    def __init__(self, kernel):
        self.kernel = kernel
        self.thread = threading.Thread(target=self.work)
        self.thread.setDaemon(False)
        self.keep_working = True
        
    def work(self):
        while self.should_work():
            self.do_work()
        self.end()
            
    def do_work(self):
        raise NotImplementedError
        
    def should_work(self):
        return self.keep_working is True
    
    def end(self):
        self.kernel.remove_worker(self)
    
    def start(self):
        self.thread.start()
    
    def stop(self):
        self.keep_working = False
        
    def join(self):
        self.thread.join()
        
    def __hash__(self):
        return hash(self.__class__)
    
    def __eq__(self, other):
        return self.__class__ == other.__class__

        
class SocketWorker(Worker):

    def __init__(self, kernel):
        Worker.__init__(self, kernel)
        self.socket = kernel.get_socket()
    
    def do_work(self):
        raise NotImplementedError   
    
        
class PacketReceiver(SocketWorker):
    
    TIMEOUT = 0.5
    
    def do_work(self):
        try:
            packet = self.socket.receive(timeout=self.TIMEOUT)
            self.kernel.dispatch_incoming_packet(packet)
        except socket.timeout:
            pass
        
        
class PacketSender(SocketWorker):
    
    def wait(self):
        return self.kernel.wait()
    
    def do_work(self):
        self.wait()
        self.kernel.protocol.handle_outgoing()