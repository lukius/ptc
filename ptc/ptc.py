import random

from client import PTCClientProtocol
from server import PTCServerProtocol


class PTCObject(object):
    
    def __init__(self, address, port = None):
        if port is None:
            port = random.randint(10000, 40000)
        self.protocol = self.protocol_class()(address, port)
        
    def __del__(self):
        try:
            self.close()
        except:
            pass
        
    def is_connected(self):
        return self.protocol.is_connected()
        
    def last_error(self):
        try:
            error = self.protocol.error
        except:
            error = str()
        return error


class PTCServer(PTCObject):
    
    def protocol_class(self):
        return PTCServerProtocol
    
    def recv(self, size):
        data = self.protocol.receive(size)
        return data    
    
    def accept(self):
        if not self.protocol.is_connected():
            self.protocol.accept()
        else:
            raise Exception('already connected')            
        
    def close(self, wait=True):
        if self.protocol.is_connected():
            if wait is True:
                self.close_wait()
            else:
                self.close_no_wait()
            
    def close_wait(self):
        self.protocol.wait_for_close()
        self.protocol.shutdown()
    
    def close_no_wait(self):
        if self.protocol.is_closed():
            self.protocol.shutdown()
        else:
            raise Exception('cannot close connection yet')


class PTCClient(PTCObject):
    
    def protocol_class(self):
        return PTCClientProtocol  
    
    def send(self, data):
        self.protocol.send(data)    
 
    def connect(self, address, port):
        if not self.protocol.is_connected():
            self.protocol.connect_to(address, port)
        else:
            raise Exception('already connected')
        
    def close(self):
        if self.protocol.is_connected():
            self.protocol.close()        