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
                # Ignore packets not following protocol specification.
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
            # The next byte we send should be sequenced after the SYN flag.
            self.control_block.increment_snd_nxt()
            self.socket.send(syn_ack_packet)
            
    def handle_incoming_on_syn_sent(self, packet):
        if SYNFlag not in packet or ACKFlag not in packet:
            return
        ack_number = packet.get_ack_number()
        # +1 since the SYN flag is also sequenced.
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
            # This packet is acknowledging our SYN. We must increment SND_UNA
            # in order to reflect this.
            self.control_block.increment_snd_una()
            
    def handle_incoming_fin(self, packet, next_state):
        seq_number = packet.get_seq_number()
        # SEQ number should be the one we are expecting.
        if seq_number == self.control_block.get_rcv_nxt():
            self.set_state(next_state)
            self.protocol.read_stream_open = False
            # The FIN flag is also sequenced, and so we must increment the next
            # byte we expect to receive.
            self.control_block.increment_rcv_nxt()
        # Send ACK (if the previous check fails, the ACK number will be
        # automatically set to the proper one).
        self.send_ack()
        
    def process_on_control_block(self, packet):
        ignore_payload = not self.protocol.read_stream_open
        self.control_block.process_incoming(packet,
                                            ignore_payload=ignore_payload)
        
    def send_ack_for_packet_only_if_it_has_payload(self, packet):
        # This is to avoid sending ACKs for plain ACK segments.
        if packet.has_payload():
            self.send_ack()
            
    def handle_incoming_on_established(self, packet):
        if FINFlag in packet:
            self.handle_incoming_fin(packet, next_state=CLOSE_WAIT)
        else:
            self.process_on_control_block(packet)
            if not self.control_block.has_data_to_send():
                # If some data is about to be sent, then just piggyback the ACK
                # there. It is not necessary to manually send an ACK.
                self.send_ack_for_packet_only_if_it_has_payload(packet)
        
    def handle_incoming_on_fin_wait1(self, packet):
        should_send_ack = True
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            # It can only be the ACK to our FIN packet previously sent.
            self.set_state(FIN_WAIT2)
            if FINFlag in packet:
                self.handle_incoming_fin(packet, next_state=CLOSED)
                # This last method already sends an ACK.
                should_send_ack = False
        else:
            # Check if it is a FIN packet, meaning that our peer closed
            # its write stream simultaneously.
            if FINFlag in packet:
                self.handle_incoming_fin(packet, next_state=CLOSING)
                # Same comment from above applies here as well.
                should_send_ack = False
        # We might receive data, so we must process the packet accordingly.
        self.process_on_control_block(packet)
        if should_send_ack:
            # Finally, send an ACK (if this packet contains some data).
            self.send_ack_for_packet_only_if_it_has_payload(packet)
            
    def handle_incoming_on_fin_wait2(self, packet):
        if FINFlag in packet:
            self.handle_incoming_fin(packet, next_state=CLOSED)
        else:
            self.process_on_control_block(packet)
            self.send_ack_for_packet_only_if_it_has_payload(packet)
            
    def handle_incoming_on_close_wait(self, packet):
        # We should only process incoming ACKs and ignore everything else since
        # the other side has closed its write stream.
        # Since the read stream is closed, we know that the control block will
        # ignore any incoming data. 
        self.process_on_control_block(packet)
    
    def set_closed_if_packet_acknowledges_fin(self, packet):
        # Move to CLOSED only if this packet ACKs the FIN we sent before.
        ack_number = packet.get_ack_number()
        if self.control_block.ack_is_accepted(ack_number):
            self.set_state(CLOSED)
    
    def handle_incoming_on_last_ack(self, packet):
        self.set_closed_if_packet_acknowledges_fin(packet)
            
    def handle_incoming_on_closing(self, packet):
        self.set_closed_if_packet_acknowledges_fin(packet)