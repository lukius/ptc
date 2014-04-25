import threading
import traceback

import ptc
from ptc.packet import SYNFlag, ACKFlag
from base import PTCTestCase


class SYNTest(PTCTestCase):

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
                socket.accept()
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

    def test_server_connection(self):
        # 1. Create a server instance
        server = self.launch_server()
        self.assertEquals(server.protocol.state, ptc.constants.LISTEN)

        # 2. Send SYN
        seq_number = 1111
        syn_packet = self.packet_builder.build(flags=[SYNFlag], seq=seq_number)
        self.send(syn_packet)

        # 3. Get SYN/ACK
        syn_ack_packet = self.receive()
        received_seq_number = syn_ack_packet.get_seq_number()
        received_ack_number = syn_ack_packet.get_ack_number()
        self.assertIn(SYNFlag, syn_ack_packet)
        self.assertIn(ACKFlag, syn_ack_packet)
        self.assertEquals(received_ack_number, seq_number)
        self.assertEquals(server.protocol.state, ptc.constants.SYN_RCVD)
        
        # 4. Send ACK
        ack_packet = self.packet_builder.build(flags=[ACKFlag], seq=seq_number,
                                               ack=received_seq_number)
        self.send(ack_packet)
        
        # 5. Assert that the connection is established
        self.assertEquals(server.protocol.state, ptc.constants.ESTABLISHED)
    
    def test_client_connection(self):
        # 1. Create a client instance
        client = self.launch_client()
        
        # 2. Receive SYN
        syn_packet = self.receive()
        received_seq_number = syn_packet.get_seq_number()
        self.assertIn(SYNFlag, syn_packet)
        self.assertEquals(client.protocol.state, ptc.constants.SYN_SENT)
        
        # 3. Send SYN/ACK
        seq_number = 1111
        syn_ack_packet = self.packet_builder.build(flags=[SYNFlag, ACKFlag],
                                                   seq=seq_number,
                                                   ack=received_seq_number)
        self.send(syn_ack_packet)
        
        # 4. Receive ACK and assert that the connection is established
        ack_packet = self.receive()
        received_ack_number = ack_packet.get_ack_number()
        self.assertIn(ACKFlag, ack_packet)
        self.assertEquals(received_ack_number, seq_number)
        self.assertEquals(client.protocol.state, ptc.constants.ESTABLISHED)        