## Типовая структура

```python
class UserService(
    users_pb2_grpc.UserServiceServicer
):
    async def GetUser(self, request, context):
        ...


async def serve():
    server = grpc.aio.server()

    users_pb2_grpc.add_UserServiceServicer_to_server(
        UserService(),
        server,
    )

    server.add_insecure_port("[::]:50051")

    await server.start()
    await server.wait_for_termination()
```

## `grpc.aio.server()`

Создаёт server runtime object. На этом этапе сервер ещё не обслуживает RPC.

```text
server object created
services: none
endpoint: none
started: no
```

## Создание Servicer

```python
service = UserService()
```

Это обычный Python object. В нём может храниться shared application state:

```text
self._users
self._cache
self._subscribers
self._locks
```

Если приложение запущено в нескольких replicas, in-memory state автоматически между ними не разделяется.

## Регистрация методов

```python
users_pb2_grpc.add_UserServiceServicer_to_server(
    service,
    server,
)
```

Generated registration function связывает network RPC path и Python method:

```text
/demo.users.v1.UserService/GetUser
       ↓
service.GetUser
```

Одновременно задаются request deserializer, response serializer и RPC cardinality. Это аналог routing table.

## Endpoint

```python
address = "[::]:50051"
server.add_insecure_port(address)
```

```
[ : : ] 
``` 
— это IPv6 wildcard address. `50051` — TCP port. `insecure` означает без TLS.

Точная последовательность системных вызовов скрыта внутри gRPC runtime, но на уровне ОС появляется listening socket, связанный с процессом.

```bash
ss -ltnp | grep 50051
```

## `await server.start()`

Переводит сервер в рабочее состояние.

```text
принимать TCP connections
↓
обрабатывать HTTP/2
↓
разбирать gRPC
↓
маршрутизировать RPC
↓
запускать handlers
```

## `await server.wait_for_termination()`

Не означает «сервер завис и ничего не делает».

```text
serve Task
    ↓
await wait_for_termination()
    ↓
SUSPENDED

event loop
    ├── GetUser Task
    ├── WatchUsers Task
    ├── UploadUsers Task
    └── SyncUsers Task
```

## Handler

```python
async def GetUser(
    self,
    request: users_pb2.GetUserRequest,
    context: grpc.aio.ServicerContext,
) -> users_pb2.GetUserResponse:
    ...
```

К моменту вызова handler `request` уже готовый Protobuf object.

```text
TCP bytes
↓
HTTP/2
↓
gRPC framing
↓
protobuf bytes
↓
GetUserRequest.FromString()
↓
request
```

## `context`

`context` — server-side объект конкретного RPC. Он даёт доступ к metadata, deadline, cancellation, peer, status/details и abort.

Это не Protobuf message и не объект, отправленный клиентом.

См. [[09 - gRPC - Context, ошибки, deadline и cancellation]].

## Возврат response

```python
return users_pb2.GetUserResponse(
    user=user
)
```

После `return` runtime сам выполняет:

```text
GetUserResponse
↓
SerializeToString()
↓
gRPC framing
↓
HTTP/2
↓
TCP
```

## Streaming handler

```python
async def WatchUsers(...):
    while True:
        event = await queue.get()
        yield event
```

`yield` означает «отдать очередное gRPC message, но RPC не завершать».

После завершения async generator response stream закрывается.

## Mental model

```text
Servicer
= application RPC handlers

generated registration
= RPC routing + serializers

grpc.aio.Server
= network/runtime/server lifecycle

event loop
= scheduling async handlers
```
