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
from ptc.exceptions import PTCError
from ptc.timer import PTCTimer


class CustomTimer(PTCTimer):
    
    def __init__(self, protocol):
        PTCTimer.__init__(self, protocol)
        self.expired = False
    
    def on_expired(self):
        self.expired = True


class TimerTest(ConnectedSocketTestCase):
    
    def set_up(self):
        ConnectedSocketTestCase.set_up(self)
        self.target_ticks = 3
        self.timer = CustomTimer(self.socket.protocol)
    
    def do_ticks(self, ticks):
        for _ in range(ticks):
            self.timer.tick()
                                
    def test_timer_expires(self):
        self.timer.start(self.target_ticks)
        self.do_ticks(self.target_ticks)

        self.assertTrue(self.timer.expired)
        
    def test_timer_stopped_before_expiring(self):
        self.timer.start(self.target_ticks)
        self.timer.tick()
        self.timer.stop()

        self.assertFalse(self.timer.expired)
        
    def test_timer_restarted(self):
        new_target_ticks = self.target_ticks - 1
        self.timer.start(self.target_ticks)
        self.timer.tick()
        self.timer.restart(new_target_ticks)
        
        self.assertEquals(0, self.timer.current_ticks)
        self.assertEquals(new_target_ticks, self.timer.target_ticks)
        
        self.do_ticks(new_target_ticks)
        
        self.assertTrue(self.timer.expired)
        
    def test_timer_cannot_be_started_twice(self):
        self.timer.start(self.target_ticks)
        self.assertRaises(PTCError, self.timer.start, (self.target_ticks,))