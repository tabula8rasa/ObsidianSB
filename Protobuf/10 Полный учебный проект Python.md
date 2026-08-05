---
tags:
  - protobuf
  - python
  - tutorial
---
## 1. Структура

```text
protobuf-demo/
├── .venv/
├── proto/
│   └── demo/
│       └── users/
│           └── v1/
│               └── users.proto
├── generated/
├── src/
│   ├── local_demo.py
│   ├── tcp_client.py
│   └── tcp_server.py
├── buf.yaml
└── buf.gen.yaml
```

## 2. Установка

```bash
python -m venv .venv
source .venv/bin/activate

python -m pip install protobuf grpcio-tools
```

Buf устанавливается отдельно удобным для системы способом.

## 3. Схема

`proto/demo/users/v1/users.proto`:

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

message GetUserRequest {
  int64 user_id = 1;
}

message GetUserResponse {
  User user = 1;
}
```

## 4. Buf configuration

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

## 5. Проверка и генерация

```bash
buf lint
buf generate
```

Добавить generated в Python path:

```bash
export PYTHONPATH="$PWD/generated:$PWD/src"
```

Для package imports могут понадобиться `__init__.py` в зависимости от структуры и инструментов проекта.

## 6. Локальная сериализация

`src/local_demo.py`:

```python
from pathlib import Path

from demo.users.v1 import users_pb2


def create_user() -> users_pb2.User:
    return users_pb2.User(
        id=150,
        name="Ann",
        email="ann@example.com",
        status=users_pb2.USER_STATUS_ACTIVE,
        address=users_pb2.Address(
            country="Georgia",
            city="Tbilisi",
        ),
        roles=["user", "operator"],
    )


def main() -> None:
    user = create_user()

    payload = user.SerializeToString()

    print("Объект:")
    print(user)

    print("HEX:")
    print(payload.hex(" "))

    path = Path("user.bin")
    path.write_bytes(payload)

    restored = users_pb2.User.FromString(
        path.read_bytes()
    )

    print("Восстановленный объект:")
    print(restored)


if __name__ == "__main__":
    main()
```

Запуск:

```bash
python src/local_demo.py
```

## 7. TCP server

`src/tcp_server.py`:

```python
import socket
import struct

from google.protobuf.message import DecodeError

from demo.users.v1 import users_pb2


HOST = "127.0.0.1"
PORT = 5000
HEADER_SIZE = 4
MAX_MESSAGE_SIZE = 1_000_000


def recv_exact(
    sock: socket.socket,
    size: int,
) -> bytes:
    chunks: list[bytes] = []
    received = 0

    while received < size:
        chunk = sock.recv(size - received)

        if not chunk:
            raise ConnectionError(
                "Соединение закрыто до получения "
                "всех ожидаемых данных"
            )

        chunks.append(chunk)
        received += len(chunk)

    return b"".join(chunks)


def receive_message(
    sock: socket.socket,
) -> users_pb2.User:
    header = recv_exact(sock, HEADER_SIZE)
    payload_size = struct.unpack("!I", header)[0]

    if payload_size > MAX_MESSAGE_SIZE:
        raise ValueError(
            f"Сообщение слишком большое: "
            f"{payload_size} байт"
        )

    payload = recv_exact(sock, payload_size)

    try:
        return users_pb2.User.FromString(payload)
    except DecodeError as exc:
        raise ValueError(
            "Получен некорректный Protobuf payload"
        ) from exc


def main() -> None:
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as server:
        server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )
        server.bind((HOST, PORT))
        server.listen()

        print(f"Сервер слушает {HOST}:{PORT}")

        connection, address = server.accept()

        with connection:
            print(f"Подключение: {address}")

            user = receive_message(connection)

            print("Получен пользователь:")
            print(user)


if __name__ == "__main__":
    main()
```

## 8. TCP client

`src/tcp_client.py`:

```python
import socket
import struct

from demo.users.v1 import users_pb2


HOST = "127.0.0.1"
PORT = 5000


def send_message(
    sock: socket.socket,
    user: users_pb2.User,
) -> None:
    payload = user.SerializeToString()
    header = struct.pack("!I", len(payload))
    sock.sendall(header + payload)


def main() -> None:
    user = users_pb2.User(
        id=150,
        name="Ann",
        email="ann@example.com",
        status=users_pb2.USER_STATUS_ACTIVE,
        address=users_pb2.Address(
            country="Georgia",
            city="Tbilisi",
        ),
        roles=["user", "operator"],
    )

    with socket.create_connection(
        (HOST, PORT),
        timeout=10,
    ) as sock:
        send_message(sock, user)

    print("Сообщение отправлено")


if __name__ == "__main__":
    main()
```

Запуск сервера:

```bash
python src/tcp_server.py
```

В другом терминале:

```bash
python src/tcp_client.py
```

## 9. Что происходит

```text
users_pb2.User
    ↓ SerializeToString()
payload bytes
    ↓ struct.pack()
4-байтовая длина + payload
    ↓ socket.sendall()
TCP
    ↓ recv_exact()
payload bytes
    ↓ User.FromString()
users_pb2.User
```

## 10. Добавление нового поля

Новая схема:

```proto
message User {
  int64 id = 1;
  string name = 2;
  optional string email = 3;
  UserStatus status = 4;
  Address address = 5;
  repeated string roles = 6;
  optional string telegram = 7;
}
```

Проверка:

```bash
buf lint
buf breaking --against '.git#branch=main'
buf generate
```

Старый получатель продолжит читать поля `1–6`, если изменение совместимо.

## 11. Что улучшить для production

- TLS или mTLS;
- timeouts;
- retries только для безопасных операций;
- логирование;
- metrics;
- ограничение размера;
- authentication;
- authorization;
- версия протокола;
- корреляционный ID;
- обработка нескольких сообщений в одном соединении;
- graceful shutdown;
- тесты совместимости;
- gRPC вместо собственного TCP-протокола, если нужен RPC.
