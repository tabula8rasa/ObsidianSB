## Что демонстрирует проект

Учебный `UserService` объединяет все четыре типа RPC:

```proto
service UserService {
  rpc GetUser(GetUserRequest)
      returns (GetUserResponse);

  rpc WatchUsers(WatchUsersRequest)
      returns (stream UserEvent);

  rpc UploadUsers(stream User)
      returns (UploadUsersResponse);

  rpc SyncUsers(stream UserCommand)
      returns (stream UserEvent);
}
```

## Shared state

Сервис хранит:

```text
_users
→ in-memory database

_lock
→ async mutex around shared state

_subscribers
→ queues active WatchUsers subscribers

_sequence
→ event sequence numbers
```

## `GetUser`

Unary.

```text
GetUserRequest(user_id)
        ↓
lookup _users
        │
        ├── missing → context.abort(NOT_FOUND)
        │
        └── exists → GetUserResponse(user)
```

## `WatchUsers`

Server streaming.

Для каждого вызова создаётся:

```python
queue = asyncio.Queue()
self._subscribers.add(queue)
```

Если `include_existing = true`, сначала отправляется snapshot текущих users.

Затем:

```python
while True:
    event = await queue.get()
    yield event
```

RPC спит до появления event.

## `_publish`

Broadcast:

```python
for queue in self._subscribers:
    await queue.put(event)
```

Один event попадает всем active watchers.

## `UploadUsers`

Client streaming.

```text
User 100
User 101
User 102
↓
server stores each
↓
publishes CREATED_OR_UPDATED events
↓
request stream ends
↓
UploadUsersResponse(
    accepted=3,
    ids=[100,101,102]
)
```

Каждый batch конечен. Клиент может повторять batches forever, но каждый отдельный RPC должен завершиться.

## `SyncUsers`

Bidirectional streaming.

Имеет локальную `outgoing Queue` и две internal Tasks:

```text
reader_task
→ reads UserCommand from client

heartbeat_task
→ periodically creates HEARTBEAT events
```

Обе складывают events в outgoing Queue.

Основной handler:

```python
event = await outgoing.get()
yield event
```

отправляет их клиенту.

## Почему reader и heartbeat отдельными Tasks

Если написать:

```python
await read_client_stream()
await produce_heartbeats()
```

heartbeats начнутся только после полного завершения client request stream.

Поэтому используются `asyncio.create_task(...)`.

## Связь RPC между собой

`UploadUsers`:

```text
stores User
↓
creates UserEvent
↓
_publish
↓
WatchUsers sees event
```

`SyncUsers`:

```text
receives UserCommand
↓
stores User
↓
creates event
├── outgoing → same bidi client
└── _publish → all WatchUsers clients
```

## Клиент advanced-проекта

Один Channel, один `UserServiceStub` и четыре independent application Tasks:

```text
unary_forever
watch_users_forever
upload_batches_forever
bidi_forever
```

Запуск:

```python
await asyncio.gather(
    unary_forever(stub),
    watch_users_forever(stub),
    upload_batches_forever(stub),
    bidi_forever(stub),
)
```

## `unary_forever`

```text
GetUser(1)
↓
response
↓
sleep
↓
new GetUser RPC
```

Это polling, не один permanent RPC.

## `watch_users_forever`

Открывает long-lived server stream и читает `async for event in call`.

## `one_upload_batch`

Async generator из трёх users:

```text
User N
User N+1
User N+2
END
```

Именно завершение generator завершает request side `UploadUsers`.

## `upload_batches_forever`

```text
batch 100-102
↓
response
↓
sleep
↓
batch 103-105
↓
response
...
```

## `bidi_commands`

Бесконечный async generator:

```text
UserCommand 1000
UserCommand 1001
UserCommand 1002
...
```

Пока клиент работает, request stream не заканчивается.

## `bidi_forever`

```text
bidi_commands() → SERVER

SERVER events → async for event in call
```

При gRPC error outer loop может открыть новый bidi RPC.

## Итоговая схема

```text
                         CLIENT
                           │
                      one Channel
                           │
                       one Stub
                           │
      ┌────────────────────┼───────────────────┐
      │                    │                   │
  GetUser loop         WatchUsers         UploadUsers
      │                    │                   │
      │                    └──────┐            │
      │                           │            │
      └─────────────── SyncUsers ─┘            │
                           │                    │
========================= gRPC =========================
                           │
                        SERVER
                           │
                   shared UserService
                           │
             ┌─────────────┼─────────────┐
             │             │             │
           _users     _subscribers    outgoing
             │             │             │
             └──── events ─┴─────────────┘
```

## Что вынести из проекта

1. Streaming — это разные patterns сообщений внутри RPC/HTTP2 streams, а не новые TCP connections на каждое сообщение.
2. AsyncIO позволяет одновременно держать long-lived RPC и выполнять unary calls.
3. `asyncio.Queue` удобно отделяет producers событий от consumers.
4. Long-lived bidi требует аккуратного lifecycle, cancellation и reconnect.
5. In-memory state подходит для учебного примера, но production replicas требуют внешнего shared storage/broker.
