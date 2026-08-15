---
tags:
  - avro
  - serialization
  - schema
  - kafka
  - data-engineering
aliases:
  - Apache Avro
---
## Кратко

**Apache Avro** — schema-driven система сериализации данных.

Её главная идея:

```text
Schema
  ↓
данные сериализуются без повторения имён полей и типов
  ↓
получается компактный binary payload
  ↓
при чтении используется writer schema
  ↓
при необходимости writer schema сопоставляется с reader schema
```

Самое важное отличие от [[Protocol Buffers]]:

```text
Protobuf
→ каждое поле имеет стабильный numeric field number
→ wire format содержит tag поля

Avro
→ вручную назначаемых field IDs нет
→ binary record хранит значения по структуре schema
→ reader должен знать writer schema
```

Avro особенно хорошо подходит для:

```text
event streams
Kafka
data pipelines
data lake / lakehouse
long-term storage
schema evolution
generic data processing
```

Avro также содержит RPC specification, но основная концептуальная сила технологии — именно schema-driven сериализация и эволюция данных.

---

# 1. Зачем нужен Avro

Представим событие:

```json
{
  "id": 123,
  "name": "Ilya",
  "email": "ilya@example.com"
}
```

Если отправить его как JSON, вместе со значениями каждый раз передаются имена полей:

```text
"id"
"name"
"email"
```

Для миллионов сообщений это повторяющийся overhead.

Avro говорит:

> Давайте договоримся о schema отдельно, а в payload будем хранить в основном сами значения.

Например schema:

```json
{
  "type": "record",
  "name": "User",
  "namespace": "example",
  "fields": [
    {"name": "id", "type": "long"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": ["null", "string"], "default": null}
  ]
}
```

Теперь binary record может быть записан без строк:

```text
"id"
"name"
"email"
```

в каждом объекте.

---

# 2. Главная ментальная модель

Avro нужно понимать через две схемы:

```text
Writer Schema
Reader Schema
```

## Writer Schema

Schema, которой пользовалось приложение, когда сериализовало данные.

## Reader Schema

Schema, которую ожидает приложение, читающее данные сейчас.

Это очень важная идея.

Например:

```text
2025
Writer schema v1
     ↓
сохранили данные

2026
Reader schema v3
     ↓
читаем старые данные
```

Avro умеет разрешать совместимые различия между этими schemas.

---

# 3. Почему schema критична

Avro binary data **не содержит имён полей и полной информации о типах каждого отдельного значения**.

Например schema:

```json
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "long"},
    {"name": "name", "type": "string"}
  ]
}
```

Binary record концептуально выглядит:

```text
[value of id][value of name]
```

а не:

```text
[id][long][123]
[name][string]["Ilya"]
```

Поэтому без schema reader не знает:

```text
первые bytes — это id?
string?
long?
array?
```

---

# 4. Почему это делает Avro компактным

Если у нас миллион записей:

```text
User
User
User
User
...
```

не нужно миллион раз повторять:

```text
id
name
email
```

Schema хранится или согласовывается отдельно.

Таким образом:

```text
schema overhead
```

амортизируется на большой объём данных.

---

# 5. Где хранится schema

Зависит от способа использования Avro.

## Object Container File

В `.avro` файле writer schema хранится в header файла.

```text
Avro file
├── header
│   ├── magic
│   ├── metadata
│   │   └── avro.schema
│   └── sync marker
│
└── data blocks
```

## RPC

Client и server могут согласовать protocol/schema во время handshake.

## Event streaming

При передаче отдельных сообщений schema должна быть доступна reader каким-то согласованным способом.

Типичная архитектурная идея:

```text
message
  ↓
schema identifier / fingerprint
  ↓
Schema Registry
  ↓
writer schema
  ↓
deserialize
```

Важно:

```text
Schema Registry — не обязательная часть core Avro specification.
```

Это отдельный компонент инфраструктуры.

---

# 6. Avro Schema

Основной формат схемы — JSON.

Файлы часто имеют расширение:

```text
.avsc
```

