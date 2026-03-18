
Видео-источник: https://www.youtube.com/watch?v=pBASqUbZgkY

---
# Основные типы API

## 1. REST API

REST API можно представить как официанта в ресторане: клиент отправляет запрос, сервер обрабатывает его и возвращает ответ.  
REST расшифровывается как **Representational State Transfer** и является одним из самых распространенных способов взаимодействия между приложениями через интернет.

REST обычно работает поверх **HTTP** и использует стандартные методы:

- **GET** — получить данные
- **POST** — создать данные
- **PUT** — обновить данные
- **DELETE** — удалить данные

Чаще всего данные передаются в формате **JSON**.  
Важная особенность REST — **stateless**, то есть сервер не хранит состояние между запросами: каждый запрос считается самостоятельным. Это упрощает масштабирование и позволяет обслуживать большое количество пользователей.

REST хорошо подходит для:

- веб-приложений
- мобильных приложений
- публичных API    
- микросервисов, где не требуется сверхбыстрая бинарная передача


### Простейший пример REST API на Python

Клиентский запрос через `requests`:

```python
import requests

url = "https://jsonplaceholder.typicode.com/users/1"
response = requests.get(url)

print(response.status_code)
print(response.json())
```

Простейший REST-сервер на Flask:

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

users = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
]

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    for user in users:
        if user["id"] == user_id:
            return jsonify(user)
    return jsonify({"error": "User not found"}), 404

@app.route("/users", methods=["POST"])
def create_user():
    data = request.json
    users.append(data)
    return jsonify(data), 201

if __name__ == "__main__":
    app.run(debug=True)
```

---

## 2. SOAP API

SOAP (**Simple Object Access Protocol**) — один из старейших и самых строгих способов взаимодействия между системами.  
Если REST можно сравнить с обычным разговором, то SOAP — это формальный документ с четкой структурой и правилами.

SOAP-сообщения обычно передаются в формате **XML** и включают:

- **Envelope** — оболочку сообщения
- **Header** — заголовок
- **Body** — тело запроса

SOAP отличается строгой стандартизацией, поддержкой сложных корпоративных сценариев, встроенными механизмами безопасности и формализованной обработкой ошибок. Он может работать не только через HTTP, но и через другие протоколы.

SOAP часто применяется там, где особенно важны:

- надежность транзакций
- строгие контракты между системами
- совместимость со старыми корпоративными платформами
- высокая формальность интеграции

Типичные области применения:

- банки
- страхование
- государственные системы
- медицинские информационные системы

### Простейший пример SOAP на Python

Через библиотеку `zeep`:

```python
from zeep import Client

wsdl = "http://www.dneonline.com/calculator.asmx?WSDL"
client = Client(wsdl=wsdl)

result = client.service.Add(5, 3)
print(result)
```

Здесь Python-клиент обращается к SOAP-сервису так, как будто вызывает обычную функцию.

---

## 3. gRPC API

gRPC — это современный и очень быстрый вариант **RPC** (**Remote Procedure Call**), разработанный Google.  
Идея RPC в том, что программа вызывает удаленную функцию так, будто она локальная.

В отличие от REST, где часто используется текстовый JSON, gRPC применяет **Protocol Buffers (Protobuf)** — компактный бинарный формат сериализации. За счет этого обмен данными получается быстрее и экономичнее.

Также gRPC использует **HTTP/2**, что дает важные преимущества:

- мультиплексирование запросов
- меньше накладных расходов
- поддержка потоковой передачи данных    

gRPC поддерживает 4 модели взаимодействия:

- один запрос — один ответ
- серверный стриминг
- клиентский стриминг
- двусторонний стриминг

gRPC особенно хорошо подходит для:

- микросервисной архитектуры
- внутренних высоконагруженных систем
- real-time сервисов
- передачи большого числа сообщений с минимальной задержкой

### Простейший пример gRPC на Python

Сначала `.proto` файл:

```proto
syntax = "proto3";

service Greeter {
  rpc SayHello (HelloRequest) returns (HelloReply);
}

message HelloRequest {
  string name = 1;
}

message HelloReply {
  string message = 1;
}
```

После генерации Python-кода можно сделать сервер так:

```python
import grpc
from concurrent import futures
import hello_pb2
import hello_pb2_grpc

class GreeterService(hello_pb2_grpc.GreeterServicer):
    def SayHello(self, request, context):
        return hello_pb2.HelloReply(message=f"Hello, {request.name}!")

server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
hello_pb2_grpc.add_GreeterServicer_to_server(GreeterService(), server)
server.add_insecure_port("[::]:50051")
server.start()
server.wait_for_termination()
```

Клиент:

```python
import grpc
import hello_pb2
import hello_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
stub = hello_pb2_grpc.GreeterStub(channel)

response = stub.SayHello(hello_pb2.HelloRequest(name="Alice"))
print(response.message)
```

---

## 4. GraphQL API

GraphQL — это язык запросов к API, созданный Facebook.  
Он решает типичную проблему REST: иногда REST возвращает слишком много данных, а иногда — слишком мало, и тогда приходится делать несколько запросов.

Главная идея GraphQL проста: клиент сам указывает, **какие именно поля ему нужны**.  
Например, вместо получения полного профиля пользователя можно запросить только имя и email.

Преимущества GraphQL:

- точный запрос нужных данных
    
- одна точка входа
    
- удобная работа со связанными сущностями
    
- самодокументируемая схема
    
- поддержка подписок в реальном времени
    

GraphQL хорошо подходит для:

- сложных фронтендов
    
- мобильных приложений
    
- систем с большим числом связанных сущностей
    
- интерфейсов, где важно снизить число запросов
    

### Простейший пример GraphQL на Python

Клиентский запрос через `requests`:

```python
import requests

