from base import PTCTestCase
from ptc import constants
from ptc.packet import ACKFlag
from ptc.protocol import PTCControlBlock


class ControlBlockTest(PTCTestCase):
    
    DEFAULT_ISS = 20000
    DEFAULT_IRS = 10000
    DEFAULT_IW = 64000
    DEFAULT_DATA = 'data' * 50
    MSS = 150
    
    
    def set_up(self):
        constants.RECEIVE_BUFFER_SIZE = self.DEFAULT_IW
        self.control_block = PTCControlBlock(self.DEFAULT_ISS,
                                             self.DEFAULT_IRS,
                                             self.DEFAULT_IW)
    
    def test_creation(self):
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        rcv_nxt = self.control_block.get_rcv_nxt()
        snd_wl1 = self.control_block.get_snd_wl1()
        snd_wl2 = self.control_block.get_snd_wl2()        
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEqual(snd_nxt, snd_una)
        self.assertEqual(snd_nxt, self.DEFAULT_ISS)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS)
        self.assertEqual(snd_wl1, self.DEFAULT_IRS)
        self.assertEqual(snd_wl2, self.DEFAULT_ISS)                
        self.assertEqual(usable_window_size, self.DEFAULT_IW)
        
    def test_new_data_to_send(self):
        data = self.DEFAULT_DATA
        self.control_block.to_out_buffer(data)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEqual(snd_nxt, snd_una)
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(usable_window_size, self.DEFAULT_IW)
        
    def test_extracting_outgoing_data(self):
        data = self.DEFAULT_DATA
        self.control_block.to_out_buffer(data)
        to_send = self.control_block.extract_from_out_buffer(self.MSS)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, self.DEFAULT_ISS + len(to_send))
        self.assertEqual(usable_window_size, self.DEFAULT_IW - len(to_send))
        
        to_send = self.control_block.extract_from_out_buffer(self.MSS)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, self.DEFAULT_ISS + len(data))
        self.assertEqual(usable_window_size, self.DEFAULT_IW - len(data))
        self.assertLess(len(to_send), self.MSS)
        
    def test_bytes_to_send_do_not_exceed_snd_wnd(self):
        data = self.DEFAULT_DATA * self.DEFAULT_IW
        mss = len(data) / 2
        self.control_block.to_out_buffer(data)
        
        to_send = self.control_block.extract_from_out_buffer(mss)
        to_send += self.control_block.extract_from_out_buffer(mss)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEqual(snd_nxt, snd_una + self.DEFAULT_IW)
        self.assertEqual(usable_window_size, 0)
        self.assertEqual(len(to_send), self.DEFAULT_IW)

    def test_receiving_valid_ack(self):
        size = 100
        ack_number = self.DEFAULT_ISS + size
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=ack_number)
        
        self.control_block.snd_nxt += size
        self.control_block.process_incoming(ack_packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEqual(snd_una, ack_number)
        self.assertEqual(snd_nxt, ack_number)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS)        
    
    def test_receiving_invalid_ack_greater_than_snd_nxt(self):
        size = 100
        offset = 50
        
        ack_number = self.DEFAULT_ISS + size + offset
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=ack_number)
        
        self.control_block.snd_nxt += size
        self.control_block.process_incoming(ack_packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        snd_wnd = self.control_block.get_snd_wnd()
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, ack_number - offset)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS)
        # Window should not be updated when receiving invalid ACKs.
        self.assertEqual(snd_wnd, self.DEFAULT_IW)
        
    def test_receiving_invalid_ack_lesser_than_snd_una(self):
        size = 100
        offset = 50
        
        ack_number = self.DEFAULT_ISS - offset
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=ack_number)
        
        self.control_block.snd_nxt += size
        self.control_block.process_incoming(ack_packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        snd_wnd = self.control_block.get_snd_wnd()
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, self.DEFAULT_ISS + size)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS)
        # Window should not be updated when receiving invalid ACKs.
        self.assertEqual(snd_wnd, self.DEFAULT_IW)      
    
    def test_receiving_window_update(self):
        size = 100
        new_window = self.DEFAULT_IW - 200 
        ack_number = self.DEFAULT_ISS + size
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=ack_number,
                                               window=new_window)
        
        self.control_block.snd_nxt += size
        self.control_block.process_incoming(ack_packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        snd_wnd = self.control_block.get_snd_wnd()
        snd_wl1 = self.control_block.get_snd_wl1()
        snd_wl2 = self.control_block.get_snd_wl2()
        
        self.assertEqual(snd_una, ack_number)
        self.assertEqual(snd_nxt, ack_number)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS)
        self.assertEqual(snd_wnd, new_window)
        self.assertEqual(snd_wl1, self.DEFAULT_IRS)
        self.assertEqual(snd_wl2, ack_number)

    def test_receiving_new_data(self):
        size = 100
        payload = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        data = self.control_block.from_in_buffer(size)
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, snd_una)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS + size)
        self.assertEqual(data, payload)
    
    def test_receiving_new_data_partially_overlapping_window(self):
        size = 100
        offset = 50
        payload = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS
        seq_number = self.DEFAULT_IRS + self.DEFAULT_IW - offset
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=seq_number,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, snd_una)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS)
        
    def test_receiving_new_data_after_processing_contiguous_chunks(self):
        size = 100
        offset = 50
        payload = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS
        seq_number = self.DEFAULT_IRS + offset
        packet1 = self.packet_builder.build(flags=[ACKFlag],
                                            seq=seq_number,
                                            ack=ack_number,
                                            payload=payload[offset:])
        seq_number = self.DEFAULT_IRS
        packet2 = self.packet_builder.build(flags=[ACKFlag],
                                            seq=seq_number,
                                            ack=ack_number,
                                            payload=payload[:offset])        
        
        self.control_block.process_incoming(packet1)
        self.control_block.process_incoming(packet2)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        data = self.control_block.from_in_buffer(size)
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, snd_una)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS + size)
        self.assertEqual(data, payload)
    
    def test_receiving_new_data_outside_window(self):
        size = 100
        offset = 50
        payload = self.DEFAULT_DATA[:size]
        
        # 1. Data starts beyond RCV_NXT + RCV_WND
        ack_number = self.DEFAULT_ISS
        seq_number = self.DEFAULT_IRS + self.DEFAULT_IW + offset
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=seq_number,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, snd_una)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS)
        self.assertFalse(self.control_block.payload_is_accepted(packet))
        
        # 2. Data ends below RCV_NXT
        ack_number = self.DEFAULT_ISS
        seq_number = self.DEFAULT_IRS - 2*size
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=seq_number,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, snd_una)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS)
        self.assertFalse(self.control_block.payload_is_accepted(packet))        
    
    def test_receiving_new_data_with_piggybacked_ack(self):
        size = 100
        payload = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS + size
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.snd_nxt += size
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        data = self.control_block.from_in_buffer(size)
        
        self.assertEqual(snd_una, ack_number)
        self.assertEqual(snd_nxt, ack_number)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS + size)
        self.assertEqual(data, payload)
    
    def test_extracting_incoming_data(self):
        size = 100
        rcv_size = 50
        payload = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        data1 = self.control_block.from_in_buffer(rcv_size)
        data2 = self.control_block.from_in_buffer(rcv_size)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEqual(snd_una, self.DEFAULT_ISS)
        self.assertEqual(snd_nxt, snd_una)
        self.assertEqual(rcv_nxt, self.DEFAULT_IRS + size)
        self.assertEqual(data1, payload[:rcv_size])
        self.assertEqual(data2, payload[rcv_size:])
                