Пример:

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": "long"
    },
    {
      "name": "name",
      "type": "string"
    }
  ]
}
```

---

# 7. Primitive types

Основные primitive types:

```text
null
boolean
int
long
float
double
bytes
string
```

## int

32-bit signed integer.

## long

64-bit signed integer.

## bytes

Произвольные bytes.

## string

Unicode string, binary encoding использует UTF-8.

---

# 8. Complex types

Avro поддерживает:

```text
record
enum
array
map
union
fixed
```

---

# 9. record

Главный структурированный тип.

```json
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "long"},
    {"name": "name", "type": "string"}
  ]
}
```

По смыслу это аналог:

```protobuf
message User {
    int64 id = 1;
    string name = 2;
}
```

или:

```thrift
struct User {
    1: i64 id,
    2: string name
}
```

Но Avro **не использует numeric field IDs**.

---

# 10. enum

```json
{
  "type": "enum",
  "name": "Status",
  "symbols": [
    "ACTIVE",
    "BLOCKED",
    "DELETED"
  ]
}
```

В binary формате enum сериализуется через позицию символа в schema.

---

# 11. array

```json
{
  "type": "array",
  "items": "string"
}
```

Использование:

```json
{
  "name": "roles",
  "type": {
    "type": "array",
    "items": "string"
  }
}
```

---

# 12. map

```json
{
  "type": "map",
  "values": "string"
}
```

Avro map имеет string keys.

Пример:

```json
{
  "name": "metadata",
  "type": {
    "type": "map",
    "values": "string"
  }
}
```

---

# 13. union

Union описывается массивом schemas:

```json
["null", "string"]
```

Это означает:

```text
значение может быть null
ИЛИ
string
```

В Avro именно union обычно используется для nullable fields.

Например:

```json
{
  "name": "email",
  "type": ["null", "string"],
  "default": null
}
```

---

# 14. Nullable в Avro

Это важно, потому что синтаксис отличается от Protobuf.

Avro:

```json
{
  "name": "email",
  "type": ["null", "string"],
  "default": null
}
```

Protobuf:

```protobuf
optional string email = 3;
```

То есть в Avro nullable является union:

```text
null | string
```

---

# 15. fixed

`fixed` описывает байтовое значение фиксированной длины.

Например:

```json
{
  "type": "fixed",
  "name": "Md5",
  "size": 16
}
```

Это может быть полезно для:

```text
hash
fixed-size identifiers
binary keys
```

---

# 16. Logical Types

Avro имеет logical types.

Они накладывают логический смысл на primitive storage representation.

Например date:

```json
{
  "type": "int",
  "logicalType": "date"
}
```

Физически:

```text
int
```

Логически:

```text
calendar date
```

Avro определяет logical types для таких концепций, как:

```text
decimal
uuid
date
time
timestamp
local timestamp
duration
```

---

# 17. Пример полноценной schema

`user.avsc`:

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example.users",
  "fields": [
    {
      "name": "id",
      "type": "long"
    },
    {
      "name": "name",
      "type": "string"
    },
    {
      "name": "email",
      "type": ["null", "string"],
      "default": null
    },
    {
      "name": "roles",
      "type": {
        "type": "array",
        "items": "string"
      },
      "default": []
    },
    {
      "name": "created_at",
      "type": {
        "type": "long",
        "logicalType": "timestamp-millis"
      }
    }
  ]
}
```

---

# 18. Важное отличие: code generation не обязателен

Это одна из самых характерных особенностей Avro.

Protobuf workflow обычно выглядит:

```text
.proto
  ↓
protoc
  ↓
generated class
  ↓
serialize()
```

Avro может работать так:

```text
.avsc
 ↓
runtime schema parser
 ↓
Python dict
 ↓
DatumWriter
 ↓
binary
```

То есть Python-приложению необязательно иметь generated `User` class.

---

# 19. Почему это удобно для dynamic languages

В Python можно представить record обычным словарём:

```python
user = {
    "id": 1,
    "name": "Ilya",
    "email": None,
}
```

Schema проверяет и определяет, как сериализовать этот dict.

Это делает Avro удобным для generic data systems.

Например один pipeline может читать множество разных schemas без компиляции отдельного Python-класса для каждого record type.

---

# 20. Python installation

Официальная Python library:

```bash
pip install avro
```

Импорт:

```python
import avro.schema
```

---

# 21. Python serialization в Avro file

Schema:

```json
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "long"},
    {"name": "name", "type": "string"},
    {
      "name": "email",
      "type": ["null", "string"],
      "default": null
    }
  ]
}
```

Python:

```python
import avro.schema

from avro.datafile import (
    DataFileWriter,
    DataFileReader,
)

from avro.io import (
    DatumWriter,
    DatumReader,
)


schema = avro.schema.parse(
    open("user.avsc", "rb").read()
)


with open("users.avro", "wb") as file:
    writer = DataFileWriter(
        file,
        DatumWriter(),
        schema,
    )

    writer.append({
        "id": 1,
        "name": "Ilya",
        "email": "ilya@example.com",
    })

    writer.append({
        "id": 2,
        "name": "Alice",
        "email": None,
    })

    writer.close()
```

