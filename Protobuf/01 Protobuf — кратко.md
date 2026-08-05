---
tags:
  - protobuf
  - cheatsheet
  - python
aliases:
  - Protobuf кратко
---
**Protocol Buffers** — это технология, которая позволяет:

1. описать структуру данных в `.proto`;
2. сгенерировать классы для Python, Java, Go, C++ и других языков;
3. создать объект сообщения;
4. сериализовать его в `bytes`;
5. передать байты через любой транспорт;
6. восстановить объект на другой стороне.

```text
объект → bytes → транспорт → bytes → объект
```

Protobuf сам не открывает соединение и не отправляет данные. Это делают TCP, HTTP, gRPC, Kafka и другие технологии.

## 1. Установка

```bash
python -m pip install protobuf grpcio-tools
```

## 2. Схема `user.proto`

```proto
syntax = "proto3";

package demo.v1;

message User {
  int64 id = 1;
  string name = 2;
  optional string email = 3;
}
```

## 3. Генерация Python-кода

```bash
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  user.proto
```

Появится:

```text
user_pb2.py
```

## 4. Создание и сериализация

```python
import user_pb2

user = user_pb2.User(
    id=1,
    name="Alex",
    email="alex@example.com",
)

payload: bytes = user.SerializeToString()

print(payload)
print(payload.hex(" "))
```

## 5. Десериализация

```python
received_user = user_pb2.User()
received_user.ParseFromString(payload)

print(received_user.id)
print(received_user.name)
print(received_user.email)
```

Можно короче:

```python
received_user = user_pb2.User.FromString(payload)
```

## 6. Передача

```python
sock.sendall(payload)
```

или:

```python
requests.post(
    url,
    data=payload,
    headers={"Content-Type": "application/protobuf"},
)
```

При TCP нужно дополнительно передавать длину сообщения, потому что TCP является потоком байтов и не сохраняет границы сообщений.

## Главная мысль

```text
.proto
  ↓ генерация
класс конкретного языка
  ↓ сериализация
одинаковый бинарный формат
  ↓
другой язык восстанавливает объект
```

Получателю не обязательно иметь буквально тот же файл, но его схема должна быть бинарно совместимой: номера, типы и смысл существующих полей должны совпадать.
