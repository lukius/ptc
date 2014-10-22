# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


from base import FileTransferBase


class FileTransferClient(FileTransferBase):

    def __init__(self):
        FileTransferBase.__init__(self)
        self.incoming_filename = 'thunder.jpg'
        self.outgoing_filename = 'dwight.jpg'
        
    def _connect_socket(self, sock):
        sock.connect((self.server_ip, self.server_port), timeout=10)

        
if __name__ == '__main__':
    FileTransferClient().run()