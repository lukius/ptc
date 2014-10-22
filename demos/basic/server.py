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
    from ptc import Socket
except:
    import sys
    sys.path.append('../../')
    from ptc import Socket

SERVER_IP = '127.0.0.1'
SERVER_PORT = 6677

to_send = 'Lorem ipsum dolor sit amet'
received = str()

# Usar sockets PTC dentro de bloques with. Esto nos asegura que los recursos
# subyacentes serán liberados de forma adecuada una vez que el socket ya no
# se necesite.
with Socket() as server_sock:
    # Ligar el socket a una interfaz local a través de la tupla (IP, PORT).
    server_sock.bind((SERVER_IP, SERVER_PORT))
    # Pasar al estado LISTEN.
    server_sock.listen()
    # Esta llamada se bloqueará hasta que otro PTC intente conectarse. No
    # obstante, luego de diez segundos de no recibir conexiones, PTC se
    # dará por vencido.
    server_sock.accept(timeout=10)
    # Una vez aquí, la conexión queda establecida exitosamente. Podemos enviar
    # y recibir datos arbitrarios.
    received += server_sock.recv(15)
    server_sock.send(to_send)
print 'server_sock received: %s' % received