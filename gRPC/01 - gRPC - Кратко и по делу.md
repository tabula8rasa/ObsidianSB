## Что такое gRPC

gRPC — framework для удалённого вызова методов между приложениями.

Вместо мышления:

```text
POST /users/123
```

можно мыслить:

```text
UserService.GetUser(...)
```

Но физически это всё равно сеть:

```text
Python method call
      ↓
gRPC
      ↓
HTTP/2
      ↓
TCP
      ↓
другой процесс
```

gRPC не превращает удалённый вызов в обычный локальный вызов. Между клиентом и сервером остаются сеть, задержка, disconnect, deadline, retry, serialization и частичные ошибки.

---

## Минимальный `.proto`

```proto
syntax = "proto3";

message HelloRequest {
  string name = 1;
}

message HelloReply {
  string message = 1;
}

service Greeter {
  rpc SayHello(HelloRequest) returns (HelloReply);
}
```

Генерация Python-кода:

```bash
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --pyi_out=. \
  --grpc_python_out=. \
  service.proto
```

Получаем:

```text
service.proto
service_pb2.py
service_pb2.pyi
service_pb2_grpc.py
```

---

## Минимальный сервер

```python
import asyncio
import grpc

import service_pb2
import service_pb2_grpc


class Greeter(service_pb2_grpc.GreeterServicer):
    async def SayHello(self, request, context):
        return service_pb2.HelloReply(
            message=f"Hello, {request.name}!"
        )


async def serve():
    server = grpc.aio.server()

    service_pb2_grpc.add_GreeterServicer_to_server(
        Greeter(),
        server,
    )

    server.add_insecure_port("[::]:50051")

    await server.start()
    await server.wait_for_termination()


asyncio.run(serve())
```

---

## Минимальный клиент

```python
import asyncio
import grpc

import service_pb2
import service_pb2_grpc


async def run():
    async with grpc.aio.insecure_channel(
        "localhost:50051"
    ) as channel:
        stub = service_pb2_grpc.GreeterStub(channel)

        response = await stub.SayHello(
            service_pb2.HelloRequest(name="Ilya")
        )

        print(response.message)


asyncio.run(run())
```

---

## Что происходит при вызове

```python
response = await stub.SayHello(request)
```

Логически:

```text
HelloRequest
     ↓
SerializeToString()
     ↓
gRPC framing
     ↓
HTTP/2 stream
     ↓
TCP
     ↓
server
     ↓
routing by RPC method
     ↓
HelloRequest.FromString()
     ↓
Greeter.SayHello(request, context)
     ↓
HelloReply
     ↓
SerializeToString()
     ↓
HTTP/2 / TCP
     ↓
HelloReply.FromString()
     ↓
response
```

---

## Четыре типа RPC

```text
Unary
1 request → 1 response

Client streaming
N requests → 1 response

Server streaming
1 request → N responses

Bidirectional streaming
N requests ↔ N responses
```

См. [[05 - gRPC - Четыре типа RPC и streaming]].

---

## Что важно помнить

`Channel` — клиентская транспортная абстракция. Он может управлять соединением, reconnect и несколькими RPC.

`Stub` — сгенерированный клиентский API конкретного сервиса.

`Servicer` — серверный интерфейс, который реализует разработчик.

`context` — состояние конкретного RPC на стороне сервера.

Один RPC обычно соответствует одному HTTP/2 stream.

Один TCP connection может одновременно переносить множество HTTP/2 streams.

`await` не означает «отправить запрос». В `grpc.aio` вызов вроде:

```python
call = stub.SayHello(request)
```

уже инициирует RPC. Затем:

```python
response = await call
```

означает «дождаться результата уже инициированного RPC».

---

## Когда использовать gRPC

Хорошо подходит для:

- service-to-service взаимодействия;
- строгих контрактов;
- высокочастотных вызовов;
- streaming;
- polyglot-сервисов;
- внутренних платформенных API.

Не всегда лучший выбор для публичного browser API, где REST/JSON обычно проще для клиентов и debugging.
