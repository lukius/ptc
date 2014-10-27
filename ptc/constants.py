# Protocol ID field of IP header
PROTOCOL_NUMBER = 202

# Clock granularity in seconds
CLOCK_TICK = 0.01

# Maximum SEQ/ACK number and maximum window
MAX_SEQ = (1<<32) - 1
MAX_WND = (1<<16) - 1

# Protocol states
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

# Socket shutdown modes
SHUT_RD = 0
SHUT_WR = 1
SHUT_RDWR = 2

# Socket close modes
WAIT = 3    # Close gracefully and synchronized with the other party
NO_WAIT = 4 # Close gracefully; don't wait for the other party to close
ABORT = 5   # Close immediately; abort the connection

# Size in bytes of the buffer that holds incoming data
RECEIVE_BUFFER_SIZE = 1024

# Maximum segment size
MSS = 2*1024*1024

# RTO estimation and retransmission constants
# TODO: this is getting ugly. Better organization required.
MAX_RETRANSMISSION_ATTEMPTS = 12
BOGUS_RTT_RETRANSMISSIONS = MAX_RETRANSMISSION_ATTEMPTS / 4
INITIAL_RTO = 1 / CLOCK_TICK
MAX_RTO = 60 / CLOCK_TICK
ALPHA = 0.125
BETA = 0.25
K = 4