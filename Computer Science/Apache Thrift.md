---
tags:
  - thrift
  - rpc
  - serialization
  - idl
  - distributed-systems
aliases:
  - Apache Thrift
---
## Кратко

**Apache Thrift** — это кросс-языковый фреймворк для описания структур данных и RPC-интерфейсов.

Главная идея:

```text
один контракт .thrift
        ↓
Thrift Compiler
        ↓
сгенерированный код для разных языков
        ↓
клиент и сервер используют одинаковые типы и RPC-методы
        ↓
Thrift runtime сериализует данные и передаёт их по сети
```

По смыслу Thrift объединяет несколько задач:

1. **IDL** — язык описания интерфейсов и типов.
2. **Code generation** — генерация классов, клиентов и серверной обвязки.
3. **Serialization** — преобразование объектов в wire format.
4. **Transport abstraction** — способ доставки байтов.
5. **RPC** — вызов методов удалённого сервиса.

Поэтому Thrift ближе всего не просто к [[Protocol Buffers]], а к связке:

```text
Protocol Buffers + gRPC
```

Потому что Protobuf сам по себе в первую очередь решает задачу описания сообщений и сериализации, а gRPC добавляет RPC. В Thrift обе задачи находятся в одном фреймворке.

---

# 1. Зачем нужен Thrift

Представим два сервиса:

```text
Python service
      ↓
     сеть
      ↓
Java service
```

Python-приложение хочет вызвать:

```python
user = client.get_user(123)
```

Java-сервис должен понимать:

- что такое `get_user`;
- какие параметры у метода;
- что означает `123`;
- какой объект надо вернуть;
- как этот объект сериализован;
- как передать ошибку;
- как отделять запросы и ответы;
- каким бинарным форматом пользоваться.

Без IDL/RPC-фреймворка всё это пришлось бы согласовывать самостоятельно.

Thrift позволяет описать контракт:

```thrift
struct User {
    1: i64 id,
    2: string name,
    3: optional string email
}

service UserService {
    User getUser(1: i64 id)
}
```

После этого один и тот же файл может быть использован для генерации кода для Python, Java, Go, C++ и других языков.

---

# 2. Главная архитектура Thrift

Упрощённый стек:

```text
Application
     ↓
Generated Client / Handler
     ↓
Generated Processor
     ↓
Protocol
     ↓
Transport
     ↓
TCP / HTTP / file / memory / ...
```

На клиенте:

```text
Python code
    ↓
UserService.Client
    ↓
TBinaryProtocol
    ↓
TBufferedTransport
    ↓
TSocket
    ↓
TCP
```

На сервере:

```text
TCP
 ↓
TServerSocket
 ↓
Transport
 ↓
Protocol
 ↓
UserService.Processor
 ↓
Handler
 ↓
наш Python-код
```

Основные компоненты:

```text
IDL
Compiler
Generated Types
Generated Client
Generated Processor
Protocol
Transport
Server
Handler
```

Разберём каждый отдельно.

---

# 3. IDL — Interface Definition Language

Thrift использует собственный язык описания интерфейсов.

Файлы обычно имеют расширение:

```text
.thrift
```

Пример:

```thrift
namespace py users
namespace java com.example.users

enum UserStatus {
    ACTIVE = 1,
    BLOCKED = 2
}

struct User {
    1: required i64 id,
    2: required string name,
    3: optional string email,
    4: optional UserStatus status
}

exception UserNotFound {
    1: i64 id,
    2: string message
}

service UserService {

    User getUser(
        1: i64 id
    ) throws (
        1: UserNotFound notFound
    )

    void deleteUser(
        1: i64 id
    )
}
```

Этот файл является контрактом между клиентом и сервером.

---

# 4. Типы данных Thrift

## Базовые типы

Основные базовые типы:

```text
bool
byte / i8
i16
i32
i64
double
string
binary
uuid
```

Пример:

```thrift
struct Example {
    1: bool enabled,
    2: i32 count,
    3: i64 userId,
    4: double price,
    5: string name,
    6: binary payload
}
```

### string

`string` предназначен для текстовых строк.

```thrift
1: string username
```

