## 1. Unary → Unary

```proto
rpc GetUser(GetUserRequest)
    returns (GetUserResponse);
```

Клиент:

```python
response = await stub.GetUser(request)
```

Сервер:

```python
async def GetUser(self, request, context):
    return response
```

```text
CLIENT                       SERVER

request ───────────────────►
        ◄────────────────── response
```

Использовать для обычных request-response операций.

## 2. Client streaming

```proto
rpc UploadUsers(stream User)
    returns (UploadUsersResponse);
```

Клиент:

```python
async def users():
    yield User(id=1)
    yield User(id=2)
    yield User(id=3)

response = await stub.UploadUsers(users())
```

Сервер:

```python
async def UploadUsers(
    self,
    request_iterator,
    context,
):
    async for user in request_iterator:
        ...

    return UploadUsersResponse(...)
```

```text
CLIENT                       SERVER

User 1 ────────────────────►
User 2 ────────────────────►
User 3 ────────────────────►
END REQUEST STREAM ────────►

       ◄─────────────────── summary response
```

### Почему request stream должен закончиться

`stream → unary` предполагает, что request stream когда-нибудь закончится. Иначе сервер не сможет перейти к итоговому единственному response.

Для постоянной загрузки можно делать конечные batches или использовать bidi.

## 3. Server streaming

```proto
rpc WatchUsers(WatchUsersRequest)
    returns (stream UserEvent);
```

Клиент:

```python
call = stub.WatchUsers(request)

async for event in call:
    print(event)
```

Сервер:

```python
async def WatchUsers(...):
    while True:
        event = await queue.get()
        yield event
```

```text
CLIENT                       SERVER

request ───────────────────►

       ◄─────────────────── event 1
       ◄─────────────────── event 2
       ◄─────────────────── event 3
       ◄─────────────────── ...
```

Use cases: subscriptions, watch APIs, server push.

## 4. Bidirectional streaming

```proto
rpc SyncUsers(stream UserCommand)
    returns (stream UserEvent);
```

Клиент:

```python
call = stub.SyncUsers(commands())

async for event in call:
    ...
```

```text
CLIENT                       SERVER

command 1 ─────────────────►
command 2 ─────────────────►

        ◄────────────────── event A
        ◄────────────────── heartbeat

command 3 ─────────────────►

        ◄────────────────── event B
```

Главное свойство: два направления логически независимы. Не требуется `1 request → 1 response`.

## Async generator

```python
async def messages():
    await asyncio.sleep(1)
    yield Message(...)
```

`async def` + `yield` создаёт async generator.

```python
generator = messages()
```

возвращает async iterator.

Чтение:

```python
async for message in generator:
    ...
```

концептуально многократно делает `await generator.__anext__()`.

## `yield` на сервере

```python
yield UserEvent(...)
```

не означает TCP packet.

```text
1 gRPC message ≠ 1 TCP packet
```

Application message boundaries задаются gRPC framing, а не TCP packet boundaries.

## Один RPC ≠ одно TCP connection

Server streaming из 1000 responses:

```text
1 RPC
1 HTTP/2 stream
1000 gRPC messages
```

## Быстрая таблица

| Тип | Client API | Server API | Типичный use case |
|---|---|---|---|
| unary-unary | `await stub.X(req)` | `return response` | CRUD / lookup |
| stream-unary | `await stub.X(async_iter)` | `async for request` + `return` | batch upload |
| unary-stream | `call=stub.X(req)` + `async for` | `yield` | subscription |
| stream-stream | `call=stub.X(async_iter)` + `async for` | `async for` + `yield` | realtime sync |
