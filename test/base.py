# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


import collections
import os
import Queue
import socket
import threading
import time
import traceback
import unittest

import ptc


class PTCTestSuite(object):

    SOURCE_FILES = os.listdir('test')
    
    @classmethod
    def build_from(cls, args):
        test_files = cls.get_test_files_from(args)
        return cls.get_test_suite_from(test_files)

    @classmethod
    def get_test_suite_from(cls, test_files):
        test_loader = unittest.defaultTestLoader
        test_modules = map(lambda filename: 'test.%s' % filename[:-3],
                           test_files)
        suites = map(test_loader.loadTestsFromName, test_modules) 
        test_suite = unittest.TestSuite(suites)
        return test_suite

    @classmethod
    def get_test_files_from(cls, args):
        if len(args) == 1:
            return cls.get_all_test_files()
        tests = list()    
        args = args[1:]
        for arg in args:
            if not arg.startswith('--'):
                continue
            arg = arg.lower()
            if not arg.startswith('--test'):
                test = 'test_%s.py' % arg[2:]
            else:
                test = '%s.py' % arg[2:]
            test = test.replace('-', '_')
            if cls.test_is_valid(test):
                tests.append(test)
        return tests

    @classmethod
    def get_all_test_files(cls):
        return filter(lambda filename: filename.startswith('test') and\
                      filename.endswith('.py'), cls.SOURCE_FILES)

    @classmethod
    def test_is_valid(cls, test):
        return test in cls.SOURCE_FILES

        
class PTCTestCase(unittest.TestCase):
    
    DEFAULT_SRC_ADDRESS = '192.168.0.101'
    DEFAULT_DST_ADDRESS = '192.168.0.102'
    DEFAULT_SRC_PORT = 7777
    DEFAULT_DST_PORT = 8888
    DEFAULT_TIMEOUT = 1
    
    def setUp(self):
        self.network = Network()
        self.end_event = threading.Event()
        self.threads = list()
        self.patch_socket()
        self.patch_threads()
        self.set_up_packet_builder()
        self.set_up()
        
    def tearDown(self):
        self.tear_down()
        self.end_event.set()
        self.join_threads()
        self.restore_socket()
        self.restore_threads()
        
    def set_up_packet_builder(self):
        self.packet_builder = ptc.packet_utils.PacketBuilder()
        self.packet_builder.set_source_address(self.DEFAULT_SRC_ADDRESS)
        self.packet_builder.set_source_port(self.DEFAULT_SRC_PORT)
        self.packet_builder.set_destination_port(self.DEFAULT_DST_PORT)
        self.packet_builder.set_destination_address(self.DEFAULT_DST_ADDRESS)
        
    def set_up(self):
        # Overridear en subclases para dar comportamiento de setUp.
        pass
        
    def tear_down(self):
        # Ídem anterior.
        pass        
    
    def join_threads(self):
        for thread in self.threads:
            if thread.is_alive():
                thread.join()
        
    def send(self, packet):
        self.network.send(packet)
        # Para darle tiempo suficiente al protocolo para poder procesar el
        # paquete.
        time.sleep(0.1)
        
    def receive(self, timeout=None):
        address = self.DEFAULT_SRC_ADDRESS
        port = self.DEFAULT_SRC_PORT 
        packet = self.network.receive_for(address, port, timeout=timeout)
        if packet is None:
            self.fail('Something went wrong. See details above.')
        return packet
    
    def patch_socket(self):
        def custom_send(_self, packet):
            self.network.send(packet)

        def custom_receive(_self, timeout=None):
            address = _self.address
            port = _self.port
            return self.network.receive_for(address, port, timeout=timeout)
        
        def custom_bind(_self, address, port):
            _self.address = address
            _self.port = port
        
        def dummy_method(_self, *args, **kwargs):
            pass
        
        socket_class = ptc.soquete.Soquete
        self.socket_send = getattr(socket_class, 'send')
        self.socket_receive = getattr(socket_class, 'receive')
        self.socket_bind = getattr(socket_class, 'bind')
        self.socket_close = getattr(socket_class, 'close')
        self.socket_init = getattr(socket_class, '__init__')
        
        setattr(socket_class, 'send', custom_send)
        setattr(socket_class, 'receive', custom_receive)
        setattr(socket_class, 'bind', custom_bind)
        setattr(socket_class, 'close', dummy_method)
        delattr(socket_class, '__init__')
    
    def patch_threads(self):
        def custom_run(_self):
            try:
                self.thread_run(_self)
            except Exception, e:
                traceback.print_exc(e)
                self.network.close()
                _self.protocol.free()
                     
        def custom_init(_self, protocol):
            threading.Thread.__init__(_self)
            _self.protocol = protocol
            _self.setDaemon(False)
            _self.keep_running = True
            self.threads.append(_self)
        
        thread_class = ptc.thread.PTCThread
        self.thread_init = getattr(thread_class, '__init__')
        self.thread_run = getattr(thread_class, 'run')
        setattr(thread_class, '__init__', custom_init)
        setattr(thread_class, 'run', custom_run)

    def restore_socket(self):
        socket_class = ptc.soquete.Soquete
        setattr(socket_class, 'send', self.socket_send)
        setattr(socket_class, 'receive', self.socket_receive)
        setattr(socket_class, 'bind', self.socket_bind)
        setattr(socket_class, 'close', self.socket_close)
        setattr(socket_class, '__init__', self.socket_init)

    def restore_threads(self):
        thread_class = ptc.thread.PTCThread
        setattr(thread_class, 'run', self.thread_run)
        setattr(thread_class, '__init__', self.thread_init)
        
    def launch_server(self, address=None, port=None):
        launched_event = threading.Event()
        if address is None:
            address = self.DEFAULT_DST_ADDRESS
        if port is None:
            port = self.DEFAULT_DST_PORT
            
        def run(socket):
            socket.bind((address, port))
            socket.listen()
            launched_event.set()
            try:
                socket.accept(timeout=self.DEFAULT_TIMEOUT)
                self.end_event.wait()
                socket.free()
            except Exception, e:
                traceback.print_exc(e)
                self.network.close()
        
        ptc_socket = ptc.Socket()
        thread = threading.Thread(target=run, args=(ptc_socket,))
        thread.start()
        launched_event.wait()
        return ptc_socket
    
    def launch_client(self, address=None, port=None):
        if address is None:
            address = self.DEFAULT_DST_ADDRESS
        if port is None:
            port = self.DEFAULT_DST_PORT
                    
        def run(socket):
            socket.bind((address, port))
            try:
                socket.connect((self.DEFAULT_SRC_ADDRESS,
                                self.DEFAULT_SRC_PORT))
                self.end_event.wait()
                socket.free()
            except Exception, e:
                traceback.print_exc(e)
                self.network.close()
        
        ptc_socket = ptc.Socket()
        thread = threading.Thread(target=run, args=(ptc_socket,))
        thread.start()
        return ptc_socket        
        

