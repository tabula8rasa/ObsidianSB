---
tags:
  - protobuf
  - buf
  - ci
  - sdk
---
## 1. Что такое Buf

Buf — набор инструментов вокруг Protobuf.

Он помогает:

- организовать `.proto` как модули;
- выполнять lint;
- искать breaking changes;
- генерировать код;
- управлять зависимостями;
- хранить схемы в registry;
- распространять generated SDK.

```text
protoc → компилятор
Buf → workflow и инструменты вокруг схем
```

## 2. `buf.yaml`

Пример:

```yaml
version: v2

modules:
  - path: proto

lint:
  use:
    - STANDARD

breaking:
  use:
    - FILE
```

Каталог `proto` становится областью Protobuf-модуля.

Это важно, чтобы Buf не заходил в:

```text
.venv/
node_modules/
build/
dist/
```

## 3. `buf lint`

```bash
buf lint
```

Проверяет текущие `.proto` на:

- соглашения именования;
- наличие package;
- структуру каталогов;
- enum;
- RPC request/response;
- импорты;
- рекомендуемый стиль.

Пример плохой схемы:

```proto
message user {
  int64 UserId = 1;
}
```

Исправление:

```proto
package company.users.v1;

message User {
  int64 user_id = 1;
}
```

`lint` не проверяет значения конкретных сообщений и бизнес-валидацию.

## 4. `buf breaking`

```bash
buf breaking \
  --against '.git#branch=main'
```

Сравнивает текущие схемы с базовой версией.

Ищет:

- изменение типа;
- изменение номера;
- удаление API;
- перемещение типов;
- переименования, ломающие source/JSON compatibility;
- другие несовместимые изменения.

Главное различие:

```text
buf lint
  хороша ли схема сама по себе?

buf breaking
  не сломала ли схема старый контракт?
```

## 5. Категории breaking-проверок

### `FILE`

Строгая проверка, учитывающая расположение по `.proto`-файлам и generated code.

```yaml
breaking:
  use:
    - FILE
```

### `PACKAGE`

Проверяет совместимость внутри Protobuf package и допускает больше перемещений между файлами.

### `WIRE_JSON`

Защищает бинарный wire format и ProtoJSON.

### `WIRE`

Проверяет преимущественно бинарную совместимость. Самый мягкий вариант.

Для учебного и большинства сервисных проектов разумно начинать с `FILE`.

## 6. `buf.gen.yaml`

Определяет генераторы:

```yaml
version: v2

plugins:
  - protoc_builtin: python
    out: generated/python
```

Генерация:

```bash
buf generate
```

Для gRPC используются дополнительные плагины.

Результат:

```text
generated/python/
└── company/
    └── users/
        └── v1/
            ├── users_pb2.py
            └── users_pb2_grpc.py
```

## 7. Генерация кода и генерация SDK

### Генерация кода

```text
.proto → users_pb2.py
```

### SDK

Готовый версионируемый пакет, который можно установить через пакетный менеджер.

```text
company-users-protobuf-python
├── pyproject.toml
└── company/users/v1/
    ├── users_pb2.py
    ├── users_pb2.pyi
    └── users_pb2_grpc.py
```

Установка:

```bash
pip install company-users-protobuf==1.5.0
```

Из одной схемы можно выпустить:

```text
Python package
Java JAR
Go module
npm package
```

## 8. Зачем публиковать SDK

Потребителю не нужно:

- устанавливать `protoc`;
- настраивать плагины;
- вручную копировать `.proto`;
- следить за версиями генераторов;
- писать одинаковый pipeline.

Он подключает обычную зависимость нужной версии.

## 9. Production-процесс

```text
изменение .proto
    ↓
pull request
    ↓
buf lint
    ↓
buf breaking
    ↓
review владельца API
    ↓
merge
    ↓
buf generate
    ↓
сборка SDK
    ↓
публикация версии
    ↓
обновление сервисов
```

## 10. CODEOWNERS

```text
/proto/company/users/  @users-team
/proto/company/orders/ @orders-team
/proto/company/common/ @architecture-team
```

Контракт меняется только после review владельца предметной области.

## 11. Версии SDK

```text
company-users-protobuf==1.4.0
company-users-protobuf==1.5.0
```

Разные сервисы могут временно использовать разные совместимые версии.

Согласованность означает не обязательное равенство версий, а совместимость контрактов.

## 12. Buf и `.venv`

Ошибка:

```text
.venv/.../grpc_tools/_proto/google/protobuf/descriptor.proto
```

означает, что модулем случайно объявлен весь корень проекта.

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

Лучше хранить схемы в отдельном каталоге `proto/`.

## 13. Минимальная структура

```text
project/
├── proto/
│   └── demo/
│       └── v1/
│           └── user.proto
├── generated/
├── src/
├── buf.yaml
└── buf.gen.yaml
```

`buf.yaml`:

```yaml
version: v2

modules:
  - path: proto

lint:
  use:
    - STANDARD

breaking:
  use:
    - FILE
```

`buf.gen.yaml`:

```yaml
version: v2

plugins:
  - protoc_builtin: python
    out: generated
```

Команды:

```bash
buf lint
buf generate
```
