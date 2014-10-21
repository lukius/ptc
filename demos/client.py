from ptc import Socket, SHUT_WR
from server import SERVER_IP, SERVER_PORT

to_send = 'foo bar baz'
received = str()

# Use PTC sockets within with blocks. This ensures proper disposal of the
# underlying resources once the socket is no longer needed.
with Socket() as client_sock:
    # Make a connection to the PTC instance running on port SERVER_PORT on
    # host with IP address SERVER_IP. Block until it replies (no timeout was
    # given).
    client_sock.connect((SERVER_IP, SERVER_PORT))
    # Once here, the connection is successfully established. We can send as
    # well as receive arbitrary data.    
    client_sock.send(to_send)
    received += client_sock.recv(10)
    # We close the write stream but we can keep receiving further
    # data.
    client_sock.shutdown(SHUT_WR)
    received += client_sock.recv(20)
print 'client_sock received: %s' % received
