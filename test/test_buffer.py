import unittest

from ptc.buffers import DataBuffer
from ptc.exceptions import BufferFullException


class BufferTest(unittest.TestCase):
    
    DEFAULT_START_INDEX = 15672
    DEFAULT_DATA = 'data to put inside a buffer' 
    
    def setUp(self):
        self.data = self.DEFAULT_DATA
        self.index = self.DEFAULT_START_INDEX
    
    def get_buffer(self, size=None):
        return DataBuffer(start_index=self.DEFAULT_START_INDEX, size=size)
        
    def test_buffer_without_size(self):
        data_buffer = self.get_buffer()
        self.do_basic_test_with(data_buffer)
        
        new_index = self.index+5
        data = self.data[5:]
        
        data_buffer[new_index+5:new_index+10] = data
        expected_data = data[:5] + data + data[10:]
        retrieved_data = data_buffer[:]
        self.assertEqual(expected_data, retrieved_data)
        
    def test_buffer_with_size(self):
        size = len(self.DEFAULT_DATA)
        data_buffer = self.get_buffer(size)
        self.do_basic_test_with(data_buffer)
        
    def test_buffer_full(self):
        size = len(self.DEFAULT_DATA)
        data_buffer = self.get_buffer(size)
        data_buffer.put(self.data)
        
        self.assertRaises(BufferFullException, data_buffer.put, self.data)
        
        def slice_insertion(data_buffer, index, data):
            data_buffer[index+5:index+10] = data
            
        self.assertRaises(BufferFullException, slice_insertion,
                          data_buffer, self.index, self.data)
                      
                
    def do_basic_test_with(self, data_buffer):
        data_buffer.put(self.data)
        
        retrieved_data = data_buffer[:]
        self.assertEqual(self.data, retrieved_data)
        
        retrieved_data = data_buffer[:self.index+5] + \
                         data_buffer[self.index+5:]
        self.assertEqual(self.data, retrieved_data)
        
        retrieved_char = data_buffer[self.index+5]
        self.assertEqual(self.data[5], retrieved_char)
        
        new_index = self.index+5
        data = self.data[5:]
        del data_buffer[:new_index]
        retrieved_data = data_buffer[:]
        self.assertEqual(data, retrieved_data)