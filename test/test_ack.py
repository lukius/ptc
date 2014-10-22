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

from base import ConnectedSocketTestCase

from ptc.packet import ACKFlag


class ACKTest(ConnectedSocketTestCase):
    
    def test_sending_ack_for_valid_segment(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        packet = self.packet_builder.build(payload=data,
                                           flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS)
        self.send(packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        ack_number = ack_packet.get_ack_number()
        
        self.assertIn(ACKFlag, ack_packet)
        self.assertEqual(ack_number, self.DEFAULT_IRS + size)
    
    def test_sending_ack_for_invalid_segment(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        packet = self.packet_builder.build(payload=data,
                                           flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS + 3*size,
                                           ack=self.DEFAULT_ISS)
        self.send(packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        ack_number = ack_packet.get_ack_number()
        
        self.assertIn(ACKFlag, ack_packet)
        self.assertEqual(ack_number, self.DEFAULT_IRS)
    
    def test_sending_ack_for_repeated_segment(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        packet = self.packet_builder.build(payload=data,
                                           flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS)
        self.send(packet)
        self.send(packet)
        ack_packet1 = self.receive(self.DEFAULT_TIMEOUT)
        ack_packet2 = self.receive(self.DEFAULT_TIMEOUT)
        ack_number1 = ack_packet1.get_ack_number()
        ack_number2 = ack_packet2.get_ack_number()
        
        self.assertIn(ACKFlag, ack_packet1)
        self.assertIn(ACKFlag, ack_packet2)
        self.assertEqual(ack_number1, self.DEFAULT_IRS + size)
        self.assertEqual(ack_number2, ack_number1)
    
    def test_sending_accumulated_ack(self):
        size = 10
        offset = 5
        to_send = self.DEFAULT_DATA[:size]
        first_chunk = to_send[offset:]
        first_chunk_seq_number = self.DEFAULT_IRS + offset
        second_chunk = to_send[:offset]
        second_chunk_seq_number = self.DEFAULT_IRS        
        first_packet = self.packet_builder.build(payload=first_chunk,
                                                 flags=[ACKFlag],
                                                 seq=first_chunk_seq_number,
                                                 ack=self.DEFAULT_ISS)
        second_packet = self.packet_builder.build(payload=second_chunk,
                                                  flags=[ACKFlag],
                                                  seq=second_chunk_seq_number,
                                                  ack=self.DEFAULT_ISS)        
        self.send(first_packet)
        self.send(second_packet)
        ack_packet1 = self.receive(self.DEFAULT_TIMEOUT)
        ack_number1 = ack_packet1.get_ack_number()
        ack_packet2 = self.receive(self.DEFAULT_TIMEOUT)
        ack_number2 = ack_packet2.get_ack_number()        
        
        self.assertIn(ACKFlag, ack_packet1)
        self.assertIn(ACKFlag, ack_packet2)
        self.assertEqual(ack_number1, self.DEFAULT_IRS)
        self.assertEqual(ack_number2, self.DEFAULT_IRS + size)
        
    def test_sending_piggybacked_ack(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        packet = self.packet_builder.build(payload=data,
                                           flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS,
                                           window=self.DEFAULT_IW)
        self.send(packet)
        self.receive(self.DEFAULT_TIMEOUT)
        self.socket.send(data)
        packet = self.receive(self.DEFAULT_TIMEOUT)
        ack_number = packet.get_ack_number()
        payload = packet.get_payload()
        
        self.assertIn(ACKFlag, packet)
        self.assertEqual(ack_number, self.DEFAULT_IRS + size)
        self.assertEqual(data, payload)
    
    def test_not_sending_ack_for_ack_segment(self):
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS)
        self.send(packet)
        
        self.assertRaises(socket.timeout, self.receive, self.DEFAULT_TIMEOUT)
        
    def test_send_window_update_after_recv(self):
        size = 10
        data = self.DEFAULT_DATA[:size]        
        packet = self.packet_builder.build(payload=data,
                                           flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS,
                                           window=self.DEFAULT_IW)
        self.send(packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        window = ack_packet.get_window_size()
        expected_ack = ack_packet.get_ack_number()
        self.assertEquals(0, window)
        
        received_data = self.socket.recv(size)
        wnd_packet = self.receive(self.DEFAULT_TIMEOUT)
        new_window = wnd_packet.get_window_size()
        
        self.assertEquals(size, new_window)
        self.assertEquals(expected_ack, wnd_packet.get_ack_number())
        self.assertEquals(0, len(wnd_packet.get_payload()))
        self.assertEquals(data, received_data)