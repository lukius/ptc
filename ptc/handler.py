# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


from constants import CLOSED, SYN_RCVD, ESTABLISHED, SYN_SENT,\
                      LISTEN, FIN_WAIT1, FIN_WAIT2, CLOSE_WAIT,\
                      LAST_ACK, CLOSING
from packet import SYNFlag, ACKFlag, FINFlag


class IncomingPacketHandler(object):
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.socket = self.protocol.socket
        
    def initialize_control_block_from(self, packet):
        self.protocol.initialize_control_block_from(packet)
        self.control_block = self.protocol.control_block

    def build_packet(self, *args, **kwargs):
        return self.protocol.build_packet(*args, **kwargs)
    
    def set_state(self, state):
        self.protocol.set_state(state)
        
    def send_ack(self):
        ack_packet = self.build_packet()
        self.socket.send(ack_packet)

    def handle(self, packet):
        state = self.protocol.state
        if state == LISTEN:
            self.handle_incoming_on_listen(packet)
        elif state == SYN_SENT:
            self.handle_incoming_on_syn_sent(packet)
        else:
            if ACKFlag not in packet:
                # Ignorar paquetes que no sigan la especificación.
                return
            with self.control_block:
                self.protocol.acknowledge_packets_and_update_timers_with(packet)
                if state == SYN_RCVD:
                    self.handle_incoming_on_syn_rcvd(packet)
                elif state == ESTABLISHED:
                    self.handle_incoming_on_established(packet)
                elif state == FIN_WAIT1:
                    self.handle_incoming_on_fin_wait1(packet)
                elif state == FIN_WAIT2:
                    self.handle_incoming_on_fin_wait2(packet)
                elif state == CLOSE_WAIT:
                    self.handle_incoming_on_close_wait(packet)
                elif state == LAST_ACK:
                    self.handle_incoming_on_last_ack(packet)
                elif state == CLOSING:
                    self.handle_incoming_on_closing(packet)
    
    def handle_incoming_on_listen(self, packet):
        if SYNFlag in packet:
            self.set_state(SYN_RCVD)
            self.initialize_control_block_from(packet)
            destination_ip = packet.get_source_ip()
            destination_port = packet.get_source_port()
            self.protocol.set_destination_on_packet_builder(destination_ip,
                                                            destination_port)
            syn_ack_packet = self.build_packet(flags=[SYNFlag, ACKFlag])
            # El próximo byte que enviemos debe secuenciarse después del SYN.
            self.control_block.increment_snd_nxt()
            self.socket.send(syn_ack_packet)
            
    def handle_incoming_on_syn_sent(self, packet):
        if SYNFlag not in packet or ACKFlag not in packet:
            return
        ack_number = packet.get_ack_number()
        # +1 dado que el SYN también se secuencia.
        expected_ack = 1 + self.protocol.iss
        if expected_ack == ack_number:
            self.initialize_control_block_from(packet)
            self.protocol.\
            remove_from_retransmission_queue_packets_acked_by(packet)
            self.set_state(ESTABLISHED)
            self.send_ack()

    def handle_incoming_on_syn_rcvd(self, packet):
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            self.set_state(ESTABLISHED)
            # Este paquete está reconociendo nuestro SYN. Debemos incrementar
            # SND_UNA para reflejar esto.
            self.control_block.increment_snd_una()
            
    def handle_incoming_fin(self, packet, next_state):
        seq_number = packet.get_seq_number()
        # El número de SEQ debería ser el que estamos esperando.
        if seq_number == self.control_block.get_rcv_nxt():
            self.set_state(next_state)
            self.protocol.read_stream_open = False
            # El FIN también se secuencia, y por ende debemos incrementar el
            # próximo byte que esperamos recibir.
            self.control_block.increment_rcv_nxt()
        # Enviar ACK (si el checkeo anterior falla, el número de ACK del
        # paquete a enviar será el adecuado).
        self.send_ack()
        
    def process_on_control_block(self, packet):
        ignore_payload = not self.protocol.read_stream_open
        self.control_block.process_incoming(packet,
                                            ignore_payload=ignore_payload)
        
    def send_ack_for_packet_only_if_it_has_payload(self, packet):
        # Esto es para evitar el envío de ACKs para paquetes que sólo
        # reconozcan datos.
        if packet.has_payload():
            self.send_ack()
            
    def handle_incoming_on_established(self, packet):
        if FINFlag in packet:
            self.handle_incoming_fin(packet, next_state=CLOSE_WAIT)
        else:
            self.process_on_control_block(packet)
            if not self.control_block.has_data_to_send():
                # Si hay datos a punto de enviarse, "piggybackear" el ACK ahí
                # mismo. No es necesario mandar un ACK manualmente.
                self.send_ack_for_packet_only_if_it_has_payload(packet)
        
    def handle_incoming_on_fin_wait1(self, packet):
        should_send_ack = True
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            # Sólo puede ser el ACK al FIN previamente enviado.
            self.set_state(FIN_WAIT2)
            if FINFlag in packet:
                self.handle_incoming_fin(packet, next_state=CLOSED)
                # El método anterior ya se encarga de disparar un ACK.
                should_send_ack = False
        else:
            # Analizar si es un FIN, lo cual significaría que nuestro
            # interlocutor cerró su stream de escritura en simultáneo.
            if FINFlag in packet:
                self.handle_incoming_fin(packet, next_state=CLOSING)
                # Ídem comentario de líneas arriba.
                should_send_ack = False
        # Podríamos continuar recibiendo datos, por lo que debemos procesar el
        # paquete de forma adecuada.
        self.process_on_control_block(packet)
        if should_send_ack:
            # Y por último mandar un ACK (de haber datos en el paquete).
            self.send_ack_for_packet_only_if_it_has_payload(packet)
            
    def handle_incoming_on_fin_wait2(self, packet):
        if FINFlag in packet:
            self.handle_incoming_fin(packet, next_state=CLOSED)
        else:
            self.process_on_control_block(packet)
            self.send_ack_for_packet_only_if_it_has_payload(packet)
            
    def handle_incoming_on_close_wait(self, packet):
        # Sólo deberíamos procesar ACKs entrantes e ignorar todo lo demás
        # (pues la otra parte ya cerró su stream de escritura).
        # Al estar cerrado el stream de lectura, sabemos que el bloque de
        # control ignorará eventuales datos contenidos en el paquete.
        self.process_on_control_block(packet)
    
    def set_closed_if_packet_acknowledges_fin(self, packet):
        # Pasar a CLOSED sólo si este paquete reconoce el FIN que mandamos
        # antes.
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            self.set_state(CLOSED)
    
    def handle_incoming_on_last_ack(self, packet):
        self.set_closed_if_packet_acknowledges_fin(packet)
            
    def handle_incoming_on_closing(self, packet):
        self.set_closed_if_packet_acknowledges_fin(packet)