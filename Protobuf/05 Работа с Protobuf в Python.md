---
tags:
  - protobuf
  - python
  - api
---
## 1. Создание сообщения

```python
import user_pb2

user = user_pb2.User()
user.id = 1
user.name = "Alex"
```

Через конструктор:

```python
user = user_pb2.User(
    id=1,
    name="Alex",
)
```

Неизвестные поля добавить нельзя:

```python
user.unknown_field = 10  # ошибка
```

## 2. Проверка типов

```python
user.id = 10       # нормально
user.id = "10"     # TypeError
user.id = 10**100  # ValueError для int64
```

Protobuf проверяет технический тип и диапазон, но не бизнес-правила:

```python
user.email = "не email"  # допустимая строка
```

Проверку формата email нужно писать отдельно или подключать валидатор.

## 3. Сериализация

```python
payload: bytes = user.SerializeToString()
```

Детерминированный режим:

```python
payload = user.SerializeToString(
    deterministic=True,
)
```

Он не создаёт универсальное каноническое представление для всех языков и версий.

## 4. Десериализация

### В существующий объект

```python
user = user_pb2.User()
user.ParseFromString(payload)
```

`ParseFromString()` очищает прежнее содержимое объекта.

### Создание нового объекта

```python
user = user_pb2.User.FromString(payload)
```

### Объединение с текущими данными

```python
user.MergeFromString(payload)
```

## 5. `CopyFrom()`

Полностью заменяет содержимое:

```python
target.CopyFrom(source)
```

По смыслу:

```text
target.Clear()
target.MergeFrom(source)
```

Особенно полезно для вложенных сообщений:

```python
user.address.CopyFrom(address)
```

## 6. `MergeFrom()`

```python
base.MergeFrom(patch)
```

Правила:

- scalar-поле заменяется установленным значением;
- repeated-поле дополняется;
- вложенное сообщение объединяется рекурсивно;
- активное поле oneof заменяется.

## 7. Очистка

Всё сообщение:

```python
user.Clear()
```

Одно поле:

```python
user.ClearField("email")
```

Группа oneof:

```python
user.ClearField("contact")
```

## 8. Presence и `HasField()`

Схема:

```proto
message User {
  string name = 1;
  optional string email = 2;
  Address address = 3;
}
```

Работает:

```python
user.HasField("email")
user.HasField("address")
```

Не работает для обычного implicit scalar:

```python
user.HasField("name")  # ValueError
```

Не применяется к repeated и map.

## 9. `WhichOneof()`

```python
active = user.WhichOneof("contact")
```

Результат:

```text
"email"
"phone"
None
```

## 10. `ListFields()`

Возвращает установленные поля:

```python
for descriptor, value in user.ListFields():
    print(
        descriptor.name,
        descriptor.number,
        value,
    )
```

Пары имеют вид:

```text
(FieldDescriptor, value)
```

## 11. `ByteSize()`

```python
size = user.ByteSize()
```

Обычно:

```python
size == len(user.SerializeToString())
```

Можно проверять лимит до отправки:

```python
if user.ByteSize() > 1_000_000:
    raise ValueError("Сообщение слишком большое")
```

## 12. Unknown fields

Старый код может прочитать сообщение с новыми неизвестными полями.

Удаление:

```python
user.DiscardUnknownFields()
```

Обычно unknown fields полезно сохранять, чтобы прокси или промежуточный сервис не потерял незнакомые данные.

## 13. `IsInitialized()`

```python
user.IsInitialized()
```

Особенно важно для старых proto2-схем с `required`. Для обычного proto3 обычно возвращает `True`.

## 14. `SetInParent()`

Отмечает пустое вложенное сообщение как присутствующее:

```python
user.settings.SetInParent()
```

После этого:

```python
user.HasField("settings")  # True
```

Редкий метод.

## 15. `DESCRIPTOR`

Свойство класса:

```python
print(user_pb2.User.DESCRIPTOR.full_name)
```

Поля:

```python
for field in user_pb2.User.DESCRIPTOR.fields:
    print(field.name, field.number)
```

По имени:

```python
field = user_pb2.User.DESCRIPTOR.fields_by_name["email"]
```

По номеру:

```python
field = user_pb2.User.DESCRIPTOR.fields_by_number[3]
```

## 16. Repeated scalar

Схема:

```proto
repeated string roles = 1;
```

Python:

```python
user.roles.append("admin")
user.roles.extend(["operator", "manager"])
user.roles.insert(0, "user")
user.roles.remove("operator")
role = user.roles.pop()
user.roles.clear()
del user.roles[0]
```

Контейнер похож на список, но управляется runtime Protobuf.

## 17. Repeated messages

```proto
message Order {
  int64 id = 1;
}

message User {
  repeated Order orders = 1;
}
```

Добавление:

```python
order = user.orders.add()
order.id = 100
```

Сразу с полями:

```python
user.orders.add(id=200)
```

Существующий объект:

```python
source = user_pb2.Order(id=300)
user.orders.append(source)
```

Runtime копирует сообщение, а не просто сохраняет произвольную Python-ссылку.

## 18. Map

```proto
map<string, int32> counters = 1;
```

```python
user.counters["views"] = 10
user.counters.update({
    "likes": 3,
    "comments": 5,
})

for key, value in user.counters.items():
    print(key, value)

del user.counters["likes"]
user.counters.clear()
```

## 19. Вложенные сообщения

```python
user.address.city = "Tbilisi"
```

Замена через обычное присваивание обычно запрещена:

```python
user.address = address  # ошибка
```

Используйте:

```python
user.address.CopyFrom(address)
```

## 20. Enum

```python
user.status = user_pb2.USER_STATUS_ACTIVE
```

Имя значения:

```python
name = user_pb2.UserStatus.Name(user.status)
```

Номер по имени:

```python
value = user_pb2.UserStatus.Value(
    "USER_STATUS_ACTIVE"
)
```

## 21. Преобразование в JSON

```python
from google.protobuf.json_format import (
    MessageToJson,
    Parse,
)

json_text = MessageToJson(user)

restored = user_pb2.User()
Parse(json_text, restored)
```

В словарь:

```python
from google.protobuf.json_format import MessageToDict

data = MessageToDict(user)
```

ProtoJSON имеет собственные правила и не равен произвольному JSON.

Преобразование бинарного сообщения в JSON и обратно может потерять неизвестные поля.

## 22. Text format

Удобен для отладки:

```python
print(user)
```

Явное преобразование:

```python
from google.protobuf import text_format

text = text_format.MessageToString(user)
```

Это не бинарный wire format.

## 23. Основные методы

| Метод | Назначение |
|---|---|
| `SerializeToString()` | сообщение → bytes |
| `ParseFromString()` | очистить и прочитать bytes |
| `FromString()` | создать объект из bytes |
| `MergeFromString()` | объединить с bytes |
| `CopyFrom()` | полностью скопировать сообщение |
| `MergeFrom()` | объединить два сообщения |
| `Clear()` | очистить всё |
| `ClearField()` | очистить поле |
| `HasField()` | проверить presence |
| `WhichOneof()` | узнать активное поле oneof |
| `ListFields()` | получить установленные поля |
| `ByteSize()` | размер бинарного сообщения |
| `DiscardUnknownFields()` | удалить неизвестные поля |
| `IsInitialized()` | проверить required |
| `SetInParent()` | отметить пустое вложенное сообщение |
| `DESCRIPTOR` | получить описание схемы |
