# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


import unittest

from ptc.packet import PTCPacket, SYNFlag, ACKFlag
from ptc.packet_utils import PacketDecoder


class PacketTest(unittest.TestCase):

    PAYLOAD = 'payload'
    SOURCE_IP = '192.168.0.101'
    DESTINATION_IP = '192.168.0.102'
    SOURCE_PORT = 55221
    DESTINATION_PORT = 22
    SEQ_NUMBER = 1234
    ACK_NUMBER = 10
    WINDOW_SIZE = 10000

    def get_custom_packet(self):
        packet = PTCPacket()
        packet.set_source_ip(self.SOURCE_IP)
        packet.set_destination_ip(self.DESTINATION_IP)
        packet.set_source_port(self.SOURCE_PORT)
        packet.set_destination_port(self.DESTINATION_PORT)
        packet.set_payload(self.PAYLOAD)
        packet.set_seq_number(self.SEQ_NUMBER)
        packet.set_ack_number(self.ACK_NUMBER)
        packet.set_window_size(self.WINDOW_SIZE)
        packet.add_flags([SYNFlag, ACKFlag])
        return packet
    
    def get_expected_packet_bytes(self):
        packet_bytes = "E\x00\x00$\x00\x00@\x00\xff\xca\x00\x00\xc0\xa8\x00e"
        packet_bytes += "\xc0\xa8\x00f\xd7\xb5\x00\x16\x00\x00\x04\xd2\x00"
        packet_bytes += "\x00\x00\n\x00\x12'\x10payload"
        return packet_bytes
    
    def build_packet_from_bytes(self, packet_bytes):
        packet_decoder = PacketDecoder()
        packet = packet_decoder.decode(packet_bytes)
        return packet

    def test_bytes_from_packet(self):
        packet = self.get_custom_packet()
        packet_bytes = packet.get_bytes()
        expected_packet_bytes = self.get_expected_packet_bytes()
        
        ip_id_offset = 4
        checksum_offset = 10
        packet_bytes = packet_bytes[:ip_id_offset] + '\0'*2 +\
                       packet_bytes[ip_id_offset+2:]
        packet_bytes = packet_bytes[:checksum_offset] + '\0'*2 +\
                       packet_bytes[checksum_offset+2:]
                                                 
        self.assertEqual(packet_bytes, expected_packet_bytes)
        
    def test_packet_from_bytes(self):
        packet_bytes = self.get_expected_packet_bytes()
        packet = self.build_packet_from_bytes(packet_bytes)
        
        source_ip = packet.get_source_ip()
        source_port = packet.get_source_port()
        destination_ip = packet.get_destination_ip()
        destination_port = packet.get_destination_port()
        seq_number = packet.get_seq_number()
        ack_number = packet.get_ack_number()
        window_size = packet.get_window_size()
        payload = packet.get_payload()
        flags = packet.get_flags()        
        
        self.assertEqual(source_ip, self.SOURCE_IP)
        self.assertEqual(source_port, self.SOURCE_PORT)
        self.assertEqual(destination_ip, self.DESTINATION_IP)
        self.assertEqual(destination_port, self.DESTINATION_PORT)
        self.assertEqual(seq_number, self.SEQ_NUMBER)
        self.assertEqual(ack_number, self.ACK_NUMBER)
        self.assertIn(SYNFlag, flags)
        self.assertIn(ACKFlag, flags)
        self.assertEqual(window_size, self.WINDOW_SIZE)
        self.assertEqual(payload, self.PAYLOAD)