---

# 22. Что делает DataFileWriter

Архитектура:

```text
Python dict
    ↓
DatumWriter
    ↓
Avro binary encoding
    ↓
DataFileWriter
    ↓
Avro Object Container File
```

`DatumWriter` отвечает за сериализацию datum согласно schema.

`DataFileWriter` добавляет файловый контейнер:

```text
schema
metadata
sync markers
blocks
compression
```

---

# 23. Чтение

```python
from avro.datafile import DataFileReader
from avro.io import DatumReader


with open("users.avro", "rb") as file:
    reader = DataFileReader(
        file,
        DatumReader(),
    )

    for user in reader:
        print(user)

    reader.close()
```

Получаем Python dict:

```python
{
    "id": 1,
    "name": "Ilya",
    "email": "ilya@example.com"
}
```

---

# 24. Object Container File

Avro определяет собственный container file format.

Обычно:

```text
*.avro
```

Структура:

```text
Header
  ↓
Data Block
  ↓
Sync Marker
  ↓
Data Block
  ↓
Sync Marker
  ↓
...
```

---

# 25. Header

Header содержит:

```text
Magic
Metadata
Sync Marker
```

Magic bytes:

```text
Obj\x01
```

Metadata включает:

```text
avro.schema
avro.codec
```

То есть schema действительно находится внутри Avro Object Container File.

---

# 26. Data blocks

Каждый data block содержит:

```text
record count
block size
serialized records
sync marker
```

Упрощённо:

```text
[count]
[size]
[data data data ...]
[sync]
```

---

# 27. Зачем нужны blocks

Blocks позволяют:

```text
batch processing
compression
splitting
parallel reading
```

Это особенно удобно для data processing systems.

---

# 28. Compression

Object Container File поддерживает codec на уровне blocks.

Базовые/поддерживаемые implementations могут использовать codecs вроде:

```text
null
deflate
snappy
bzip2
xz
zstandard
```

Конкретная доступность зависит от реализации и установленных зависимостей.

---

# 29. Sync marker

Header содержит случайный 16-byte sync marker.

Между blocks он повторяется:

```text
block
sync
block
sync
```

Это позволяет reader находить границы blocks.

Полезно для:

```text
splitting files
parallel processing
recovery/resynchronization
```

---

# 30. Как выглядит binary encoding

Это один из самых важных моментов.

Для record:

```json
{
  "type": "record",
  "name": "Test",
  "fields": [
    {"name": "a", "type": "long"},
    {"name": "b", "type": "string"}
  ]
}
```

значение:

```json
{
  "a": 27,
  "b": "foo"
}
```

кодируется просто как последовательность encodings полей:

```text
a
+
b
```

без:

```text
"a"
"b"
```

и без field separators.

---

# 31. Field order имеет значение в writer schema

Record сериализуется:

```text
в порядке объявления полей schema
```

Например:

```json
[
  {"name": "a", "type": "long"},
  {"name": "b", "type": "string"}
]
```

значит binary:

```text
encode(a)
encode(b)
```

Поэтому для чтения требуется writer schema.

---

# 32. int и long

Avro использует variable-length zig-zag encoding для:

```text
int
long
```

Пример концепции zig-zag:

```text
0  → 0
-1 → 1
1  → 2
-2 → 3
2  → 4
```

После этого значение кодируется variable-length integer.

Это делает маленькие по абсолютному значению числа компактными.

---

# 33. string

String кодируется как:

```text
length
+
UTF-8 bytes
```

Например:

```text
"foo"
```

содержит 3 UTF-8 bytes.

Avro сначала кодирует длину, затем:

```text
66 6f 6f
```

---

# 34. Arrays и Maps кодируются блоками

Avro arrays/maps не обязательно требуют заранее буферизовать всю коллекцию.

Они представлены последовательностью blocks.

Концептуально:

```text
count
items...

count
items...

0
```

`0` означает конец.

Это позволяет работать с большими коллекциями потоково.

---

# 35. Union encoding

Для:

```json
["null", "string"]
```

Avro сначала пишет индекс выбранной branch.

```text
0 → null
1 → string
```

После индекса пишется само значение выбранного типа.

---

# 36. Single-object encoding

Иногда нужно хранить не целый `.avro` container file, а **один Avro record**.

Например:

```text
Kafka message
database value
cache entry
```

Avro specification определяет single-object encoding:

```text
2-byte marker
+
8-byte schema fingerprint
+
binary Avro object
```

Marker:

```text
C3 01
```

Далее:

```text
CRC-64-AVRO schema fingerprint
```