### binary

`binary` — произвольная последовательность байтов.

```thrift
2: binary image
```

Например туда можно положить:

```text
PDF
JPEG
protobuf payload
compressed bytes
```

---

# 5. Контейнерные типы

Thrift поддерживает:

```text
list<T>
set<T>
map<K, V>
```

Пример:

```thrift
struct User {
    1: i64 id,
    2: list<string> roles,
    3: set<string> permissions,
    4: map<string, string> metadata
}
```

В Python это обычно концептуально превращается в:

```python
roles: list[str]
permissions: set[str]
metadata: dict[str, str]
```

Конкретное представление зависит от language binding.

---

# 6. struct

Основной составной тип Thrift — `struct`.

```thrift
struct User {
    1: i64 id,
    2: string name
}
```

Он похож на:

```python
@dataclass
class User:
    id: int
    name: str
```

Но важное отличие:

```text
Thrift struct
```

— это часть межъязыкового контракта.

Python и Java получат разные нативные классы, но оба будут описывать одну и ту же wire-структуру.

---

# 7. Field ID

Очень важная часть Thrift:

```thrift
1: i64 id
2: string name
3: string email
```

Числа:

```text
1
2
3
```

— **field IDs**.

По смыслу они очень похожи на номера полей в Protobuf:

```protobuf
message User {
    int64 id = 1;
    string name = 2;
}
```

Field ID позволяет wire protocol определять, какое поле передаётся.

Главное правило для production-контрактов:

```text
ID существующего поля нельзя бездумно менять или переиспользовать.
```

Например было:

```thrift
1: i64 id
2: string name
```

Плохое изменение:

```thrift
1: string email
2: string name
```

Старые клиенты будут интерпретировать поле `1` как `id`, а новые — как `email`.

Практически field ID надо воспринимать как долговременную часть контракта.

---

# 8. required / optional / default requiredness

Thrift поддерживает:

```thrift
required
optional
```

и поле без явного модификатора.

Пример:

```thrift
struct User {
    1: required i64 id,
    2: string name,
    3: optional string email
}
```

## required

```thrift
1: required i64 id
```

Поле ожидается всегда.

Проблема:

```text
required сильно усложняет schema evolution.
```

Если старые клиенты ожидают поле обязательным, его сложно безопасно удалить.

Поэтому для долговременно развивающихся API `required` следует использовать осторожно.

## optional

```thrift
3: optional string email
```

Поле может отсутствовать.

Это намного удобнее для эволюции схем.

## default requiredness

Если написать:

```thrift
2: string name
```

без `required` и `optional`, применяется отдельная семантика default requiredness.

Она исторически находится между required и optional и может иметь нюансы между language bindings.

Для публичных и долго живущих контрактов лучше сознательно понимать requiredness каждого поля, а не полагаться на случайные предположения.

---

# 9. enum

```thrift
enum UserStatus {
    ACTIVE = 1,
    BLOCKED = 2,
    DELETED = 3
}
```

Использование:

```thrift
struct User {
    1: UserStatus status
}
```

После code generation язык получает подходящее представление enum.

---

# 10. union

`union` означает:

> в каждый момент установлено только одно из нескольких возможных полей.

Пример:

```thrift
union Contact {
    1: string email,
    2: string phone,
    3: string telegram
}
```

Можно передать:

```text
email
```

или:

```text
phone
```

но не все одновременно.

По смыслу близко к Protobuf:

```protobuf
oneof contact {
    string email = 1;
    string phone = 2;
}
```

---

# 11. exception

Thrift умеет описывать RPC-ошибки как часть IDL:

```thrift
exception UserNotFound {
    1: i64 id,
    2: string message
}
```

Метод:

```thrift
User getUser(1: i64 id)
    throws (1: UserNotFound notFound)
```

На стороне сервера handler может выбросить сгенерированное исключение.

На стороне клиента оно будет восстановлено в соответствующий тип исключения языка клиента.

Это важное преимущество RPC IDL:

```text
ошибки являются частью контракта,
а не случайной строкой.
```

---

# 12. service

Главная RPC-конструкция:

```thrift
service UserService {

    User getUser(1: i64 id)

    void deleteUser(1: i64 id)
}
```

Она говорит:

```text
существует удалённый сервис UserService

у него есть методы:

getUser
deleteUser
```

После code generation создаются клиентские и серверные компоненты.

---

# 13. service inheritance

Thrift позволяет расширять service:

```thrift
service BaseService {
    void ping()
}

service UserService extends BaseService {
    User getUser(1: i64 id)
}
```

`UserService` получает также методы `BaseService`.

---

# 14. oneway

Thrift может описывать fire-and-forget вызов:

```thrift
service EventService {

    oneway void sendEvent(
        1: string payload
    )
}
```

Идея:

```text
client
  ↓
отправил запрос
  ↓
не ждёт response
```

Это не значит, что доставка автоматически становится гарантированной. `oneway` всего лишь меняет RPC-семантику ожидания ответа.

---

# 15. Include и namespaces

Большие контракты можно разделять:

```thrift
include "common.thrift"
```

Использование:

```thrift
struct UserResponse {
    1: common.Metadata metadata
}
```

Для разных языков можно задавать namespaces:

```thrift
namespace py company.users
namespace java com.company.users
namespace go users
```

Это определяет, куда попадут generated types.

---

# 16. Thrift Compiler

После создания:

```text
users.thrift
```

выполняется:

```bash
thrift --gen py users.thrift
```

Для рекурсивной генерации include-файлов:

```bash
thrift -r --gen py users.thrift
```

Для Java:

```bash
thrift --gen java users.thrift
```

Для Go:

```bash
thrift --gen go users.thrift
```

Таким образом:

```text
users.thrift
    │
    ├── thrift --gen py
    │       ↓
    │   Python SDK
    │
    ├── thrift --gen java
    │       ↓
    │   Java SDK
    │
    └── thrift --gen go
            ↓
        Go SDK
```

---

# 17. Что генерируется для Python

Для контракта с namespace:

```thrift
namespace py users
```

можно получить структуру примерно такого вида:

```text
gen-py/
└── users/
    ├── __init__.py
    ├── ttypes.py
    ├── constants.py
    └── UserService.py
```

## ttypes.py

Содержит generated classes для:

```text
struct
enum
union
exception
```

Например:

```thrift
struct User {
    1: i64 id,
    2: string name
}
```

превращается в Python-класс `User`.

---

# 18. Что находится в generated service

Для:

```thrift
service UserService {
    User getUser(1: i64 id)
}
```

генератор создаёт RPC-обвязку.

Концептуально там есть:

```text
Iface
Client
Processor
args structures
result structures
```

## Client

Используется клиентским приложением:

```python
client.getUser(123)
```

На самом деле generated Client:

1. создаёт RPC request;
2. сериализует аргументы;
3. пишет запрос через Protocol;
4. отправляет через Transport;
5. получает response;
6. десериализует результат;
7. возвращает Python-объект.

## Processor

Processor используется сервером.

Он:

```text
читает имя RPC-метода
        ↓
десериализует arguments
        ↓
вызывает Handler
        ↓
получает result
        ↓
сериализует response
```

---

# 19. Handler

Generated код не знает бизнес-логику.

Мы должны написать её сами.

Например:

```python
class UserServiceHandler:

    def getUser(self, user_id):
        return User(
            id=user_id,
            name="Ilya"
        )
```

То есть:

```text
Generated Processor
        ↓
наш Handler
        ↓
business logic
```

---

# 20. Protocol

**Protocol** отвечает за то, **как структуры Thrift превращаются в bytes**.

Важно не путать:

```text
Protocol ≠ TCP
```

В терминологии Thrift:

```text
Protocol = serialization format
```

Например:

```text
TBinaryProtocol
TCompactProtocol
TJSONProtocol
```

---

# 21. TBinaryProtocol

Один из основных бинарных протоколов.

Упрощённо информация передаётся как:

```text
field type
field id
field value
```

То есть receiver способен понять:

```text
какое поле
какого типа
какое значение
```

Это похоже на идею Protobuf wire format, хотя конкретное бинарное кодирование отличается.

---

# 22. TCompactProtocol

