# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


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
    
    def set_up(self):
        constants.RECEIVE_BUFFER_SIZE = self.DEFAULT_IW
        self.control_block = PTCControlBlock(self.DEFAULT_ISS,
                                             self.DEFAULT_IRS,
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
        data = self.DEFAULT_DATA
        self.control_block.to_out_buffer(data)
        to_send = self.control_block.extract_from_out_buffer(self.MSS)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(self.DEFAULT_ISS + len(to_send), snd_nxt)
        self.assertEquals(self.DEFAULT_IW - len(to_send), usable_window_size)
        
        to_send = self.control_block.extract_from_out_buffer(self.MSS)
        snd_nxt = self.control_block.get_snd_nxt()
        snd_una = self.control_block.get_snd_una()
        usable_window_size = self.control_block.usable_window_size()
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(self.DEFAULT_ISS + len(data), snd_nxt)
        self.assertEquals(self.DEFAULT_IW - len(data), usable_window_size)
        self.assertLess(len(to_send), self.MSS)
        self.assertFalse(self.control_block.has_data_to_send())
        
    def test_bytes_to_send_do_not_exceed_snd_wnd(self):
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

    def test_reception_of_valid_ack(self):
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
        
        self.assertEquals(ack_number, snd_una)
        self.assertEquals(ack_number, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS, rcv_nxt)        
    
    def test_reception_of_invalid_ack_greater_than_snd_nxt(self):
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
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(ack_number - offset, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS, rcv_nxt)
        # No actualizar ventana al recibir ACKs inválidos.
        self.assertEquals(self.DEFAULT_IW, snd_wnd)
        
    def test_reception_of_invalid_ack_lesser_than_snd_una(self):
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
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(self.DEFAULT_ISS + size, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS, rcv_nxt)
        # No actualizar ventana al recibir ACKs inválidos.
        self.assertEquals(self.DEFAULT_IW, snd_wnd)      
    
    def test_reception_of_window_update(self):
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
        
        self.assertEquals(ack_number, snd_una)
        self.assertEquals(ack_number, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS, rcv_nxt)
        self.assertEquals(new_window, snd_wnd)
        self.assertEquals(self.DEFAULT_IRS, snd_wl1)
        self.assertEquals(ack_number, snd_wl2)

    def test_reception_of_new_data(self):
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
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS + size, rcv_nxt)
        self.assertEquals(payload, data)
    
    def test_reception_of_new_data_partially_overlapping_window_to_the_right(self):
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
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS, rcv_nxt)
        
        # Enviar el primer bloque para obtener los datos a continuación.
        custom_data = 'x' * (self.DEFAULT_IW - offset)
        expected_data = custom_data + payload[:offset]
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS,
                                           payload=custom_data)
        
        self.control_block.process_incoming(packet)
        size = len(custom_data) + len(payload)
        data = self.control_block.from_in_buffer(size)
        
        self.assertEquals(len(expected_data), len(data))
        self.assertEquals(expected_data, data)
        
    def test_reception_of_new_data_partially_overlapping_window_to_the_left(self):
        size = 100
        offset = 50
        payload = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS
        seq_number = self.DEFAULT_IRS - offset
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=seq_number,
                                           ack=ack_number,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        snd_una = self.control_block.get_snd_una()
        snd_nxt = self.control_block.get_snd_nxt()
        rcv_nxt = self.control_block.get_rcv_nxt()
        data = self.control_block.from_in_buffer(size)
        # Los primeros <offset> bytes deberían ignorarse al caer fuera de
        # RCV_WND.
        expected_data = payload[offset:]
        expected_size = size - offset
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(snd_nxt, snd_una)
        self.assertEquals(self.DEFAULT_IRS + expected_size, rcv_nxt)
        self.assertEquals(expected_size, len(data))
        self.assertEquals(expected_data, data)
        
    def test_update_rcv_wnd(self):
        size = 100
        payload = self.DEFAULT_DATA[:size]
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           seq=self.DEFAULT_IRS,
                                           ack=self.DEFAULT_ISS,
                                           payload=payload)
        
        self.control_block.process_incoming(packet)
        
        rcv_nxt = self.control_block.get_rcv_nxt()
        rcv_wnd = self.control_block.get_rcv_wnd()
        
        self.assertEquals(self.DEFAULT_IRS + size, rcv_nxt)
        # RCV_WND debería considerar el payload que enviamos.
        self.assertEquals(self.DEFAULT_IW - size, rcv_wnd)
        
        data = self.control_block.from_in_buffer(size)
        rcv_wnd = self.control_block.get_rcv_wnd()        
        
        # Y una vez consumidos los datos, la ventana debería crecer de nuevo.
        self.assertEquals(self.DEFAULT_IW, rcv_wnd)
        self.assertEquals(size, len(data))
        self.assertEquals(data, payload)                
        
    def test_reception_of_new_data_after_processing_contiguous_chunks(self):
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
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS + size, rcv_nxt)
        self.assertEquals(payload, data)
    
    def test_reception_of_new_data_outside_window(self):
        size = 100
        offset = 50
        payload = self.DEFAULT_DATA[:size]
        
        # 1. Los datos empiezan después de RCV_NXT + RCV_WND
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
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS, rcv_nxt)
        self.assertFalse(self.control_block.payload_is_accepted(packet))
        
        # 2. Los datos terminan antes de RCV_NXT
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
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS, rcv_nxt)
        self.assertFalse(self.control_block.payload_is_accepted(packet))        
    
    def test_reception_of_new_data_with_piggybacked_ack(self):
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
        
        self.assertEquals(ack_number, snd_una)
        self.assertEquals(ack_number, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS + size, rcv_nxt)
        self.assertEquals(payload, data)
    
    def test_extraction_of_incoming_data(self):
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
        
        self.assertEquals(self.DEFAULT_ISS, snd_una)
        self.assertEquals(snd_una, snd_nxt)
        self.assertEquals(self.DEFAULT_IRS + size, rcv_nxt)
        self.assertEquals(payload[:rcv_size], data1)
        self.assertEquals(payload[rcv_size:], data2)
                