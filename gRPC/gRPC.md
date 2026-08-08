## Что такое gRPC

**gRPC** — это фреймворк для удалённого вызова процедур (**RPC — Remote Procedure Call**), который позволяет одному приложению вызывать методы другого приложения по сети почти так, как будто это обычные методы локального объекта.

Главная идея:

```text
Обычный вызов:

result = service.get_user(42)

gRPC:

result = remote_service.get_user(42)
                    │
                    └── на самом деле запрос уходит по сети
```

То есть разработчик работает не с URL и HTTP-запросами напрямую, а с **методами удалённого сервиса**.

Типичная схема:

```text
Client
  │
  │ stub.GetUser(...)
  ▼
gRPC client library
  │
  │ HTTP/2 + Protobuf
  ▼
Network
  │
  ▼
gRPC server library
  │
  ▼
GetUser(...)
  │
  ▼
Business logic
```

gRPC особенно часто используется для общения **между внутренними микросервисами**, где важны:

- строгий контракт;
- высокая скорость;
- небольшие сообщения;
- генерация клиентского SDK;
- поддержка нескольких языков программирования;
- streaming;
- deadlines;
- cancellation;
- retries;
- балансировка;
- единообразные ошибки.

---

# 1. Главное: gRPC и Protobuf — не одно и то же

Это два разных уровня.

## Protocol Buffers

**Protocol Buffers / Protobuf** отвечает прежде всего за:

1. описание структуры данных;
2. генерацию классов из `.proto`;
3. сериализацию объектов в бинарный формат;
4. десериализацию бинарных данных обратно в объекты.

Например:

```proto
syntax = "proto3";

message User {
    int64 id = 1;
    string name = 2;
}
```

После генерации Python-кода можно работать с:

```python
user = User(
    id=42,
    name="Alice",
)

binary = user.SerializeToString()
```

Protobuf сам по себе **не обязан передавать данные по сети**.

Можно сделать:

```text
Protobuf
   │
   ├── сохранить в файл
   ├── положить в Kafka
   ├── отправить через TCP
   ├── отправить через HTTP
   └── использовать внутри gRPC
```

---

## gRPC

gRPC отвечает за сам механизм удалённого вызова:

```text
кто вызывает
куда вызывает
какой метод
какой request
какой response
как передать сообщения
как обработать ошибки
как отменить запрос
какой timeout
как организовать streaming
```

По умолчанию gRPC очень тесно интегрирован с Protobuf.

Поэтому обычно `.proto` описывает сразу:

1. сообщения;
2. интерфейс удалённого сервиса.

Пример:

```proto
syntax = "proto3";

package users;

message GetUserRequest {
    int64 id = 1;
}

message User {
    int64 id = 1;
    string name = 2;
}

service UserService {
    rpc GetUser(GetUserRequest) returns (User);
}
```

Здесь:

```text
message
```

описывает данные, а:

```text
service
rpc
```

описывает gRPC API.

---

# 2. RPC-модель

REST и gRPC предлагают разные способы смотреть на API.

В REST мы обычно думаем в терминах **ресурсов**:

```http
GET /users/42
POST /users
DELETE /users/42
```

В gRPC мы думаем в терминах **методов**:

```text
UserService.GetUser(...)
UserService.CreateUser(...)
UserService.DeleteUser(...)
```

Пример:

```proto
service UserService {

    rpc GetUser(GetUserRequest)
        returns (GetUserResponse);

    rpc CreateUser(CreateUserRequest)
        returns (CreateUserResponse);

    rpc DeleteUser(DeleteUserRequest)
        returns (DeleteUserResponse);
}
```

То есть gRPC API больше похож на интерфейс класса:

```python
class UserService:
    def get_user(...)
    def create_user(...)
    def delete_user(...)
```

только реализация этого класса находится на другом сервере.

---

# 3. Основные компоненты gRPC

Упрощённо архитектура выглядит так:

```text
                    .proto
                      │
                      ▼
                   protoc
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   message classes          gRPC interfaces
     *_pb2.py              *_pb2_grpc.py
          │                       │
          │                       │
Client    │                       │    Server
──────────┼───────────────────────┼────────────
          │                       │
          ▼                       ▼
      Request                  Servicer
          │                       │
          ▼                       ▼
        Stub ───── HTTP/2 ───► gRPC Server
          ▲                       │
          │                       ▼
      Response               Business logic
```

Основные сущности:

```text
.proto
protoc
Message
Stub
Channel
Servicer
Server
Interceptor
Metadata
Status
Deadline
```

---

# 4. `.proto` как контракт API

В gRPC `.proto` становится **контрактом между клиентом и сервером**.

Например:

```proto
syntax = "proto3";

package users.v1;

service UserService {
    rpc GetUser(GetUserRequest)
        returns (GetUserResponse);
}

message GetUserRequest {
    int64 user_id = 1;
}

message GetUserResponse {
    User user = 1;
}

message User {
    int64 id = 1;
    string name = 2;
    string email = 3;
}
```

Из этого контракта клиент понимает:

```text
существует сервис:

users.v1.UserService

у него есть метод:

GetUser

он принимает:

GetUserRequest

он возвращает:

GetUserResponse
```

Клиенту и серверу не нужно вручную договариваться о JSON:

```json
{
  "userId": 42
}
```

и отдельно писать документацию вида:

```text
GET /users/{id}
response:
{
    ...
}
```

Схема уже формально описана в `.proto`.

---

# 5. Генерация кода

Для Python обычно устанавливают:

```bash
pip install grpcio grpcio-tools
```

Пусть есть файл:

```text
user.proto
```

Генерация:

```bash
python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    user.proto
```

Обычно появляются:

```text
user_pb2.py
user_pb2_grpc.py
```

---

## `user_pb2.py`

Это часть **Protobuf**.

Там находятся:

- описания сообщений;
- generated message classes;
- descriptors;
- сериализация;
- десериализация.

Например:

```python
request = user_pb2.GetUserRequest(
    user_id=42
)
```

---

## `user_pb2_grpc.py`

