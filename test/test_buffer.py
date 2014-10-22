# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


import threading
import unittest

from ptc.buffer import DataBuffer


class BufferTest(unittest.TestCase):
    
    DEFAULT_START_INDEX = 15672
    DEFAULT_DATA = 'data' * 10 
    
    def setUp(self):
        self.data = self.DEFAULT_DATA
        self.buffer = DataBuffer(start_index=self.DEFAULT_START_INDEX)
                
    def test_basic_buffer_manipulation(self):
        self.assertTrue(self.buffer.empty())
        
        size = 25
        self.buffer.put(self.data)
        self.assertFalse(self.buffer.empty())
        
        data1 = self.buffer.get(size)
        data2 = self.buffer.get(size)
        
        self.assertEqual(data1, self.data[:size])
        self.assertEqual(data2, self.data[size:])
        
    def test_adding_chunks(self):
        size = 25
        first_chunk = 'first chunk'
        second_chunk = 'second chunk'
        offset1 = self.DEFAULT_START_INDEX + len(self.data) + 10
        offset2 = offset1 + len(first_chunk)
        
        self.buffer.add_chunk(offset1, first_chunk)
        self.buffer.add_chunk(offset2, second_chunk)
        self.buffer.put(self.data)
        
        data1 = self.buffer.get(size)
        data2 = self.buffer.get(size)
        self.assertEqual(data1, self.data[:size])
        self.assertEqual(data2, self.data[size:])
        
        size = 10
        self.buffer.put(self.data[:size])
        data = self.buffer.get(size + len(first_chunk) + len(second_chunk))
        self.assertEqual(data, self.data[:size] + first_chunk + second_chunk)
        
    def test_multiple_threads_accessing_buffer(self):
        chunk1 = 'chunk data'
        chunk2 = 'a' * 10
        def writer1():
            self.buffer.put(self.data)
        def writer2():
            offset = self.DEFAULT_START_INDEX + len(self.data) + len(chunk2)
            self.buffer.add_chunk(offset, chunk1)
        def writer3():
            offset = self.DEFAULT_START_INDEX + len(self.data)
            self.buffer.add_chunk(offset, chunk2)
        def reader():
            size = len(self.data) + len(chunk1) + len(chunk2)
            current_size = 0
            data = str()
            while current_size < size:
                current_data = self.buffer.get(size)
                current_size += len(current_data)
                data += current_data
            self.assertEqual(data, self.data + chunk2 + chunk1)
            
        thread1 = threading.Thread(target=writer1)
        thread2 = threading.Thread(target=writer2)
        thread3 = threading.Thread(target=writer3)
        thread4 = threading.Thread(target=reader)
        thread1.start()
        thread2.start()
        thread3.start()
        thread4.start()
        thread1.join()
        thread2.join()
        thread3.join()
        thread4.join()