Затем сам binary object.

---

# 37. Зачем нужен schema fingerprint

Если payload не содержит полную schema, можно передать небольшой идентификатор schema.

Упрощённо:

```text
message
├── schema fingerprint
└── binary data
```

Reader:

```text
fingerprint
   ↓
найти writer schema
   ↓
deserialize payload
```

Это одна из моделей, хорошо подходящих для persistent message systems.

---

# 38. Schema Registry

Schema Registry концептуально решает:

```text
какой schema соответствует этому message?
```

Архитектура:

```text
Producer
   ↓
schema registered
   ↓
Schema Registry
   ↓
schema id/fingerprint
   ↓
message broker
   ↓
Consumer
   ↓
resolve schema
```

Но важно разделять:

```text
Apache Avro
```

и:

```text
Schema Registry product/protocol
```

Schema Registry — внешняя инфраструктура, а не обязательный компонент Avro runtime.

---

# 39. Avro и Kafka

Avro логично использовать для Kafka events, потому что:

```text
Kafka хранит bytes
Avro даёт schema + binary serialization
```

Архитектурно:

```text
Python object
    ↓
Avro serializer
    ↓
bytes
    ↓
Kafka Producer
    ↓
Kafka topic
    ↓
Kafka Consumer
    ↓
Avro deserializer
    ↓
Python object
```

Kafka сам по себе не понимает:

```text
Avro
Protobuf
JSON
```

Для Kafka payload — просто bytes.

---

# 40. Writer Schema

Допустим producer использовал:

```json
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "long"},
    {"name": "name", "type": "string"}
  ]
}
```

Это:

```text
writer schema
```

Binary data физически соответствует именно ей.

---

# 41. Reader Schema

Позже consumer обновился:

```json
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "long"},
    {"name": "name", "type": "string"},
    {
      "name": "email",
      "type": ["null", "string"],
      "default": null
    }
  ]
}
```

Это:

```text
reader schema
```

Reader хочет получить более современную структуру.

---

# 42. Schema Resolution

Avro сравнивает:

```text
writer schema
       ↕
reader schema
```

и определяет, можно ли преобразовать старые данные в новую модель.

Это фундаментальный механизм Avro schema evolution.

---

# 43. Добавление поля с default

Writer:

```json
{
  "name": "User",
  "type": "record",
  "fields": [
    {"name": "id", "type": "long"}
  ]
}
```

Reader:

```json
{
  "name": "User",
  "type": "record",
  "fields": [
    {"name": "id", "type": "long"},
    {
      "name": "email",
      "type": ["null", "string"],
      "default": null
    }
  ]
}
```

В старых данных `email` нет.

Reader использует:

```text
default = null
```

Получается:

```python
{
    "id": 1,
    "email": None
}
```

---

# 44. Добавление поля без default

Если reader ожидает новое поле:

```json
{
  "name": "email",
  "type": "string"
}
```

но:

```text
writer schema этого поля не содержит
```

и:

```text
default отсутствует
```

schema resolution заканчивается ошибкой.

Поэтому default values очень важны для evolution.

---

# 45. Удаление поля

Writer schema:

```text
id
name
email
```

Reader schema:

```text
id
name
```

Reader просто игнорирует writer field, которого нет в reader schema.

Это делает удаление полей в reader относительно естественным.

---

# 46. Поля сопоставляются по именам

При schema resolution record fields сопоставляются:

```text
по name
```

а не по позиции.

Это кажется странным, потому что binary record записан по writer order.

Но reader имеет writer schema, поэтому он знает:

```text
какое значение writer положил на какой позиции.
```

Затем writer fields можно сопоставить с reader fields по именам.

---

# 47. Порядок полей reader может отличаться

Writer:

```text
id
name
email
```

Reader:

```text
email
id
name
```

Schema resolution способен сопоставлять fields по name.

Но writer schema всё равно нужна, чтобы правильно разобрать binary sequence.

---

# 48. Aliases

Avro поддерживает aliases.

Было:

```json
{
  "name": "name",
  "type": "string"
}
```

Хотим переименовать в:

```text
full_name
```

Можно использовать:

```json
{
  "name": "full_name",
  "type": "string",
  "aliases": ["name"]
}
```

Это позволяет reader сопоставить старое имя с новым.

---

# 49. Type promotion

Avro разрешает некоторые promotions writer → reader:

```text
int → long
int → float
int → double

long → float
long → double

float → double

string → bytes
bytes → string
```

Пример:

Writer:

```json
{"name": "count", "type": "int"}
```

Reader:

```json
{"name": "count", "type": "long"}
```

