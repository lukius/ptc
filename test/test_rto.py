# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


import time

from base import ConnectedSocketTestCase
from ptc.constants import INITIAL_RTO, CLOCK_TICK
from ptc.packet import ACKFlag
from ptc.rto import RTOEstimator


class RTOEstimatorTest(ConnectedSocketTestCase):
    
    def set_up(self):
        ConnectedSocketTestCase.set_up(self)
        self.rto_estimator = RTOEstimator(self.socket.protocol)
        self.packet = self.packet_builder.build(seq=self.DEFAULT_ISS + 1)
        self.ack_packet = self.packet_builder.build(flags=[ACKFlag],
                                                    ack=self.DEFAULT_ISS + 5)
        self.rto_estimator.track(self.packet)
    
    def test_ack_covers_tracked_packet(self):
        ack_number = self.ack_packet.get_ack_number()
        seq_covered = self.rto_estimator.ack_covers_tracked_packet(ack_number)
        
        self.assertTrue(seq_covered)

    def test_not_tracking_after_processing_ack(self):
        self.rto_estimator.process_ack(self.ack_packet)
        
        self.assertFalse(self.rto_estimator.is_tracking_packets())
    
    def test_estimation_after_first_sample(self):
        self.rto_estimator.process_ack(self.ack_packet)
        srtt = self.rto_estimator.srtt
        rttvar = self.rto_estimator.rttvar
        
        self.assertEquals(rttvar, srtt/2)
    
    def test_estimation_after_multiple_samples(self):
        real_rtt = 1
        real_rtt_ticks = real_rtt / CLOCK_TICK
        
        # Primera muestra
        time.sleep(real_rtt)
        self.rto_estimator.process_ack(self.ack_packet)
        first_rto = self.rto_estimator.get_current_rto()
        
        # Segunda muestra (es irrelevante usar el mismo paquete)
        self.rto_estimator.track(self.packet)
        time.sleep(real_rtt)
        self.rto_estimator.process_ack(self.ack_packet)
        second_rto = self.rto_estimator.get_current_rto()
        
        # Tercera muestra
        self.rto_estimator.track(self.packet)
        time.sleep(real_rtt)
        self.rto_estimator.process_ack(self.ack_packet)
        third_rto = self.rto_estimator.get_current_rto()
        
        # El primer RTO debería ser alto. Luego, a medida que más muestras
        # van computándose, la estimación debería converger al valor real.
        self.assertGreater(first_rto, second_rto) 
        self.assertGreater(second_rto, third_rto)
        self.assertGreater(third_rto, real_rtt_ticks)
    
    def test_ack_not_covering_tracked_packet_is_ignored(self):
        packet = self.packet_builder.build(flags=[ACKFlag],
                                           ack=self.DEFAULT_ISS - 5)
        self.rto_estimator.process_ack(packet)
        rto = self.rto_estimator.get_current_rto()
        
        self.assertEquals(INITIAL_RTO, rto)
    
    def test_ack_is_ignored_when_not_tracking(self):
        self.rto_estimator.untrack()
        self.rto_estimator.process_ack(self.ack_packet)
        rto = self.rto_estimator.get_current_rto()
        
        self.assertEquals(INITIAL_RTO, rto)