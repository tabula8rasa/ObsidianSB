## Базовый клиент

```python
async with grpc.aio.insecure_channel(
    "localhost:50051"
) as channel:
    stub = users_pb2_grpc.UserServiceStub(channel)

    response = await stub.GetUser(
        users_pb2.GetUserRequest(user_id=1)
    )
```

## Channel

```python
channel = grpc.aio.insecure_channel(
    "localhost:50051"
)
```

`Channel` — не просто TCP socket. Это gRPC transport abstraction, которая знает target и управляет connectivity, transport connections, reconnect, HTTP/2, RPC multiplexing и lifetime.

Нельзя утверждать:

```text
1 Channel = всегда ровно 1 TCP connection
```

Но типичный ready transport может использовать один HTTP/2/TCP connection для множества RPC.

## Lazy connection

Создание channel не нужно воспринимать как гарантированный немедленный `connect()`.

gRPC использует lazy connectivity. Соединение обычно требуется при фактическом RPC.

## `async with`

```python
async with grpc.aio.insecure_channel(...) as channel:
    ...
```

Главная роль — lifetime management. При выходе из блока channel закрывается.

`async with` не означает «TCP handshake обязательно происходит на `__aenter__`».

## Stub

```python
stub = users_pb2_grpc.UserServiceStub(channel)
```

Stub — generated client API. Он знает method path, RPC type, request serializer, response deserializer и channel.

## Когда начинается RPC

Очень важный момент `grpc.aio`:

```python
call = stub.GetUser(request)
```

возвращает специальный gRPC Call object и инициирует RPC.

Затем:

```python
response = await call
```

означает «дождаться результата уже существующего RPC».

## Эксперимент

```python
call = stub.GetUser(request)

print("RPC initiated")

await asyncio.sleep(10)

print("Now await")

response = await call
```

Сервер может получить request, выполнить handler и отправить response ещё во время `sleep(10)`.

## Отличие от обычной coroutine

Обычная:

```python
coro = foo()
```

обычно не запускает `foo` сама по себе. Нужно `await coro` или `asyncio.create_task(coro)`.

А:

```python
call = stub.GetUser(request)
```

возвращает gRPC Call object, который одновременно представляет инициированный RPC и является awaitable.

## Несколько RPC через один Channel

```python
call1 = stub.GetUser(req1)
call2 = stub.GetUser(req2)
call3 = stub.GetUser(req3)

r1 = await call1
r2 = await call2
r3 = await call3
```

RPC могут существовать конкурентно.

```text
one HTTP/2 connection

stream 1 → RPC 1
stream 3 → RPC 2
stream 5 → RPC 3
```

TCP не знает, что это разные RPC. Разделение выполняет HTTP/2 по `stream_id`.

## Stub не проверяет сервер при создании

```python
stub = UserServiceStub(channel)
```

не обязан обращаться к серверу. Generated code просто создаёт client-side callables.

Ошибка проявится при фактическом RPC/connectivity.

## Ошибки

```python
try:
    response = await stub.GetUser(
        request,
        timeout=3,
    )
except grpc.aio.AioRpcError as error:
    print(error.code())
    print(error.details())
```