совместим по правилам promotion.

Обратное:

```text
long → int
```

не является безопасным promotion.

---

# 50. Enum evolution

Если writer использовал symbol:

```text
BLOCKED
```

а reader enum его больше не знает, reader может использовать enum default, если он определён.

Иначе возникает ошибка schema resolution.

---

# 51. Почему в Avro нет field numbers

Это одно из фундаментальных отличий от Protobuf и Thrift.

Protobuf:

```protobuf
string name = 2;
```

Thrift:

```thrift
2: string name
```

Avro:

```json
{
  "name": "name",
  "type": "string"
}
```

Почему?

Потому что Avro предполагает наличие writer schema при чтении.

Поэтому reader может понять структуру data через schema, а при schema evolution сопоставлять поля по names.

---

# 52. Avro vs Protocol Buffers: фундаментальная разница

## Protobuf

Message:

```protobuf
message User {
    int64 id = 1;
    string name = 2;
}
```

Wire data концептуально:

```text
field 1 tag
value

field 2 tag
value
```

Reader может:

```text
увидеть неизвестный field number
→ определить wire type
→ пропустить field
```

---

# 53. Avro

Schema:

```json
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "long"},
    {"name": "name", "type": "string"}
  ]
}
```

Binary:

```text
value(id)
value(name)
```

без field tags.

Reader:

```text
должен иметь writer schema
```

чтобы правильно пройти payload.

---

# 54. Почему Protobuf не требует writer schema рядом с каждым message

Generated Protobuf class уже знает:

```text
field 1 = id
field 2 = name
```

И wire payload содержит numeric tags.

Если появился unknown field:

```text
field 7
```

старый parser может пропустить его благодаря wire type.

---

# 55. Почему Avro требует writer schema

Потому что binary data не содержит tags.

Если bytes означают:

```text
27
foo
```

без schema невозможно надёжно знать:

```text
27 = long?
enum?
array block count?

foo = string?
bytes?
```

---

# 56. Размер данных

Avro может быть очень компактным именно потому, что record не повторяет field tags.

Но реальный размер зависит от:

```text
schema
data distribution
message size
compression
container format
protobuf field numbers
types
```

Поэтому нельзя утверждать:

```text
Avro всегда меньше Protobuf
```

или наоборот.

Нужно benchmark-ить конкретный payload.

---

# 57. Code generation

## Protobuf

Code generation является центральной частью обычного workflow:

```text
.proto
 ↓
protoc
 ↓
user_pb2.py
 ↓
User(...)
```

## Avro

Можно работать dynamic:

```text
.avsc
 ↓
schema.parse()
 ↓
dict
 ↓
DatumWriter
```

Code generation возможен в некоторых language implementations, особенно для statically typed languages, но не является обязательной основой формата.

---

# 58. Generic processing

Это важное преимущество Avro.

Можно построить generic tool:

```text
получить schema
      ↓
получить record
      ↓
прочитать fields runtime-способом
```

без заранее сгенерированного конкретного класса.

Это особенно удобно в:

```text
ETL
data platforms
schema registries
stream processing
data lake tooling
```

---

# 59. Protobuf тоже может быть dynamic

Важно не создавать ложное противопоставление.

Protobuf имеет:

```text
descriptors
reflection
dynamic messages
```

То есть dynamic processing возможно.

Но основной ergonomic workflow Protobuf гораздо сильнее ориентирован на:

```text
.proto → generated language classes
```

У Avro schema-at-runtime является более центральной идеей дизайна.

---

# 60. Avro vs gRPC

Здесь важно сначала разделить уровни.

```text
Avro
→ serialization/data format
→ container files
→ schema evolution
→ также имеет RPC specification

gRPC
→ RPC framework
→ transport/lifecycle/status/deadlines/streaming
→ обычно использует Protobuf
```

То есть сравнение не полностью симметричное.

---

# 61. Типичный gRPC stack

```text
.proto
   ↓
Protobuf messages
   ↓
gRPC generated stub
   ↓
gRPC runtime
   ↓
HTTP/2
   ↓
network
```

---

# 62. Типичный Avro event stack

```text
.avsc
   ↓
Avro serializer
   ↓
binary payload
   ↓
Kafka
   ↓
Avro deserializer
   ↓
reader schema
```

Они решают разные задачи.

---

# 63. Avro RPC существует

Avro specification включает Protocol Declaration.

Пример концептуальной protocol schema:

