---
tags:
  - protobuf
  - proto
  - schema
---
## 1. Базовая структура файла

```proto
syntax = "proto3";

package company.users.v1;

message User {
  int64 id = 1;
  string name = 2;
  optional string email = 3;
}
```

### `syntax`

```proto
syntax = "proto3";
```

Определяет вариант языка описания. В новых проектах также может использоваться система Editions.

### `package`

```proto
package company.users.v1;
```

Создаёт логическое пространство имён Protobuf:

```text
company.users.v1.User
```

`package` не обязательно равен Python-пакету. Путь Python-модуля главным образом зависит от расположения `.proto` и параметров генерации.

### `message`

```proto
message User {
  ...
}
```

Объявляет тип структурированного сообщения.

## 2. Структура поля

```proto
optional string email = 3 [deprecated = true];
```

```text
optional | string | email | 3 | options
кратность   тип      имя    номер  настройки
```

## 3. Номера полей

```proto
int64 id = 1;
string name = 2;
```

В бинарном сообщении записываются номера, а не имена.

Правила:

- номер уникален внутри одного `message`;
- допустимый диапазон: `1–536870911`;
- диапазон `19000–19999` зарезервирован;
- после публикации номер нельзя менять;
- удалённый номер нельзя использовать повторно;
- часто используемым полям выгодно давать номера `1–15`.

Порядок строк не является частью бинарного контракта:

```proto
message User {
  string name = 2;
  int64 id = 1;
}
```

эквивалентен варианту с `id` выше `name`, если номера не изменены.

## 4. Скалярные типы

| Protobuf | Python | Особенности |
|---|---|---|
| `double` | `float` | 64-битное число с плавающей точкой |
| `float` | `float` | 32-битное число |
| `int32` | `int` | Varint, отрицательные значения неэффективны |
| `int64` | `int` | Varint |
| `uint32` | `int` | Без знака |
| `uint64` | `int` | Без знака |
| `sint32` | `int` | ZigZag, удобно для отрицательных |
| `sint64` | `int` | ZigZag |
| `fixed32` | `int` | Всегда 4 байта |
| `fixed64` | `int` | Всегда 8 байт |
| `sfixed32` | `int` | Знаковое, 4 байта |
| `sfixed64` | `int` | Знаковое, 8 байт |
| `bool` | `bool` | `true` / `false` |
| `string` | `str` | Текст UTF-8 |
| `bytes` | `bytes` | Произвольные бинарные данные |

### Выбор целого типа

```text
в основном небольшие положительные → int32 / int64
только неотрицательные             → uint32 / uint64
часто бывают отрицательные         → sint32 / sint64
обычно очень большие значения      → fixed32 / fixed64
```

## 5. Обычное singular-поле

```proto
string name = 1;
```

Хранит одно значение.

В proto3 обычные scalar-поля используют implicit presence. Нельзя отличить:

```text
поле не передали
```

от:

```text
поле явно передали со значением по умолчанию
```

Например:

```python
user = User()
print(user.name)  # ""
```

## 6. `optional`

```proto
optional string email = 2;
```

Позволяет проверять наличие:

```python
user.HasField("email")
```

Различаются состояния:

```text
email отсутствует
email присутствует и равен ""
```

`optional` стоит использовать, когда отсутствие значения имеет самостоятельный смысл.

## 7. `repeated`

```proto
repeated string roles = 3;
```

Коллекция из нуля или более элементов:

```python
user.roles.append("admin")
user.roles.extend(["operator", "manager"])
```

Для числовых repeated-полей используется компактное packed-кодирование.

## 8. `map`

```proto
map<string, string> attributes = 4;
```

Python:

```python
user.attributes["department"] = "IT"
```

Ограничения ключа:

- целочисленные типы;
- `bool`;
- `string`.

Ключом не может быть сообщение, `float`, `double`, `bytes` или enum.

Порядок элементов `map` не должен использоваться как часть контракта.

## 9. Вложенные сообщения

```proto
message Address {
  string city = 1;
  string street = 2;
}

message User {
  int64 id = 1;
  Address address = 2;
}
```

Python:

