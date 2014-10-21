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

# Use PTC sockets within with blocks. This ensures proper disposal of the
# underlying resources once the socket is no longer needed.
with Socket() as server_sock:
    # Bind the socket to a local interface by supplying an (IP, PORT) tuple. 
    server_sock.bind((SERVER_IP, SERVER_PORT))
    # Move the socket to the LISTEN state.
    server_sock.listen()
    # Block until some other PTC makes an active connection. Time out after
    # ten seconds.
    server_sock.accept(timeout=10)
    # Once here, the connection is successfully established. We can send as
    # well as receive arbitrary data.
    received += server_sock.recv(15)
    server_sock.send(to_send)
print 'server_sock received: %s' % received