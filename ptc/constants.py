# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


# Campo Protocol ID del header IP
PROTOCOL_NUMBER = 202

# Granularidad del reloj (en segundos)
CLOCK_TICK = 0.01

# Máximo SEQ/ACK y máximo tamaño de ventana
MAX_SEQ = (1<<32) - 1
MAX_WND = (1<<16) - 1

# Estados del protocolo
SYN_SENT = 1
SYN_RCVD = 2
ESTABLISHED = 3
CLOSED = 6
LISTEN = 7
FIN_WAIT1 = 10
FIN_WAIT2 = 11
CLOSE_WAIT = 12
LAST_ACK = 13
CLOSING = 14

# Modos soportados por el método shutdown de los sockets
SHUT_RD = 0
SHUT_WR = 1
SHUT_RDWR = 2

# Modos soportados por el método close de los sockets
WAIT = 3    # Cerrar normalmente y en forma sincronizada con el interlocutor
NO_WAIT = 4 # Cerrar normalmente; no esperar a que interlocutor también cierre
ABORT = 5   # Cerrar inmediatamente; abortar la conexión

NULL_ADDRESS = '0.0.0.0'

# Tamaño en bytes del buffer que almacena los datos entrantes
RECEIVE_BUFFER_SIZE = 1024

# Tamaño máximo de segmento
MSS = 2*1024*1024

# Constantes vinculadas a estimación del RTO y retransmisiones
MAX_RETRANSMISSION_ATTEMPTS = 12
BOGUS_RTT_RETRANSMISSIONS = MAX_RETRANSMISSION_ATTEMPTS / 4
INITIAL_RTO = 1 / CLOCK_TICK
MAX_RTO = 60 / CLOCK_TICK
ALPHA = 0.125
BETA = 0.25
K = 4