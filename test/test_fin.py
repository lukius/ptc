# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


import socket
import threading
import time

from base import ConnectedSocketTestCase
from ptc.constants import SHUT_RD, SHUT_WR,\
                          ESTABLISHED, FIN_WAIT1, FIN_WAIT2, CLOSED,\
                          CLOSE_WAIT, LAST_ACK, CLOSING,\
                          INITIAL_RTO, CLOCK_TICK
from ptc.exceptions import PTCError
from ptc.packet import ACKFlag, FINFlag


class FINTest(ConnectedSocketTestCase):
    
    def set_state_on_socket(self, state):
        # Simular lo que hace el protocolo al transicionar a estos estados.
        self.socket.protocol.state = state
        if state == CLOSE_WAIT:
            self.socket.protocol.read_stream_open = False
        if state in [FIN_WAIT1, FIN_WAIT2]:
            self.socket.protocol.write_stream_open = False
        if state == FIN_WAIT1:
            # Para simular que ya fue enviado el FIN.
            self.socket.protocol.control_block.increment_snd_nxt()        
    
    def test_close_read_stream(self):
        data_size = 10
        data = self.DEFAULT_DATA[:data_size]
        data_packet = self.packet_builder.build(flags=[ACKFlag],
                                                seq=self.DEFAULT_IRS,
                                                ack=self.DEFAULT_ISS,
                                                window=self.DEFAULT_IW,
                                                payload=data)
        self.send(data_packet)
        # Descartar ACK.
        self.receive(self.DEFAULT_TIMEOUT)
        self.socket.shutdown(SHUT_RD)
        data_packet = self.packet_builder.build(flags=[ACKFlag],
                                                seq=self.DEFAULT_IRS+data_size,
                                                ack=self.DEFAULT_ISS,
                                                window=self.DEFAULT_IW,
                                                payload=data)        
        self.send(data_packet)
        self.receive(self.DEFAULT_TIMEOUT)
        data_received = self.socket.recv(2*data_size)
        
        self.assertEquals(ESTABLISHED, self.socket.protocol.state)
        # Los datos después del shutdown deberían ignorarse.
        self.assertEquals(data, data_received)
        
        # El stream de salida debería estar funcionando bien.
        self.socket.send(data)
        # Para ignorar el paquete de actualización de ventana.
        self.receive(self.DEFAULT_TIMEOUT)
        packet = self.receive(self.DEFAULT_TIMEOUT)
        self.assertNotIn(FINFlag, packet)
        self.assertEquals(data, packet.get_payload())
        
    def test_close_write_stream_without_pending_data(self):
        self.socket.shutdown(SHUT_WR)
        fin_packet = self.receive(self.DEFAULT_TIMEOUT)
        seq_number = fin_packet.get_seq_number()
        
        self.assertEquals(FIN_WAIT1, self.socket.protocol.state)
        self.assertIn(FINFlag, fin_packet)
        self.assertEquals(0, len(fin_packet.get_payload()))
        self.assertEquals(self.DEFAULT_ISS, seq_number)

    def receive_fin_and_assert_retransmissions(self, data_packet):
        packet = self.receive(self.DEFAULT_TIMEOUT)
        while FINFlag not in packet:
            # Esto debería ser una retransmisión.
            self.assertEquals(data_packet.get_seq_number(),
                              packet.get_seq_number())
            self.assertEquals(data_packet.get_payload(), packet.get_payload())
            packet = self.receive(self.DEFAULT_TIMEOUT)
        return packet

    def test_close_write_stream_with_pending_data(self):
        data_size = 10
        data = self.DEFAULT_DATA[:data_size]
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=self.DEFAULT_ISS+data_size)          
        self.socket.send(data)
        data_packet = self.receive(self.DEFAULT_TIMEOUT)
        self.socket.shutdown(SHUT_WR)
        self.assertRaises(PTCError, self.socket.send, self.DEFAULT_DATA)

        time.sleep(INITIAL_RTO * CLOCK_TICK)
        retransmitted_packet = self.receive(self.DEFAULT_TIMEOUT)
        self.send(ack_packet)
        
        self.assertNotIn(FINFlag, data_packet)
        self.assertNotIn(FINFlag, retransmitted_packet)
        self.assertEquals(data, data_packet.get_payload())
        self.assertEquals(data, retransmitted_packet.get_payload())
        
        fin_packet = self.receive_fin_and_assert_retransmissions(data_packet)
        seq_number = fin_packet.get_seq_number()
        
        self.assertEquals(FIN_WAIT1, self.socket.protocol.state)
        self.assertIn(FINFlag, fin_packet)
        self.assertEquals(0, len(fin_packet.get_payload()))
        self.assertEquals(self.DEFAULT_ISS+data_size, seq_number)
        
    def test_receive_ack_after_sending_fin(self):
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=1+self.DEFAULT_ISS) 
        self.set_state_on_socket(FIN_WAIT1)
        self.send(ack_packet)
        
        self.assertEquals(FIN_WAIT2, self.socket.protocol.state)
        # No deberíamos recibir nada.
        self.assertRaises(socket.timeout, self.receive, self.DEFAULT_TIMEOUT)

    def test_send_ack_on_fin_wait1(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        # El #ACK es "viejo" porque sólo interesa enviar datos y recibir el ACK
        # respectivo.
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS-1,
                                           payload=data) 
        self.set_state_on_socket(FIN_WAIT1)
        self.send(packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        ack_number = ack_packet.get_ack_number()
        rcv_nxt = self.socket.protocol.control_block.get_rcv_nxt()
        data_received = self.socket.recv(size)
        
        self.assertEquals(self.DEFAULT_IRS+size, ack_number)
        self.assertEquals(ack_number, rcv_nxt)
        self.assertEquals(FIN_WAIT1, self.socket.protocol.state)
        self.assertEquals(data, data_received)
        
    def test_receive_fin_ack_after_sending_fin(self):
        packet = self.packet_builder.build(flags=[FINFlag, ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=1+self.DEFAULT_ISS) 
        self.set_state_on_socket(FIN_WAIT1)
        self.send(packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        ack_number = ack_packet.get_ack_number()
        
        self.assertEquals(CLOSED, self.socket.protocol.state)
        self.assertIn(ACKFlag, ack_packet)
        self.assertEquals(1+self.DEFAULT_IRS, ack_number)
        
    def test_simultaneous_close(self):
        packet = self.packet_builder.build(flags=[FINFlag, ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS) 
        self.set_state_on_socket(FIN_WAIT1)
        self.send(packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        ack_number = ack_packet.get_ack_number()
        
        self.assertEquals(CLOSING, self.socket.protocol.state)
        self.assertIn(ACKFlag, ack_packet)
        self.assertEquals(1+self.DEFAULT_IRS, ack_number)
        
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=1+self.DEFAULT_ISS)
        self.send(packet)
        
        self.assertRaises(socket.timeout, self.receive, self.DEFAULT_TIMEOUT)
        self.assertEquals(CLOSED, self.socket.protocol.state)
                
    def test_receive_data_when_write_stream_is_closed(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        data_packet = self.packet_builder.build(flags=[ACKFlag],
                                                seq=self.DEFAULT_IRS,
                                                ack=self.DEFAULT_ISS,
                                                payload=data) 
        self.set_state_on_socket(FIN_WAIT2)
        self.send(data_packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        seq_number = ack_packet.get_seq_number()
        ack_number = ack_packet.get_ack_number()
        
        self.assertEquals(FIN_WAIT2, self.socket.protocol.state)
        self.assertEquals(self.DEFAULT_ISS, seq_number)
        self.assertEquals(self.DEFAULT_IRS+size, ack_number)
        self.assertEquals(0, len(ack_packet.get_payload()))
        
    def test_receive_fin_on_established(self):
        fin_packet = self.packet_builder.build(flags=[ACKFlag, FINFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=self.DEFAULT_ISS) 
        self.send(fin_packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        seq_number = ack_packet.get_seq_number()
        ack_number = ack_packet.get_ack_number()
        
        self.assertEquals(CLOSE_WAIT, self.socket.protocol.state)
        self.assertFalse(self.socket.protocol.read_stream_open)
        self.assertEquals(self.DEFAULT_ISS, seq_number)
        self.assertEquals(1+self.DEFAULT_IRS, ack_number)
        self.assertEquals(0, len(ack_packet.get_payload()))
        
    def test_fin_with_unexpected_seq_number_is_ignored(self):
        fin_packet = self.packet_builder.build(flags=[ACKFlag, FINFlag],
                                               seq=self.DEFAULT_IRS+10,
                                               ack=self.DEFAULT_ISS) 
        self.send(fin_packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        seq_number = ack_packet.get_seq_number()
        ack_number = ack_packet.get_ack_number()
        
        self.assertEquals(ESTABLISHED, self.socket.protocol.state)
        self.assertTrue(self.socket.protocol.read_stream_open)
        self.assertEquals(self.DEFAULT_ISS, seq_number)
        self.assertEquals(self.DEFAULT_IRS, ack_number)
        self.assertEquals(0, len(ack_packet.get_payload()))
               
    def test_receive_fin_on_fin_wait2(self):
        fin_packet = self.packet_builder.build(flags=[ACKFlag, FINFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=self.DEFAULT_ISS) 
        self.set_state_on_socket(FIN_WAIT2)
        self.send(fin_packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        seq_number = ack_packet.get_seq_number()
        ack_number = ack_packet.get_ack_number()
        
        self.assertEquals(CLOSED, self.socket.protocol.state)
        self.assertFalse(self.socket.protocol.read_stream_open)
        self.assertEquals(self.DEFAULT_ISS, seq_number)
        self.assertEquals(1+self.DEFAULT_IRS, ack_number)
        self.assertEquals(0, len(ack_packet.get_payload()))
        
    def test_ignore_data_packets_on_close_wait(self):
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS,
                                           payload=self.DEFAULT_DATA) 
        self.set_state_on_socket(CLOSE_WAIT)
        self.send(packet)
        
        self.assertRaises(socket.timeout, self.receive, self.DEFAULT_TIMEOUT)
        self.assertEquals(CLOSE_WAIT, self.socket.protocol.state)

    def test_close_write_stream_on_close_wait(self):
        self.set_state_on_socket(CLOSE_WAIT)
        self.socket.shutdown(SHUT_WR)
        fin_packet = self.receive(self.DEFAULT_TIMEOUT)
        seq_number = fin_packet.get_seq_number()
        
        self.assertEquals(LAST_ACK, self.socket.protocol.state)
        self.assertIn(FINFlag, fin_packet)
        self.assertEquals(0, len(fin_packet.get_payload()))
        self.assertEquals(self.DEFAULT_ISS, seq_number)
        
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=1+self.DEFAULT_ISS)
        self.send(ack_packet)
        
        self.assertEquals(CLOSED, self.socket.protocol.state)
        self.assertRaises(socket.timeout, self.receive, self.DEFAULT_TIMEOUT)
        
    def test_send_data_on_close_wait(self):
        self.set_state_on_socket(CLOSE_WAIT)
        size = 5
        data = self.DEFAULT_DATA[:size]
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=size+self.DEFAULT_ISS)
        self.socket.send(data)
        data_packet = self.receive(self.DEFAULT_TIMEOUT)
        self.send(ack_packet)
        snd_una = self.socket.protocol.control_block.get_snd_una()
        
        self.assertEquals(data, data_packet.get_payload())
        self.assertEquals(size+self.DEFAULT_ISS, snd_una)
        
    def test_close_socket(self):
        def send_ack():
            ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                                   seq=self.DEFAULT_IRS,
                                                   ack=1+self.DEFAULT_ISS)
            self.send(ack_packet)

        # La llamada a close de abajo va a bloquear el thread principal.
        # Definimos un timer que lo va a desbloquear al enviarlo un ACK para el
        # FIN disparado por ese close.
        ack_sender = threading.Timer(1, send_ack)
        ack_sender.start()
        self.socket.close()
        
        self.assertEquals(CLOSED, self.socket.protocol.state)
        self.assertFalse(self.socket.protocol.write_stream_open)
        self.assertFalse(self.socket.protocol.read_stream_open)