from base import FileTransferBase


class FileTransferServer(FileTransferBase):

    def __init__(self):
        FileTransferBase.__init__(self)
        self.incoming_filename = 'dwight.jpg'
        self.outgoing_filename = 'thunder.jpg'
        
    def _connect_socket(self, sock):
        sock.bind((self.server_ip, self.server_port))
        sock.listen()
        sock.accept(timeout=10)
        
        
if __name__ == '__main__':
    FileTransferServer().run()