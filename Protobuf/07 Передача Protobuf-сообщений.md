---
tags:
  - protobuf
  - networking
  - grpc
  - kafka
  - http
---
## 1. Кто передаёт бинарник

Распределение обязанностей:

```text
прикладной код
    выбирает сообщение и получателя

Protobuf runtime
    превращает сообщение в bytes

транспортная библиотека
    передаёт bytes операционной системе

TCP/IP-стек
    доставляет данные по сети

транспорт получателя
    возвращает bytes приложению

Protobuf runtime получателя
    восстанавливает объект
```

Точная формулировка:

> Protobuf создаёт и читает бинарный payload. Передачей занимается транспорт.

## 2. Передача через файл

```python
from pathlib import Path

payload = user.SerializeToString()
Path("user.bin").write_bytes(payload)
```

Чтение:

```python
payload = Path("user.bin").read_bytes()
user = User.FromString(payload)
```

Файл играет роль простейшего транспорта.

## 3. Raw TCP

### Проблема TCP

TCP — поток байтов. Он не сохраняет границы вызовов `sendall()`.

Отправитель:

```python
sock.sendall(message1)
sock.sendall(message2)
```

Получатель может получить:

```text
часть message1
message1 + часть message2
оба сообщения вместе
```

Поэтому нужно framing.

### Length prefix

```text
4 байта длины + Protobuf payload
```

Отправка:

``` Python
import
```


``` py
import struct

payload = user.SerializeToString()
frame = struct.pack("!I", len(payload)) + payload
sock.sendall(frame)
```

```

Чтение:

```python
def recv_exact(sock, size: int) -> bytes:
    chunks = []
    received = 0

    while received < size:
        chunk = sock.recv(size - received)

        if not chunk:
            raise ConnectionError(
                "Соединение закрылось раньше времени"
            )

        chunks.append(chunk)
        received += len(chunk)

    return b"".join(chunks)
```

```python
length_bytes = recv_exact(sock, 4)
message_size = struct.unpack("!I", length_bytes)[0]
payload = recv_exact(sock, message_size)

user = User.FromString(payload)
```

Необходимо ограничивать максимальный размер:

```python
if message_size > 1_000_000:
    raise ValueError("Слишком большое сообщение")
```

## 4. HTTP

Клиент:

```python
import requests

payload = user.SerializeToString()

response = requests.post(
    "https://service.internal/users",
    data=payload,
    headers={
        "Content-Type": "application/protobuf",
    },
    timeout=10,
)
response.raise_for_status()
```

Сервер получает готовое тело запроса как `bytes`.

HTTP уже содержит:

- URL;
- метод;
- заголовки;
- Content-Length или chunked framing;
- код ответа.

Тип сообщения может определяться маршрутом:

```text
POST /users/create → CreateUserRequest
POST /users/get    → GetUserRequest
```

## 5. Kafka

Producer:

```python
event = UserCreatedEvent(
    user_id=100,
    name="Alex",
)

producer.send(
    "users.created.v1",
    value=event.SerializeToString(),
)
```

Consumer:

```python
for record in consumer:
    event = UserCreatedEvent.FromString(
        record.value
    )
```

Границы события уже задаются Kafka record.

Тип определяется:

- названием topic;
- отдельным header;
- envelope;
- Schema Registry;
- соглашением producer/consumer.

## 6. RabbitMQ и другие брокеры

Protobuf payload помещается в тело сообщения.

Дополнительно задаются metadata:

```text
content_type = application/protobuf
message_type = company.users.v1.UserCreatedEvent
schema_version = ...
```

## 7. gRPC

В `.proto` описываются сообщения и сервис:

```proto
service UserService {
  rpc GetUser(GetUserRequest)
      returns (GetUserResponse);
}
```

Клиент:

```python
request = GetUserRequest(user_id=100)
response = stub.GetUser(request)
```

Прикладной код не вызывает `SerializeToString()` вручную.

Внутри:

```text
GetUserRequest
    ↓ сериализация
Protobuf bytes
    ↓ gRPC framing
HTTP/2
    ↓
gRPC server
    ↓ десериализация
GetUserRequest
```

gRPC отвечает за:

- соединение;
- HTTP/2;
- границы сообщений;
- клиентские stubs;
- серверный интерфейс;
- статусы ошибок;
- metadata;
- deadlines;
- unary и streaming RPC.

## 8. Protobuf и gRPC — разные технологии

| Protobuf | gRPC |
|---|---|
| Описывает сообщения | Описывает удалённые вызовы |
| Сериализует в bytes | Передаёт запросы и ответы |
| Не знает адрес | Работает через channel |
| Не задаёт статус RPC | Имеет status codes |
| Может работать без сети | Предназначен для RPC |

## 9. Несколько типов сообщений

Protobuf payload обычно не хранит название типа. Варианты определения типа:

### По endpoint

```text
/users/create → CreateUserRequest
/users/get → GetUserRequest
```

### По Kafka topic

```text
users.created.v1 → UserCreatedEvent
users.deleted.v1 → UserDeletedEvent
```

### По gRPC-методу

```text
GetUser → GetUserRequest / GetUserResponse
```

### Через envelope

```proto
message Envelope {
  string type = 1;
  bytes payload = 2;
}
```

Недостаток: `bytes` теряет статическую связь со вложенным типом.

### Через `Any`

```proto
import "google/protobuf/any.proto";

message Envelope {
  google.protobuf.Any payload = 1;
}
```

Python:

```python
from google.protobuf.any_pb2 import Any

envelope.payload.Pack(user)
```

Распаковка:

```python
if envelope.payload.Is(User.DESCRIPTOR):
    user = User()
    envelope.payload.Unpack(user)
```

`Any` хранит type URL и сериализованный payload.

### Через `oneof`

Когда набор типов заранее ограничен:

```proto
message Event {
  oneof payload {
    UserCreated user_created = 1;
    UserDeleted user_deleted = 2;
  }
}
```

Это наиболее типобезопасный вариант для закрытого набора событий.

## 10. Безопасность

Protobuf не шифрует данные.

Для сети используйте:

- TLS / HTTPS;
- mTLS между сервисами;
- аутентификацию;
- авторизацию;
- ограничения размера;
- timeouts;
- rate limiting;
- проверку входных данных.

## 11. Ошибки транспорта и Protobuf

Разделяйте:

```text
ошибка сети
ошибка framing
ошибка десериализации
ошибка бизнес-валидации
```

Пример:

```python
from google.protobuf.message import DecodeError

try:
    user = User.FromString(payload)
except DecodeError as exc:
    raise ValueError(
        "Некорректный Protobuf payload"
    ) from exc
```