Это часть **gRPC**.

Для сервиса:

```proto
service UserService {
    rpc GetUser(GetUserRequest)
        returns (GetUserResponse);
}
```

обычно генерируются сущности вроде:

```text
UserServiceStub
UserServiceServicer
add_UserServiceServicer_to_server
```

### Stub

Используется клиентом:

```python
stub = UserServiceStub(channel)
```

И позволяет написать:

```python
response = stub.GetUser(request)
```

---

### Servicer

Это базовый интерфейс сервера.

Мы наследуемся от него и реализуем настоящую бизнес-логику:

```python
class UserService(
    user_pb2_grpc.UserServiceServicer
):

    def GetUser(self, request, context):
        ...
```

---

### Регистрация сервиса

Generated-функция связывает реализацию с gRPC server:

```python
user_pb2_grpc.add_UserServiceServicer_to_server(
    UserService(),
    server,
)
```

---

# 6. Channel и Stub

Клиент gRPC обычно работает через две основные сущности:

```text
Channel
Stub
```

## Channel

**Channel** представляет логический канал связи с сервером.

```python
channel = grpc.insecure_channel(
    "localhost:50051"
)
```

Channel управляет большим количеством сетевых деталей:

```text
TCP connection
HTTP/2
повторное использование соединений
состояние подключения
name resolution
load balancing
keepalive
TLS
```

Важно:

```text
Channel ≠ один RPC-запрос
```

Один channel может использоваться для большого количества RPC.

Обычно channel стараются **переиспользовать**, а не создавать заново на каждый запрос.

---

## Stub

Stub — generated client для конкретного сервиса:

```python
stub = user_pb2_grpc.UserServiceStub(channel)
```

После этого вызов выглядит как обычный метод:

```python
response = stub.GetUser(
    user_pb2.GetUserRequest(user_id=42)
)
```

Но внутри происходит удалённый вызов.

---

# 7. Что реально происходит при вызове метода

Рассмотрим:

```python
response = stub.GetUser(
    GetUserRequest(user_id=42)
)
```

Упрощённый lifecycle:

```text
1. Python создаёт GetUserRequest
        │
        ▼
2. Protobuf сериализует сообщение
        │
        ▼
3. gRPC определяет вызываемый service/method
        │
        ▼
4. gRPC формирует HTTP/2 request
        │
        ▼
5. данные отправляются по TCP
        │
        ▼
6. gRPC server принимает HTTP/2 stream
        │
        ▼
7. Protobuf десериализует request
        │
        ▼
8. вызывается UserService.GetUser()
        │
        ▼
9. сервер создаёт GetUserResponse
        │
        ▼
10. Protobuf сериализует response
        │
        ▼
11. response идёт обратно через HTTP/2
        │
        ▼
12. клиент десериализует response
        │
        ▼
13. Python получает объект GetUserResponse
```

То есть код:

```python
stub.GetUser(request)
```

скрывает довольно большую сетевую инфраструктуру.

---

# 8. gRPC работает поверх HTTP/2

Классический gRPC transport использует:

```text
Application
    │
    ▼
gRPC
    │
    ▼
Protobuf
    │
    ▼
HTTP/2
    │
    ▼
TLS (обычно в production)
    │
    ▼
TCP
    │
    ▼
IP
```

При этом важно:

```text
gRPC ≠ HTTP/2
```

HTTP/2 — транспортный HTTP-протокол.

gRPC строит поверх него RPC-модель:

- service;
- method;
- messages;
- metadata;
- status codes;
- deadlines;
- streaming;
- cancellation;
- retries и другие механизмы.

---

# 9. Как gRPC выглядит внутри HTTP/2

Хотя программист обычно не видит HTTP-запрос, внутри gRPC использует HTTP/2.

Для:

```proto
package users.v1;

service UserService {
    rpc GetUser(GetUserRequest)
        returns (GetUserResponse);
}
```

запрос концептуально имеет путь:

```text
/users.v1.UserService/GetUser
```

и использует:

```http
:method: POST
content-type: application/grpc
```

Это важное отличие от REST.

REST может использовать:

```http
GET
POST
PUT
PATCH
DELETE
```

gRPC обычно передаёт RPC-вызовы как HTTP/2 `POST`, а семантика операции определяется именем RPC-метода.

Например:

```text
/users.v1.UserService/GetUser
/users.v1.UserService/CreateUser
/users.v1.UserService/DeleteUser
```

---

# 10. Как выглядит gRPC message на wire

Protobuf создаёт бинарное сообщение:

```text
<protobuf bytes>
```

Перед ним gRPC добавляет небольшой prefix:

```text
┌──────────────┬──────────────────┬───────────────────────┐
│ compressed   │ message length   │ protobuf message      │
│ 1 byte       │ 4 bytes          │ N bytes               │
└──────────────┴──────────────────┴───────────────────────┘
```

То есть gRPC message имеет:

```text
1 byte  — compressed flag
4 bytes — длина сообщения
N bytes — payload
```

После этого этот поток передаётся через HTTP/2 DATA frames.

Важно:

```text
gRPC message
```

и:

```text
HTTP/2 DATA frame
```

— не одно и то же.

Одно gRPC сообщение может быть разбито на несколько HTTP/2 frames.

И наоборот, границы HTTP/2 DATA frames не обязаны совпадать с границами gRPC messages.

---

# 11. Почему HTTP/2 особенно подходит для gRPC

HTTP/2 даёт несколько важных свойств.

## Multiplexing

Через одно TCP-соединение могут одновременно идти несколько независимых HTTP/2 streams:

```text
TCP connection
│
├── HTTP/2 stream 1 ── GetUser
├── HTTP/2 stream 3 ── CreateOrder
├── HTTP/2 stream 5 ── GetBalance
└── HTTP/2 stream 7 ── StreamEvents
```

Это позволяет не создавать отдельное TCP-соединение под каждый RPC.

---

## Streaming

HTTP/2 естественно поддерживает долгоживущие streams.

Поэтому gRPC может эффективно реализовать:

