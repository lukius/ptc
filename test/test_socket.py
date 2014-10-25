from ptc import Socket
from ptc.exceptions import PTCError

from test.base import PTCTestCase, ConnectedSocket
from ptc.constants import FIN_WAIT2
import threading
from ptc.packet import FINFlag, ACKFlag


class PTCSocketTest(PTCTestCase):
    
    IP_ADDRESS = '127.0.0.1'
    PORT = 5555
    ADDRESS = (IP_ADDRESS, PORT)
    TIMEOUT = 0.5
    
    def set_up(self):
        self.socket = Socket()
    
    def test_timeout_on_connect(self):
        self.assertRaises(PTCError, self.socket.connect,
                          self.ADDRESS, timeout=self.TIMEOUT)
    
    def test_timeout_on_accept(self):
        self.socket.bind(self.ADDRESS)
        self.socket.listen()
        self.assertRaises(PTCError, self.socket.accept,
                          timeout=self.TIMEOUT)
        
    def test_send_and_recv_on_closed_sockets(self):
        self.assertRaises(PTCError, self.socket.send, 'data')
        self.assertRaises(PTCError, self.socket.recv, 1)
        
    def test_recv_interrupted_when_connection_ends(self):
        socket = ConnectedSocket()
        self.recv_interrupted = False
        # A single byte to feed the socket in order to abort the test.
        # Used only if the recv call is not interrupted.
        dummy_data = 'x'

        # This will run in a new thread.
        def recv():
            try:
                socket.recv(10)
            except PTCError:
                self.recv_interrupted = True
        
        # Thread to abort the test if the recv call is not interrupted.
        timeout = 3
        def recv_timeout_handler():
            socket.free()
            socket.protocol.control_block.in_buffer.put(dummy_data)
            
        socket.protocol.state = FIN_WAIT2
        # This packet will close the connection.
        fin_packet = self.packet_builder.build(flags=[FINFlag, ACKFlag],
                                               seq=socket.DEFAULT_IRS,
                                               ack=socket.DEFAULT_ISS)
        recv_thread = threading.Thread(target=recv)
        timer = threading.Timer(timeout, recv_timeout_handler)
        recv_thread.start()
        timer.start()
        self.send(fin_packet)
        recv_thread.join()
        timer.cancel()
        self.assertTrue(self.recv_interrupted)
        socket.free()