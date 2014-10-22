# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


import ptc
from ptc.packet import SYNFlag, ACKFlag
from base import PTCTestCase


class SYNTest(PTCTestCase):
    
    def test_server_connection(self):
        # 1. Crear un socket "servidor"
        server = self.launch_server()
        self.assertEquals(ptc.constants.LISTEN, server.protocol.state)

        # 2. Mandarle SYN
        seq_number = 1111
        syn_packet = self.packet_builder.build(flags=[SYNFlag], seq=seq_number)
        self.send(syn_packet)

        # 3. Obtener SYN/ACK
        syn_ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        received_seq_number = syn_ack_packet.get_seq_number()
        received_ack_number = syn_ack_packet.get_ack_number()
        self.assertIn(SYNFlag, syn_ack_packet)
        self.assertIn(ACKFlag, syn_ack_packet)
        self.assertEquals(seq_number+1, received_ack_number)
        self.assertEquals(ptc.constants.SYN_RCVD, server.protocol.state)
        
        # 4. Mandarle ACK
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=seq_number+1,
                                               ack=received_seq_number+1)
        self.send(ack_packet)
        snd_nxt = server.protocol.control_block.get_snd_nxt()
        snd_una = server.protocol.control_block.get_snd_una()
        rcv_nxt = server.protocol.control_block.get_rcv_nxt()
        
        # 5. Verificar que la conexión se estableció y que el bloque de control
        # quedó bien configurado.
        self.assertEquals(received_seq_number+1, snd_nxt)
        self.assertEquals(snd_nxt, snd_una)
        self.assertEquals(seq_number+1, rcv_nxt)
        self.assertEquals(ptc.constants.ESTABLISHED, server.protocol.state)
    
    def test_client_connection(self):
        # 1. Crear un socket "cliente".
        client = self.launch_client()
        
        # 2. Recibir su SYN.
        syn_packet = self.receive(self.DEFAULT_TIMEOUT)
        received_seq_number = syn_packet.get_seq_number()
        self.assertIn(SYNFlag, syn_packet)
        self.assertEquals(ptc.constants.SYN_SENT, client.protocol.state)
        
        # 3. Mandarle SYN/ACK.
        seq_number = 1111
        syn_ack_packet = self.packet_builder.build(flags=[SYNFlag, ACKFlag],
                                                   seq=seq_number,
                                                   ack=received_seq_number+1)
        self.send(syn_ack_packet)
        snd_nxt = client.protocol.control_block.get_snd_nxt()
        snd_una = client.protocol.control_block.get_snd_una()
        rcv_nxt = client.protocol.control_block.get_rcv_nxt()        
        
        # 4. Recibir el ACK y verificar que la conexión está establecida, y que
        # el bloque de control quedó bien configurado.
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        new_seq_number  = ack_packet.get_seq_number()
        received_ack_number = ack_packet.get_ack_number()
        self.assertIn(ACKFlag, ack_packet)
        self.assertEquals(seq_number+1, received_ack_number)
        self.assertEquals(received_seq_number+1, new_seq_number)
        self.assertEquals(received_seq_number+1, snd_nxt)
        self.assertEquals(snd_nxt, snd_una)
        self.assertEquals(seq_number+1, rcv_nxt)
        self.assertEquals(ptc.constants.ESTABLISHED, client.protocol.state)