```text
client streaming
server streaming
bidirectional streaming
```

---

## Header compression

HTTP/2 использует сжатие заголовков, что уменьшает overhead при большом количестве запросов.

---

## Flow control

HTTP/2 имеет механизм flow control.

Он не позволяет быстрому отправителю бесконечно забивать память медленного получателя.

Пример:

```text
Server
  │
  │ быстро отправляет сообщения
  ▼
HTTP/2 flow control
  │
  │ ограничивает поток
  ▼
Slow Client
```

---

# 12. Четыре типа RPC

Одна из главных особенностей gRPC — четыре модели взаимодействия.

---

## 12.1 Unary RPC

Один request → один response.

```text
Client                Server

Request  ───────────►
         ◄─────────── Response
```

`.proto`:

```proto
rpc GetUser(GetUserRequest)
    returns (GetUserResponse);
```

Это самый близкий аналог обычного REST request/response.

Python:

```python
response = stub.GetUser(
    GetUserRequest(user_id=42)
)
```

Используется для:

- CRUD;
- получения объекта;
- команд;
- коротких синхронных операций.

---

# 12.2 Server Streaming

Один request → много responses.

```text
Client                Server

Request  ───────────►
         ◄─────────── Response 1
         ◄─────────── Response 2
         ◄─────────── Response 3
         ◄─────────── ...
```

`.proto`:

```proto
rpc SubscribeEvents(
    SubscribeRequest
) returns (
    stream Event
);
```

Клиент:

```python
for event in stub.SubscribeEvents(request):
    print(event)
```

Подходит для:

- подписок;
- передачи большого результата частями;
- логов;
- событий;
- progress updates;
- real-time данных.

---

# 12.3 Client Streaming

Много requests → один response.

```text
Client                Server

Request 1 ──────────►
Request 2 ──────────►
Request 3 ──────────►
...
         ◄─────────── Response
```

`.proto`:

```proto
rpc UploadMetrics(
    stream Metric
) returns (
    UploadResult
);
```

Используется для:

- загрузки последовательности событий;
- batch-like ingest;
- телеметрии;
- передачи большого входного потока.

---

# 12.4 Bidirectional Streaming

Много requests ↔ много responses.

```text
Client                Server

Message 1 ──────────►
         ◄─────────── Message A
Message 2 ──────────►
Message 3 ──────────►
         ◄─────────── Message B
         ◄─────────── Message C
```

`.proto`:

```proto
rpc Chat(
    stream ChatMessage
) returns (
    stream ChatMessage
);
```

Обе стороны могут независимо читать и писать сообщения.

Используется для:

- чатов;
- real-time coordination;
- игровых сервисов;
- телеметрии;
- двустороннего event stream;
- взаимодействия агентов;
- долгоживущих соединений.

---

# 13. Streaming ≠ один огромный Protobuf

Допустим сервер должен отправить миллион объектов.

Можно сделать:

```proto
message Response {
    repeated Item items = 1;
}
```

и вернуть один огромный response.

Но при server streaming можно отправлять:

```text
Item 1
Item 2
Item 3
...
```

по мере появления данных.

Преимущества:

```text
меньше memory pressure
меньше time-to-first-result
не нужно ждать формирования всего ответа
можно начать обработку раньше
```

---

# 14. Metadata

REST использует HTTP headers:

```http
Authorization: Bearer ...
X-Request-ID: ...
traceparent: ...
```

В gRPC аналогичную роль играет **metadata**.

Metadata — пары:

```text
key → value
```

Например:

```text
authorization → Bearer ...
request-id    → 07c...
traceparent   → ...
```

Они передаются поверх HTTP/2 headers/trailers.

Используются для:

- authentication;
- tracing;
- correlation ID;
- tenant ID;
- locale;
- custom technical information.

Metadata не стоит использовать вместо normal protobuf payload для основной бизнес-информации.

Хорошо:

```text
authorization
trace-id
request-id
```

Плохо:

```text
user_name
order_price
product_list
```

Бизнес-данные лучше помещать в protobuf messages.

---

# 15. gRPC Status Codes

В REST ошибки обычно выражаются HTTP status codes:

```text
200
400
401
403
404
409
429
500
503
```

В gRPC есть собственный набор status codes.

Наиболее важные:

| gRPC status | Смысл |
|---|---|
| `OK` | успех |
| `CANCELLED` | RPC отменён |
| `UNKNOWN` | неизвестная ошибка |
| `INVALID_ARGUMENT` | неправильные аргументы |
| `DEADLINE_EXCEEDED` | превышен deadline |
| `NOT_FOUND` | объект не найден |
| `ALREADY_EXISTS` | объект уже существует |
| `PERMISSION_DENIED` | нет прав |
| `RESOURCE_EXHAUSTED` | исчерпан ресурс / quota |
| `FAILED_PRECONDITION` | состояние системы не позволяет выполнить операцию |
| `ABORTED` | операция прервана, например из-за concurrency conflict |
| `OUT_OF_RANGE` | значение вне допустимого диапазона |
| `UNIMPLEMENTED` | метод не реализован |
| `INTERNAL` | внутренняя ошибка |
| `UNAVAILABLE` | сервис временно недоступен |
| `DATA_LOSS` | потеря или повреждение данных |
| `UNAUTHENTICATED` | нет корректной аутентификации |

Пример серверной ошибки:

```python
context.abort(
    grpc.StatusCode.NOT_FOUND,
    "user not found",
)
```

Клиент:

```python
try:
    response = stub.GetUser(request)
except grpc.RpcError as exc:
    print(exc.code())
    print(exc.details())
```

---

# 16. HTTP status и gRPC status — разные вещи

Это важный момент.

Успешно доставленный gRPC protocol response на HTTP-уровне часто имеет:

```http
:status: 200
```

При этом бизнес/RPC результат может быть:

```text
grpc-status: NOT_FOUND
```

Поэтому нельзя анализировать gRPC API так же, как обычный REST API, смотря только на HTTP status.

У gRPC собственная модель завершения RPC.

---

# 17. Deadlines и Timeouts

