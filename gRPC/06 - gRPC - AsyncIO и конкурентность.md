## Что даёт `grpc.aio`

`grpc.aio` интегрирует gRPC с Python AsyncIO.

Application handlers работают в asyncio programming model:

```text
event loop
+
Tasks
+
coroutines
+
await
```

Не нужно представлять, что каждый RPC обязательно получает отдельный Python thread.

Внутри native gRPC runtime могут существовать внутренние threads, но user handlers в `grpc.aio` планируются через AsyncIO.

## Coroutine

```python
async def foo():
    ...
```

```python
coro = foo()
```

обычно создаёт coroutine object. Чтобы она исполнялась:

```python
await coro
```

или:

```python
task = asyncio.create_task(coro)
```

## `await`

```python
result = await operation()
```

означает: текущая coroutine не может продолжить, пока operation не завершится.

Если operation ожидает IO/timer, текущая Task suspended, а event loop выполняет другие ready Tasks.

Важно:

```text
await не останавливает весь процесс
await не обязательно блокирует OS thread
```

## Blocking vs non-blocking

Плохо:

```python
async def handler(...):
    time.sleep(10)
```

`time.sleep()` блокирует event loop thread.

Хорошо:

```python
async def handler(...):
    await asyncio.sleep(10)
```

Эта Task suspended, event loop свободен.

## CPU-heavy работа

```python
async def handler():
    huge_cpu_loop()
```

всё равно блокирует event loop на время CPU работы.

Для тяжёлого CPU нужны process pool, отдельный worker, native implementation или другой service.

## `asyncio.gather`

```python
await asyncio.gather(
    unary_forever(stub),
    watch_users_forever(stub),
    upload_batches_forever(stub),
    bidi_forever(stub),
)
```

Несколько awaitables выполняются конкурентно.

```text
Task A → unary
Task B → server stream
Task C → batch upload
Task D → bidi
```

## Пример переключений

```text
Task A
await RPC
↓ suspended

Task B
await queue.get()
↓ suspended

Task C
await sleep(0.6)
↓ suspended

Task D
await next event
↓ suspended

event loop ждёт network / timer / queue notification
```

## `asyncio.create_task`

```python
reader_task = asyncio.create_task(
    read_client_stream()
)

heartbeat_task = asyncio.create_task(
    produce_heartbeats()
)
```

Обе работают конкурентно.

Если написать:

```python
await read_client_stream()
await produce_heartbeats()
```

вторая запустится только после полного завершения первой.

## Почему это важно для bidi

Bidi часто требует одновременно:

```text
читать CLIENT → SERVER
и
производить SERVER → CLIENT
```

Например:

```text
Task 1: read_client_stream
Task 2: heartbeat producer
main handler: outgoing queue → yield
```

## Cleanup Tasks

```python
reader_task.cancel()
heartbeat_task.cancel()

await asyncio.gather(
    reader_task,
    heartbeat_task,
    return_exceptions=True,
)
```

Иначе можно получить dangling tasks при завершении event loop.

## Async iterator

```python
async for request in request_iterator:
    ...
```

Если следующий message ещё не пришёл по сети, текущая Task suspended.

## Главная мысль

AsyncIO даёт **конкурентность во время ожидания**, а не магический параллелизм CPU.