url = "https://countries.trevorblades.com/"
query = """
{
  country(code: "US") {
    name
    capital
    currency
  }
}
"""

response = requests.post(url, json={"query": query})
print(response.json())
```

Простейший GraphQL-сервер на Python обычно делают через `graphene`, но для первого знакомства достаточно понять именно формат клиентского запроса.

---

## 5. Webhooks

Webhooks часто называют «обратным API».  
Вместо того чтобы приложение постоянно спрашивало сервер: «Есть ли что-то новое?», сервис сам отправляет уведомление при наступлении события.

Это похоже на звонок в дверь: не вы идете проверять, пришел ли кто-то, а вам сразу сообщают о визите.

Обычно схема такая:

1. вы указываете **callback URL**
    
2. на стороне сервиса происходит событие
    
3. сервис отправляет **POST-запрос** на ваш URL
    
4. ваше приложение получает данные и реагирует
    

Webhooks хорошо подходят для:

- уведомлений о платежах
    
- событий из GitHub/GitLab
    
- интеграций с CRM
    
- ботов и систем оповещений
    

### Простейший пример Webhook на Python

Сервер, принимающий webhook:

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Получено событие:", data)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
```

Пример отправки тестового webhook-запроса:

```python
import requests

url = "http://localhost:5000/webhook"
payload = {
    "event": "payment_success",
    "order_id": 123,
    "amount": 5000
}

response = requests.post(url, json=payload)
print(response.json())
```

---

## 6. WebSocket API

WebSocket — это технология постоянного двустороннего соединения между клиентом и сервером.  
Если REST — это отдельные запросы и ответы, то WebSocket — это постоянно открытый канал связи.

Соединение начинается с HTTP-handshake, после чего превращается в постоянный канал, по которому и клиент, и сервер могут отправлять данные в любой момент.

WebSocket особенно полезен там, где данные должны приходить мгновенно:

- чаты
    
- онлайн-игры
    
- биржевые котировки
    
- live-дашборды
    
- уведомления в реальном времени
    

### Простейший пример WebSocket на Python

Сервер через `websockets`:

```python
import asyncio
import websockets

async def echo(websocket):
    async for message in websocket:
        print("Получено:", message)
        await websocket.send(f"Echo: {message}")

async def main():
    server = await websockets.serve(echo, "localhost", 8765)
    await server.wait_closed()

asyncio.run(main())
```

Клиент:

```python
import asyncio
import websockets

async def main():
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.send("Привет, сервер!")
        response = await websocket.recv()
        print(response)

asyncio.run(main())
```

---

## 7. WebRTC API

WebRTC (**Web Real-Time Communication**) — это технология прямой связи между устройствами в реальном времени.  
Ее ключевая идея в том, что аудио, видео или файлы могут передаваться **напрямую между клиентами**, без постоянного прохождения через центральный сервер.

Именно WebRTC лежит в основе браузерных видеозвонков, онлайн-конференций и P2P-коммуникаций.

WebRTC умеет решать сложные задачи автоматически:

- обход NAT
    
- согласование параметров соединения
    
- адаптацию качества под канал связи
    
- передачу аудио, видео и данных
    

WebRTC полезен для:

- видеозвонков
    
- голосовых вызовов
    
- P2P-файлообмена
    
- совместной работы в реальном времени
    

### Простейший пример WebRTC на Python

Чистый WebRTC чаще используют в браузере на JavaScript, но в Python можно работать с ним через `aiortc`.

Пример создания peer connection:

```python
import asyncio
from aiortc import RTCPeerConnection

async def main():
    pc = RTCPeerConnection()
    channel = pc.createDataChannel("chat")

    @channel.on("open")
    def on_open():
        channel.send("Привет через WebRTC")

    @channel.on("message")
    def on_message(message):
        print("Получено:", message)

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    print("SDP offer created")
    print(pc.localDescription.sdp)

asyncio.run(main())
```

Это не полный готовый видеочат, а самый простой учебный пример, показывающий, что в WebRTC создается peer connection и канал передачи данных.

---

# Итог

Все перечисленные подходы решают одну и ту же базовую задачу — обмен данными между системами, но делают это по-разному.

- **REST** — универсальный и понятный вариант
    
- **SOAP** — строгий и формальный
    
- **gRPC** — быстрый и эффективный
    
- **GraphQL** — гибкий по структуре данных
    
- **Webhooks** — событийный
    
- **WebSocket** — для постоянного канала связи
    
- **WebRTC** — для прямого общения между устройствами
    

Поэтому выбор API зависит не от того, какой подход «лучше вообще», а от того, **какую задачу нужно решить**.

Могу дальше сделать из этого:

1. аккуратный конспект для учебы,
    
2. таблицу сравнения,
    
3. или версию в стиле доклада/реферата.