В распределённой системе запрос не должен ждать бесконечно.

Клиент обычно задаёт предел:

```python
response = stub.GetUser(
    request,
    timeout=2.0,
)
```

То есть:

```text
если операция не завершилась примерно за 2 секунды,
клиент больше не хочет ждать
```

При превышении времени клиент получает:

```text
DEADLINE_EXCEEDED
```

Это крайне важно в цепочках микросервисов:

```text
API Gateway
    │
    ▼
Service A
    │
    ▼
Service B
    │
    ▼
Service C
```

Без deadlines зависание `Service C` способно накопить запросы во всей цепочке.

Правильная идея:

```text
каждый RPC имеет конечный бюджет времени
```

Важно: по умолчанию gRPC не обязан автоматически назначать хороший deadline за приложение. Deadline нужно проектировать осознанно.

---

# 18. Deadline propagation

Представим:

```text
Client
  │ deadline = 5 sec
  ▼
Service A
  │
  │ потратил 1 sec
  ▼
Service B
```

Service B уже не должен получать полноценные новые 5 секунд.

Логичнее передать оставшийся бюджет:

```text
≈ 4 sec
```

Так deadline может распространяться по цепочке вызовов.

Это помогает не выполнять работу, результат которой клиент всё равно уже не сможет получить вовремя.

---

# 19. Cancellation

RPC можно отменить.

Например:

```text
Client закрыл экран
Client отменил задачу
deadline истёк
upstream request отменился
```

После этого downstream computation часто тоже нет смысла продолжать.

Схема:

```text
Client
  │
  X cancel
  │
  ▼
Service A
  │
  X cancel
  │
  ▼
Service B
```

Но важно:

**отмена RPC не откатывает уже выполненные side effects.**

Если сервер уже сделал:

```sql
UPDATE accounts ...
```

а после этого клиент отменил RPC, изменение в БД само по себе назад не откатится.

---

# 20. Retry

В distributed system временные ошибки неизбежны:

```text
connection reset
pod restart
temporary unavailable
network glitch
load balancer transition
```

Для некоторых операций gRPC может использовать retry policies.

Типичная стратегия:

```text
attempt 1
   │
UNAVAILABLE
   │
   ▼
backoff
   │
attempt 2
   │
success
```

Но retry требует осторожности.

Рассмотрим:

```proto
rpc ChargeCard(ChargeCardRequest)
    returns (ChargeCardResponse);
```

Если клиент не получил ответ, неизвестно:

```text
сервер не успел списать деньги

или

сервер списал деньги,
но response потерялся
```

Без идемпотентности повтор:

```text
ChargeCard()
```

может списать деньги дважды.

Поэтому retry особенно безопасен для:

```text
Get...
List...
идемпотентных операций
операций с idempotency key
```

---

# 21. Interceptors

Interceptor — аналог middleware.

Он позволяет выполнить общую логику вокруг RPC.

```text
Request
  │
  ▼
Interceptor
  │
  ├── auth
  ├── logging
  ├── tracing
  ├── metrics
  ├── validation
  └── error mapping
  │
  ▼
Service Method
```

Аналогичная идея в FastAPI:

```text
middleware
dependency
```

или в других backend frameworks:

```text
filter
middleware
hook
```

Interceptors полезны, чтобы не писать в каждом методе:

```python
check_token()
log_request()
start_trace()
measure_latency()
```

---

# 22. Authentication и TLS

В development иногда используют:

```python
grpc.insecure_channel(...)
```

Это значит, что транспорт не защищён TLS.

В production типичнее:

```text
gRPC
 ↓
HTTP/2
 ↓
TLS
 ↓
TCP
```

TLS даёт:

```text
encryption
server authentication
integrity
```

Также возможен **mTLS**:

```text
Client verifies Server
Server verifies Client
```

mTLS особенно распространён во внутренних service-to-service системах и service mesh.

Application credentials могут передаваться через metadata:

```text
authorization: Bearer <token>
```

То есть транспортная безопасность и пользовательская аутентификация — разные уровни:

```text
TLS
└── защищает канал

JWT/OAuth/etc.
└── идентифицирует caller
```

---

# 23. Name Resolution

Клиенту обычно нужно обратиться не обязательно к конкретному IP:

```text
10.0.1.42:50051
```

а к логическому имени:

```text
user-service:50051
```

Далее name resolver определяет backend addresses:

```text
user-service
     │
     ▼
DNS / service discovery
     │
     ├── 10.0.1.11
     ├── 10.0.1.12
     └── 10.0.1.13
```

---

# 24. Load Balancing

Представим Kubernetes:

```text
             UserService

        ┌──── Pod A
Client ─┼──── Pod B
        └──── Pod C
```

gRPC может работать с балансировкой на разных уровнях.

Например:

```text
Client
  │
  ▼
Load Balancer
  │
  ├── Pod A
  ├── Pod B
  └── Pod C
```

или через client-side подход:

```text
Client
  │
  ├── Pod A
  ├── Pod B
  └── Pod C
```

В gRPC есть концепции:

```text
name resolution
service config
load balancing policy
```

Например клиент может выбрать backend по стратегии вроде round-robin, если конкретная реализация и конфигурация это поддерживают.

---

# 25. Почему gRPC и балансировщик требуют внимания

gRPC часто использует долгоживущее HTTP/2 connection.

Допустим клиент установил:

```text
Client ─────────► Load Balancer ─────────► Pod A
```

и затем отправляет по этому соединению множество streams.

Если инфраструктура балансирует только на уровне одного TCP connection, большое число RPC может фактически долго идти на один backend.

Поэтому proxy/load balancer должен корректно понимать HTTP/2/gRPC или архитектура должна использовать подходящую client-side balancing модель.

Это одна из причин, почему нельзя автоматически применять к gRPC все правила, которые работали для коротких HTTP/1.1 REST connections.

---

# 26. Health Checking

У gRPC есть стандартный health checking service.

Идея:

```text
Health.Check(...)
```

Сервис может сообщить:

```text
SERVING
NOT_SERVING
```

