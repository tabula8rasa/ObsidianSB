## `ServicerContext`

```python
async def GetUser(
    self,
    request,
    context: grpc.aio.ServicerContext,
):
    ...
```

`context` существует отдельно для каждого RPC и связан с lifecycle данного вызова.

## `context.abort()`

```python
await context.abort(
    grpc.StatusCode.NOT_FOUND,
    f"user {request.user_id} not found",
)
```

Означает: немедленно завершить текущий RPC с указанным gRPC status и details.

Это terminating operation. Нормальное выполнение handler после успешного `abort()` не продолжается.

Не нужно:

```python
await context.abort(...)
return
```

## Что получает клиент

```python
try:
    response = await stub.GetUser(request)

except grpc.aio.AioRpcError as error:
    print(error.code())
    print(error.details())
```

Например:

```text
StatusCode.NOT_FOUND
user 999 not found
```

## Частые gRPC statuses

```text
OK
CANCELLED
UNKNOWN
INVALID_ARGUMENT
DEADLINE_EXCEEDED
NOT_FOUND
ALREADY_EXISTS
PERMISSION_DENIED
UNAUTHENTICATED
RESOURCE_EXHAUSTED
FAILED_PRECONDITION
ABORTED
OUT_OF_RANGE
UNIMPLEMENTED
INTERNAL
UNAVAILABLE
DATA_LOSS
```

## Полезные значения

```text
NOT_FOUND
→ ресурс не найден

INVALID_ARGUMENT
→ request некорректен

UNAUTHENTICATED
→ нет валидной аутентификации

PERMISSION_DENIED
→ identity есть, но нет прав

UNAVAILABLE
→ service временно недоступен

DEADLINE_EXCEEDED
→ response не получен до deadline

INTERNAL
→ внутренняя ошибка сервера
```

## Deadline

```python
response = await stub.GetUser(
    request,
    timeout=3,
)
```

Caller готов ждать ограниченное время. При превышении:

```text
DEADLINE_EXCEEDED
```

## Почему deadline важен

Без deadline distributed chain может ждать слишком долго:

```text
A waits B
B waits C
C waits D
```

## Cancellation

RPC может быть отменён из-за client cancellation, channel close, deadline, network failure или application logic.

Особенно важно для long-lived streams.

## Metadata

Metadata — дополнительные key-value данные call.

Use cases:

```text
authorization
trace id
request id
tenant
locale
```

Это не часть Protobuf business payload.

## Retry и неоднозначный результат

Сеть может оборваться после того, как сервер уже применил mutation, но клиент не получил response:

```text
server committed
↓
response lost
↓
client does not know result
```

Поэтому mutation retries требуют idempotency design.

gRPC сам по себе не даёт ACID-атомарность распределённой операции.