```python
user.address.city = "Tbilisi"
```

или:

```python
address = Address(city="Tbilisi")
user.address.CopyFrom(address)
```

## 10. Вложенные типы

```proto
message User {
  message Address {
    string city = 1;
  }

  int64 id = 1;
  Address address = 2;
}
```

Python:

```python
address = user_pb2.User.Address(city="Tbilisi")
```

Если тип используется многими сущностями, его лучше сделать верхнеуровневым.

## 11. `enum`

```proto
enum UserStatus {
  USER_STATUS_UNSPECIFIED = 0;
  USER_STATUS_ACTIVE = 1;
  USER_STATUS_BLOCKED = 2;
}
```

Первое значение должно иметь номер `0`.

```proto
message User {
  UserStatus status = 1;
}
```

Python:

```python
user.status = user_pb2.USER_STATUS_ACTIVE
```

Хорошая практика — использовать префикс имени enum в именах значений.

## 12. `oneof`

```proto
message User {
  oneof contact {
    string email = 1;
    string phone = 2;
  }
}
```

Одновременно установлено только одно поле.

```python
user.email = "a@example.com"
user.phone = "+995..."
```

После установки `phone` поле `email` очистится.

Проверка:

```python
user.WhichOneof("contact")
```

## 13. `reserved`

После удаления поля:

```proto
message User {
  reserved 3;
  reserved "old_login";

  int64 id = 1;
}
```

Диапазоны:

```proto
reserved 4, 7, 10 to 20;
```

Имена и номера резервируются отдельными выражениями.

## 14. Options полей

### `deprecated`

```proto
string old_login = 3 [deprecated = true];
```

Помечает поле устаревшим, но не удаляет и не запрещает его использование.

### `json_name`

```proto
string user_name = 1 [json_name = "username"];
```

Влияет на ProtoJSON, но не на бинарный формат.

### `packed`

```proto
repeated int32 values = 1 [packed = false];
```

Управляет packed-кодированием repeated-чисел. В proto3 оно обычно включено по умолчанию.

### Пользовательские options

```proto
string email = 1 [
  (validate.rules).string.email = true
];
```

Они требуют отдельного описания и инструмента, который понимает эти annotations.

## 15. Значения по умолчанию

| Тип | Значение |
|---|---|
| числа | `0` |
| `bool` | `false` |
| `string` | `""` |
| `bytes` | `b""` |
| enum | элемент с номером `0` |
| repeated | пустой контейнер |
| map | пустая карта |

В proto3 нельзя объявить собственный default:

```proto
int32 retries = 1 [default = 3]; // нельзя
```

Используйте `optional` и задавайте default в прикладном коде.

## 16. Несколько сообщений в одном файле

```proto
message User {
  int64 id = 1;
  string name = 2;
}

message CreateUserRequest {
  string name = 1;
}

message CreateUserResponse {
  User user = 1;
}

message GetUserRequest {
  int64 user_id = 1;
}

message GetUserResponse {
  User user = 1;
}
```

Все классы попадут в один модуль:

```python
users_pb2.User
users_pb2.CreateUserRequest
users_pb2.CreateUserResponse
users_pb2.GetUserRequest
users_pb2.GetUserResponse
```

## 17. Разделение по файлам и импорты

`common.proto`:

```proto
syntax = "proto3";

package company.common.v1;

message Money {
  int64 units = 1;
  int32 nanos = 2;
  string currency_code = 3;
}
```

`orders.proto`:

```proto
syntax = "proto3";

package company.orders.v1;

import "company/common/v1/common.proto";

message Order {
  int64 id = 1;
  company.common.v1.Money total = 2;
}
```

Типы следует группировать по предметным областям, а не складывать всю компанию в один файл.

## 18. Стандартные типы Google

Часто используются:

```proto
import "google/protobuf/timestamp.proto";
import "google/protobuf/duration.proto";
import "google/protobuf/empty.proto";
import "google/protobuf/wrappers.proto";
import "google/protobuf/any.proto";
import "google/protobuf/struct.proto";
```

Пример:

```proto
message User {
  google.protobuf.Timestamp created_at = 1;
}
```
