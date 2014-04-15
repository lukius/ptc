import socket
import time

from base import ConnectedSocketTestCase
from ptc.constants import RETRANSMISSION_TIMEOUT, SHUT_RD, SHUT_WR, SHUT_RDWR,\
                          ESTABLISHED, FIN_WAIT1, FIN_WAIT2, CLOSED
from ptc.exceptions import WriteStreamClosedException
from ptc.packet import ACKFlag, FINFlag


class FINTest(ConnectedSocketTestCase):
    
    def test_close_read_stream(self):
        data_size = 10
        data = self.DEFAULT_DATA[:data_size]
        data_packet = self.packet_builder.build(flags=[ACKFlag],
                                                seq=self.DEFAULT_IRS,
                                                ack=self.DEFAULT_ISS,
                                                window=self.DEFAULT_IW,
                                                payload=data)
        self.send(data_packet)
        # Discard ACK packet.
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
        # Data after shutdown should be discarded.
        self.assertEquals(data, data_received)
        
        # Send stream should be working normally.
        self.socket.send(data)
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
        # FIN flag should be sequenced.
        self.assertEquals(self.DEFAULT_ISS, seq_number)

    def receive_fin_and_assert_retransmissions(self, data_packet):
        packet = self.receive(self.DEFAULT_TIMEOUT)
        while FINFlag not in packet:
            # This should be a retransmission.
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
        # There will be no race conditions here: the socket will have pending
        # data since we still need to manually send our ACKs.
        self.socket.shutdown(SHUT_WR)
        self.assertRaises(WriteStreamClosedException, self.socket.send,
                          self.DEFAULT_DATA)

        time.sleep(2*RETRANSMISSION_TIMEOUT)
        self.send(ack_packet)
        data_packet = self.receive(self.DEFAULT_TIMEOUT)
        retransmitted_packet = self.receive(self.DEFAULT_TIMEOUT)
        
        self.assertNotIn(FINFlag, data_packet)
        self.assertNotIn(FINFlag, retransmitted_packet)
        self.assertEquals(data, data_packet.get_payload())
        self.assertEquals(data, retransmitted_packet.get_payload())
        
        fin_packet = self.receive_fin_and_assert_retransmissions(data_packet)
        seq_number = fin_packet.get_seq_number()
        
        self.assertEquals(FIN_WAIT1, self.socket.protocol.state)
        self.assertIn(FINFlag, fin_packet)
        self.assertEquals(0, len(fin_packet.get_payload()))
        # FIN flag should be sequenced.
        self.assertEquals(self.DEFAULT_ISS+data_size, seq_number)
        
    def test_receive_ack_after_sending_fin(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=self.DEFAULT_ISS,
                                               payload=data) 
        # Hack: make the socket think it is on FIN_WAIT1.
        self.socket.protocol.state = FIN_WAIT1
        self.socket.protocol.write_stream_open = False
        self.send(ack_packet)
        data_received = self.socket.recv(size)
        
        self.assertEquals(FIN_WAIT2, self.socket.protocol.state)
        # Nothing should be sent back.
        self.assertRaises(socket.timeout, self.receive, self.DEFAULT_TIMEOUT)
        self.assertEquals(data, data_received)
        
    def test_receive_data_when_write_stream_is_closed(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        data_packet = self.packet_builder.build(flags=[ACKFlag],
                                                seq=self.DEFAULT_IRS,
                                                ack=self.DEFAULT_ISS,
                                                payload=data) 
        # Hack: make the socket think it is on FIN_WAIT2.
        self.socket.protocol.state = FIN_WAIT2
        self.socket.protocol.write_stream_open = False
        self.send(data_packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        seq_number = ack_packet.get_seq_number()
        ack_number = ack_packet.get_ack_number()
        
        self.assertEquals(FIN_WAIT2, self.socket.protocol.state)
        self.assertEquals(self.DEFAULT_ISS, seq_number)
        self.assertEquals(self.DEFAULT_IRS+size, ack_number)
        self.assertEquals(0, len(ack_packet.get_payload()))
        
    def test_receive_fin_on_fin_wait2(self):
        fin_packet = self.packet_builder.build(flags=[ACKFlag, FINFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=self.DEFAULT_ISS) 
        # Hack: make the socket think it is on FIN_WAIT2.
        self.socket.protocol.state = FIN_WAIT2
        self.socket.protocol.write_stream_open = False
        self.send(fin_packet)
        ack_packet = self.receive(self.DEFAULT_TIMEOUT)
        seq_number = ack_packet.get_seq_number()
        ack_number = ack_packet.get_ack_number()
        
        self.assertEquals(CLOSED, self.socket.protocol.state)
        self.assertEquals(self.DEFAULT_ISS, seq_number)
        self.assertEquals(self.DEFAULT_IRS, ack_number)
        self.assertEquals(0, len(ack_packet.get_payload()))        