import os
import Queue
import socket
import threading
import time
import traceback
import unittest

import ptc


class PTCTestSuite(object):
    
    @classmethod
    def build(cls):
        test_loader = unittest.defaultTestLoader
        test_files = cls.get_test_files()
        test_modules = map(lambda filename: 'test.%s' % filename[:-3],
                           test_files)
        suites = map(test_loader.loadTestsFromName, test_modules) 
        test_suite = unittest.TestSuite(suites)
        return test_suite
        
    @classmethod
    def get_test_files(cls):
        files = os.listdir('test')
        return filter(lambda filename: filename.startswith('test') and\
                      filename.endswith('.py'), files)

        
class PTCTestCase(unittest.TestCase):
    
    DEFAULT_SOURCE_PORT = 7777
    DEFAULT_DESTINATION_PORT = 8888
    
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.control_block = self
        self.patch_socket()
        self.patch_threads()
        
    def setUp(self):
        self.network = Network()
        self.packet_builder = ptc.common.PacketBuilder(self)
        self.end_event = threading.Event()
        self.set_up()
        
    def tearDown(self):
        self.end_event.set()
        self.tear_down()
        
    def set_up(self):
        # This should be overriden for custom test set-up.
        pass
        
    def tear_down(self):
        # This should be overriden for custom test tear-down.
        pass        
        
    def send(self, packet):
        self.network.inject(packet)
        # This is to give enough time to the protocol to process the packet.
        time.sleep(0.1)
        
    def receive(self):
        return self.network.get_next()
    
    def launch_server(self):
        launched_event = threading.Event()
        def run(socket):
            socket.bind((ptc.constants.NULL_ADDRESS,
                         self.DEFAULT_DESTINATION_PORT))
            socket.listen()
            launched_event.set()
            socket.accept()
            self.end_event.wait()
            socket.close()
        
        ptc_socket = ptc.Socket()
        thread = threading.Thread(target=run, args=(ptc_socket,))
        thread.start()
        launched_event.wait()
        return ptc_socket
    
    def patch_socket(self):
        def dummy_method(_self, *args, **kwargs):
            pass
        
        socket_class = ptc.soquete.Soquete
        setattr(socket_class, 'send', self.custom_socket_send)
        setattr(socket_class, 'receive', self.custom_socket_receive)
        setattr(socket_class, 'bind', dummy_method)
        setattr(socket_class, 'close', dummy_method)
        try:
            delattr(socket_class, '__init__')
        except:
            pass
    
    def patch_threads(self):
        thread_class = ptc.worker.PTCThread
        custom_init = getattr(self, 'custom_thread_init')
        bound_custom_init = custom_init.__get__(self, thread_class)
        setattr(thread_class, '__init__', bound_custom_init)
    
        worker_class = ptc.worker.Worker
        self.work_method = getattr(worker_class, 'work')
        def custom_work(_self):
            try:
                self.work_method(_self)
            except Exception, e:
                traceback.print_exc(e)
                os._exit(1)                
        setattr(worker_class, 'work', custom_work)

    def custom_work(self):
        pass
    
    def custom_socket_send(self, packet):
        self.network.send(packet)
        
    def custom_socket_receive(self, timeout=None):
        return self.network.receive(timeout)
    
    def custom_thread_init(self):
        # This will be executed in the context of a PTCThread object.
        superclass = self.__class__.__base__
        superclass.__init__(self)
        self.setDaemon(False)
        
    def get_source_address(self):
        return ptc.constants.NULL_ADDRESS
    
    def get_source_port(self):
        return self.DEFAULT_SOURCE_PORT
    
    def get_destination_port(self):
        return self.DEFAULT_DESTINATION_PORT    
    
    def get_destination_address(self):
        return ptc.constants.NULL_ADDRESS    
        
        
class Network(object):
    
    def __init__(self):
        self.sent_packets = Queue.Queue()
        self.injected_packets = Queue.Queue()
        
    def send(self, packet):
        self.sent_packets.put(packet)
        
    def receive(self, timeout=None):
        try:
            return self.injected_packets.get(timeout=timeout)
        except Queue.Empty:
            raise socket.timeout
    
    def inject(self, packet):
        self.injected_packets.put(packet)
        
    def get_next(self, timeout=None):
        return self.sent_packets.get(timeout=timeout)