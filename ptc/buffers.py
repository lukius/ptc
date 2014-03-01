import array
import threading

import exceptions


class DataBuffer(object):
    
    DEFAULT_BYTE = '\x00'
    
    def __init__(self, start_index=0, size=None):
        content = list() if size is None else [self.DEFAULT_BYTE] * size
        self.buffer = array.array('c', content)
        self.buffer_lock = threading.Lock()
        self.size = size
        self.start_index = start_index
        self.last_index = start_index
        
    def shift_index(self, index):
        if isinstance(index, slice):
            if index.start is None or index.start==0:
                shifted_start = 0
            else:
                shifted_start =  index.start - self.start_index
            if index.stop is None:
                shifted_stop = None if self.size is None \
                                    else self.last_index - self.start_index
            else:
                shifted_stop = index.stop - self.start_index
            shifted_index = slice(shifted_start, shifted_stop)
        else:
            shifted_index = index - self.start_index
        return shifted_index
        
    def validate_index_on_delete(self, index):
        if isinstance(index, slice):
            is_null = index.start == 0 or index.start is None
            valid = index.start == self.start_index or is_null
        else:
            is_null = index == 0
            valid = index == self.start_index or is_null
        if not valid:
            raise IndexError('Must delete from first position')
        
    def __getitem__(self, index):
        with self.buffer_lock:
            shifted_index = self.shift_index(index)
            value = self.buffer[shifted_index]
            if isinstance(value, array.array):
                value = value.tostring()
            return value
        
    def __setitem__(self, index, value):
        with self.buffer_lock:
            shifted_index = self.shift_index(index)
            if isinstance(index, slice):
                value = array.array('c', value)
            self.buffer[shifted_index] = value
            if self.size is not None and len(self.buffer) > self.size:
                raise exceptions.BufferFullException
            if not isinstance(index, slice):
                start_index = index
                stop_index = index + 1
            else:
                start_index = index.start
                stop_index = index.stop
            offset = len(value) - stop_index + start_index
            if stop_index >= start_index + len(value):
                last_index = start_index + len(value)
            else:
                last_index = 1 + start_index + offset
            if start_index < self.last_index <= stop_index:
                self.last_index = last_index
            else:
                self.last_index += offset            
            
    def __delitem__(self, index):
        with self.buffer_lock:
            self.validate_index_on_delete(index)
            shifted_index = self.shift_index(index)
            old_size = len(self.buffer)
            del self.buffer[shifted_index]
            new_size = len(self.buffer)
            reduction = old_size - new_size
            if self.size is not None:
                self.buffer.extend([self.DEFAULT_BYTE] * reduction)
            last_index = index + 1 if not isinstance(index, slice) \
                                    else index.stop
            if self.start_index + reduction < last_index:
                self.start_index += reduction
            else:
                self.start_index = last_index
            if self.last_index <= last_index:
                self.last_index = self.start_index
            
    def put(self, data):
        with self.buffer_lock:
            final_index = self.last_index + len(data)
            if self.size is not None and \
               final_index > self.start_index + self.size:
                raise exceptions.BufferFullException
            index = slice(self.last_index, final_index)
            shifted_index = self.shift_index(index)
            self.buffer[shifted_index] = array.array('c', data)
            self.last_index = final_index
            
    def get(self, size):
        with self.buffer_lock:
            data = self.buffer[:size]
            del self.buffer[:size]
            return data.tostring()