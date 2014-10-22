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
import time

from base import ConnectedSocketTestCase, PTCTestCase
from ptc.constants import INITIAL_RTO, CLOCK_TICK,\
                          MAX_RETRANSMISSION_ATTEMPTS,\
                          BOGUS_RTT_RETRANSMISSIONS
from ptc.packet import SYNFlag, ACKFlag


class RetransmissionTestMixin(object):
    
    def get_retransmitted_packets(self):
        packets = list()
        while True:
            try:
                packet = self.receive(self.DEFAULT_TIMEOUT)
                packets.append(packet)
            except Exception:
                break
        # El primer paquete debería ser el original.
        return packets[1:]
    
    def wait_until_retransmission_timer_expires(self):
        time.sleep(INITIAL_RTO * CLOCK_TICK)
        

# TODO: refactorizar.
class RetransmissionTest(ConnectedSocketTestCase, RetransmissionTestMixin):
    
    def assert_retransmission(self, first_packet, second_packet):
        self.assertEquals(first_packet.get_seq_number(),
                          second_packet.get_seq_number())
        self.assertEquals(first_packet.get_ack_number(),
                          second_packet.get_ack_number())
        self.assertEquals(first_packet.get_payload(),
                          second_packet.get_payload())
        
    def test_retransmission_after_lost_packet(self):
        self.socket.send(self.DEFAULT_DATA)
        first_packet = self.receive(self.DEFAULT_TIMEOUT)
        self.wait_until_retransmission_timer_expires()
        second_packet = self.receive(self.DEFAULT_TIMEOUT)

        self.assert_retransmission(first_packet, second_packet)
        
    def test_give_up_after_enough_retransmissions(self):
        self.socket.send(self.DEFAULT_DATA)
        self.receive()
        # Esto hará que el protocolo piense que ya retransmitió ese número de
        # veces.
        self.socket.protocol.retransmissions = MAX_RETRANSMISSION_ATTEMPTS
        self.wait_until_retransmission_timer_expires()

        self.assertRaises(socket.timeout, self.receive, self.DEFAULT_TIMEOUT)
        self.assertFalse(self.socket.is_connected())
        
    def test_packet_removed_from_retransmission_queue_after_ack(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS + size
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=ack_number,
                                               window=self.DEFAULT_IW)
        self.socket.send(data)
        self.receive()
        self.send(ack_packet)
        self.wait_until_retransmission_timer_expires()
        packets = self.get_retransmitted_packets()
        
        self.assertEquals(0, len(packets))
        self.assertTrue(self.socket.is_connected())
    
    def test_unaccepted_ack_ignored_when_updating_retransmission_queue(self):
        ack_number = self.DEFAULT_ISS + self.DEFAULT_IW + 1
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=ack_number,
                                               window=self.DEFAULT_IW)
        self.socket.send(self.DEFAULT_DATA)
        self.send(ack_packet)
        self.wait_until_retransmission_timer_expires()
        packets = self.get_retransmitted_packets()
        
        self.assertEquals(1, len(packets))
        self.assertTrue(self.socket.is_connected())
        
    def test_retransmission_timer_off_after_acking_all_data(self):
        size = 10
        data = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS + size
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=ack_number,
                                               window=self.DEFAULT_IW)
        self.socket.send(data)
        self.receive()
        self.send(ack_packet)
        timer = self.socket.protocol.retransmission_timer
        
        self.assertFalse(timer.is_running())
    
    def test_retransmission_time_backed_off_after_retransmission(self):
        rto_estimator = self.socket.protocol.rto_estimator
        first_rto = rto_estimator.get_current_rto()
        self.socket.send(self.DEFAULT_DATA)
        self.receive()
        self.wait_until_retransmission_timer_expires()
        # Para asegurarnos de que la retransmisión ocurrió.
        self.receive()
        new_rto = rto_estimator.get_current_rto()
        
        self.assertEquals(2*first_rto, new_rto)
        
    def test_rtt_cleared_after_several_retransmissions(self):
        rto_estimator = self.socket.protocol.rto_estimator
        srtt = rto_estimator.srtt
        self.socket.send(self.DEFAULT_DATA)
        self.receive()
        # Esto hará que el protocolo piense que ya retransmitió ese número de
        # veces.
        self.socket.protocol.retransmissions = BOGUS_RTT_RETRANSMISSIONS
        self.wait_until_retransmission_timer_expires()

        self.assertEquals(0, rto_estimator.srtt)
        self.assertEquals(srtt, rto_estimator.rttvar)
    
    def test_retransmission_timer_restarted_after_acking_some_data(self):
        size = 5
        data = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS + size
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=ack_number,
                                               window=self.DEFAULT_IW)
        rto_estimator = self.socket.protocol.rto_estimator
        first_rto = rto_estimator.get_current_rto()        
        self.socket.send(data)
        self.receive()
        self.socket.send(data)
        self.receive()
        # Reconocer el primer paquete pero no el segundo.
        self.send(ack_packet)
        timer = self.socket.protocol.retransmission_timer
        new_rto = rto_estimator.get_current_rto()

        self.assertTrue(timer.is_running())
        # El primer RTO muestreado debería ser más chico que el inicial,
        # fijado en 1 segundo.
        self.assertLess(new_rto, first_rto)
    
    def test_retransmitted_packet_not_used_for_estimating_rto_1(self):
        # Escenario: un paquete se envìa y se retransmite inmediatamente,
        # y el ACK viene después.
        size = 10
        data = self.DEFAULT_DATA[:size]
        ack_number = self.DEFAULT_ISS + size
        ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                               seq=self.DEFAULT_IRS,
                                               ack=ack_number,
                                               window=self.DEFAULT_IW)
        rto_estimator = self.socket.protocol.rto_estimator
        self.socket.send(data)
        self.receive()
        self.wait_until_retransmission_timer_expires()
        self.receive()
        first_rto = rto_estimator.get_current_rto()        
        self.send(ack_packet)
        new_rto = rto_estimator.get_current_rto()

        # Ambos RTOs deberían coincidir dado que el ACK llegó despues de la
        # retransmisión del paquete.
        self.assertEquals(first_rto, new_rto)
        
    def test_retransmitted_packet_not_used_for_estimating_rto_2(self):
        # Escenario: se transmiten dos paquetes. El primero se reconoce,
        # mientras que el segundo se retransmite y se reconoce luego.
        size = 5
        data = self.DEFAULT_DATA[:size]
        ack_number1 = self.DEFAULT_ISS + size
        ack_number2 = self.DEFAULT_ISS + 2*size
        ack_packet1 = self.packet_builder.build(flags=[ACKFlag],
                                                seq=self.DEFAULT_IRS,
                                                ack=ack_number1,
                                                window=self.DEFAULT_IW)
        ack_packet2 = self.packet_builder.build(flags=[ACKFlag],
                                                seq=self.DEFAULT_IRS,
                                                ack=ack_number2,
                                                window=self.DEFAULT_IW)        
        rto_estimator = self.socket.protocol.rto_estimator
        self.socket.send(data)
        self.receive()
        self.socket.send(data)
        self.receive()
        # Reconocer el primer paquete pero no el segundo.
        self.send(ack_packet1)
        self.wait_until_retransmission_timer_expires()
        self.receive()
        first_rto = rto_estimator.get_current_rto()
        self.send(ack_packet2)        
        new_rto = rto_estimator.get_current_rto()

        # Ambos RTOs deberían coincidir dado que el ACK llegó despues de la
        # retransmisión del segundo paquete.
        self.assertEquals(first_rto, new_rto)        
        

class SYNRetransmissionTest(PTCTestCase, RetransmissionTestMixin):

    def test_syn_packet_removed_from_retransmission_queue_after_syn_ack(self):
        self.launch_client()
        syn_packet = self.receive(self.DEFAULT_TIMEOUT)
        received_seq_number = syn_packet.get_seq_number()
        seq_number = 1111
        syn_ack_packet = self.packet_builder.build(flags=[SYNFlag, ACKFlag],
                                                   seq=seq_number,
                                                   ack=received_seq_number+1)
        self.send(syn_ack_packet)
        self.wait_until_retransmission_timer_expires()
        packets = self.get_retransmitted_packets()
        
        self.assertEquals(0, len(packets))