---
tags:
  - protobuf
  - python
  - protoc
  - descriptor
---
## 1. Общая цепочка

```text
user.proto
    ↓ синтаксический разбор
FileDescriptorProto
    ↓ Python generator
user_pb2.py
    ↓ импорт
динамически созданный класс User
```

`user_pb2.py` — не вручную написанный класс, а сгенерированный модуль, который регистрирует описание схемы и создаёт классы через runtime Protobuf.

## 2. `protoc` и runtime — разные компоненты

### Компилятор

```bash
protoc --version
```

Читает `.proto` и генерирует исходный код.

### Python runtime

```bash
python -m pip install protobuf
```

Используется при выполнении программы:

- создаёт сообщения;
- сериализует;
- десериализует;
- проверяет значения;
- хранит дескрипторы.

### `grpcio-tools`

Python-пакет, содержащий доступный через модуль компилятор:

```bash
python -m pip install grpcio-tools
```

Запуск:

```bash
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  user.proto
```

## 3. Генерация `.py` и `.pyi`

```bash
protoc \
  -I. \
  --python_out=. \
  --pyi_out=. \
  user.proto
```

Результат:

```text
user_pb2.py   — runtime-код
user_pb2.pyi  — type stubs для IDE и анализаторов
```

`.pyi` не участвует в выполнении программы.

## 4. Почему файл называется `_pb2.py`

Это историческое имя Python API второй версии Protocol Buffers. Суффикс используется и для proto3.

## 5. Основные части `user_pb2.py`

Упрощённый файл:

```python
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b"..."
)

_globals = globals()

_builder.BuildMessageAndEnumDescriptors(
    DESCRIPTOR,
    _globals,
)

_builder.BuildTopDescriptorsAndMessages(
    DESCRIPTOR,
    "user_pb2",
    _globals,
)
```

## 6. `runtime_version`

```python
_runtime_version.ValidateProtobufRuntimeVersion(...)
```

Проверяет совместимость сгенерированного кода с установленным runtime.

Проблема возникает, когда:

```text
generated code слишком новый
runtime protobuf слишком старый
```

Проверка версии:

```bash
python -c "import google.protobuf; print(google.protobuf.__version__)"
```

## 7. Дескрипторы

Дескриптор описывает схему, а не конкретные данные.

```python
user_pb2.DESCRIPTOR
```

описывает `.proto`-файл.

```python
user_pb2.User.DESCRIPTOR
```

описывает сообщение `User`.

```python
user_pb2.User(id=1)
```

является конкретным экземпляром с данными.

### Основные типы дескрипторов

| Тип | Что описывает |
|---|---|
| `FileDescriptor` | весь `.proto` |
| `Descriptor` | `message` |
| `FieldDescriptor` | поле |
| `EnumDescriptor` | enum |
| `ServiceDescriptor` | service |
| `MethodDescriptor` | RPC-метод |

## 8. `AddSerializedFile`

Самая важная строка:

```python
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b"\n\nuser.proto..."
)
```

В `b"..."` находится не пользователь `User`, а сериализованное описание схемы.

То есть байты описывают:

```text
файл user.proto
package demo
message User
поле id: номер 1, тип int64
поле name: номер 2, тип string
```

`AddSerializedFile`:

1. разбирает байты как `FileDescriptorProto`;
2. создаёт runtime-дескрипторы;
3. регистрирует их в `DescriptorPool`;
4. возвращает `FileDescriptor`.

## 9. `DescriptorPool`

Глобальный реестр известных схем:

```text
полное Protobuf-имя → дескриптор
```

Пример:

```python
from google.protobuf import descriptor_pool

pool = descriptor_pool.Default()
descriptor = pool.FindMessageTypeByName("demo.v1.User")
```

## 10. `symbol_database`

```python
_sym_db = _symbol_database.Default()
```

Связывает имена Protobuf-типов с созданными Python-классами.

Условно:

```text
demo.v1.User → user_pb2.User
```

В обычном прикладном коде напрямую почти не используется.

## 11. `_builder`

```python
_builder.BuildMessageAndEnumDescriptors(...)
_builder.BuildTopDescriptorsAndMessages(...)
```

Runtime проходит по дескрипторам и создаёт классы сообщений динамически.

Поэтому в `user_pb2.py` может не быть обычного кода:

```python
class User:
    ...
```

Но после импорта существует:

```python
import user_pb2

print(user_pb2.User)
```

## 12. Что происходит при импорте

```python
import user_pb2
```

Запускает:

```text
1. Проверку версии runtime.
2. Чтение сериализованной схемы.
3. Регистрацию схемы в DescriptorPool.
4. Создание дескрипторов сообщений и enum.
5. Динамическое создание классов.
6. Регистрацию классов в symbol database.
```

## 13. Как посмотреть сериализованную схему

```python
from google.protobuf import descriptor_pb2
import user_pb2

proto = descriptor_pb2.FileDescriptorProto.FromString(
    user_pb2.DESCRIPTOR.serialized_pb
)

print(proto)
```

Пример вывода:

```text
name: "user.proto"
package: "demo.v1"
message_type {
  name: "User"
  field {
    name: "id"
    number: 1
    type: TYPE_INT64
  }
}
syntax: "proto3"
```

## 14. Инспекция классов

```python
import user_pb2
from google.protobuf.message import Message

print(issubclass(user_pb2.User, Message))
print(user_pb2.User.DESCRIPTOR.full_name)
```

Поля:

```python
for field in user_pb2.User.DESCRIPTOR.fields:
    print(
        field.name,
        field.number,
        field.type,
        field.label,
    )
```

## 15. Почему нельзя редактировать `user_pb2.py`

Источник истины:

```text
user.proto
```

Сгенерированный файл:

```text
user_pb2.py
```

будет перезаписан при следующем запуске генератора.

Правильный процесс:

```text
изменить .proto
→ проверить совместимость
→ повторно сгенерировать код
→ обновить приложение
```

## 16. Организация каталогов

```text
project/
├── proto/
│   └── company/
│       └── users/
│           └── v1/
│               └── users.proto
├── generated/
├── src/
├── buf.yaml
└── buf.gen.yaml
```

В production generated code либо:

- генерируется во время сборки;
- хранится в репозитории;
- публикуется как отдельный SDK-пакет.
