import sys
try:
    from ptc import Socket
except:
    sys.path.append('../../')
    from ptc import Socket


class FileTransferBase(object):
    
    CHUNK_SIZE = 500
    DEFAULT_IP = '127.0.0.1'
    DEFAULT_PORT = 6677    
    
    def __init__(self):
        self.received_bytes = str()
        self._initialize_address()
        
    def _initialize_address(self):
        # Address and port can be supplied by command-line arguments.
        if len(sys.argv) >= 4:
            self.server_ip = sys.argv[1]
            self.server_port = int(sys.argv[2])
        elif len(sys.argv) == 3:
            self.server_ip = sys.argv[1]
            self.server_port = self.DEFAULT_PORT
        else:
            self.server_ip = self.DEFAULT_IP
            self.server_port = self.DEFAULT_PORT        

    def run(self):
        to_send = open(self.outgoing_filename).read()
        expected_size = len(open(self.incoming_filename).read())
        with Socket() as sock:
            # Socket connection is implemented by subclasses.
            # The client actively connects, while the server will bind to a
            # given address and listen.
            self._connect_socket(sock)
            i = 0
            # In order to receive the file, iterate until we complete the
            # desired length.
            while len(self.received_bytes) < expected_size:
                # Being the protocol full-duplex, at the same time we can also
                # send some data to the other side.
                sock.send(to_send[i:i+self.CHUNK_SIZE])
                chunk = sock.recv(self.CHUNK_SIZE)
                self.received_bytes += chunk
                i += self.CHUNK_SIZE
            # Finally, send every remaining byte.
            if i < len(to_send):
                sock.send(to_send[i:])
            sock.close()
        self._write_file()
    
    def _write_file(self):
        incoming_filename = 'recvd_%s' % self.incoming_filename
        out_file = open(incoming_filename, 'w')
        out_file.write(self.received_bytes)
        out_file.close()

    def _connect_socket(self, sock):
        raise NotImplementedError