Это может использоваться:

- балансировщиками;
- orchestration;
- мониторингом;
- gRPC clients.

Важно отличать:

```text
process жив
```

и:

```text
service реально готов обслуживать запросы
```

Например процесс Python работает, но соединение с критической БД отсутствует.

---

# 27. Reflection

Protobuf бинарный и сам по себе плохо читается человеком.

В REST разработчик часто имеет:

```text
OpenAPI / Swagger
```

Для gRPC существует **Server Reflection**.

Reflection позволяет инструментам узнать:

```text
какие services существуют
какие methods существуют
какие request/response types используются
```

Это используют инструменты вроде:

```text
grpcurl
Postman
```

Пример концептуально:

```bash
grpcurl localhost:50051 list
```

может показать доступные services, если reflection включён.

Reflection можно условно воспринимать как близкий аналог возможности получить описание API, похожей по назначению на OpenAPI discovery, хотя механизмы разные.

---

# 28. Observability

Для production gRPC нужно наблюдать так же, как REST.

Обычно собирают:

```text
request count
error count
latency
status codes
active streams
message sizes
retry count
deadline exceeded count
connection state
```

Очень полезны:

```text
OpenTelemetry
tracing
metrics
structured logs
```

В tracing желательно видеть цепочку:

```text
API Gateway
   │
   ▼
UserService
   │
   ▼
BillingService
   │
   ▼
PostgreSQL
```

Trace context можно распространять через metadata.

---

# 29. gRPC и REST: главное отличие

Самая важная концептуальная разница:

```text
REST
ориентирован на ресурсы

gRPC
ориентирован на методы удалённого сервиса
```

REST:

```http
GET /users/42
```

gRPC:

```text
UserService.GetUser(
    GetUserRequest(user_id=42)
)
```

---

# 30. REST request

Например:

```http
GET /users/42 HTTP/1.1
Host: api.example.com
Authorization: Bearer ...
```

Response:

```json
{
  "id": 42,
  "name": "Alice"
}
```

На клиенте:

```python
response = requests.get(
    "https://api.example.com/users/42"
)

data = response.json()
```

Клиент сам знает:

```text
URL
HTTP method
headers
JSON structure
status codes
```

---

# 31. Аналогичный gRPC request

`.proto`:

```proto
service UserService {
    rpc GetUser(GetUserRequest)
        returns (GetUserResponse);
}

message GetUserRequest {
    int64 user_id = 1;
}

message GetUserResponse {
    int64 id = 1;
    string name = 2;
}
```

Клиент:

```python
response = stub.GetUser(
    GetUserRequest(user_id=42)
)
```

Он работает с generated API, а не вручную строит:

```text
URL
JSON
HTTP method
```

---

# 32. Подробное сравнение gRPC и REST

| Свойство | REST | gRPC |
|---|---|---|
| Основная модель | ресурсы | remote methods |
| Контракт | часто OpenAPI | `.proto` |
| Payload | обычно JSON | обычно Protobuf |
| Читаемость человеком | высокая | низкая на wire |
| Размер payload | обычно больше | обычно меньше |
| Типизация | зависит от tooling | строгая схема |
| Code generation | опциональна | центральная часть подхода |
| Transport | HTTP/1.1, HTTP/2, HTTP/3 | классически HTTP/2 |
| Unary request/response | да | да |
| Server streaming | возможно разными способами | встроено |
| Client streaming | нетипично | встроено |
| Bidirectional streaming | обычно WebSocket/другие механизмы | встроено |
| Browser support | отличный | native gRPC ограничен |
| Debug через curl | очень просто | нужен gRPC-aware tool |
| Публичный API | очень удобно | зависит от аудитории |
| Internal microservices | хорошо | часто отлично |
| Межъязыковое SDK | возможно | одно из ключевых преимуществ |
| Error model | HTTP codes | gRPC status codes |
| Deadline | обычно вручную | first-class concept |
| Metadata | HTTP headers | gRPC metadata |
| Schema evolution | JSON более свободный | Protobuf compatibility rules |
| Streaming semantics | не единообразны | формализованы |

---

# 33. Почему gRPC часто быстрее REST + JSON

Нельзя говорить:

```text
gRPC всегда быстрее REST
```

Но у него часто есть преимущества.

## 1. Protobuf binary encoding

JSON:

```json
{
  "user_id": 42,
  "is_active": true
}
```

содержит имена полей прямо в payload:

```text
"user_id"
"is_active"
```

Protobuf использует numeric field identifiers:

```proto
int64 user_id = 1;
bool is_active = 2;
```

Поэтому сообщение часто получается компактнее.

---

## 2. Меньше parsing overhead

JSON требует text parsing.

Protobuf использует бинарный формат с заранее известной schema.

---

## 3. HTTP/2 multiplexing

Много concurrent RPC могут работать поверх одного connection.

---

## 4. Streaming встроен в API

Для многих real-time сценариев не нужно самостоятельно строить дополнительный protocol поверх WebSocket.

---

# 34. Но gRPC не всегда лучше REST

REST обычно лучше, если API:

- публичный;
- должен быть легко понятен сторонним разработчикам;
- вызывается непосредственно браузером;
- должен удобно тестироваться обычным `curl`;
- хорошо представляется ресурсами;
- не требует сложного streaming;
- нужен простой JSON interface.

gRPC часто лучше, если:

- много микросервисов;
- сервисы написаны на разных языках;
- важна строгая schema;
- высокая частота внутренних RPC;
- нужен streaming;
- нужно автоматически генерировать clients;
- важны deadlines/cancellation;
- API полностью контролируется одной организацией.

---

# 35. Browser и gRPC-Web

Обычный браузерный frontend не всегда может напрямую работать с native gRPC так же свободно, как backend client.

Для browser use case существует:

```text
gRPC-Web
```

Типичная архитектура:

```text
Browser
   │
   │ gRPC-Web
   ▼
Proxy / Gateway
   │
   │ native gRPC
   ▼
Backend gRPC Service
```

Поэтому распространённая архитектура:

