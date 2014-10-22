# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


import threading

from exceptions import PTCError


class PTCTimer(object):

    def __init__(self, protocol):
        self.protocol = protocol
        self.current_ticks = None
        self.target_ticks = None
        self.running = False
        self.lock = threading.RLock()
        
    def on_expired(self):
        raise NotImplementedError
        
    def is_running(self):
        with self.lock:
            return self.running
        
    def has_expired(self):
        with self.lock:
            return self.current_ticks is not None and\
                   self.target_ticks is not None and\
                   self.current_ticks >= self.target_ticks
        
    def start(self, target_ticks):
        with self.lock:
            if self.is_running():
                raise PTCError('timer already running')
            self.target_ticks = target_ticks
            self.current_ticks = 0
            self.running = True
    
    def stop(self):
        with self.lock:
            self.running = False

    def restart(self, target_ticks):
        with self.lock:
            self.stop()
            self.start(target_ticks)

    def tick(self):
        with self.lock:
            if not self.is_running():
                return
            self.current_ticks += 1
            if self.has_expired():
                self.on_expired()
                self.stop()
    

class RetransmissionTimer(PTCTimer):
    
    def on_expired(self):
        # Notificar al packet sender: él se encargará de hacer la
        # retransmisión necesaria.
        self.protocol.packet_sender.notify()