`TCompactProtocol` предназначен для более компактного бинарного представления.

Общая идея:

```text
TBinaryProtocol
    ↓
простое бинарное кодирование

TCompactProtocol
    ↓
более агрессивное уменьшение размера
```

Это может уменьшить network/storage overhead ценой дополнительной логики кодирования.

---

# 23. TJSONProtocol

Thrift также имеет JSON protocol.

Это не превращает Thrift автоматически в REST API.

Схема всё равно остаётся:

```text
Thrift Client
   ↓
Thrift RPC
   ↓
JSON wire representation
   ↓
Thrift Server
```

То есть:

```text
JSON — формат сериализации,
а не архитектурный стиль API.
```

---

# 24. Transport

**Transport** отвечает уже не за формат структуры, а за поток байтов.

Главная идея:

```text
Protocol:
    как объект → bytes

Transport:
    куда эти bytes читать/писать
```

Это принципиальное разделение архитектуры Thrift.

---

# 25. TSocket

Обычный socket transport.

```python
transport = TSocket.TSocket(
    "localhost",
    9090
)
```

Упрощённо:

```text
Thrift
 ↓
TCP socket
 ↓
Linux kernel
 ↓
network
```

---

# 26. TBufferedTransport

Можно обернуть socket:

```python
transport = TTransport.TBufferedTransport(
    socket
)
```

Получается:

```text
TBinaryProtocol
       ↓
TBufferedTransport
       ↓
TSocket
       ↓
TCP
```

Буферизация уменьшает количество мелких операций чтения/записи.

В официальном Python tutorial прямо подчёркивается, что использование buffering важно для производительности raw socket transport.

---

# 27. TFramedTransport

Framed transport формирует отдельные frames.

Концептуально:

```text
[length][payload]
[length][payload]
[length][payload]
```

Это особенно полезно для некоторых неблокирующих/event-driven серверных реализаций.

Важно:

```text
Framed Transport
```

не является тем же самым, что:

```text
TCompactProtocol
```

Первое — framing транспорта.

Второе — формат сериализации данных.

---

# 28. Protocol и Transport можно комбинировать

Это одна из сильных архитектурных идей Thrift.

Например:

```text
TBinaryProtocol
       +
TBufferedTransport
       +
TSocket
```

или:

```text
TCompactProtocol
       +
TFramedTransport
       +
TSocket
```

То есть serialization format и transport decoupled.

---

# 29. Почему client и server должны согласовать Protocol/Transport

Если client использует:

```text
TCompactProtocol
```

а server пытается прочитать:

```text
TBinaryProtocol
```

данные интерпретируются неправильно.

Поэтому стороны должны согласовать стек:

```text
Transport
Protocol
Service IDL
```

---

# 30. Полный Python-пример

Допустим `user.thrift`:

```thrift
namespace py user_api

struct User {
    1: i64 id,
    2: string name,
    3: optional string email
}

exception UserNotFound {
    1: i64 id,
    2: string message
}

service UserService {

    User getUser(
        1: i64 id
    ) throws (
        1: UserNotFound error
    )
}
```

Генерация:

```bash
thrift --gen py user.thrift
```

Получаем:

```text
gen-py/
└── user_api/
    ├── UserService.py
    ├── ttypes.py
    └── constants.py
```

---

# 31. Server на Python

Упрощённый сервер:

```python
import sys

sys.path.append("gen-py")

from user_api import UserService
from user_api.ttypes import User, UserNotFound

from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
from thrift.transport import TSocket
from thrift.transport import TTransport


class UserHandler:
    def getUser(self, user_id):
        if user_id != 1:
            raise UserNotFound(
                id=user_id,
                message="User not found",
            )

        return User(
            id=1,
            name="Ilya",
            email="ilya@example.com",
        )


handler = UserHandler()

processor = UserService.Processor(handler)

server_transport = TSocket.TServerSocket(
    host="127.0.0.1",
    port=9090,
)

transport_factory = (
    TTransport.TBufferedTransportFactory()
)

protocol_factory = (
    TBinaryProtocol.TBinaryProtocolFactory()
)

server = TServer.TSimpleServer(
    processor,
    server_transport,
    transport_factory,
    protocol_factory,
)

server.serve()
```

