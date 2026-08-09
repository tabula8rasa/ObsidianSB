## Три разных «конца»

```text
конец одного Protobuf message
≠
конец gRPC request/response stream
≠
конец TCP connection
```

## Client-streaming example

```proto
rpc UploadUsers(stream User)
    returns (UploadUsersResponse);
```

# gRPC — завершение stream, END_STREAM, FIN и RST
```python
async def one_batch():
    yield User(id=1)
    yield User(id=2)
    yield User(id=3)
```

После третьего `yield` generator заканчивается.

gRPC client runtime понимает: больше request messages не будет, и завершает send-side данного RPC.

## HTTP/2 END_STREAM

```text
CLIENT                        SERVER

User 1 ─────────────────────►
User 2 ─────────────────────►
User 3 ─────────────────────►
END_STREAM ─────────────────►
```

Серверный runtime получает EOF конкретного HTTP/2 request stream.

Из-за этого:

```python
async for user in request_iterator:
    ...
```

заканчивается.

После этого сервер может вернуть `UploadUsersResponse`.

## Half-close

После клиентского END_STREAM:

```text
CLIENT → SERVER    closed
CLIENT ← SERVER    still open
```

Это half-close HTTP/2 stream, а не TCP connection.

После завершения server-side направления:

```text
CLIENT → SERVER    closed
CLIENT ← SERVER    closed
```

RPC stream полностью завершён.

## TCP connection остаётся

```text
TCP connection
├── UploadUsers stream   DONE
├── WatchUsers stream    OPEN
├── SyncUsers stream     OPEN
└── можно открыть новый RPC
```

## TCP FIN

TCP FIN означает: эта сторона больше не будет отправлять байты в данном TCP connection direction.

```text
CLIENT                  SERVER

FIN ──────────────────►
    ◄──────────────── ACK
    ◄──────────────── FIN
ACK ──────────────────►
```

FIN относится ко всему TCP connection direction, а не к одному HTTP/2 stream.

## FIN consume sequence number

В TCP SYN и FIN занимают один sequence number.

## RST

```text
FIN → graceful shutdown
RST → abrupt termination
```

## HTTP/2 GOAWAY

При shutdown HTTP/2 connection может использовать GOAWAY, чтобы сообщить, что новые streams больше не следует открывать.

## TIME_WAIT

После TCP close одна сторона может остаться в `TIME_WAIT`.

```bash
ss -tan | grep 50051
```

Это нормальная часть TCP state machine.

## Практическое правило

Если закончился gRPC RPC — не жди TCP FIN.

Если закрылся Channel/transport connection — тогда уже может появиться TCP FIN.
