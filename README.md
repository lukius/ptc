### PTC -- Protocolo de Teoría de las Comunicaciones

#### Introduction

PTC is a TCP-based but extremely simplified transport protocol. It was (and still is!) developed in the context of [Teoría de las Comunicaciones](http://dc.uba.ar/tdc), an undergraduate course on networking of the MSc in Computer Science at the University of Buenos Aires. It is mainly aimed at providing a simple enough framework for delving into several transport-layer concepts (such as the implementation of "real" sliding window algorithms, connection establishment and maintenance, state transitions, and so forth) in a pragmatic way.

#### The protocol

##### Basic features

From a general standpoint, PTC has the following features:

 * **Bidirectionality**: it is a full-duplex protocol on which both parts can send data simultaneously and independently.
 * **Connection-oriented**: includes formal processes of connection establishment and connection release.
 * **Reliability**: through a sliding window algorithm, it guarantees reliable data delivery.

In what follows, we will give a more detailed overview of the protocol, starting with the segment format.

##### Segment format

The segment header has a fixed length of 16 bytes:

    0                   1                   2                   3   
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |          Source port        |       Destination port          |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                    #SEQ (sequence number)                     |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                   #ACK (acknowledge number)                   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                     |A|N|R|S|F|                               |
    |      Reserved       |C|D|S|Y|I|            Window             |
    |                     |K|T|T|N|N|                               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                          Payload                              |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    
Below we briefly discuss each of these fields:
 * `Source port` (16 bits): port number used by the sender of the packet.
 * `Destination port` (16 bits): port number used by the receiver of the packet.
 * `#SEQ` (32 bits):  indicates the first byte of data contained in the packet. Regarding this, note that the `SYN` and `FIN` control bits (explained soon) **must**  be sequenced. 
 * `#ACK` (32 bits): indicates the value of the next byte that the sender expects to receive. Once a connection is successfully established, this value **must** be sent.
 * `Reserved` (11 bits): reserved for future use; **must** be zero.
 * Control bits (5 bits):
  * `ACK` **must** be always set. Indicates that the `#ACK` field is significant.
  * `SYN` should be only set when attempting to establish a connection or when replying to a previously received `SYN` packet. Used to synchronize sequence numbers.
  * Similarly, `FIN` should be set only when the sender is willing to close its write stream. Note that the receiver might continue to send data, which implies that the sender **must** continue to correctly process the payload contained in every incoming packet.
  * At the moment, the other flags (i.e., `RST` and `NDT`) have no use.
 * `Window` (16 bits): the number of bytes starting with `#ACK` that the sender is willing to accept.
 * `Payload` (variable length): data provided by upper-layer protocols.
    
Just like a TCP segment travels inside an IP datagram, our PTC packets will do so as well. In order for hosts to be aware of this, the `proto` field of the IP header must be set to 202, a value typically not assigned to any other known protocol.

##### Connection establishment and release

Before being able to send data, PTC instances must establish a connection. For this, a three-way handshake algorithm is used:
 1. First, the active instance (*client*) must send a `SYN` segment having an arbitrary `#SEQ` number (the *initial sequence number*). Moreover, `Window` must contain the allocated size in bytes for the receive buffer. The remaining fields may have any value; they will be ignored by the interlocutor.
 2. The passive instance (*server*) will respond with a `SYN`+`ACK` packet whose purpose is to not only acknowledge the connection establishment request but also to inform its initial sequence number. Thus, `#ACK` must be set to the received `#SEQ` plus one.
 3. Finally, the client will acknowledge the `SYN` sent by the server by sending an `ACK` packet on which the `#ACK` field must be set to the received `#SEQ` plus one as well.

Once this is done, both parts will consider that the connection is established.   

In order to release the connection, an asymmetric, four-way handshake algorithm is used. When a PTC is willing to close the connection, it will no longer be able to send further data (i.e., its write stream will be closed). However, it will be able to keep receiving data sent by its peer (i.e., its read stream remains open). The `FIN` control bit is used to accomplish this half-closing. The *States* section below covers every possible scenario regarding connection release.

##### Sliding window and control block

PTC flow control is essentially analogous to that of TCP (without options). It uses cumulative acknowledgements and provides a variable-sized receive window whose actual size is usually determined by the space allocated for the incoming buffer. Every aspect of the sliding window is encapsulated in a structure called *control block*, which is instanciated by a PTC once it has made contact with a remote interlocutor. The control block manages both the send and receive windows and also the incoming and outgoing data buffers. Regarding the send side, the following variables are defined:
 * `SND_UNA`, which contains the smallest sequence number still not acknowledged.
 * `SND_NXT`, which represents the next sequence number to be used in an outgoing segment.
 * `SND_WND`, which is the maximum number of bytes that can be sent at the moment, conforming to the information provided by the interlocutor.
 * `SND_WL1`, which indicates the sequence number of the last incoming packet used to update `SND_WND`.
 * `SND_WL2`, which, similarly, indicates the acknowledge number of the last incoming packet used to update `SND_WND`.
 
The next diagram shows the sequence space as defined by these variables:


                   1         2          3          4      
              ----------|----------|----------|---------- 
                     SND_UNA    SND_NXT    SND_UNA + SND_WND
                     
Each fragment may be understood as follows:
 1. Sequence numbers already acknowledged.
 2. Sequence numbers used in outgoing segments still not acknowledged.
 3. Sequence numbers currently available to dispatch new data segments.
 4. Sequence numbers that will be available in the future, as acknowledges arrive.
 

The receive window is managed by keeping track of these variables:
 * `RCV_NXT`, whose value corresponds to the next sequence number that PTC expects to receive.
 * `RCV_WND`, which is the number of bytes that PTC is able to accept at the moment.

In a similar fashion, the sequence space might be pictured like so:

                       1          2          3      
                   ----------|----------|---------- 
                          RCV_NXT    RCV_NXT + RCV_WND  
            
Here, the first portion contains every sequence number already received and acknowledged, while portion 2 represents the sequence numbers that PTC is now willing to accept. Finally, portion 3 has every sequence number which will be acceptable in the future. These will move to portion 2 when data arrives and `RCV_NXT` moves right.

##### Retransmissions

After sending a data segment, PTC will also enqueue it in the retransmission queue. This packet will remain there until it is eventually acknowledged. Moreover, the protocol specifies a timeout for this acknowledge, `RETRANSMISSION_TIMEOUT`. Should this time be exceeded, PTC must assume that its packet did not reach destination and thus will have to be retransmitted.  

A maximum number of retransmissions is defined as well (`MAX_RETRANSMISSION_ATTEMPTS`). If any segment happens to be retransmitted more times than this value, PTC must assume that the connection died and will proceed to close it without sending `FIN`, freeing instead every resource allocated.

##### States

Cada PTC puede atravesar una serie de estados durante el ciclo de vida de una conexión:
 * `LISTEN`, que representa la espera de una conexión entrante por parte de un PTC remoto.
 * `SYN_SENT`, en el que el PTC está a la espera de una respuesta a la solicitud de conexión previamente enviada.
 * `SYN_RCVD`, donde el PTC ya recibió una solicitud de conexión y respondió afirmativamente a ella, y está aguardado a que este último mensaje sea confirmado.
 * `ESTABLISHED`, que indica una conexión abierta y activa. Es el estado normal de intercambio de datos.
 * `FIN_WAIT1`, en donde el PTC inició el cierre de su stream de salida y está aguardado la confirmación de su interlocutor.
 * `FIN_WAIT2`, en donde el PTC ya cerró exitosamente su stream de salida y queda a la espera de que su interlocutor cierre el suyo.
 * `CLOSE_WAIT`, que indica que el interlocutor ya cerró su stream de salida y el PTC está esperando que el usuario decida cerrar la conexión.
 * `CLOSING`, que representa un cierre simultáneo de ambas partes.
 * `LAST_ACK`, en el que el PTC sólo espera a recibir la confirmación del cierre de su stream de salida (su interlocutor ya cerró previamente el suyo).
 * `CLOSED`, que es la ausencia de conexión.

Las transiciones entre dichos estados se disparan por medio de tres tipos de eventos: acciones del usuario (`close`/`shutdown`, `listen` y `connect`), arribo de segmentos y exceso de retransmisiones. El diagrama que se muestra abajo resume los cambios de estado posibles junto con los respectivos eventos y las acciones tomadas por el protocolo en respuesta a ellos.

                                  +---------+ --------        connect  
                                  |  CLOSED |         \     ----------  
                                  +---------+           \      SYN 
                                    |     ^               \     
                         listen     |     |   close         \           
                       ----------   |     | ----------        \         
                                    |     |                     \       
                                    V     |                       \     
                                  +---------+                       \   
                                  |  LISTEN |                        |  
                                  +---------+                        |  
                           SYN      |                                |  
                        ---------   |                                V  
    +---------+          SYN+ACK   /                           +----------+
    |         |<------------------                             |          |
    |SYN_RCVD |                                                | SYN_SENT |
    |         |-------------------           ------------------|          |
    +---------+          ACK       \       /     SYN+ACK       +----------+
                      ---------     |     |   -----------                  
                                    |     |       ACK                    
                                    V     V                                
                               +---------------+                              
                               |  ESTABLISHED  |                              
                               +---------------+                              
                           close    |     |      FIN                     
                          -------   |     |    -------                     
     +-----------+          FIN     /      \     ACK             +-------------+
     | FIN_WAIT1 |<----------------          ------------------->|  CLOSE_WAIT |
     |           |--------------------                           +-------------+
     +-----------+          FIN        \                        close  |
       |      ACK         -------      |                       ------- |  
       |   --------         ACK        |                         FIN   |  
       V                               V                               V  
     +---------+                  +---------+                    +----------+
     |FIN_WAIT2|                  | CLOSING |                    | LAST_ACK |
     +---------+                  +---------+                    +----------+
       |                       ACK     |                     ACK   |  
       |    FIN              -------   |                   ------- |  
       |  -------                      V                           |  
       \    ACK                   +---------+                      /
         ------------------------>|  CLOSED |<--------------------
                                  +---------+

A los efectos de mantener la simplicidad del diagrama, el paso a `CLOSED` luego de exceder el máximo de retransmisiones fue omitido. Observar que esta transición podría originarse no sólo en `ESTABLISHED` sino también en cualquier otro estado sincronizado que involucre el envío de un paquete de datos o un paquete `FIN`.

##### Procesamiento de paquetes

Al recibir un paquete, éste se procesará de una u otra manera en función del estado transitado por PTC. En lo que sigue, notaremos con `SEG_SEQ`, `SEG_ACK` y `SEG_LEN` el número de secuencia del paquete entrante, su número de ACK y el tamaño de sus datos respectivamente. Notar además que todo paquete cuyo flag de `ACK` esté apagado **debe** ser automáticamente descartado sin importar en qué estado esté el protocolo (a excepción de `LISTEN`).

###### `LISTEN`

Sólo se debe aceptar un paquete `SYN` y se debe inicializar el bloque de control a partir de la información provista por dicho paquete y por un número de secuencia inicial (`ISS`) computado aleatoriamente. Luego de cambiar el estado, se deberá enviar un paquete `SYN`/`ACK` en respuesta y por último incrementar `SND_NXT`.

###### `SYN_SENT`

Sólo se debe aceptar un paquete con los flags de `SYN` y `ACK` prendidos. Además, `SEG_ACK` debe ser el valor del número de secuencia previamente enviado más uno. En tal caso, se deberá inicializar el bloque de control, pasar a `ESTABLISHED` y enviar el reconocimiento respectivo.

###### `SYN_RCVD`

Si `SEG_ACK` es aceptable (i.e., su valor es uno más que el número de secuencia enviado), se debe pasar a `ESTABLISHED` e incrementar `SND_UNA` (recordar que el flag `SYN` también se secuencia).

###### `ESTABLISHED`

Si el flag de `FIN` está prendido, deberá validarse que `SEG_SEQ` coincida con `RCV_NXT`, en cuyo caso se deberá pasar al estado `CLOSE_WAIT`, incrementar `RCV_NXT` (dado que el `FIN` se secuencia) y enviar un reconocimiento adecuado. Si `SEG_SEQ` tuviese un valor inesperado, simplemente se deberá enviar un `ACK` informando el valor actual de `RCV_NXT`.  

En otro caso (i.e., el paquete no es `FIN`),  se debe validar en el bloque de control la aceptación del paquete. `SEG_ACK` es aceptable si su valor está dentro de los valores de secuenciamiento esperados:
    
    SND_UNA < SEG_ACK <= SND_NXT
    
En tal caso, el nuevo valor de `SND_UNA` será precisamente `SEG_ACK`. Por otro lado, los datos serán aceptables sólo si los números de secuencia contenidos en el paquete tienen intersección no nula con la ventana de recepción:

    RCV_NXT <= SEG_SEQ < RCV_NXT + RCV_WND  o bien
    RCV_NXT <= SEG_SEQ + SEG_LEN - 1 < RCV_NXT + RCV_WND

De ser así, se deberá guardar en el buffer de entrada la porción de datos que esté contenida en la ventana de recepción. Si esta porción comienza en `RCV_NXT`, entonces se debe actualizar este valor sumándole la longitud de los datos aceptados. Además de esto, se debe actualizar el valor de `RCV_WND` decrementándola para reflejar el hecho de que el buffer contiene más información.  

El bloque de control también debe analizar si corresponde actualizar el valor de `SND_WND` con este paquete. Esto se hará en caso de que el paquete esté reconociendo números de secuencia esperados:

    SND_UNA <= SEG_ACK <= SND_NXT

Notar que en esta ocasión es necesario el `<=` de la izquierda para procesar correctamente potenciales actualizaciones de ventana con valores de `ACK` repetidos.  

Además de `SND_WND`, también se requiere actualizar `SND_WL1` y `SND_WL2` sólo si se trata de un segmento "más nuevo":

    SND_WL1 < SEG_SEQ o bien
    SND_WL1 = SEG_SEQ y SND_WL2 <= SEG_ACK
    
En este escenario, se hará efectiva la actualización de las variables: `SND_WND` tomará el valor de la ventana informada en el paquete, `SND_WL1` tomará el valor de `SEG_SEQ` y `SND_WL2`, el de `SEG_ACK`.  

Finalmente, si el paquete contiene datos, se debe enviar un `ACK` independientemente de si fue o no aceptado. Para ello, el protocolo podría hacer piggybacking si es que hubiera datos en el buffer de salida aguardando a ser enviados. Caso contrario, un `ACK` ad-hoc deberá enviarse.

###### `FIN_WAIT1`

Si el bloque de control acepta `SEG_ACK`, significa que este paquete reconoce el `FIN` enviado. Luego, se debe pasar a `FIN_WAIT2`. Si además viniese un `FIN`, éste se deberá procesar tal como se describió para el caso de `ESTABLISHED`, pero pasando al estado `CLOSED`.  

Si `SEG_ACK` no fuese aceptado y el paquete fuese un `FIN`, se deberá hacer lo mismo sólo que el próximo estado debe ser `CLOSING` (dado que se trata de un cierre simultáneo).  

En cualquier caso, se deberá validar el paquete en el bloque de control y eventualmente enviar un `ACK` tal como se explicó más arriba. Esto es porque el paquete podría contener datos válidos. Observar que en este caso no podrá hacerse piggybacking dado que ya se envió el `FIN`. 

###### `FIN_WAIT2`

Si el paquete es `FIN`, se deberá proceder tal como en `ESTABLISHED` pero, a diferencia, el siguiente estado deberá ser `CLOSED`. De lo contrario, se deberá procesar el paquete en el bloque de control y enviar un `ACK` si el paquete tuviera datos (notar que esto se corresponde con el último párrafo de lo explicado para `FIN_WAIT1`).

###### `CLOSING`

En este caso, sólo resta esperar que `SEG_ACK` sea aceptado, lo cual sólo puede significar que el `FIN` fue reconocido y que por ende el protocolo debe pasar al estado `CLOSED`.

###### `CLOSE_WAIT`

Dado que el interlocutor cerró su stream de datos, sólo deben esperarse reconocimientos en este estado. Por ello, se deberá procesar el paquete en el bloque de control para ajustar las variables de la ventana de emisión.

###### `LAST_ACK`

El procesamiento en este caso es análogo al de `CLOSING`.


#### Código fuente

La implementación de PTC está hecha en Python 2.7 y viene acompañada de un plugin para Wireshark que permite visualizar los paquetes capturados. En las secciones que siguen veremos la estructura de módulos a alto nivel, mostraremos algunos ejemplos de uso de sockets PTC y mencionaremos cómo correr los casos de prueba. 

##### Módulos

Los módulos que implementan el protocolo están en el directorio `ptc`. A continuación listamos cada uno de ellos: 

###### `buffer`

Implementación de un buffer de bytes (`DataBuffer`) que es usado por el bloque de control para definir los buffers de entrada y de salida. Este buffer ofrece funcionalidad para reflejar el hecho de que los datos pueden llegar potencialmente fuera de orden. Por ejemplo, el método `add_chunk` recibe un offset dentro del buffer y los bytes a agregar a partir de dicho offset. El siguiente fragmento ilustra un posible uso del mismo:

```python
>>> buffer = DataBuffer()
>>> buffer.add_chunk(8, 'baz')
>>> buffer.add_chunk(4, 'bar ')
>>> buffer.put('foo ')
>>> buffer.get(15)
'foo bar baz'
>>> buffer.empty()
True
```

Notar que `get` extrae los datos del buffer. El argumento que recibe indica la máxima cantidad de bytes a extraer, aunque potencialmente podrían ser menos.

###### `cblock`

Implementación del bloque de control, `PTCControlBlock`. Todo lo referente a los buffers de datos y la manipulación de las ventanas de emisión y recepción está en esta clase.

###### `constants`

Definición de diversas constantes utilizadas por el protocolo, entre las que se encuentran, por ejemplo, los estados.

###### `exceptions`
 
Definición de una excepción genérica (`PTCError`) para representar errores del protocolo o de uso inválido del mismo. El constructor recibe un string como argumento que permite indicar con mayor detalle qué fue lo que realmente ocurrió.
 
###### `handler`

Implementación del handler de paquetes entrantes, `IncomingPacketHandler`. El método principal, `handle`, recibe un paquete que acaba de ser recibido y, en función del estado del protocolo, termina derivando en otro método específico para tal estado. 

###### `packet`

Implementación del paquete PTC, `PTCPacket`. Esta clase brinda una interfaz que permite definir el valor de cada campo del segmento y también de las direcciones IP involucradas:

```python
>>> packet = PTCPacket()
>>> packet.set_source_ip('192.168.0.1')
>>> packet.set_destination_ip('192.168.0.100')
>>> packet.set_source_port(12345)
>>> packet.set_destination_port(80)
>>> packet.set_seq_number(8989)
>>> packet.add_flag(SYNFlag)
>>> packet.set_payload('hola!')
>>> packet.set_window_size(1024)
>>> packet
From: (192.168.0.1, 12345)
To: (192.168.0.100, 80)
Seq: 8989
Ack: 0
Flags: SYN
Window: 1024
Payload: hola!
>>> packet.get_ack_number()
0
>>> packet.get_seq_number()
8989
>>> # Con el siguiente método podemos conocer el intervalo de números
>>> # de secuencia consumidos por el paquete (#SEQ + |payload|).
>>> packet.get_seq_interval()
(8989, 8994)
```

Para averiguar si un flag determinado está presente en un paquete, puede utilizarse el operador `in`:

```python
>>> ACKFlag in packet
False
>>> SYNFlag in packet
True
>>> FINFlag in packet
False
```


###### `packet_utils`

Herramientas para facilitar la manipulación de paquetes: un decodificador de bytes (`PacketDecoder`), que es utilizado para mapear los datos recibidos de la red a un `PTCPacket`,  y un constructor de paquetes (`PacketBuilder`), que simplemente recibe argumentos (flags, número de secuencia, número de reconocimiento, ventana, etc.) y arma un paquete con tales características.   

La clase que implementa el protocolo, `PTCProtocol` (mencionada más abajo) ofrece un método de conveniencia que se apoya en el `PacketBuilder` para armar paquetes con la información actual del bloque de control:

```python
def build_packet(self, seq=None, ack=None, payload=None, flags=None,
                 window=None):
    if seq is None:
        seq = self.control_block.get_snd_nxt()
    if flags is None:
        flags = [ACKFlag]
    if ack is None and ACKFlag in flags:
        ack = self.control_block.get_rcv_nxt()
    if window is None:
        window = self.control_block.get_rcv_wnd()
    packet = self.packet_builder.build(payload=payload, flags=flags,
                                       seq=seq, ack=ack, window=window)
    return packet
```

De esta forma, al momento de enviar un `ACK`, sólo basta con invocar a este método sin argumentos para generar el paquete adecuado.

###### `thread`

Implementación de los threads en los que se apoya el protocolo para su funcionamiento:
 * Uno de ellos se encarga de simular el clock del sistema (`Clock`). Cada `CLOCK_TICK` segundos (definido por defecto en 0.1) invocará al método `tick` del protocolo.
 * Otro tiene como objetivo monitorear el socket y recibir los paquetes (`PacketReceiver`). Al detectar la llegada de uno, se invocará el método `handle_incoming` del protocolo (que a su vez se apoyará en el handler mencionado más arriba).
 * El último de ellos es el que envía los paquetes de datos y eventualmente el `FIN` (`PacketSender`). Este comportamiento queda definido en el método `handle_outgoing` del protocolo, que es ejecutado en el contexto de este thread cada vez que ocurre algún evento que podría motivar el envío de nuevos datos (e.g., llegada de reconocimientos o invocaciones a `send` por parte del usuario).

###### `rqueue`

Implementación de la cola de retransmisión (`RetransmissionQueue`). Al encolarse, los paquetes se asocian con un timestamp que irá revisándose en cada tick del reloj (mediante el método `tick`, que de hecho es invocado por el método homónimo del protocolo). Cada vez que expira un timeout, el paquete respectivo se mueve a una lista interna de paquetes a retransmitir que luego es consumida por el protocolo. Por otra parte, al procesar un `ACK`, el método `remove_acknowledged_by` permite extraer de la cola todo paquete cuyo payload quede completamente cubierto por el `#ACK` contenido en el paquete.

###### `seqnum`

Implementación de números de secuencia (`SequenceNumber`). Son utilizados dentro de los paquetes y dentro del bloque de control para representar las variables de la ventana deslizante ligadas a números de secuencia (como `SND_UNA` o `SND_NXT`). Internamente trabaja con aritmética modular y sobrecarga los operadores aritméticos tradicionales de manera de poder utilizarlos en contextos donde se esperen enteros standard:

```python
>>> n = SequenceNumber(5, modulus=10)
>>> m = SequenceNumber(9, modulus=10)
>>> n + m
4
>>> n + 16
1
>>> n > 1
True
>>> n > 6
False
```

La clase `SequenceNumber` también provee una serie de métodos de clase que permiten hacer comparaciones en rango teniendo en cuenta que, eventualmente, puede haber *wrap-around*. Por ejemplo, si el límite superior de la ventana de emisión supera el máximo valor permitido, éste arrancará desde 0. Por ende, las comparaciones efectuadas en el protocolo deben tolerar tales escenarios. A raíz de esto, el método `a_leq_b_leq_c` recibe tres valores `a`, `b` y `c` y computa el valor de verdad de `a <= b <= c`:

```python
>>> eight = SequenceNumber(8, modulus=10)
>>> five = SequenceNumber(5, modulus=10)
>>> three = SequenceNumber(3, modulus=10)
>>> # Caso normal
>>> SequenceNumber.a_leq_b_leq_c(three, five, eight)
True
>>> # Caso en el que el c superó el máximo
>>> SequenceNumber.a_leq_b_leq_c(five, eight, three)
True
>>> # Caso en el que b y c superaron el máximo, b < c
>>> SequenceNumber.a_leq_b_leq_c(eight, three, five)
True
>>> # b y c superaron el máximo pero b > c
>>> SequenceNumber.a_leq_b_leq_c(eight, five, three)
False
>>> # b > max(a, c)
>>> SequenceNumber.a_leq_b_leq_c(three, eight, five)
False
>>> # b < min(a, c)
>>> SequenceNumber.a_leq_b_leq_c(five, three, eight)
False
```

###### `ptc_socket`

Provee un wrapper sobre el protocolo (`Socket`) para definir una interfaz de uso similar a la de los sockets de Python tradicionales. El usuario final del protocolo interactuará directamente con instancias de `Socket`, tal como se ve en la sección `Modo de uso`.

###### `soquete`

Provee una abstracción del socket raw subyacente al protocolo (`Soquete`). Esto permite desligarse de la declaración y uso del mismo, pudiendo así evitar la manipulación explícita de los bytes dentro del código del protocolo.

###### `protocol`

Implementación del núcleo del protocolo (`PTCProtocol`). Además de los handlers invocados por los threads, también manipula la cola de retransmisión y ofrece métodos que implementan el comportamiento del `Socket` mencionado más arriba.  
El protocolo mantiene una instancia de `Soquete` en la variable `socket`. A través de ella es posible inyectar paquetes en la red invocando al método `send` y pasando como argumento el paquete que deseamos enviar a destino. Por otro lado, el protocolo provee el método `send_and_queue` en caso de querer no sólo enviar el paquete sino además encolarlo en la cola de retransmisión.


##### Modo de uso

La forma de usar el protocolo desde otras aplicaciones es a través del wrapper `Socket` nombrado en la sección anterior. Al implementar los métodos más comunes de los sockets tradicionales, la experiencia de uso será esencialmente análoga. No obstante, todo programa que use sockets PTC **debe** ejecutarse con permisos elevados al requerir instanciaciones de sockets raw. Además, a los efectos de asegurar un correcto cierre del programa, sugerimos utilizar los sockets dentro de bloques `with`. De no hacer esto, será necesario llamar manualmente a `close` o a `free` para que el protocolo pueda finalizar la conexión y apagar los threads. En el caso donde esta llamada no se haga, el programa podría quedar "colgado" a causa de tales threads.  

A continuación mostramos un breve ejemplo en el que un script liga un socket PTC al puerto 6677 de localhost y otro script diferente declara y conecta un nuevo socket a dicho puerto. Ambos se envían datos mutuamente y por último muestran por la salida standard la información recibida:

```python
# Script que liga un socket al puerto 6677 de localhost.
from ptc import Socket
to_send = 'Lorem ipsum dolor sit amet'
received = str()
with Socket() as sock1:
    sock1.bind(('127.0.0.1', 6677))
    sock1.listen()
    sock1.accept()
    received += sock1.recv(15)
    sock1.send(to_send)
    sock1.close()
print 'sock1 received: %s' % received
```

```python
# Script que abre un socket y lo conecta al puerto 6677 de localhost.
from ptc import Socket, SHUT_WR
to_send = 'foo bar baz'
received = str()
with Socket() as sock2:
    sock2.connect(('127.0.0.1', 6677))
    sock2.send(to_send)
    received += sock2.recv(10)
    # Cerramos el stream de escritura pero podemos seguir recibiendo datos.
    sock2.shutdown(SHUT_WR)
    received += sock2.recv(20)
print 'sock2 received: %s' % received
```

Al finalizar, se debería visualizar `sock1 received: foo bar baz` en la salida del primer script y `sock2 received: Lorem ipsum dolor sit amet` en la salida del segundo.

##### Tests

La implementación de PTC provee un conjunto de casos de prueba con la particularidad de que éstos corren íntegramente en memoria. Además de optimizar el tiempo de ejecución y evitar depender de la red, esto también permite desarrollar sin necesidad de instanciar un socket raw, de lo que se desprende que deja de ser requisito tener permisos elevados para ejecutar el código.  

La forma de correr los tests es ejecutando el script `run_tests.py` con el intérprete de Python 2.7. Al no recibir argumentos adicionales, el script extraerá todos los tests que encuentre en el directorio `test` y correrá uno tras uno hasta finalizar, mostrando los resultados por la salida standard. Es posible, no obstante, ejecutar clases de test individuales. Esto se logra pasando un argumento de la forma `--<identificador>`, en donde los valores de `<identificador>` se corresponden con los nombres de los archivos de test. La siguiente lista muestra los identificadores disponibles:

 * `syn`: tests de inicio de conexión.
 * `fin`: tests de finalización de conexión.
 * `ack`: tests que involucran distintos escenarios de reconocimiento.
 * `data`: tests de intercambio de datos.
 * `control-block`: tests del bloque de control.
 * `retransmission`: tests del mecanismo de retransmisión en el protocolo.
 * `rqueue`: tests de la estructura de datos que implementa la cola de retransmisión.
 * `buffer`: tests de la estructura de datos que implementa el buffer.
 * `seqnum`: tests de la clase que implementa los números de secuencia. 
 * `packet`: tests de paquetes (mapeo de bytes a paquete y viceversa).

 
A modo de ejemplo, la siguiente línea puede usarse para correr los tests de inicio y finalización de conexión:  
```
$ python run_tests.py --syn --fin
```

##### Disector de Wireshark

El directorio `dissector` contiene un plugin de Wireshark para interpretar los paquetes del protocolo. Por medio de éste, podremos observar qué paquetes envían y reciben nuestros sockets PTC y qué contiene cada uno de sus campos. El modo de uso es simple: basta con usar `ptc` como filtro para que Wireshark nos muestre sólo los paquetes capturados que pertenezcan a nuestro protocolo.    

El disector está compilado para arquitecturas Intel de 32 ó 64 bits; se deberá escoger la versión correspondiente según la máquina donde se vaya a utilizar el protocolo. Para instalarlo, es necesario copiar el archivo al directorio de plugins globales de Wireshark, que puede conocerse accediendo al menú `Help --> About Wireshark --> Folders`. Tener en cuenta que el plugin es compatible con versiones de Wireshark posteriores a la 1.6, por lo que es muy posible que no funcione en versiones previas. Por este motivo, sugerimos revisar la versión a utilizar y hacer la actualización si fuese necesario.

#### Referencias

[1] [RFC 793: Transmission Control Protocol](http://www.ietf.org/rfc/rfc793.txt)  
[2] [RFC 1122: Requirements for Internet Hosts -- Communication Layers](http://www.ietf.org/rfc/rfc1122.txt)  
[3] Tanenbaum, A. *Computer Networks*, 3ra Ed. Capítulo 3: págs. 202-213.