```json
{
  "protocol": "UserService",
  "namespace": "example",
  "types": [
    {
      "type": "record",
      "name": "User",
      "fields": [
        {"name": "id", "type": "long"},
        {"name": "name", "type": "string"}
      ]
    }
  ],
  "messages": {
    "getUser": {
      "request": [
        {"name": "id", "type": "long"}
      ],
      "response": "User"
    }
  }
}
```

То есть Avro способен описать:

```text
types
+
RPC methods
```

---

# 64. Avro RPC handshake

Avro RPC учитывает необходимость обмена schemas/protocols.

Концептуально:

```text
Client
   ↓
какой protocol/schema я знаю?
   ↓
Server
   ↓
согласование protocol
   ↓
RPC call
```

Schema fingerprints позволяют оптимизировать повторные interactions и не передавать полную schema каждый раз.

---

# 65. Почему Avro RPC не равно gRPC

Даже если оба способны:

```text
remote method call
```

архитектура различается.

gRPC делает RPC своей центральной моделью и предоставляет:

```text
unary
client streaming
server streaming
bidirectional streaming
deadlines
metadata
status model
interceptors
HTTP/2 transport semantics
```

Avro RPC является частью Avro specification, но сама технология Avro гораздо шире ориентирована на данные и serialization.

---

# 66. Avro vs Thrift

См. [[Apache Thrift]].

Thrift:

```text
IDL
generated code
RPC client
Processor
Protocol
Transport
Server
```

Avro:

```text
Schema
binary encoding
reader/writer schema resolution
container files
optional code generation
RPC specification
```

Очень грубо:

```text
Thrift → service-oriented

Avro → data-oriented
```

---

# 67. Schema evolution: Protobuf vs Avro

## Protobuf

Главная identity поля:

```text
field number
```

Например:

```protobuf
string email = 3;
```

Можно переименовать source-level поле, не меняя wire ID:

```protobuf
string contact_email = 3;
```

Binary identity всё ещё:

```text
3
```

Удалённые номера нужно резервировать и не переиспользовать.

---

# 68. Avro

Identity record field при resolution основана на:

```text
field name
aliases
writer schema
reader schema
```

Ручного numeric field number нет.

Поэтому rename требует учитывать aliases/compatibility.

---

# 69. Unknown fields

## Protobuf

Unknown field присутствует непосредственно в payload как:

```text
tag + wire value
```

Старый parser может пропустить его.

## Avro

Reader понимает неизвестное writer field благодаря:

```text
writer schema
```

Если reader schema не содержит это field:

```text
writer value игнорируется
```

---

# 70. Default values

В Avro default используется прежде всего при **чтении**, когда reader schema имеет поле, которого не было у writer.

Это важное отличие от распространённой интуиции:

```text
default не означает:
"поле вообще не будет сериализовано, если равно default"
```

Avro binary encoding всё равно кодирует поле согласно writer schema.

---

# 71. Avro default и nullable

Очень распространённый шаблон:

```json
{
  "name": "email",
  "type": ["null", "string"],
  "default": null
}
```

Это обеспечивает удобный migration path:

```text
старые records без email
      ↓
новый reader
      ↓
email = null
```

---

# 72. Schema compatibility

В production часто вводят правила:

```text
BACKWARD
FORWARD
FULL
```

Это удобные operational concepts, часто реализуемые schema registry systems.

Но нужно отличать их от core Avro schema resolution rules.

Core Avro определяет, как:

```text
writer schema
```

сопоставляется с:

```text
reader schema
```

А registry уже может проверять набор версий согласно выбранной policy.

---

# 73. Backward compatibility — интуитивно

Новая версия reader может читать старые данные.

```text
old writer
   ↓
old data
   ↓
new reader
```

Типичный пример:

```text
добавили новое поле с default
```

---

# 74. Forward compatibility — интуитивно

Старый reader способен читать данные нового writer.

```text
new writer
   ↓
new data
   ↓
old reader
```

Например новый writer добавил поле, которое старый reader может просто игнорировать.

---

# 75. Full compatibility

Обе стороны:

```text
old ↔ new
```

должны быть совместимы.

Это сильнее ограничивает допустимые изменения.

---

# 76. Почему Avro хорош для long-lived data

Представим Kafka topic:

```text
2024 messages schema v1
2025 messages schema v2
2026 messages schema v4
```

Consumer 2026 года может встретить records разных версий.

Schema-aware architecture позволяет:

```text
message
 ↓
writer schema version
 ↓
reader schema
 ↓
schema resolution
 ↓
current object
```

Это очень естественная модель для event history.

---

# 77. Avro Object Container File vs Protobuf file

Avro определяет стандартный файл:

```text
schema
metadata
blocks
compression
sync markers
records
```

