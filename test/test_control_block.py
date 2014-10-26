from base import PTCTestCase
from ptc import constants
from ptc.packet import ACKFlag
from ptc.cblock import PTCControlBlock
from ptc.seqnum import SequenceNumber


class ControlBlockTest(PTCTestCase):
    
    DEFAULT_ISS = SequenceNumber(20000)
    DEFAULT_IRS = SequenceNumber(10000)
    DEFAULT_IW = 64000
    DEFAULT_DATA = 'data' * 50
    MSS = 150
    
    HIGH_ISS = SequenceNumber(constants.MAX_SEQ)
    HIGH_IRS = SequenceNumber(constants.MAX_SEQ)
    
    def set_up(self):
        constants.RECEIVE_BUFFER_SIZE = self.DEFAULT_IW
        self.initialize_control_block_with(self.DEFAULT_ISS,
                                           self.DEFAULT_IRS)
    
    def initialize_control_block_with(self, iss, irs):
        self.control_block = PTCControlBlock(iss, irs,
                                             self.DEFAULT_IW,
                                             self.DEFAULT_IW)
    
    def test_creation(self):
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        rcv_nxt = self.control_block.get_rcv_nxt()
        snd_wl1 = self.control_block.get_snd_wl1()
        snd_wl2 = self.control_block.get_snd_wl2()        
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEquals(snd_nxt, snd_una)
        self.assertEquals(self.DEFAULT_ISS, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS, rcv_nxt)
        self.assertEquals(self.DEFAULT_IRS, snd_wl1)
        self.assertEquals(self.DEFAULT_ISS, snd_wl2)                
        self.assertEquals(self.DEFAULT_IW, usable_window_size)
        self.assertFalse(self.control_block.has_data_to_send())
        
    def test_new_data_to_send(self):
        data = self.DEFAULT_DATA
        self.control_block.to_out_buffer(data)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEquals(snd_nxt, snd_una)
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(self.DEFAULT_IW, usable_window_size)
        self.assertTrue(self.control_block.has_data_to_send())
        
    def test_extraction_of_outgoing_data(self):
        self._test_extraction_of_outgoing_data(iss=self.DEFAULT_ISS,
                                               irs=self.DEFAULT_IRS)

    def test_extraction_of_outgoing_data_with_wrapped_around_values(self):
        self._test_extraction_of_outgoing_data(iss=self.HIGH_ISS,
                                               irs=self.HIGH_IRS)
        
    def _test_extraction_of_outgoing_data(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        data = self.DEFAULT_DATA
        self.control_block.to_out_buffer(data)
        to_send = self.control_block.extract_from_out_buffer(self.MSS)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(iss + len(to_send), snd_nxt)
        self.assertEquals(self.DEFAULT_IW - len(to_send), usable_window_size)
        
        to_send = self.control_block.extract_from_out_buffer(self.MSS)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(iss + len(data), snd_nxt)
        self.assertEquals(self.DEFAULT_IW - len(data), usable_window_size)
        self.assertLess(len(to_send), self.MSS)
        self.assertFalse(self.control_block.has_data_to_send())

    def test_bytes_to_send_do_not_exceed_snd_wnd(self):
        self._test_bytes_to_send_do_not_exceed_snd_wnd(iss=self.DEFAULT_ISS,
                                                       irs=self.DEFAULT_IRS)

    def test_bytes_to_send_do_not_exceed_snd_wnd_with_wrapped_around_values(self):
        self._test_bytes_to_send_do_not_exceed_snd_wnd(iss=self.HIGH_ISS,
                                                       irs=self.HIGH_IRS)
        
    def _test_bytes_to_send_do_not_exceed_snd_wnd(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        data = self.DEFAULT_DATA * self.DEFAULT_IW
        mss = len(data) / 2
        self.control_block.to_out_buffer(data)
        
        to_send = self.control_block.extract_from_out_buffer(mss)
        to_send += self.control_block.extract_from_out_buffer(mss)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEquals(snd_una + self.DEFAULT_IW, snd_nxt)
        self.assertEquals(0, usable_window_size)
        self.assertEquals(self.DEFAULT_IW, len(to_send))

    def test_null_usable_window_when_window_upper_limit_is_below_snd_nxt(self):
        self._test_null_usable_window_when_window_upper_limit_is_below_snd_nxt(iss=self.DEFAULT_ISS,
                                                                               irs=self.DEFAULT_IRS)

    def test_null_usable_window_when_window_upper_limit_is_below_snd_nxt_with_wrapped_around_values(self):
        self._test_null_usable_window_when_window_upper_limit_is_below_snd_nxt(iss=self.HIGH_ISS,
                                                                               irs=self.HIGH_IRS)
        
    def _test_null_usable_window_when_window_upper_limit_is_below_snd_nxt(self, iss, irs):
        # This test covers the scenario where a window update shrunk the
        # send window, and thus SND_UNA + SND_WND < SND_NXT. Naturally, we
        # cannot send anything here, and so the usable window must be 0.
        self.initialize_control_block_with(iss, irs)
        self.control_block.snd_nxt += self.DEFAULT_IW/2
        self.control_block.snd_wnd = 1
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        snd_wnd = self.control_block.get_snd_wnd()
        self.assertLess(snd_una + snd_wnd, snd_nxt)
                
        usable_window_size = self.control_block.usable_window_size()
        self.assertEquals(0, usable_window_size)

    def test_reception_of_valid_ack(self):
        self._test_reception_of_valid_ack(iss=self.DEFAULT_ISS,
                                          irs=self.DEFAULT_IRS)

    def test_reception_of_valid_ack_with_wrapped_around_values(self):
        self._test_reception_of_valid_ack(iss=self.HIGH_ISS,
                                          irs=self.HIGH_IRS)

    def _test_reception_of_valid_ack(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        ack_number = iss + size
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=irs,
                                               ack=ack_number)
        
        self.control_block.snd_nxt += size
        self.control_block.process_incoming(ack_packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEquals(ack_number, snd_una)
        self.assertEquals(ack_number, snd_nxt)
        self.assertEquals(irs, rcv_nxt)        

    def test_reception_of_invalid_ack_greater_than_snd_nxt(self):
        self._test_reception_of_invalid_ack_greater_than_snd_nxt(iss=self.DEFAULT_ISS,
                                                                 irs=self.DEFAULT_IRS)

    def test_reception_of_invalid_ack_greater_than_snd_nxt_with_wrapped_around_values(self):
        self._test_reception_of_invalid_ack_greater_than_snd_nxt(iss=self.HIGH_ISS,
                                                                 irs=self.HIGH_IRS)
    
    def _test_reception_of_invalid_ack_greater_than_snd_nxt(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        offset = 50
        
        ack_number = iss + size + offset
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=irs,
                                               ack=ack_number)
        
        self.control_block.snd_nxt += size
        self.control_block.process_incoming(ack_packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        snd_wnd = self.control_block.get_snd_wnd()
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(ack_number - offset, snd_nxt)
        self.assertEquals(irs, rcv_nxt)
        # Window should not be updated when receiving invalid ACKs.
        self.assertEquals(self.DEFAULT_IW, snd_wnd)

    def test_reception_of_invalid_ack_lesser_than_snd_una(self):
        self._test_reception_of_invalid_ack_lesser_than_snd_una(iss=self.DEFAULT_ISS,
                                                                irs=self.DEFAULT_IRS)

    def test_reception_of_invalid_ack_lesser_than_snd_una_with_wrapped_around_values(self):
        self._test_reception_of_invalid_ack_lesser_than_snd_una(iss=self.HIGH_ISS,
                                                                irs=self.HIGH_IRS)
        
    def _test_reception_of_invalid_ack_lesser_than_snd_una(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        offset = 50
        
        ack_number = iss - offset
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=irs,
                                               ack=ack_number)
        
        self.control_block.snd_nxt += size
        self.control_block.process_incoming(ack_packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        snd_wnd = self.control_block.get_snd_wnd()
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(iss + size, snd_nxt)
        self.assertEquals(irs, rcv_nxt)
        # Window should not be updated when receiving invalid ACKs.
        self.assertEquals(self.DEFAULT_IW, snd_wnd)      

    def test_reception_of_window_update(self):
        self._test_reception_of_window_update(iss=self.DEFAULT_ISS,
                                              irs=self.DEFAULT_IRS)

    def test_reception_of_window_update_with_wrapped_around_values(self):
        self._test_reception_of_window_update(iss=self.HIGH_ISS,
                                              irs=self.HIGH_IRS)
    
    def _test_reception_of_window_update(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        new_window = self.DEFAULT_IW - 200 
        ack_number = iss + size
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=irs,
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
        
        self.assertEquals(ack_number, snd_una)
        self.assertEquals(ack_number, snd_nxt)
        self.assertEquals(irs, rcv_nxt)
        self.assertEquals(new_window, snd_wnd)
        self.assertEquals(irs, snd_wl1)
        self.assertEquals(ack_number, snd_wl2)

    def test_snd_wnd_updated_when_ack_equals_snd_una(self):
        self._test_snd_wnd_updated_when_ack_equals_snd_una(iss=self.DEFAULT_ISS,
                                                           irs=self.DEFAULT_IRS)

    def test_snd_wnd_updated_when_ack_equals_snd_una_with_wrapped_around_values(self):
        self._test_snd_wnd_updated_when_ack_equals_snd_una(iss=self.HIGH_ISS,
                                                           irs=self.HIGH_IRS)
        
    def _test_snd_wnd_updated_when_ack_equals_snd_una(self, iss, irs):
        # This test covers the scenario where a window update is received
        # and the ACK provided equals SND_UNA. RFC 793 explicitly forbids
        # this, but a correction was later introduced on RFC 1122 (page 94).
        self.initialize_control_block_with(iss, irs)
        size = 100
        self.control_block.snd_una += size
        new_window = self.DEFAULT_IW - 200 
        ack_number = self.control_block.get_snd_una()
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=irs,
                                               ack=ack_number,
                                               window=new_window)
        
        self.control_block.process_incoming(ack_packet)
        
        snd_wnd = self.control_block.get_snd_wnd()
        self.assertEquals(new_window, snd_wnd)

    def test_reception_of_new_data(self):
        self._test_reception_of_new_data(iss=self.DEFAULT_ISS,
                                         irs=self.DEFAULT_IRS)

    def test_reception_of_new_data_with_wrapped_around_values(self):
        self._test_reception_of_new_data(iss=self.HIGH_ISS,
                                         irs=self.HIGH_IRS)

    def _test_reception_of_new_data(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        payload = self.DEFAULT_DATA[:size]
        ack_number = iss
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=irs,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        data = self.control_block.from_in_buffer(size)
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(irs + size, rcv_nxt)
        self.assertEquals(payload, data)

    def test_reception_of_new_data_partially_overlapping_window_to_the_right(self):
        self._test_reception_of_new_data_partially_overlapping_window_to_the_right(iss=self.DEFAULT_ISS,
                                                                                   irs=self.DEFAULT_IRS)

    def test_reception_of_new_data_partially_overlapping_window_to_the_right_with_wrapped_around_values(self):
        self._test_reception_of_new_data_partially_overlapping_window_to_the_right(iss=self.HIGH_ISS,
                                                                                   irs=self.HIGH_IRS)

    def _test_reception_of_new_data_partially_overlapping_window_to_the_right(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        offset = 50
        payload = self.DEFAULT_DATA[:size]
        ack_number = iss
        seq_number = irs + self.DEFAULT_IW - offset
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=seq_number,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(irs, rcv_nxt)
        
        # Send the first chunk in order to retrieve the data after.
        custom_data = 'x' * (self.DEFAULT_IW - offset)
        expected_data = custom_data + payload[:offset]
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=irs,
                                           ack=iss,
                                           payload=custom_data)
        
        self.control_block.process_incoming(packet)
        size = len(custom_data) + len(payload)
        data = self.control_block.from_in_buffer(size)
        
        self.assertEquals(len(expected_data), len(data))
        self.assertEquals(expected_data, data)
        
    def test_reception_of_new_data_partially_overlapping_window_to_the_left(self):
        self._test_reception_of_new_data_partially_overlapping_window_to_the_left(iss=self.DEFAULT_ISS,
                                                                                  irs=self.DEFAULT_IRS)

    def test_reception_of_new_data_partially_overlapping_window_to_the_left_with_wrapped_around_values(self):
        self._test_reception_of_new_data_partially_overlapping_window_to_the_left(iss=self.HIGH_ISS,
                                                                                  irs=self.HIGH_IRS)
    
    def _test_reception_of_new_data_partially_overlapping_window_to_the_left(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        offset = 50
        payload = self.DEFAULT_DATA[:size]
        ack_number = iss
        seq_number = irs - offset
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=seq_number,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        data = self.control_block.from_in_buffer(size)
        # First <offset> bytes should be ignored since they fall outside
        # RCV_WND.
        expected_data = payload[offset:]
        expected_size = size - offset
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(snd_nxt, snd_una)
        self.assertEquals(irs + expected_size, rcv_nxt)
        self.assertEquals(expected_size, len(data))
        self.assertEquals(expected_data, data)

    def test_update_rcv_wnd(self):
        self._test_update_rcv_wnd(iss=self.DEFAULT_ISS,
                                  irs=self.DEFAULT_IRS)

    def test_update_rcv_wnd_with_wrapped_around_values(self):
        self._test_update_rcv_wnd(iss=self.HIGH_ISS,
                                  irs=self.HIGH_IRS)
        
    def _test_update_rcv_wnd(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        payload = self.DEFAULT_DATA[:size]
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=irs,
                                           ack=iss,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        rcv_nxt = self.control_block.get_rcv_nxt()
        rcv_wnd = self.control_block.get_rcv_wnd()
        
        self.assertEquals(irs + size, rcv_nxt)
        # RCV_WND should take into account the payload just processed.
        self.assertEquals(self.DEFAULT_IW - size, rcv_wnd)
        
        data = self.control_block.from_in_buffer(size)
        rcv_wnd = self.control_block.get_rcv_wnd()        
        
        # Once this payload is consumed, RCV_WND should grow again.
        self.assertEquals(self.DEFAULT_IW, rcv_wnd)
        self.assertEquals(size, len(data))
        self.assertEquals(data, payload)           

    def test_reception_of_new_data_after_processing_contiguous_chunks(self):
        self._test_reception_of_new_data_after_processing_contiguous_chunks(iss=self.DEFAULT_ISS,
                                                                            irs=self.DEFAULT_IRS)

    def test_reception_of_new_data_after_processing_contiguous_chunks_with_wrapped_around_values(self):
        self._test_reception_of_new_data_after_processing_contiguous_chunks(iss=self.HIGH_ISS,
                                                                            irs=self.HIGH_IRS)
        
    def _test_reception_of_new_data_after_processing_contiguous_chunks(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        offset = 50
        payload = self.DEFAULT_DATA[:size]
        ack_number = iss
        seq_number = irs + offset
        packet1 = self.packet_builder.build(flags=[ACKFlag],
                                            seq=seq_number,
                                            ack=ack_number,
                                            payload=payload[offset:])
        seq_number = irs
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
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(irs + size, rcv_nxt)
        self.assertEquals(payload, data)

    def test_reception_of_new_data_outside_window(self):
        self._test_reception_of_new_data_outside_window(iss=self.DEFAULT_ISS,
                                                        irs=self.DEFAULT_IRS)

    def test_reception_of_new_data_outside_window_with_wrapped_around_values(self):
        self._test_reception_of_new_data_outside_window(iss=self.HIGH_ISS,
                                                        irs=self.HIGH_IRS)
    
    def _test_reception_of_new_data_outside_window(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        offset = 50
        payload = self.DEFAULT_DATA[:size]
        
        # 1. Data starts beyond RCV_NXT + RCV_WND
        ack_number = iss
        seq_number = irs + self.DEFAULT_IW + offset
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=seq_number,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(irs, rcv_nxt)
        self.assertFalse(self.control_block.payload_is_accepted(packet))
        
        # 2. Data ends below RCV_NXT
        ack_number = iss
        seq_number = irs - 2*size
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=seq_number,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(irs, rcv_nxt)
        self.assertFalse(self.control_block.payload_is_accepted(packet))        

    def test_reception_of_new_data_with_piggybacked_ack(self):
        self._test_reception_of_new_data_with_piggybacked_ack(iss=self.DEFAULT_ISS,
                                                              irs=self.DEFAULT_IRS)

    def test_reception_of_new_data_with_piggybacked_ack_with_wrapped_around_values(self):
        self._test_reception_of_new_data_with_piggybacked_ack(iss=self.HIGH_ISS,
                                                              irs=self.HIGH_IRS)
    
    def _test_reception_of_new_data_with_piggybacked_ack(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        payload = self.DEFAULT_DATA[:size]
        ack_number = iss + size
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=irs,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.snd_nxt += size
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        data = self.control_block.from_in_buffer(size)
        
        self.assertEquals(ack_number, snd_una)
        self.assertEquals(ack_number, snd_nxt)
        self.assertEquals(irs + size, rcv_nxt)
        self.assertEquals(payload, data)

    def test_extraction_of_incoming_data(self):
        self._test_extraction_of_incoming_data(iss=self.DEFAULT_ISS,
                                               irs=self.DEFAULT_IRS)

    def test_extraction_of_incoming_data_with_wrapped_around_values(self):
        self._test_extraction_of_incoming_data(iss=self.HIGH_ISS,
                                               irs=self.HIGH_IRS)
    
    def _test_extraction_of_incoming_data(self, iss, irs):
        self.initialize_control_block_with(iss, irs)
        size = 100
        rcv_size = 50
        payload = self.DEFAULT_DATA[:size]
        ack_number = iss
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=irs,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        data1 = self.control_block.from_in_buffer(rcv_size)
        data2 = self.control_block.from_in_buffer(rcv_size)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        
        self.assertEquals(iss, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(irs + size, rcv_nxt)
        self.assertEquals(payload[:rcv_size], data1)
        self.assertEquals(payload[rcv_size:], data2)