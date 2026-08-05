---
tags:
  - protobuf
  - troubleshooting
  - python
---

# Ошибки и диагностика Protobuf

## 1. `ModuleNotFoundError: user_pb2`

Причины:

- код не сгенерирован;
- файл находится не в Python path;
- неверный путь импорта;
- структура каталогов не совпадает с генерацией.

Проверить:

```bash
find . -name '*_pb2.py'
python -c "import sys; print('\n'.join(sys.path))"
```

## 2. Несовместимость runtime

Ошибка может указывать, что generated code создан новой версией, а установлен старый runtime.

Проверка:

```bash
python -c \
  "import google.protobuf; print(google.protobuf.__version__)"
```

Обновление:

```bash
python -m pip install -U protobuf
```

Лучше фиксировать совместимые версии в зависимостях.

## 3. `TypeError` при присваивании

```python
user.id = "123"
```

Поле имеет числовой тип.

Исправление:

```python
user.id = int("123")
```

## 4. `ValueError` для числа

```python
user.id = 10**100
```

Значение не помещается в диапазон типа.

Проверьте `int32`, `int64`, `uint64` и т. д.

## 5. `DecodeError`

```python
from google.protobuf.message import DecodeError

try:
    message.ParseFromString(payload)
except DecodeError:
    ...
```

Причины:

- повреждённый payload;
- прочитана только часть TCP-сообщения;
- неверная длина;
- это не Protobuf;
- данные обрезаны;
- выбран несовместимый тип сообщения.

## 6. Сообщение разобралось «не тем» типом

Protobuf payload не содержит полное имя типа.

Нужно внешнее соглашение:

- endpoint;
- RPC method;
- topic;
- envelope;
- `Any`;
- `oneof`.

## 7. `HasField()` вызывает ошибку

```python
user.HasField("name")
```

Но поле объявлено:

```proto
string name = 1;
```

У него implicit presence.

Исправление:

```proto
optional string name = 1;
```

Либо сравнивать с default, если отсутствие не важно.

## 8. Нельзя присвоить вложенное сообщение

```python
user.address = address
```

Используйте:

```python
user.address.CopyFrom(address)
```

Либо передайте объект в конструктор.

## 9. TCP получает не всё сообщение

Нельзя считать:

```python
payload = sock.recv(4096)
```

гарантированным чтением одного объекта.

Используйте:

- length prefix;
- цикл `recv_exact`;
- лимит размера.

## 10. `buf lint` заходит в `.venv`

Ошибка содержит путь:

```text
.venv/lib/.../grpc_tools/_proto/...
```

Buf считает корень проекта модулем и сканирует зависимости.

Правильно:

```yaml
version: v2

modules:
  - path: proto
```

Либо:

```yaml
modules:
  - path: .
    excludes:
      - .venv
      - build
      - dist
```

## 11. `cannot resolve message field name`

Если ошибка находится в служебном `descriptor.proto` внутри `.venv`, причина обычно не в вашей схеме, а в том, что Buf проверяет чужие Well-Known Types или сталкивается с версиями инструментов.

Сначала исключите `.venv` из модуля.

## 12. Импорт `.proto` не найден

```text
File not found
Import was not found or had errors
```

Нужно правильно указать корень import path:

```bash
protoc \
  -I proto \
  --python_out=generated \
  proto/company/users/v1/users.proto
```

Если внутри:

```proto
import "company/common/v1/common.proto";
```

то `-I proto` должен быть корнем, относительно которого существует этот путь.

## 13. Дублирование символов

Ошибка:

```text
duplicate symbol
```

Причины:

- два message с одинаковым полным именем;
- одинаковый package и имя;
- файл подключён двумя путями;
- в DescriptorPool загружаются конфликтующие версии.

Используйте уникальные package:

```proto
package company.users.v1;
```

## 14. Изменение поля ломает старые данные

Проверьте:

- номер;
- тип;
- singular/repeated;
- oneof;
- enum number;
- смысл.

Запускайте:

```bash
buf breaking --against '.git#branch=main'
```

## 15. Generated code изменяется у разных разработчиков

Причины:

- разные версии `protoc`;
- разные plugins;
- разные options;
- разные runtime;
- ручные команды.

Решение:

- фиксировать версии;
- использовать `buf.gen.yaml`;
- генерировать в CI;
- публиковать SDK.

## 16. JSON отличается от ожидаемого

ProtoJSON может:

- использовать camelCase;
- представлять 64-битные числа строками;
- иначе кодировать enum;
- не сохранять unknown fields;
- применять специальные правила Timestamp и Any.

Не воспринимайте ProtoJSON как произвольный JSON.

## 17. Проверка содержимого payload

HEX:

```python
print(payload.hex(" "))
```

Без схемы:

```bash
protoc --decode_raw < message.bin
```

Со схемой:

```bash
protoc \
  --decode=demo.users.v1.User \
  -I proto \
  proto/demo/users/v1/users.proto \
  < user.bin
```

## 18. Проверка дескриптора

```python
from google.protobuf import descriptor_pb2
from demo.users.v1 import users_pb2

descriptor = descriptor_pb2.FileDescriptorProto.FromString(
    users_pb2.DESCRIPTOR.serialized_pb
)

print(descriptor)
```

## 19. Диагностический чек-лист

- [ ] Какой тип сообщения ожидается?
- [ ] Полностью ли получен payload?
- [ ] Есть ли length framing?
- [ ] Совместимы ли версии схем?
- [ ] Совместимы ли generated code и runtime?
- [ ] Правильно ли настроен import path?
- [ ] Не сканирует ли Buf `.venv`?
- [ ] Не менялся ли номер поля?
- [ ] Не менялся ли тип поля?
- [ ] Не потерялись ли unknown fields после JSON?