У Protobuf есть wire format сообщений, но нет аналогичного универсального стандартного multi-record container file, эквивалентного Avro Object Container File.

Если нужно хранить много protobuf messages в файле, framing/container обычно проектируется отдельно или предоставляется другой системой.

---

# 78. Avro и data lake

Avro files удобны для row-oriented serialized records.

Но в аналитических lakehouse workloads часто встречаются также columnar formats:

```text
Parquet
ORC
```

Очень грубо:

```text
Avro
→ row-oriented serialization/events

Parquet
→ column-oriented analytics
```

При этом Avro schemas и Avro events могут быть upstream-источником данных, которые позднее записываются в Parquet/Iceberg tables.

---

# 79. Avro vs JSON

JSON:

```json
{
  "id": 1,
  "name": "Ilya"
}
```

Плюсы:

```text
human-readable
простая отладка
широчайшая поддержка
```

Минусы:

```text
имена полей повторяются
типы слабее
больше payload
schema обычно отдельно
```

Avro:

```text
binary
schema-driven
compact
stronger evolution model
```

---

# 80. Avro vs Protobuf vs JSON

| Свойство | Avro | Protobuf | JSON |
|---|---|---|---|
| Binary | Да | Да | Нет |
| Schema | Да | Да | Не обязательно |
| Field IDs | Нет | Да | Нет |
| Field names в обычном binary payload | Нет | Нет | Да |
| Codegen обязателен концептуально | Нет | Обычно используется | Нет |
| Schema evolution | Writer/Reader resolution | Field numbers + wire compatibility | Вручную/по convention |
| Standard container file | Да | Нет аналогичного core container | Обычные text files |
| Human readable | Нет | Нет | Да |
| Generic runtime processing | Сильная сторона | Возможно через descriptors | Просто |

---

# 81. Avro vs Protobuf — короткий пример

## Protobuf schema

```protobuf
message User {
    int64 id = 1;
    string name = 2;
}
```

Payload concept:

```text
[tag 1][id]
[tag 2][name]
```

## Avro schema

```json
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "long"},
    {"name": "name", "type": "string"}
  ]
}
```

Payload concept:

```text
[id][name]
```

Поэтому:

```text
Protobuf понимает границы через tags/wire types.

Avro понимает их через writer schema.
```

---

# 82. Где Avro schema находится при Kafka

Core Avro не говорит:

```text
Kafka должен обязательно использовать такой-то registry.
```

Есть несколько возможных approaches:

```text
schema inside envelope
schema fingerprint
schema ID
topic-level external agreement
registry lookup
```

В production часто используется external Schema Registry, чтобы не передавать полную schema в каждом Kafka message.

---

# 83. Почему нельзя просто отправить Avro bytes без договора о schema

Если producer сделал:

```python
serialize(user, schema_v3)
```

а consumer имеет только:

```text
schema_v1
```

и не знает writer schema, он не может надёжно интерпретировать untagged payload.

Поэтому transport contract должен гарантировать доступность writer schema.

---

# 84. Data contract vs service contract

Очень полезное различие.

## Data contract

```text
Что означает событие UserCreated?
Какие у него fields?
Как оно развивается со временем?
```

Avro очень силён здесь.

## Service contract

```text
Какие RPC методы предоставляет UserService?
Как вызвать GetUser?
Какие deadlines/status/streaming?
```

gRPC больше ориентирован сюда.

---

# 85. Когда выбирать Avro

Avro особенно логичен, когда:

```text
данные живут дольше процесса, который их записал
есть много producer/consumer versions
нужна schema evolution
нужна Kafka/event architecture
нужно generic processing
нужно хранить schema вместе с data file
нужен compact binary format
```

---

# 86. Когда выбирать Protobuf

Protobuf часто удобнее для:

```text
API messages
RPC payloads
mobile/backend communication
generated strongly typed SDKs
messages небольшого/среднего размера
когда numeric tag evolution удобнее
```

---

# 87. Когда выбирать gRPC

gRPC выбирают, когда задача именно:

```text
service-to-service RPC
```

и важны:

```text
unary calls
streaming
deadlines
metadata
status codes
HTTP/2
generated stubs
```

Чаще всего payload при этом описывают Protobuf.

---

# 88. Можно ли использовать Avro с gRPC

Концептуально gRPC допускает другие serialization mechanisms, но типичная и наиболее стандартная экосистема gRPC использует Protocol Buffers.

Поэтому связка:

```text
gRPC + Protobuf
```

является более естественной моделью, чем:

```text
gRPC + Avro
```

