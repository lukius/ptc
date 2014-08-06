import time

from base import ConnectedSocketTestCase
from ptc.constants import CLOCK_TICK
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
        self.target_ticks = 5
        self.target_time = self.target_ticks * CLOCK_TICK
        self.timer = CustomTimer(self.socket.protocol)
    
    def test_timer_expires(self):
        self.timer.start(self.target_ticks)
        # Sleep slightly more in order to be certain that it indeed expired.
        time.sleep(self.target_time + CLOCK_TICK)

        self.assertTrue(self.timer.expired)
        
    def test_timer_stopped_before_expiring(self):
        self.timer.start(self.target_ticks)
        time.sleep(CLOCK_TICK)
        self.timer.stop()
        time.sleep(self.target_time)

        self.assertFalse(self.timer.expired)
        
    def test_timer_cannot_be_started_twice(self):
        self.timer.start(self.target_ticks)
        self.assertRaises(PTCError, self.timer.start, (self.target_ticks,))