---

# 32. Что происходит при запуске сервера

```text
UserHandler
    ↓
UserService.Processor
    ↓
TBinaryProtocolFactory
    ↓
TBufferedTransportFactory
    ↓
TServerSocket(:9090)
    ↓
listen()
```

Когда приходит клиент:

```text
TCP connection
      ↓
TServerSocket.accept()
      ↓
Transport
      ↓
Protocol
      ↓
Processor
      ↓
Handler
```

---

# 33. Client на Python

```python
import sys

sys.path.append("gen-py")

from user_api import UserService
from user_api.ttypes import UserNotFound

from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket
from thrift.transport import TTransport


socket = TSocket.TSocket(
    "127.0.0.1",
    9090,
)

transport = TTransport.TBufferedTransport(
    socket
)

protocol = TBinaryProtocol.TBinaryProtocol(
    transport
)

client = UserService.Client(
    protocol
)

transport.open()

try:
    user = client.getUser(1)
    print(user)
except UserNotFound as exc:
    print(exc)

transport.close()
```

---

# 34. Что происходит при `client.getUser(1)`

Код выглядит как обычный вызов:

```python
client.getUser(1)
```

Но реально:

```text
Python
  ↓
generated Client.getUser()
  ↓
создаётся структура arguments
  ↓
TBinaryProtocol сериализует
  ↓
TBufferedTransport
  ↓
TSocket.write()
  ↓
TCP
  ↓
network
```

На server:

```text
TCP
 ↓
TSocket
 ↓
TBufferedTransport
 ↓
TBinaryProtocol
 ↓
UserService.Processor
 ↓
UserHandler.getUser(1)
```

Затем ответ проходит тот же путь обратно.

---

# 35. Где происходит сериализация

Очень важно:

```text
socket НЕ сериализует Thrift
TCP НЕ понимает Thrift
```

Сериализацией занимается:

```text
TProtocol
```

Например:

```text
TBinaryProtocol
```

Transport видит уже поток байтов.

---

# 36. Где происходит RPC

RPC-логику реализуют в основном:

```text
Generated Client
Generated Processor
Server runtime
```

Упрощённо request должен содержать:

```text
method name
message type
sequence id
arguments
```

Затем Processor понимает, какой метод handler нужно вызвать.

---

# 37. Sequence ID

RPC-запросы обычно имеют идентификатор последовательности.

Идея:

```text
request #17
      ↓
network
      ↓
response #17
```

Это помогает связать ответ с вызовом.

Реальные возможности multiplexing зависят от transport/server/client implementation.

---

# 38. Server implementations

Thrift runtime может предоставлять разные модели сервера.

В Python tutorial показаны, например:

```text
TSimpleServer
TThreadedServer
TThreadPoolServer
```

## TSimpleServer

Простая последовательная обработка.

Хорош для:

```text
обучения
тестов
простых локальных сервисов
```

## TThreadedServer

Создаёт потоковую обработку клиентов.

## TThreadPoolServer

Использует пул worker threads.

У разных языковых библиотек набор server implementations может отличаться.

---

# 39. Schema evolution в Thrift

Thrift проектировался так, чтобы контракт можно было развивать.

Базовая идея:

```text
старый client
       ↕
новый server
```

может работать, если изменения совместимы.

---

# 40. Безопасное добавление optional field

Было:

```thrift
struct User {
    1: i64 id,
    2: string name
}
```

Стало:

```thrift
struct User {
    1: i64 id,
    2: string name,
    3: optional string email
}
```

Старый клиент не знает `email`.

Но поле имеет новый ID:

```text
3
```

поэтому старый reader может пропустить неизвестное поле.

---

# 41. Удаление поля

Допустим:

```thrift
struct User {
    1: i64 id,
    2: string name,
    3: optional string email
}
```

Мы решили удалить `email`.

Лучше не переиспользовать:

```text
field id = 3
```

для совершенно другого смысла.

То есть нежелательно затем делать:

```thrift
3: i64 balance
```

Потому что старые версии контракта знают поле `3` как `email`.

