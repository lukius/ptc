# -*- coding: utf-8 -*-

##########################################################
#                 Trabajo Práctico 3                     #
#         Programación de protocolos end-to-end          #
#                                                        # 
#              Teoría de las Comunicaciones              #
#                       FCEN - UBA                       #
#              Segundo cuatrimestre de 2014              #
##########################################################


try:
    from ptc import Socket, SHUT_WR
except:
    import sys
    sys.path.append('../../')
    from ptc import Socket, SHUT_WR

SERVER_IP = '127.0.0.1'
SERVER_PORT = 6677

to_send = 'foo bar baz'
received = str()

# Usar sockets PTC dentro de bloques with. Esto nos asegura que los recursos
# subyacentes serán liberados de forma adecuada una vez que el socket ya no
# se necesite.
with Socket() as client_sock:
    # Establecer una conexión al PTC corriendo en el puerto SERVER_PORT en
    # el host con dirección SERVER_IP. Esta llamada es bloqueante, aunque
    # en este caso se declara un timeout de 10 segundos. Pasado este tiempo,
    # el protocolo se dará por vencido y la conexión no se establecerá.
    client_sock.connect((SERVER_IP, SERVER_PORT), timeout=10)
    # Una vez aquí, la conexión queda establecida exitosamente. Podemos enviar
    # y recibir datos arbitrarios.
    client_sock.send(to_send)
    received += client_sock.recv(10)
    # Cerramos nuestro stream de escritura pero podemos continuar recibiendo
    # datos de la contraparte.
    client_sock.shutdown(SHUT_WR)
    received += client_sock.recv(20)
print 'client_sock received: %s' % received
