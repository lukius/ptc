import unittest
import threading
import time

from ptc import PTCClient, PTCServer
from constants import MAX_RETRANSMISSION_ATTEMPTS, RETRANSMISSION_TIMEOUT, SEND_WINDOW

class TestPTC(unittest.TestCase):
    
    def test_data_send(self):
        result = list()
        data = 'X' * 100 + 'Y' * 100
        def client():
            c = PTCClient('127.0.0.1', 3344)
            c.connect('127.0.0.1', 6655)
            c.send(data[:50])
            c.send(data[50:100])
            c.send(data[100:150])
            c.send(data[150:])
            c.close()
        def server():
            s = PTCServer('127.0.0.1', 6655)
            s.accept()
            result.append(s.recv(50))
            result.append(s.recv(50))
            result.append(s.recv(50))
            result.append(s.recv(50))
            s.close()
        
        thread_client = threading.Thread(target=client)
        thread_server = threading.Thread(target=server)
        thread_server.start()
        thread_client.start()
        thread_client.join()
        thread_server.join()
        
        self.assertEquals(result[0], data[:50])
        self.assertEquals(result[1], data[50:100])
        self.assertEquals(result[2], data[100:150])
        self.assertEquals(result[3], data[150:])
        
    def patch_server(self, server, ack_to_drop):
        server.current_ack = 0
        send_ack = getattr(server.protocol, 'send_ack')
        def send_ack_patched():
            server.current_ack += 1
            if server.current_ack >= ack_to_drop:
                setattr(server.protocol, 'send_ack', send_ack)
            else:
                send_ack()
        setattr(server.protocol, 'send_ack', send_ack_patched)

    def test_retransmission(self):
        result = [str()]
        data = reduce(lambda a,b: a+b, [str(i) * 10 for i in range(1,6)], str())
        def client():
            c = PTCClient('127.0.0.1', 3346)
            c.connect('127.0.0.1', 6657)
            time.sleep(2)
            c.send(data[:10])
            time.sleep(1)
            c.send(data[10:20])
            time.sleep(1)
            c.send(data[20:30])
            time.sleep(1)
            c.send(data[30:40])
            time.sleep(1)
            c.send(data[40:50])
            c.close()
        def server():
            s = PTCServer('127.0.0.1', 6657)
            s.accept()
            self.patch_server(s, 3)
            # This is to ensure that retranmission took place.
            time.sleep(10)
            result[0] += s.recv(200)
            s.close()
        
        thread_client = threading.Thread(target=client)
        thread_server = threading.Thread(target=server)
        thread_server.start()
        thread_client.start()
        thread_client.join()
        thread_server.join()
        
        self.assertEquals(result[0], data)    
    
    def test_connection_dropped_after_exceeding_maximum_retransmissions(self):
        c = PTCClient('127.0.0.1')   

        init_time = time.time()
        c.connect('127.0.0.1', 34672)        
        end_time = time.time()
        
        elapsed_time = end_time - init_time
        expected_time = MAX_RETRANSMISSION_ATTEMPTS * RETRANSMISSION_TIMEOUT
        
        self.assertGreater(elapsed_time, expected_time, 'running time lower?')
        self.assertFalse(c.is_connected(), 'client is connected!')
        
    def test_sliding_window(self):
        result = [str()]
        length = 5*SEND_WINDOW
        data = reduce(lambda a,b: a+b, [str(i) * 10 for i in range(1,length)], str())
        def client():
            c = PTCClient('127.0.0.1', 3347)
            c.connect('127.0.0.1', 6658)
            x = 1 + len(data)/10
            for i in range(1, x):
                to_send = data[10*(i-1):10*i]
                c.send(to_send)
                time.sleep(0.5)
            c.close()
        def server():
            s = PTCServer('127.0.0.1', 6658)
            s.accept()
            s.close()
            result[0] += s.recv(len(data))
        
        thread_client = threading.Thread(target=client)
        thread_server = threading.Thread(target=server)
        thread_server.start()
        thread_client.start()
        thread_client.join()
        thread_server.join()
        
        self.assertEquals(result[0], data)
        
if __name__ == '__main__':
    unittest.main()        