---

# 42. Почему required опаснее

Было:

```thrift
1: required string email
```

Новый writer перестал передавать email.

Старый reader ожидает:

```text
email обязательно должен присутствовать
```

и может завершить чтение ошибкой.

Поэтому `required` ограничивает мягкую эволюцию схем.

---

# 43. Thrift vs Protocol Buffers

## Главное сходство

Оба используют:

```text
IDL
 ↓
compiler/codegen
 ↓
generated types
 ↓
binary serialization
```

Thrift:

```thrift
struct User {
    1: i64 id,
    2: string name
}
```

Protobuf:

```protobuf
message User {
    int64 id = 1;
    string name = 2;
}
```

Очень похожая концепция.

---

# 44. Field IDs: Thrift vs Protobuf

Thrift:

```thrift
1: i64 id
2: string name
```

Protobuf:

```protobuf
int64 id = 1;
string name = 2;
```

В обоих случаях числовые идентификаторы являются частью wire contract.

Но wire encoding различается.

---

# 45. Wire format

## Protobuf

Wire message состоит из записей:

```text
field number
+
wire type
+
payload
```

Это tag-based encoding.

## Thrift

Конкретная структура зависит от выбранного Protocol:

```text
TBinaryProtocol
TCompactProtocol
TJSONProtocol
...
```

То есть у Thrift формат сериализации является заменяемым компонентом.

Это одно из ключевых архитектурных различий.

---

# 46. Thrift умеет RPC сам

Protobuf:

```text
message format
serialization
code generation
```

Сам Protobuf не обязан предоставлять транспорт или RPC runtime.

Поэтому часто используется:

```text
Protobuf
    +
gRPC
```

Thrift:

```text
Thrift IDL
    +
serialization protocols
    +
transport abstraction
    +
generated RPC client
    +
generated processor
    +
server runtime
```

То есть Thrift ближе к готовому RPC stack.

---

# 47. Thrift vs gRPC

Очень полезная модель:

```text
Thrift
≈
IDL + Serialization + RPC runtime

gRPC
≈
RPC framework
   +
обычно Protobuf IDL/messages
```

---

# 48. Service definitions

Thrift:

```thrift
service UserService {
    User getUser(1: i64 id)
}
```

gRPC:

```protobuf
service UserService {
    rpc GetUser(GetUserRequest)
        returns (User);
}
```

---

# 49. RPC arguments

Thrift допускает параметры непосредственно в сигнатуре:

```thrift
i64 add(
    1: i64 a,
    2: i64 b
)
```

В gRPC обычно request всегда является отдельным message:

```protobuf
message AddRequest {
    int64 a = 1;
    int64 b = 2;
}

service Calculator {
    rpc Add(AddRequest)
        returns (AddResponse);
}
```

Это важное отличие стиля контрактов.

---

# 50. Streaming

gRPC имеет встроенные понятия:

```text
Unary RPC
Server streaming
Client streaming
Bidirectional streaming
```

Например:

```protobuf
rpc Events(stream Event)
    returns (stream Event);
```

Классический Thrift RPC в первую очередь ориентирован на request/response методы.

Если API архитектурно требует развитого streaming RPC, gRPC обычно является более естественной моделью.

---

# 51. HTTP/2

gRPC стандартно строится вокруг HTTP/2 semantics:

```text
HTTP/2
streams
headers
trailers
flow control
multiplexing
```

Thrift отделяет:

```text
Transport
```

от:

```text
Protocol
```

и может работать поверх разных transport implementations.

Это даёт больше вариативности, но меньше единой транспортной модели, чем у gRPC.

---

# 52. Ошибки

Thrift может описывать:

```thrift
throws (
    1: UserNotFound error
)
```

gRPC обычно сочетает:

```text
protobuf response
+
gRPC status codes
+
error details
```

То есть модель ошибок различается.

---

# 53. Code generation

## Thrift

```text
.thrift
  ↓
thrift compiler
  ↓
types + service client + processor
```

## Protobuf + gRPC

```text
.proto
  ↓
protoc
  ├── protobuf message classes
  └── gRPC plugin
          ↓
      stubs / servicers
```

