## `asyncio.Queue`

`asyncio.Queue` — FIFO buffer + async waiting mechanism.

```text
producer                      queue                    consumer

put(A) ───────────────────►  [A]
put(B) ───────────────────►  [A, B]

                             get() ──────────────────► A
```

## Самое важное свойство

```python
item = await queue.get()
```

Если queue не пустая — вернуть первый элемент.

Если пустая — suspend current Task. Она автоматически станет ready, когда producer положит элемент.

## Почему это лучше polling

Плохо:

```python
while True:
    if queue:
        ...
```

Хорошо:

```python
event = await queue.get()
```

Task спит до появления данных.

## `put`

```python
await queue.put(event)
```

Для unbounded queue обычно завершается сразу.

Для:

```python
queue = asyncio.Queue(maxsize=1000)
```

если очередь заполнена, `put()` может ждать. Это backpressure.

## `put_nowait` / `get_nowait`

```python
queue.put_nowait(item)
queue.get_nowait()
```

При full queue — `asyncio.QueueFull`, при empty queue — `asyncio.QueueEmpty`.

## Subscribers

В `WatchUsers` каждому RPC создаётся отдельная queue:

```python
queue = asyncio.Queue()
self._subscribers.add(queue)
```

Почему не одна общая queue? Потому что `queue.get()` забирает item.

С одной queue:

```text
Event 1 → consumer A
Event 2 → consumer B
Event 3 → consumer C
```

Это worker queue.

Но `WatchUsers` нужен broadcast:

```text
Event 1 → A
        → B
        → C
```

Поэтому каждому subscriber нужна отдельная queue.

## Как определяется «чья queue»

Каждый вызов handler имеет свои locals:

```text
WatchUsers RPC A
    local queue → Queue A

WatchUsers RPC B
    local queue → Queue B
```

`yield` из coroutine A автоматически относится к gRPC stream A.

Runtime уже знает связь:

```text
handler invocation
↔ RPC call
↔ HTTP/2 stream
↔ client
```

## Cleanup subscriber

```python
finally:
    self._subscribers.discard(queue)
```

Иначе publisher продолжал бы складывать events в queue отключившегося клиента.

## Slow consumer

Отдельные queues позволяют каждому subscriber читать со своей скоростью, но медленный consumer может накопить огромный backlog.

Production варианты:

```text
bounded queue
drop policy
disconnect slow consumer
external broker
replay from durable log
```

## `asyncio.Lock`

```python
self._lock = asyncio.Lock()
```

Async mutex внутри event loop/process.

```python
async with self._lock:
    self._users[user.id] = user
```

Нужен, когда несколько Tasks работают с общим mutable in-memory state.

## Почему Lock не заменяет СУБД

```text
Process A → asyncio.Lock A
Process B → asyncio.Lock B
```

Locks друг о друге не знают.

Если оба пишут в общий PostgreSQL, consistency обеспечивается через transactions, MVCC, row/table locks, constraints и isolation.

## Isolation vs lock

Точнее говорить:

```text
СУБД управляет concurrent access через
transactions + MVCC + locks + constraints

isolation level задаёт допустимую видимость
и anomalies между transactions
```

## Clone protobuf object

```python
copy = User()
copy.CopyFrom(user)
```

полезен, если важно отделить ownership shared mutable object.

Но:

```python
GetUserResponse(user=user)
```

валидно и обычно не требует дополнительной копии само по себе.
