## Слои

```text
Application code
    ↓
gRPC
    ↓
HTTP/2
    ↓
TCP
    ↓
IP
    ↓
network
```

## TCP

TCP даёт reliable ordered byte stream.

TCP не знает Protobuf, gRPC method, HTTP/2 stream или RPC boundaries. Для TCP это последовательность байтов.

## HTTP/2

HTTP/2 добавляет frames и streams.

```text
HTTP/2 connection
├── stream 1
├── stream 3
├── stream 5
└── stream 7
```

Каждый gRPC RPC естественно отображается на HTTP/2 stream.

Client-initiated HTTP/2 streams обычно имеют нечётные IDs.

## Multiplexing

Один TCP connection может переносить frames разных RPC:

```text
[frame stream=1]
[frame stream=5]
[frame stream=3]
[frame stream=1]
[frame stream=7]
```

HTTP/2 по `stream_id` понимает, к какому RPC относится frame.

## gRPC HTTP/2 request

Headers примерно такого смысла:

```text
:method = POST
:path = /demo.users.v1.UserService/GetUser
content-type = application/grpc
te = trailers
```

`:path` помогает runtime выбрать зарегистрированный handler.

## gRPC message framing

Базовый gRPC message prefix:

```text
1 byte  → compressed flag
4 bytes → message length, big-endian
N bytes → serialized Protobuf
```

То есть:

```text
[compression][length][protobuf bytes]
```

## Почему нельзя ориентироваться на TCP packets

Один большой Protobuf message может быть разбит на несколько TCP segments.

И наоборот, небольшие writes могут быть объединены транспортом.

```text
1 gRPC message ≠ 1 TCP packet
```

## Полный путь первого RPC

Клиент:

```python
call = stub.GetUser(request)
```

Если ready transport ещё нет:

```text
resolve target
↓
initiate connection
↓
TCP handshake
```

```text
CLIENT                  SERVER

SYN ──────────────────►
    ◄──────────────── SYN+ACK
ACK ──────────────────►
```

После этого connection `ESTABLISHED`.

## HTTP/2 initialization

Поверх TCP устанавливается HTTP/2 connection state: connection preface, SETTINGS и другие protocol frames.

После этого открывается RPC stream.

## Сервер

```text
HTTP/2 HEADERS
:path = /.../GetUser
↓
registration lookup
↓
HTTP/2 DATA
↓
gRPC envelope
↓
protobuf bytes
↓
GetUserRequest.FromString()
↓
Python handler
```

## Response

```text
GetUserResponse object
↓
SerializeToString()
↓
gRPC framing
↓
HTTP/2 DATA
↓
TCP
↓
client
↓
FromString()
↓
Python GetUserResponse
```

## `ss`

Listening socket:

```bash
ss -ltnp | grep 50051
```

Established:

```bash
ss -tnp | grep 50051
```

## `tcpdump`

```bash
sudo tcpdump -i lo -nn 'tcp port 50051'
```

Флаги:

```text
[S]   SYN
[S.]  SYN + ACK
[.]   ACK
[P.]  PSH + ACK
[F.]  FIN + ACK
[R]   RST
```

PSH не является границей gRPC message.

## Connection reuse

После завершения unary RPC TCP connection обычно остаётся пригодным для следующих RPC.

```text
RPC 1 complete
TCP remains
RPC 2 starts
```

Не нужно мыслить «каждый RPC → новый TCP handshake».