В gRPC очень явно разделены:

```text
message generation
```

и:

```text
RPC generation
```

В Thrift они воспринимаются как части одной экосистемы.

---

# 54. Thrift vs Avro

См. также [[Apache Avro]].

Главное отличие:

```text
Thrift
→ RPC-oriented IDL + generated clients + transports + protocols

Avro
→ data/schema-oriented serialization
→ code generation не обязателен
→ schema часто сопровождает данные
```

Thrift больше напоминает:

```text
service contracts
```

Avro больше напоминает:

```text
data contracts
```

Хотя Avro также имеет RPC specification.

---

# 55. Когда выбирать Thrift

Thrift подходит, когда нужны:

```text
cross-language RPC
строгий IDL
generated client/server code
компактная бинарная передача
контроль над protocol/transport
```

Пример:

```text
Python backend
   ↓ Thrift
Java service
   ↓ Thrift
Go service
```

---

# 56. Когда Protobuf + gRPC может быть удобнее

Особенно когда важны:

```text
HTTP/2
streaming RPC
современная gRPC ecosystem
interceptors
deadlines
metadata
load balancing integrations
service mesh integrations
```

Это не означает, что Thrift хуже.

Просто архитектурные акценты различаются.

---

# 57. Что надо помнить

```text
Apache Thrift
```

— это не один binary format.

Это stack:

```text
.thrift IDL
    ↓
Thrift Compiler
    ↓
Generated Types
Generated Client
Generated Processor
    ↓
Protocol
    ↓
Transport
    ↓
Network
```

Самая важная ментальная модель:

```text
Protocol = КАК кодируем данные

Transport = КУДА пишем/откуда читаем bytes

Processor = КАК request превращается в вызов handler

Handler = НАША бизнес-логика
```

---

# 58. Минимальная схема в голове

```text
CLIENT

business code
    ↓
Generated Client
    ↓
TBinaryProtocol
    ↓
TBufferedTransport
    ↓
TSocket
    ↓
TCP
================================
TCP
    ↓
TServerSocket
    ↓
TBufferedTransport
    ↓
TBinaryProtocol
    ↓
Generated Processor
    ↓
Handler
    ↓
business logic

SERVER
```

---

# 59. Сравнительная таблица

| Свойство | Thrift | Protobuf | gRPC |
|---|---|---|---|
| IDL | Да | Да | Обычно `.proto` |
| Сериализация | Да | Да | Обычно Protobuf |
| Code generation | Да | Да | Да |
| RPC | Да | Нет сам по себе | Да |
| Transport abstraction | Да | Нет | HTTP/2-based RPC transport |
| Несколько serialization protocols | Да | Основной protobuf wire format | Обычно Protobuf |
| Streaming RPC | Не основная классическая модель | Не относится | Да |
| Generated client | Да | Нет без RPC layer | Да |
| Generated server plumbing | Да | Нет без RPC layer | Да |
| Field IDs | Да | Да | Через protobuf messages |

---

# 60. Связанные заметки

- [[Protocol Buffers]]
- [[gRPC]]
- [[Apache Avro]]
- [[TCP]]
- [[HTTP 2]]
- [[RPC]]
- [[Сериализация данных]]

---

# Источники

Официальная документация Apache Thrift:

- Apache Thrift — Concepts  
  https://thrift.apache.org/docs/concepts

- Apache Thrift — IDL  
  https://thrift.apache.org/docs/idl

- Apache Thrift — Type system  
  https://thrift.apache.org/docs/types.html

- Apache Thrift — Python Tutorial  
  https://thrift.apache.org/tutorial/py.html

- Apache Thrift — Language and Feature Matrix  
  https://thrift.apache.org/docs/Languages.html

Для сравнения:

- Protocol Buffers — Overview  
  https://protobuf.dev/overview/

- Protocol Buffers — Encoding  
  https://protobuf.dev/programming-guides/encoding/

- gRPC — Introduction  
  https://grpc.io/docs/what-is-grpc/introduction/

- gRPC — Core Concepts  
  https://grpc.io/docs/what-is-grpc/core-concepts/
