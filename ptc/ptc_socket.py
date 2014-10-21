import random
import threading

from constants import NULL_ADDRESS, SHUT_RD, SHUT_WR, SHUT_RDWR,\
                      WAIT, NO_WAIT, ABORT
from exceptions import PTCError
from protocol import PTCProtocol


class Socket(object):
    
    def __init__(self):
        self.protocol = PTCProtocol()
        self.sockname = None

    def bind(self, address_tuple=None):
        if address_tuple is None:
            address = NULL_ADDRESS
            port = random.randint(1000, 60000)
            address_tuple = (address, port)
        if not self.is_bound():
            self.protocol.bind(*address_tuple)
            self.sockname = address_tuple
        else:
            raise PTCError('socket already bound')
        
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
            raise PTCError('socket already connected')
        
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
            raise PTCError('socket already connected')
        
    def _connect(self, address_tuple, timeout):
        def timeout_handler():
            print 'connect timed out.'
            self.free()
        
        timer = threading.Timer(timeout, timeout_handler)
        if timeout is not None:
            timer.start()
        self.protocol.connect_to(*address_tuple)
        timer.cancel()
        
    def _check_socket_connected(self):
        if not self.is_connected():
            raise PTCError('socket not connected')
    
    def send(self, data):
        self._check_socket_connected()
        self.protocol.send(data)
 
    def recv(self, size):
        self._check_socket_connected()       
        return self.protocol.receive(size)
    
    def shutdown(self, how=SHUT_RDWR):
        if how not in [SHUT_RD, SHUT_WR, SHUT_RDWR]:
            raise RuntimeError('%s: invalid argument' % str(how))
        self.protocol.shutdown(how)

    def close(self, mode=NO_WAIT):
        if mode not in [WAIT, NO_WAIT, ABORT]:
            raise RuntimeError('%s: invalid argument' % str(mode))
        # Abruptly close socket in order to avoid FIN segment retransmission
        # in case the other party is already gone.        
        if mode == ABORT:
            self.free()
        else:
            self.protocol.close(mode)
        
    def free(self):
        self.protocol.free()
        self.protocol.join_threads()

    def is_connected(self):
        return self.protocol.is_connected()
    
    def is_bound(self):
        return self.sockname is not None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args, **kwargs):
        # Symmetric close: wait for the other party to close as well.
        self.close(mode=WAIT)