```text
Internet clients
      │
      ▼
REST / JSON / gRPC-Web Gateway
      │
      ▼
Internal gRPC services
```

---

# 36. Типичная production-архитектура

Один из частых вариантов:

```text
                   INTERNET
                      │
                      ▼
              API Gateway / BFF
                      │
          REST / JSON │
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
    UserService               OrderService
       gRPC                      gRPC
         │                         │
         ├──────── gRPC ───────────┤
         │                         │
         ▼                         ▼
   PostgreSQL                PaymentService
                                  │
                                  ▼
                              PostgreSQL
```

То есть внешний API может быть REST, а внутреннее service-to-service взаимодействие — gRPC.

Это не правило, но очень распространённый подход.

---

# 37. Gateway REST → gRPC

Можно иметь публичный endpoint:

```http
GET /api/v1/users/42
```

Gateway преобразует его в:

```text
UserService.GetUser(
    GetUserRequest(user_id=42)
)
```

Схема:

```text
Browser
   │
   │ REST + JSON
   ▼
API Gateway
   │
   │ gRPC + Protobuf
   ▼
UserService
```

Таким образом REST и gRPC не обязательно конкурируют.

Они часто используются вместе на разных границах системы.

---

# 38. Полный простой пример на Python

Создадим:

```text
client.py
server.py
user.proto
```

---

## `user.proto`

```proto
syntax = "proto3";

package users.v1;

service UserService {
    rpc GetUser(GetUserRequest)
        returns (GetUserResponse);
}

message GetUserRequest {
    int64 user_id = 1;
}

message GetUserResponse {
    int64 id = 1;
    string name = 2;
}
```

---

## Генерация Python

```bash
python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    user.proto
```

Получим:

```text
user_pb2.py
user_pb2_grpc.py
```

Итоговая структура:

```text
project/
├── user.proto
├── user_pb2.py
├── user_pb2_grpc.py
├── server.py
└── client.py
```

---

# 39. Реализация сервера

```python
from concurrent import futures

import grpc

import user_pb2
import user_pb2_grpc


class UserService(
    user_pb2_grpc.UserServiceServicer
):

    def GetUser(self, request, context):
        return user_pb2.GetUserResponse(
            id=request.user_id,
            name="Alice",
        )


def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(
            max_workers=10
        )
    )

    user_pb2_grpc.add_UserServiceServicer_to_server(
        UserService(),
        server,
    )

    server.add_insecure_port(
        "[::]:50051"
    )

    server.start()

    print("gRPC server started")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
```

---

# 40. Реализация клиента

```python
import grpc

import user_pb2
import user_pb2_grpc


def main():
    with grpc.insecure_channel(
        "localhost:50051"
    ) as channel:

        stub = user_pb2_grpc.UserServiceStub(
            channel
        )

        request = user_pb2.GetUserRequest(
            user_id=42
        )

        response = stub.GetUser(
            request,
            timeout=2.0,
        )

        print(response.id)
        print(response.name)


if __name__ == "__main__":
    main()
```

---

# 41. Что происходит в этом примере

На клиенте:

```python
request = user_pb2.GetUserRequest(
    user_id=42
)
```

создаётся обычный generated Protobuf object.

Затем:

```python
stub.GetUser(request)
```

делает remote call.

Внутри примерно:

```text
GetUserRequest
    │
    ▼
SerializeToString()
    │
    ▼
gRPC frame
    │
    ▼
HTTP/2 stream
    │
    ▼
TCP
    │
    ▼
Server
```

На сервере framework определяет:

```text
service = users.v1.UserService
method  = GetUser
```

десериализует request и вызывает:

```python
UserService.GetUser(...)
```

Ответ:

```python
user_pb2.GetUserResponse(...)
```

сериализуется и идёт обратно клиенту.

---

# 42. AsyncIO gRPC в Python

Для асинхронного приложения Python существует API:

```python
grpc.aio
```

Например channel:

```python
channel = grpc.aio.insecure_channel(
    "localhost:50051"
)
```

Вызов:

```python
response = await stub.GetUser(
    request,
    timeout=2.0,
)
```

В async backend это часто естественнее, чем blocking API.

Концептуально архитектура при этом не меняется:

```text
Protobuf
Stub
Channel
HTTP/2
Server
Servicer
```

Меняется модель выполнения Python-кода.

---

# 43. Связь с generated SDK

`.proto` можно считать исходным machine-readable API contract.

Из него можно генерировать SDK для разных языков:

```text
                 user.proto
                     │
             ┌───────┼────────┐
             ▼       ▼        ▼
           Python    Go      Java
             │       │        │
           Client  Client   Client
```

Например:

```text
Python backend
Go backend
Java backend
```

могут общаться по одному контракту.

Каждый язык получает native classes/stubs.

Это одно из главных преимуществ gRPC в больших polyglot системах.

---

# 44. Кто должен владеть `.proto`

В production `.proto` — не случайный файл внутри одного сервиса.

Это API contract.

Возможные подходы:

```text
central proto repository
```

или:

```text
proto рядом с сервисом-владельцем
```

Главное — иметь понятного owner.

Обычно нужны:

- code review;
- CI;
- lint;
- compatibility checks;
- versioning;
- automated generation.

Здесь полезны инструменты вроде **Buf**:

```text
buf lint
buf breaking
buf generate
```

Смысл:

```text
lint
└── проверяет качество proto schema

breaking
└── ищет несовместимые изменения

generate
└── централизует code generation
```

---

# 45. Совместимость Protobuf особенно важна для gRPC

Допустим было:

```proto
message User {
    int64 id = 1;
    string name = 2;
}
```

Потом добавили:

```proto
string email = 3;
```

Это обычно нормальная эволюция schema.

Но нельзя бездумно менять field numbers:

```proto
string name = 2;
```

на:

```proto
string email = 2;
```

Потому что на wire поле идентифицируется главным образом номером.

Старый клиент может понять поле `2` как:

```text
name
```

а новый сервер — как:

```text
email
```

Это опасный breaking change.

При удалении поля номер обычно резервируют:

```proto
reserved 2;
reserved "name";
```

---

# 46. Версионирование API

Один из распространённых подходов:

```proto
package users.v1;
```

позже:

```proto
package users.v2;
```

Но не каждое изменение требует нового major version.

Protobuf специально создан для безопасной schema evolution, если соблюдать compatibility rules.

Поэтому часто:

```text
добавление нового optional-подобного поля
```

не требует `v2`.

А серьёзная смена semantic contract может потребовать новую API version.

---

# 47. gRPC API нужно проектировать как сетевой API

Очень опасная иллюзия:

```text
remote method выглядит как local method
```

Но remote call никогда не является обычным локальным вызовом.

Локальный вызов:

```python
result = obj.get_user(42)
```

обычно:

```text
быстрый
надёжный
в памяти одного процесса
```

Remote call:

```python
result = stub.GetUser(...)
```

может закончиться:

```text
timeout
packet loss
server unavailable
DNS failure
connection reset
partial failure
retry
duplicate execution
```

Поэтому существует правило:

> **A network call is not a local function call.**

Несмотря на удобный Stub API, при проектировании необходимо помнить о сети.

---

# 48. Что не нужно делать

## Не создавать channel на каждый запрос

Плохо:

```python
def get_user():
    channel = grpc.insecure_channel(...)
    stub = ...
    return stub.GetUser(...)
```

если это происходит тысячи раз.

Лучше иметь долгоживущий переиспользуемый channel.

---

## Не делать RPC слишком мелкими

Плохой дизайн:

```text
GetUserName
GetUserEmail
GetUserAge
GetUserCountry
GetUserCity
```

Если для одного UI request клиенту нужно сделать 10 RPC, network latency быстро съест выигрыш.

Иногда лучше:

```text
GetUser
```

вернуть разумно сформированный объект.

---

## Не забывать deadline

Плохо:

```python
stub.GetUser(request)
```

в критическом production path без продуманного time budget.

Лучше:

```python
stub.GetUser(
    request,
    timeout=1.5,
)
```

с осознанным значением.

---

## Не retry всё подряд

Особенно:

```text
CreateOrder
TransferMoney
ChargeCard
SendEmail
```

без idempotency strategy.

---

## Не использовать metadata как payload

Metadata — технический side channel, а не замена protobuf messages.

---

## Не ломать field numbers

Field number является частью wire contract.

---

# 49. gRPC vs message broker

gRPC также не нужно путать с Kafka/RabbitMQ.

gRPC:

```text
Service A
   │
   │ сейчас вызывает Service B
   ▼
Service B
```

Обычно это synchronous или streaming RPC communication.

Kafka:

```text
Producer
   │
   ▼
Topic
   │
   ▼
Consumer
```

Producer не обязан ждать Consumer.

Сравнение:

| | gRPC | Kafka |
|---|---|---|
| Модель | RPC | event/message log |
| Связь | относительно прямая | через broker |
| Request/response | естественно | не основной сценарий |
| Durable storage | не основная задача | одна из ключевых |
| Async decoupling | ограниченно | сильная сторона |
| Streaming | network RPC stream | persistent event stream |

Их часто используют вместе:

```text
UserService ──gRPC──► OrderService
                         │
                         ▼
                       Kafka
                         │
                         ▼
                   AnalyticsService
```

---

# 50. gRPC vs WebSocket

Оба могут поддерживать двустороннее долговременное взаимодействие.

Но WebSocket даёт в основном транспорт:

```text
bidirectional byte/message channel
```

а дальше application protocol часто нужно проектировать самому:

```text
message types
errors
correlation IDs
schema
routing
```

gRPC уже даёт:

```text
services
methods
schema
generated clients
status codes
metadata
deadlines
streaming semantics
```

Поэтому gRPC bidirectional streaming — более высокоуровневая RPC abstraction.

---

# 51. gRPC vs GraphQL

Это тоже разные задачи.

GraphQL:

```text
клиент описывает, какие поля данных ему нужны
```

gRPC:

```text
клиент вызывает заранее определённый remote method
```

GraphQL особенно популярен на client-facing API layers.

gRPC особенно силён в:

```text
service-to-service
high-performance typed communication
```

---

# 52. Где gRPC особенно полезен

Хорошие сценарии:

### Микросервисы

```text
OrderService → PaymentService
```

---

### Polyglot backend

```text
Python
  │
  ▼
Go
  │
  ▼
Java
```

с единым `.proto`.

---

### High-throughput internal API

Много маленьких typed messages.

---

### Streaming

```text
telemetry
events
logs
real-time updates
```

---

### Mobile/backend API

Когда важны компактные сообщения и generated clients.

---

### Infrastructure API

Например управляющие plane/control-plane взаимодействия между сервисами.

---

# 53. Где REST зачастую удобнее

REST часто проще для:

```text
public web API
third-party integrations
browser frontend
simple CRUD API
manual debugging
webhooks
```

Например API:

```http
GET https://api.example.com/users/42
```

легко:

- открыть;
- протестировать curl;
- показать партнёру;
- документировать OpenAPI;
- вызвать почти из любого окружения.

---

# 54. Можно ли использовать JSON с gRPC

Архитектурно gRPC не ограничен исключительно Protobuf.

Но стандартный и наиболее распространённый вариант:

```text
gRPC + Protobuf
```

Именно эта комбинация даёт:

- удобный IDL;
- code generation;
- компактный binary format;
- межъязыковую совместимость.

Поэтому на практике, говоря `gRPC`, почти всегда подразумевают именно эту связку, если явно не сказано обратное.

---

# 55. Почему gRPC называется framework, а не просто protocol

gRPC — не только формат bytes on the wire.

Экосистема включает:

```text
IDL integration
code generation
client stubs
server interfaces
channels
streaming
deadlines
cancellation
metadata
status codes
interceptors
load balancing
health checking
reflection
authentication integration
retry
```

То есть gRPC предоставляет разработчику полноценную модель построения RPC-системы.

---

# 56. Короткий mental model

Запомнить можно так:

```text
.proto
│
├── message
│     └── какие данные передаём
│
└── service/rpc
      └── какие удалённые методы можно вызвать
```

Далее:

```text
protoc
   │
   ├── *_pb2.py
   │      └── Protobuf messages
   │
   └── *_pb2_grpc.py
          ├── Stub
          ├── Servicer
          └── registration code
```

На клиенте:

```text
Message
   ↓
Stub
   ↓
Channel
   ↓
gRPC
   ↓
HTTP/2
   ↓
TCP
```

На сервере:

```text
TCP
 ↓
HTTP/2
 ↓
gRPC Server
 ↓
Servicer
 ↓
Business logic
```

---

# 57. REST и gRPC одной картинкой

## REST

```text
Client

requests.get(
    "/users/42"
)
    │
    ▼
HTTP request
    │
    ▼
REST Server
    │
    ▼
Router
    │
    ▼
Handler
    │
    ▼
JSON
```

---

## gRPC

```text
Client

stub.GetUser(
    request
)
    │
    ▼
Generated Stub
    │
    ▼
Protobuf serialization
    │
    ▼
gRPC / HTTP/2
    │
    ▼
gRPC Server
    │
    ▼
Generated routing
    │
    ▼
Servicer.GetUser()
    │
    ▼
Protobuf response
```

---

# 58. Что важно понимать для production

Если gRPC используется в production, необходимо продумать не только `.proto`.

Минимальный список:

```text
[ ] API ownership
[ ] protobuf compatibility
[ ] lint
[ ] breaking-change checks
[ ] generated SDK
[ ] deadlines
[ ] cancellation
[ ] retries
[ ] idempotency
[ ] TLS / mTLS
[ ] authentication
[ ] metadata
[ ] load balancing
[ ] name resolution
[ ] health checking
[ ] graceful shutdown
[ ] reflection policy
[ ] metrics
[ ] tracing
[ ] logs
[ ] max message sizes
[ ] backpressure / flow control
[ ] deployment compatibility
```

---

# 59. Пример реальной микросервисной цепочки

Допустим есть:

```text
Frontend
API Gateway
Order Service
User Service
Payment Service
Kafka
```

Архитектура:

```text
Frontend
   │
   │ REST/JSON
   ▼
API Gateway
   │
   │ gRPC
   ▼
OrderService
   │
   ├──── gRPC ────► UserService
   │
   ├──── gRPC ────► PaymentService
   │
   └──── event ───► Kafka
```

Почему такой дизайн имеет смысл:

```text
Frontend ↔ Gateway
```

REST удобен браузеру.

```text
Gateway ↔ backend services
```

gRPC даёт строгие contracts и generated clients.

```text
OrderService → Kafka
```

Kafka используется для асинхронных событий, которые не требуют немедленного RPC response.

---

# 60. Самое важное отличие от REST в одной фразе

REST говорит:

```text
"Вот ресурс. Работай с ним HTTP-операциями."
```

gRPC говорит:

```text
"Вот удалённый сервис. Вызывай его строго описанные методы."
```

REST:

```http
GET /users/42
```

gRPC:

```python
stub.GetUser(
    GetUserRequest(user_id=42)
)
```

---

# 61. Что нужно запомнить

**gRPC** — это RPC framework для typed communication между приложениями.

Он обычно использует:

```text
Protobuf
```

для описания и сериализации сообщений и:

```text
HTTP/2
```

как transport.

Главная цепочка:

```text
.proto
  ↓
protoc
  ↓
generated messages + Stub + Servicer
  ↓
Client calls Stub method
  ↓
Protobuf serialization
  ↓
gRPC framing
  ↓
HTTP/2
  ↓
Server
  ↓
Servicer method
```

Четыре вида RPC:

```text
Unary
Server Streaming
Client Streaming
Bidirectional Streaming
```

Ключевые production-механизмы:

```text
Metadata
Status Codes
Deadlines
Cancellation
Retries
Interceptors
TLS
Load Balancing
Health Checking
Reflection
Observability
```

И главное:

```text
Protobuf отвечает за структуру и сериализацию данных.

gRPC отвечает за удалённый вызов методов и сетевое взаимодействие.

HTTP/2 обеспечивает транспорт, streams и multiplexing.

TCP переносит байты между хостами.
```

---

# 62. Краткая шпаргалка

```text
gRPC
│
├── RPC framework
│
├── contract → .proto
│
├── serialization → usually Protobuf
│
├── transport → HTTP/2
│
├── client API → Stub
│
├── server API → Servicer
│
├── connection abstraction → Channel
│
├── errors → gRPC Status Codes
│
├── technical headers → Metadata
│
├── timeout budget → Deadline
│
├── middleware → Interceptor
│
└── RPC types
      ├── unary
      ├── server streaming
      ├── client streaming
      └── bidirectional streaming
```

Выбор:

```text
Public/browser/simple CRUD
        ↓
      REST

Internal typed microservices
high throughput / streaming
        ↓
      gRPC

Durable asynchronous events
        ↓
   Kafka / broker
```

---

# Полезные официальные источники

- gRPC — Introduction: https://grpc.io/docs/what-is-grpc/introduction/
- gRPC — Core concepts, architecture and lifecycle: https://grpc.io/docs/what-is-grpc/core-concepts/
- gRPC — Python basics: https://grpc.io/docs/languages/python/basics/
- gRPC — Python generated code: https://grpc.io/docs/languages/python/generated-code/
- gRPC — HTTP/2 protocol specification: https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-HTTP2.md
- gRPC — Status Codes: https://grpc.io/docs/guides/status-codes/
- gRPC — Deadlines: https://grpc.io/docs/guides/deadlines/
- gRPC — Retry: https://grpc.io/docs/guides/retry/
- gRPC — Metadata: https://grpc.io/docs/guides/metadata/
- gRPC — Health Checking: https://grpc.io/docs/guides/health-checking/
- gRPC — Reflection: https://grpc.io/docs/guides/reflection/
- Protocol Buffers — Programming Guides: https://protobuf.dev/programming-guides/
