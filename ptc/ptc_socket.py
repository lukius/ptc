import random
import threading

from constants import NULL_ADDRESS, SHUT_RD, SHUT_WR, SHUT_RDWR
from exceptions import SocketAlreadyConnectedException
from exceptions import SocketAlreadyBoundException
from exceptions import SocketNotConnectedException
from protocol import PTCProtocol


class Socket(object):
    
    def __init__(self):
        self.protocol = PTCProtocol()
        self.sockname = None
        
    def __del__(self):
        try:
            self.free()
        except:
            pass

    def bind(self, address_tuple=None):
        if address_tuple is None:
            address = NULL_ADDRESS
            port = random.randint(1000, 60000)
            address_tuple = (address, port)
        if not self.is_bound():
            self.protocol.bind(*address_tuple)
            self.sockname = address_tuple
        else:
            raise SocketAlreadyBoundException
        
    def listen(self):
        if self.is_bound():
            self._listen()
        else:
            self.bind()
            self._listen()
            
    def _listen(self):
        self.protocol.listen()
    
    def accept(self, timeout=None):
        if not self.is_connected() and self.is_bound():
            self._accept(timeout)
        elif not self.is_connected():
            self.listen()
            self._accept(timeout)
        else:
            raise SocketAlreadyConnectedException
        
    def _accept(self, timeout):
        def timeout_handler():
            print 'accept timed out.'
            self.free()
        
        timer = threading.Timer(timeout, timeout_handler)
        if timeout is not None:
            timer.start()
        self.protocol.accept()
        timer.cancel()
        
    def connect(self, address_tuple, timeout=None):
        if not self.is_connected():
            if not self.is_bound():
                self.bind()
            self._connect(address_tuple, timeout)
        else:
            raise SocketAlreadyConnectedException
        
    def _connect(self, address_tuple, timeout):
        def timeout_handler():
            print 'connect timed out.'
            self.free()
        
        timer = threading.Timer(timeout, timeout_handler)
        if timeout is not None:
            timer.start()
        self.protocol.connect_to(*address_tuple)
        timer.cancel()
    
    def send(self, data):
        if not self.is_connected():
            raise SocketNotConnectedException
        self.protocol.send(data)
 
    def recv(self, size):
        if not self.is_connected():
            raise SocketNotConnectedException        
        return self.protocol.receive(size)
    
    def shutdown(self, how=SHUT_RDWR):
        if how not in [SHUT_RD, SHUT_WR, SHUT_RDWR]:
            raise RuntimeError('%s: invalid argument' % str(how))
        self.protocol.shutdown(how)

    def close(self):
        self.protocol.close()
        
    def free(self):
        self.protocol.free()
        self.protocol.join_threads()

    def is_connected(self):
        return self.protocol.is_connected()
    
    def is_bound(self):
        return self.sockname is not None
        
    def last_error(self):
        try:
            error = self.protocol.error
        except:
            error = None
        return error