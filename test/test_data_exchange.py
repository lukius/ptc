from base import PTCTestCase

from ptc.packet import ACKFlag


class DataExchangeTest(PTCTestCase):
    
    DEFAULT_ISS = 20
    DEFAULT_IRS = 10
    DEFAULT_IW = 10
    DEFAULT_DATA = 'data' * 5
    
    def set_up(self):
        src_address, src_port = self.DEFAULT_DST_ADDRESS, self.DEFAULT_DST_PORT
        dst_address, dst_port = self.DEFAULT_SRC_ADDRESS, self.DEFAULT_SRC_PORT
        self.socket = self.get_connected_socket(src_address=src_address,
                                                src_port=src_port,
                                                dst_address=dst_address,
                                                dst_port=dst_port,
                                                iss=self.DEFAULT_ISS,
                                                irs=self.DEFAULT_IRS,
                                                send_window=self.DEFAULT_IW,
                                                receive_window=self.DEFAULT_IW)
        
    def tear_down(self):
        self.socket.protocol.close()
        
    def receive_data(self):
        data = str()
        timeout = 0.5
        while True:
            try:
                packet = self.receive(timeout)
            except:
                break
            payload = packet.get_payload()
            seq_number = packet.get_seq_number() + len(payload)
            data += payload
            ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                                   seq=self.DEFAULT_IRS,
                                                   ack=seq_number,
                                                   window=self.DEFAULT_IW)
            self.send(ack_packet)
        return data
    
    def test_sending_data(self):
        self.socket.send(self.DEFAULT_DATA)
        data = self.receive_data()
        self.assertEqual(data, self.DEFAULT_DATA)
    
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
        
        self.assertEqual(received, to_send)
    
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
        
        self.assertEqual(received, to_send)
        
    
    def test_sending_and_receiving_data(self):
        # TODO: complete this!
        pass        