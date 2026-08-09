## Главное разделение ответственности

Прикладной backend-код обычно не занимается прямым выбором HTTP/1.1, HTTP/2 или HTTP/3.

Например FastAPI endpoint:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/users")
async def users():
    return {"users": []}
```

не должен отдельно реализовываться для:

```text
HTTP/1.1
HTTP/2
HTTP/3
```

HTTP-версия обычно обрабатывается инфраструктурой перед приложением.

---

# Типичная production-архитектура

```text
                    INTERNET
                       │
          ┌────────────┴────────────┐
          │                         │
      TCP :443                  UDP :443
 HTTP/1.1 / HTTP/2              HTTP/3
          │                         │
          └────────────┬────────────┘
                       ↓
              Reverse Proxy /
              Edge Proxy /
              Load Balancer
                       ↓
                 backend HTTP
                       ↓
                 ASGI server
                       ↓
                    FastAPI
```

В роли внешнего компонента могут использоваться:

- Caddy;
- nginx;
- Envoy;
- HAProxy;
- Cloudflare;
- cloud load balancer;
- ingress controller.

---

# Почему так делают

Reverse proxy может заниматься:

- TLS termination;
- сертификатами;
- HTTP/1.1;
- HTTP/2;
- HTTP/3;
- QUIC;
- ALPN;
- connection management;
- timeouts;
- compression;
- rate limiting;
- load balancing;
- routing;
- observability.

А FastAPI занимается бизнес-логикой.

---

# Пример: FastAPI + Uvicorn + Caddy

Backend:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"hello": "world"}
```

Uvicorn можно слушать только локально:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

Caddy:

```caddyfile
example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Снаружи архитектура:

```text
Client
   │
   ├── HTTP/1.1 ── TCP ──┐
   ├── HTTP/2   ── TCP ──┼──> Caddy
   └── HTTP/3   ── QUIC ─┘
                          │
                          │ backend HTTP
                          ↓
                        Uvicorn
                          ↓
                        FastAPI
```

FastAPI-код не меняется.

---

# TCP 443 и UDP 443

Для HTTPS через HTTP/1.1 и HTTP/2 обычно нужен:

```text
TCP port 443
```

Для HTTP/3/QUIC нужен:

```text
UDP port 443
```

Поэтому firewall/security group должен допускать соответствующий traffic.

```text
443/tcp
443/udp
```

Если UDP/443 заблокирован, HTTP/3 работать не сможет, даже если proxy его поддерживает.

---

# HTTP/1.1 и HTTP/2 negotiation

Для HTTPS клиент и сервер могут использовать **ALPN — Application-Layer Protocol Negotiation** внутри TLS handshake.

Клиент сообщает, например:

```text
h2
http/1.1
```

Сервер выбирает поддерживаемый вариант.

```text
Client:
h2, http/1.1

Server:
h2
```

После этого соединение работает как HTTP/2.

Другой клиент может использовать HTTP/1.1.

Прикладной endpoint остаётся тем же.

---

# HTTP/3 negotiation

HTTP/3 использует другой транспорт:

```text
HTTP/3
↓
QUIC
↓
UDP
```

Клиент должен знать, что сервер предоставляет HTTP/3 endpoint.

На практике browsers/proxies умеют делать это автоматически и при невозможности QUIC используют fallback.

---

# «Сервер поддерживает HTTP/3» ≠ «все клиенты используют HTTP/3»

Production-сервер может предоставлять:

```text
HTTP/1.1 ✓
HTTP/2   ✓
HTTP/3   ✓
```

Но конкретный клиент выберет то, что доступно ему и сети.

Например:

```text
старый клиент
→ HTTP/1.1

современный клиент без HTTP/3
→ HTTP/2

современный browser + QUIC доступен
→ HTTP/3

