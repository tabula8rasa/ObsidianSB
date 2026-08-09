## Что такое gRPC?

Framework для RPC между приложениями. Контракт обычно описывается Protobuf, вызовы идут поверх HTTP/2, поддерживаются unary и streaming RPC.

## Чем gRPC отличается от Protobuf?

```text
Protobuf
→ schema + serialization

gRPC
→ remote calls + streaming + statuses + transport semantics
```

Protobuf можно использовать без gRPC.

## Что генерирует `protoc`?

```text
*_pb2.py
→ Protobuf messages/descriptors

*_pb2_grpc.py
→ Stub, Servicer, registration helpers
```

## Что такое Stub?

Generated client-side proxy/API. Знает RPC path, serializer, deserializer и type RPC.

## Что такое Servicer?

Generated server-side interface/base class, который реализует разработчик.

## Что делает registration function?

Связывает RPC path с Python handler и задаёт serializers/deserializers/cardinality.

## Что такое Channel?

Клиентская gRPC transport abstraction. Управляет connectivity, HTTP/2 transport, reconnect и RPC multiplexing.

## Когда создаётся TCP connection?

Не обязательно при `insecure_channel()`. gRPC может использовать lazy connection. Connection обычно требуется при фактическом RPC.

## Что происходит при `stub.Method(request)` в `grpc.aio`?

Создаётся/инициируется gRPC Call.

```python
call = stub.Method(request)
```

RPC уже может выполняться.

```python
response = await call
```

ждёт его результат.

## Какие есть 4 вида RPC?

```text
unary-unary
stream-unary
unary-stream
stream-stream
```

## Почему client-streaming не подходит для бесконечного stream с одним response?

Потому что сервер должен увидеть конец request stream, чтобы перейти к итоговому unary response.

## Как сервер узнаёт, что client stream закончился?

Client request iterator завершается, gRPC закрывает send-side конкретного HTTP/2 stream с `END_STREAM`, server runtime получает EOF, и `async for request in request_iterator` заканчивается.

## Это TCP FIN?

Нет. HTTP/2 END_STREAM закрывает направление конкретного stream. TCP FIN закрывает направление всего TCP connection.

## Что такое HTTP/2 multiplexing?

Один TCP connection переносит frames множества streams.

```text
stream 1 → RPC A
stream 3 → RPC B
stream 5 → RPC C
```

## Один gRPC message равен одному TCP packet?

Нет. TCP — byte stream.

## Как gRPC определяет границы message?

5-byte prefix:

```text
1 byte compression flag
4 bytes message length
```

затем serialized message.

## Что делает `context.abort()`?

Немедленно завершает server RPC с заданным gRPC status/details. На клиенте обычно `AioRpcError`.

## Что такое deadline?

Максимальное время, которое caller готов ждать RPC.

```python
await stub.GetUser(req, timeout=3)
```

## Почему retries опасны?

Server мог применить mutation, а response мог потеряться. Caller не всегда знает результат. Нужны idempotency semantics.

## Как `grpc.aio` обслуживает несколько RPC?

Через asyncio event loop и Tasks. Handlers suspended на `await`, loop выполняет другие ready Tasks.

## Concurrency vs parallelism?

AsyncIO даёт конкурентное чередование Tasks, особенно эффективно для I/O. CPU-heavy code не становится параллельным только из-за `async def`.

## Зачем `asyncio.Queue`?

Чтобы producer и consumer могли работать независимо, а consumer мог `await queue.get()` без polling.

## Зачем отдельная Queue каждому subscriber?

Чтобы каждый subscriber получил каждое событие. Одна queue распределяла бы items между consumers.

## Зачем `asyncio.Lock`?

Защищать shared mutable in-memory state между concurrent Tasks одного process/event loop.

## Может ли asyncio.Lock защитить PostgreSQL от двух replicas?

Нет. У каждой replica свой lock object. Согласованность общего storage должна обеспечиваться БД/distributed synchronization.

## Что такое backpressure?

Ограничение producer, когда consumer не успевает. Например bounded `asyncio.Queue(maxsize=...)`.

## Что происходит при закрытии Channel?

gRPC завершает transport lifecycle; HTTP/2 connection shutdown и underlying TCP connection eventually закрывается. Именно здесь уже можно увидеть TCP FIN.
