## Роль `.proto`

`.proto` — контракт между клиентом и сервером.

Он описывает:

1. сообщения;
2. поля и их номера;
3. enum;
4. вложенные типы;
5. сервисы;
6. RPC methods;
7. streaming-направления.

Пример:

```proto
syntax = "proto3";

package demo.users.v1;

enum UserStatus {
  USER_STATUS_UNSPECIFIED = 0;
  USER_STATUS_ACTIVE = 1;
  USER_STATUS_BLOCKED = 2;
}

message Address {
  string country = 1;
  string city = 2;
}

message User {
  int64 id = 1;
  string name = 2;
  optional string email = 3;
  UserStatus status = 4;
  Address address = 5;
  repeated string roles = 6;
}
```

## Почему у полей есть номера

```proto
string name = 2;
```

`2` — wire field number. Именно номер, а не имя `name`, используется в бинарном Protobuf wire format.

После публикации схемы нельзя бездумно переиспользовать старый номер под другое значение.

Хорошая практика после удаления поля:

```proto
reserved 2;
reserved "name";
```

## Что генерируется для Python

```bash
python -m grpc_tools.protoc \
  -Iprotos \
  --python_out=src \
  --pyi_out=src \
  --grpc_python_out=src \
  protos/demo/users/v1/users.proto
```

### `users_pb2.py`

Содержит Protobuf-часть:

```text
User
Address
GetUserRequest
GetUserResponse
enum metadata
DESCRIPTOR
serialization / deserialization support
```

С точки зрения приложения:

```python
user = users_pb2.User(
    id=1,
    name="Alice",
)
```

Перед сетью:

```python
payload = user.SerializeToString()
```

На другой стороне:

```python
user = users_pb2.User.FromString(payload)
```

Обычно gRPC делает это автоматически.

## Что такое `DESCRIPTOR`

Generated module регистрирует сериализованное описание `.proto` в descriptor pool.

Descriptor — runtime-метаданные схемы:

```text
какие messages существуют
какие поля есть
их номера
их типы
какие enums существуют
какие services описаны
```

## `users_pb2_grpc.py`

Содержит gRPC-часть:

```text
UserServiceStub
UserServiceServicer
add_UserServiceServicer_to_server(...)
```

### Stub

Клиентский proxy:

```python
stub = users_pb2_grpc.UserServiceStub(channel)
```

Внутри generated constructor концептуально делает:

```python
self.GetUser = channel.unary_unary(
    "/demo.users.v1.UserService/GetUser",
    request_serializer=GetUserRequest.SerializeToString,
    response_deserializer=GetUserResponse.FromString,
)
```

### Servicer

Generated base class:

```python
class UserServiceServicer:
    ...
```

Разработчик пишет:

```python
class UserService(
    users_pb2_grpc.UserServiceServicer
):
    async def GetUser(...):
        ...
```

### Registration function

```python
users_pb2_grpc.add_UserServiceServicer_to_server(
    UserService(),
    server,
)
```

Концептуально строит таблицу:

```text
/demo.users.v1.UserService/GetUser
    ↓
servicer.GetUser
request_deserializer = GetUserRequest.FromString
response_serializer = GetUserResponse.SerializeToString
```

Для каждого метода также фиксируется тип:

```text
unary_unary
unary_stream
stream_unary
stream_stream
```

## Полный путь типов

```text
GetUserRequest object
↓
request serializer
↓
protobuf bytes
↓
gRPC / HTTP2 / TCP
↓
request deserializer
↓
GetUserRequest object
↓
server handler
↓
GetUserResponse object
↓
response serializer
↓
bytes обратно
```

## `optional`, `repeated`, message и enum

### optional

```proto
optional string email = 3;
```

Позволяет различать «поле не передавалось» и «поле передано со значением по умолчанию».

```python
user.HasField("email")
```

### repeated

```proto
repeated string roles = 6;
```

```python
user.roles.append("admin")
user.roles.extend(["reader", "writer"])
```

### message field

```proto
Address address = 5;
```

```python
User(
    address=Address(
        country="Georgia",
        city="Tbilisi",
    )
)
```

Для уже созданного message:

```python
user.address.CopyFrom(address)
```

### enum

```proto
UserStatus status = 4;
```

```python
status=users_pb2.USER_STATUS_ACTIVE
```

## CopyFrom

```python
a = user
```

не копирует message, а создаёт вторую Python-ссылку на тот же mutable object.

Настоящая копия:

```python
copy = users_pb2.User()
copy.CopyFrom(user)
```

Но не нужно копировать без причины. Например:

```python
GetUserResponse(user=user)
```

валидно и обычно достаточно, если нет риска нежелательной мутации общего объекта.

## Совместимость схем

Главное правило: wire compatibility завязана на field numbers.

Безопаснее добавить новое поле с новым номером, чем изменить смысл старого номера.

Для production-контрактов полезны `buf lint` и `buf breaking`.

`buf lint` — проверка style/structure `.proto`.

`buf breaking` — сравнение контрактов и поиск несовместимых изменений.
