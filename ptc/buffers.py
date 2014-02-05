import threading
import time

from constants import RETRANSMISSION_TIMEOUT, MAX_SEQ


class NotEnoughDataException(Exception):
    pass


class DataBuffer(object):
    
    def __init__(self):
        self.lock = threading.Lock()
        self.data_event = threading.Event()
        self.buffer = str()
        
    def empty(self):
        return len(self.buffer) == 0
        
    def put(self, data):
        with self.lock:
            self.buffer += data
        self.data_event.set()
        
    def clear(self):
        with self.lock:
            self.buffer = str()
            
    def async_get(self, min_size, max_size):
        return self.get(min_size, max_size)
    
    def sync_get(self, min_size, max_size):
        return self.get(min_size, max_size, blocking = True)
        
    def get(self, min_size, max_size, blocking = False):
        if blocking:
            done = False
            while not done:
                self.lock.acquire()
                if min_size > len(self.buffer):
                    self.lock.release()
                    self.data_event.wait()
                else:
                    data = self.buffer[:max_size]
                    self.buffer = self.buffer[max_size:]
                    self.lock.release()
                    done = True
            return data                    
        else:
            with self.lock:
                if min_size > len(self.buffer):
                    raise NotEnoughDataException()
                else:
                    data = self.buffer[:max_size]
                    self.buffer = self.buffer[max_size:]
                    return data
    

class RetransmissionQueue(object):
    
    def __init__(self, parent):
        self.parent = parent
        self.packet_list = list()
        self.timer = None
        self.timer_lock = threading.Lock()
        
    def put(self, packet):
        self.packet_list.append((packet, time.time()))
        timeout = RETRANSMISSION_TIMEOUT
        self.start_timer_with(timeout)
        
    def clear(self):
        self.packet_list = list()
        self.cancel_timer()
        
    def acknowledge(self, packet):
        self.cancel_timer()
        self.remove_acknowledged_by(packet.get_ack_number())
        if self.packet_list:
            new_timeout = RETRANSMISSION_TIMEOUT - (time.time() - self.packet_list[0][1])
            self.start_timer_with(new_timeout)
            
    def remove_acknowledged_by(self, ack_number):
        first_seq = self.packet_list[0][0].get_seq_number()
        acked_offset = (ack_number - first_seq) % (MAX_SEQ + 1)
        self.packet_list = self.packet_list[1+acked_offset:]
    
    def start_timer_with(self, timeout):
        with self.timer_lock:
            if self.timer is None:
                self.timer = threading.Timer(timeout, self.timeout_expiration_handler)
                self.timer.start()
                
    def cancel_timer(self):
        with self.timer_lock:
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None
                
    def timeout_expiration_handler(self):
        self.parent.worker.signal_timeout()
        with self.timer_lock:
            self.timer = None
        
    def empty(self):
        return len(self.packet_list) == 0
            
    def __iter__(self):
        self.index = 0
        return self
    
    def next(self):
        if self.index >= len(self.packet_list):
            raise StopIteration
        packet = self.packet_list[self.index][0]
        self.index += 1
        return packet
