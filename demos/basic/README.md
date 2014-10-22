### Demo: basic

These scripts show a basic example of PTC sockets. `server.py` declares a socket that is moved to the `LISTEN` state after binding it to a local address. `client.py` instanciates another socket and actively connects it to this same address. Once this happens, both sockets exchange two short messages.