Если основной data contract уже Avro, часто разумно оставить Avro на уровне events/storage, а service RPC делать отдельным gRPC contract.

---

# 89. Можно ли использовать Protobuf с Kafka

Да.

Kafka видит:

```text
bytes
```

Поэтому payload может быть:

```text
JSON
Avro
Protobuf
MessagePack
custom format
```

Avro не является обязательным для Kafka.

Выбор зависит от:

```text
schema evolution
tooling
ecosystem
data processing
consumer languages
governance
```

---

# 90. Частая архитектура

Например:

```text
User Service
    │
    ├── gRPC + Protobuf
    │      ↓
    │  синхронный RPC
    │
    └── Kafka + Avro
           ↓
       асинхронные events
```

Это не конфликт технологий.

Они решают разные задачи.

---

# 91. Полная архитектурная модель Avro

```text
                 Schema
                   │
                   ▼
          ┌─────────────────┐
          │ Avro Serializer │
          └─────────────────┘
                   │
                   ▼
             Binary Data
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
    Avro File    Kafka      RPC
        │          │          │
        ▼          ▼          ▼
 writer schema  schema ID   handshake
        │          │          │
        └──────────┼──────────┘
                   ▼
          Avro Deserializer
                   │
       Writer Schema + Reader Schema
                   │
                   ▼
           Schema Resolution
                   │
                   ▼
               Object
```

---

# 92. Самое важное отличие от Protobuf одним предложением

```text
Protobuf кладёт identity полей в payload через numeric tags.

Avro выносит знание структуры в writer schema и поэтому может не писать field tags в каждый binary record.
```

---

# 93. Самое важное отличие от gRPC одним предложением

```text
Avro в первую очередь определяет, как описывать, сериализовать, хранить и эволюционировать данные.

gRPC в первую очередь определяет, как вызывать удалённые методы между сервисами.
```

---

# 94. Что надо запомнить

Если забыть все детали, оставь эту схему:

```text
            AVRO

Writer Object
     ↓
Writer Schema
     ↓
Binary Encoder
     ↓
bytes
     ↓
file / Kafka / transport
     ↓
bytes
     ↓
Writer Schema
     +
Reader Schema
     ↓
Schema Resolution
     ↓
Reader Object
```

---

# 95. Сравнительная таблица

| Свойство | Avro | Protobuf | gRPC | Thrift |
|---|---|---|---|---|
| Основная задача | Serialization/data contracts | Serialization/messages | RPC | Serialization + RPC |
| Schema/IDL | JSON schema / IDL | `.proto` | Обычно `.proto` | `.thrift` |
| Numeric field IDs | Нет | Да | Через Protobuf | Да |
| Writer schema нужна при decode | Да | Обычно decoder знает schema через generated type/descriptor | Через Protobuf types | Нет в Avro-смысле |
| Code generation | Не обязателен | Центральный обычный workflow | Обычно используется для stubs | Центральный workflow |
| Standard data file | Да | Нет | Нет | Не основная задача |
| RPC | Есть specification | Нет | Да | Да |
| Streaming RPC | Не главная модель | Не относится | Да | Не главная классическая модель |
| Schema evolution | Writer/Reader resolution | Stable field numbers | Через message format | Stable field IDs/requiredness |
| Kafka suitability | Очень естественная | Тоже подходит | Не Kafka format | Возможно, но не основная специализация |

---

# 96. Связанные заметки

- [[Protocol Buffers]]
- [[gRPC]]
- [[Apache Thrift]]
- [[Kafka]]
- [[Schema Registry]]
- [[Сериализация данных]]
- [[Parquet]]
- [[Apache Iceberg]]

---

# Источники

Официальная документация Apache Avro:

- Apache Avro 1.12.0 Documentation  
  https://avro.apache.org/docs/1.12.0/

- Apache Avro Specification  
  https://avro.apache.org/docs/1.12.0/specification/

- Apache Avro Python API  
  https://avro.apache.org/docs/1.12.0/api-py/

- Apache Avro — Getting Started (Python)  
  https://avro.apache.org/docs/1.11.4/getting-started-python/

Для сравнения:

- Protocol Buffers — Overview  
  https://protobuf.dev/overview/

- Protocol Buffers — Encoding  
  https://protobuf.dev/programming-guides/encoding/

- Protocol Buffers — Updating Message Types / Field Numbers  
  https://protobuf.dev/programming-guides/proto3/

- gRPC — Introduction  
  https://grpc.io/docs/what-is-grpc/introduction/

- gRPC — Core Concepts  
  https://grpc.io/docs/what-is-grpc/core-concepts/
