# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


from base import ConnectedSocketTestCase

from ptc.packet import ACKFlag


class DataExchangeTest(ConnectedSocketTestCase):
    
    def receive_data(self):
        data = str()
        timeout = 0.5
        seqs_seen = set()
        while True:
            try:
                packet = self.receive(timeout)
            except:
                break
            seq_number, ack_number = packet.get_seq_interval()
            # Esto es para evitar extraer datos de retransmisiones.
            if seq_number not in seqs_seen:
                seqs_seen.add(seq_number)
                data += packet.get_payload()
                ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                                       seq=self.DEFAULT_IRS,
                                                       ack=ack_number,
                                                       window=self.DEFAULT_IW)
                self.send(ack_packet)
        return data
    
    def test_sending_data(self):
        self.socket.send(self.DEFAULT_DATA)
        data = self.receive_data()
        self.assertEqual(self.DEFAULT_DATA, data)
        
    def test_receiving_data_out_of_order(self):
        size = 9
        offset = 4
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
        received = self.socket.recv(len(self.DEFAULT_DATA))
        
        self.assertEqual(to_send, received)
    
    def test_receiving_repeated_data(self):
        size = 10
        offset = 4
        to_send = self.DEFAULT_DATA[:size]
        first_chunk = to_send[:offset]
        first_chunk_seq_number = self.DEFAULT_IRS        
        second_chunk = to_send[offset:]
        second_chunk_seq_number = self.DEFAULT_IRS + offset
        first_packet = self.packet_builder.build(payload=first_chunk,
                                                 flags=[ACKFlag],
                                                 seq=first_chunk_seq_number,
                                                 ack=self.DEFAULT_ISS)
        second_packet = self.packet_builder.build(payload=second_chunk,
                                                  flags=[ACKFlag],
                                                  seq=second_chunk_seq_number,
                                                  ack=self.DEFAULT_ISS)        
        self.send(first_packet)
        self.send(first_packet)
        self.send(second_packet)
        self.send(second_packet)
        received = self.socket.recv(len(self.DEFAULT_DATA))
        
        self.assertEqual(to_send, received)
    
    def test_sending_and_receiving_data(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        packet = self.packet_builder.build(payload=data,
                                           flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS,
                                           window=self.DEFAULT_IW)
        self.socket.send(data)
        self.send(packet)
        
        received = self.socket.recv(size)
        packet = self.receive(self.DEFAULT_TIMEOUT)
        # El ACK podría llegar primero; debemos saltearlo.
        if not packet.get_payload():
            packet = self.receive(self.DEFAULT_TIMEOUT)
        sent = packet.get_payload()
        
        self.assertEqual(data, received)
        self.assertEqual(data, sent)