class ConnectedSocketTestCase(PTCTestCase):
    
    DEFAULT_ISS = ptc.seqnum.SequenceNumber(20)
    DEFAULT_IRS = ptc.seqnum.SequenceNumber(10)
    DEFAULT_IW = 10
    DEFAULT_DATA = 'data' * 5
    DEFAULT_TIMEOUT = 1
    
    def set_up(self):
        src_address, src_port = self.DEFAULT_DST_ADDRESS, self.DEFAULT_DST_PORT
        dst_address, dst_port = self.DEFAULT_SRC_ADDRESS, self.DEFAULT_SRC_PORT
        self.socket = self.get_connected_socket(src_address=src_address,
                                                src_port=src_port,
                                                dst_address=dst_address,
                                                dst_port=dst_port,
                                                iss=self.DEFAULT_ISS,
                                                irs=self.DEFAULT_IRS,
                                                send_window=self.DEFAULT_IW,
                                                receive_window=self.DEFAULT_IW)
        
    def tear_down(self):
        self.socket.protocol.free()    

    def get_connected_socket(self, src_address, src_port, dst_address,
                             dst_port, iss, irs, send_window, receive_window):
        ptc_socket = ptc.Socket()
        ptc_socket.bind((src_address, src_port))
        ptc_socket.protocol.start_threads()
        ptc_socket.protocol.state = ptc.constants.ESTABLISHED
        ptc_socket.protocol.connected_event = threading.Event()
        control_block = ptc.protocol.PTCControlBlock(iss, irs, send_window,
                                                     receive_window)
        ptc_socket.protocol.control_block = control_block
        ptc_socket.protocol.packet_handler.control_block = control_block
        ptc_socket.protocol.set_destination_on_packet_builder(dst_address,
                                                              dst_port)
        return ptc_socket        
    

class Network(object):
    
    def __init__(self):
        self.channels = collections.defaultdict(Queue.Queue)
        self.channels_lock = threading.Lock()
        self.is_closed = False
        
    def close(self):
        for channel in self.channels.values():
            channel.put(None)
        self.is_closed = True
        
    def get_channel_for(self, address, port):
        with self.channels_lock:
            key = (address, port)
            return self.channels[key] 
        
    def get_channel_for_destination(self, packet):
        address = packet.get_destination_ip()
        port = packet.get_destination_port()
        return self.get_channel_for(address, port)
        
    def send(self, packet):
        channel = self.get_channel_for_destination(packet)
        channel.put(packet)
        
    def receive_for(self, address, port, timeout=None):
        if self.is_closed:
            return None
        channel = self.get_channel_for(address, port)
        try:
            return channel.get(timeout=timeout)
        except Queue.Empty:
            raise socket.timeout
