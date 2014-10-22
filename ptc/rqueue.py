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


class RetransmissionQueue(object):
    
    def __init__(self):
        self.queue = list()
        self.lock = threading.RLock()
        
    def empty(self):
        with self.lock:
            return len(self.queue) == 0

    def head(self):
        with self.lock:
            if self.empty():
                raise RuntimeError('retransmission queue is empty')
            return self.queue[0]

    def put(self, packet):
        with self.lock:
            self.queue.append(packet)

    def remove_acknowledged_by(self, ack_packet, snd_una, snd_nxt):
        with self.lock:
            new_queue = list()
            acknowledged_packets = list()
            for packet in self.queue:
                ack = ack_packet.get_ack_number()
                # Checkear que ack >= seq_lo y ack >= seq_hi simultáneamente,
                # teniendo en cuenta que son valores modulares.
                if self.ack_covers_packet(ack, packet, snd_una, snd_nxt):
                    acknowledged_packets.append(packet)
                else:
                    new_queue.append(packet)
            self.queue = new_queue
            return acknowledged_packets
        
    def ack_covers_packet(self, ack, packet, snd_una, snd_nxt):
        # Método privado para comparar correctamente el ACK contra los bytes
        # secuenciados por el paquete.
        _, seq_hi = packet.get_seq_interval()
        if snd_nxt > snd_una:
            # Cuandp SND_NXT > SND_UNA, no hay wrap-around.
            # Luego, el ACK provisto cubre el paquete sii
            # ack > seq_hi = número de secuencia del último byte.            
            return ack >= seq_hi
        else:
            # Cuando SND_NXT <= SND_UNA, SND_NXT arrancó desde 0 al haber
            # superado el máximo valor. Existen dos posibilidades:
            #   * seq_hi y ack también lo hicieron, de manera que
            #     deberíamos tener que seq_hi <= ack <= snd_nxt
            #   * o tan solo ack superó el máximo, lo que significa que ya
            #     es más grande que seq_hi.             
            return (seq_hi <= ack <= snd_nxt) or\
                    snd_nxt < seq_hi
            
    def __enter__(self, *args, **kwargs):
        return self.lock.__enter__(*args, **kwargs)
    
    def __exit__(self, *args, **kwargs):
        return self.lock.__exit__(*args, **kwargs)