HTTP/3 поддерживается клиентом,
но UDP заблокирован
→ fallback на HTTP/2
```

Поэтому «гарантировать поддержку» означает:

> инфраструктура сервера способна принять все нужные версии протокола.

Это не означает:

> любой клиент обязательно будет использовать HTTP/3.

---

# Где выбирается версия HTTP при написании клиентского кода

Если приложение само является HTTP-клиентом, выбор часто задаётся возможностями библиотеки.

Например концептуально:

```python
client = SomeHttpClient(enable_http2=True)
```

Это обычно означает:

> разрешить HTTP/2, если сервер его поддерживает.

Это не обязательно означает жёсткое требование HTTP/2.

Версия может быть согласована автоматически.

---

# Где выбирается версия HTTP на сервере

Не здесь:

```python
@app.get("/users")
async def users():
    ...
```

А здесь:

```text
reverse proxy
web server
load balancer
ASGI server configuration
TLS/ALPN configuration
QUIC listener
firewall
```

То есть wire protocol — инфраструктурная ответственность.

---

# Почему backend может получать HTTP/1.1, даже если клиент использовал HTTP/3

Reverse proxy терминирует внешнее соединение.

Пример:

```text
Browser
   │
HTTP/3 + QUIC
   │
   ↓
Caddy / nginx
   │
HTTP/1.1
   │
   ↓
Uvicorn
   │
ASGI
   ↓
FastAPI
```

Это два разных сетевых соединения.

```text
connection #1:
browser ↔ reverse proxy

connection #2:
reverse proxy ↔ backend
```

Поэтому внешняя версия HTTP не обязана совпадать с внутренней.

---

# ASGI и абстракция над wire protocol

FastAPI обычно работает через ASGI.

ASGI-сервер принимает сетевой HTTP request, парсит его и передаёт приложению структурированные события.

FastAPI работает уже не с TCP segments и не с HTTP/2 frames.

Для приложения запрос выглядит как логическая сущность:

```text
method
path
headers
body
...
```

Это одна из причин, почему бизнес-код не должен зависеть от HTTP wire version.

---

# Как бы выглядело production-решение для поддержки HTTP/1.1, 2 и 3

```text
1. FastAPI реализует endpoints.

2. Uvicorn/другой ASGI server запускает приложение
   на внутреннем адресе.

3. Reverse proxy принимает публичный HTTPS traffic.

4. Proxy настроен на:
   - HTTP/1.1;
   - HTTP/2;
   - HTTP/3/QUIC.

5. Открыт TCP/443.

6. Открыт UDP/443.

7. Есть TLS certificate.

8. Клиент и proxy автоматически договариваются
   о лучшем доступном протоколе.

9. Proxy передаёт запрос backend-приложению.
```

---

# Нужно ли backend-приложению знать версию HTTP

Обычно — нет.

Но иногда версия полезна для:

- диагностики;
- метрик;
- логирования;
- тестирования;
- исследования performance.

Это infrastructure/observability concern, а не бизнес-логика.

---

# Проверка production-сервера

Полезно проверять поддержку каждой версии отдельным клиентом или инструментом.

Логическая схема тестирования:

```text
HTTP/1.1 request → должен работать
HTTP/2 request   → должен работать
HTTP/3 request   → должен работать
```

Также отдельно важно проверить fallback:

```text
UDP unavailable
↓
client всё ещё может подключиться через HTTP/2 или HTTP/1.1
```

---

# Главное

Если нужно публично поддерживать HTTP/1.1, HTTP/2 и HTTP/3, типичная ответственность распределяется так:

```text
FastAPI
→ бизнес-логика

ASGI server
→ запуск Python application

Reverse proxy / Load Balancer
→ HTTP versions + TLS + QUIC

OS / firewall
→ TCP/UDP sockets and allowed ports
```

Самая важная мысль:

> поддержку конкретных wire-версий HTTP обычно гарантирует внешний HTTP-сервер/reverse proxy, а не код endpoint'ов.
