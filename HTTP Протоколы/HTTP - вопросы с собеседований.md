# 1. В чем разница между статус-кодами 401 и 403?

## 401 Unauthorized

Несмотря на название `Unauthorized`, по смыслу этот статус ближе к:

> **Клиент не аутентифицирован. Сервер не может подтвердить, кто выполняет запрос.**

Типичные причины:

- не передан access token;
- токен истёк;
- токен повреждён;
- подпись JWT не прошла проверку;
- отсутствует или недействительна сессия;
- переданы неправильные credentials.

Пример:

```http
GET /api/profile HTTP/1.1
Host: example.com
```

Сервер:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer
```

Для Bearer-token API клиент обычно должен получить новый токен или заново пройти аутентификацию.

### `WWW-Authenticate`

Для `401` сервер может сообщить, какой способ аутентификации ожидается:

```http
WWW-Authenticate: Bearer
```

или:

```http
WWW-Authenticate: Basic realm="admin"
```

## 403 Forbidden

`403` означает:

> **Сервер понял запрос, но отказывается его выполнять.**

Частый сценарий:

```text
пользователь успешно аутентифицирован
↓
сервер знает его identity
↓
но у пользователя нет нужных прав
```

Например:

```text
user role = USER

GET /admin/users
        ↓
403 Forbidden
```

## Практическое различие

```text
401
Кто ты?
Я не могу подтвердить твою identity.

403
Я знаю, кто ты.
Но тебе нельзя выполнять эту операцию.
```

Пример:

```text
GET /admin

нет токена
→ 401

валидный токен обычного пользователя
→ 403

валидный токен администратора
→ 200
```

Иногда сервер специально возвращает `404` вместо `403`, чтобы не раскрывать факт существования ресурса.

---

# 2. Когда использовать POST, PUT и PATCH?

Упрощённое правило:

```text
POST  → создать / запустить действие
PUT   → полностью заменить ресурс
PATCH → частично изменить ресурс
```

Но у HTTP есть более точная семантика.

## POST

`POST` передаёт данные серверу для обработки.

Очень часто используется для создания ресурса:

```http
POST /users
Content-Type: application/json

{
  "name": "Alice"
}
```

Ответ:

```http
HTTP/1.1 201 Created
Location: /users/123
```

Но `POST` не ограничен только созданием. Им можно запускать действие:

```http
POST /payments/123/refund
```

или:

```http
POST /reports/generate
```

Главная особенность:

> Сервер сам определяет смысл обработки request body.

### Идемпотентность POST

`POST` по умолчанию **не считается идемпотентным**.

Если выполнить:

```text
POST /payments
```

два раза, теоретически могут появиться два платежа.

Поэтому для критичных операций часто используют idempotency key:

```http
Idempotency-Key: 8c4a...
```

## PUT

`PUT` обычно означает:

> Создай или полностью замени представление ресурса по известному URI.

Пример:

```http
PUT /users/123
Content-Type: application/json

{
  "name": "Alice",
  "email": "alice@example.com",
  "age": 25
}
```

Если API трактует `PUT` как полную замену, отсутствие поля может означать его удаление или сброс в default.

Например было:

```json
{
  "name": "Alice",
  "email": "alice@example.com",
  "age": 25
}
```

Отправили:

```json
{
  "name": "Bob"
}
```

После полного `PUT` концептуально ресурс может стать:

```json
{
  "name": "Bob"
}
```

Поэтому `PUT` удобно использовать, когда клиент передаёт **полное актуальное состояние ресурса**.

### PUT идемпотентен

Если несколько раз выполнить один и тот же `PUT` с одним и тем же body, конечное состояние ресурса должно быть тем же.

```text
PUT #1 → User = X
PUT #2 → User = X
PUT #3 → User = X
```

## PATCH

`PATCH` означает:

> Частично изменить ресурс.

Например:

```http
PATCH /users/123
Content-Type: application/json

{
  "name": "Bob"
}
```

Сервер изменяет только `name`, а остальные поля оставляет как есть.

### Форматы PATCH

JSON Merge Patch:

```json
{
  "name": "Bob"
}
```

JSON Patch:

```json
[
  {
    "op": "replace",
    "path": "/name",
    "value": "Bob"
  }
]
```

### Идемпотентность PATCH

`PATCH` **не обязан быть идемпотентным**. Конкретный API может сделать его идемпотентным, но HTTP этого не требует.

## Быстрая таблица

| Метод | Типичный смысл | Идемпотентный |
|---|---|---:|
| `POST` | Создать или выполнить действие | Обычно нет |
| `PUT` | Полностью создать/заменить ресурс по URI | Да |
| `PATCH` | Частично изменить ресурс | Не обязательно |

---

# 3. Чем Cookies отличаются от обычных HTTP-заголовков?

Cookies реализуются через HTTP-заголовки, но браузер обрабатывает их особым образом.

## Как сервер устанавливает Cookie

```http
HTTP/1.1 200 OK
Set-Cookie: session_id=abc123; HttpOnly; Secure; SameSite=Lax
```

Браузер анализирует `Set-Cookie` и сохраняет cookie в своё cookie storage.

## Как Cookie отправляется обратно

При подходящем запросе браузер автоматически добавляет:

```http
Cookie: session_id=abc123
```

То есть frontend-коду обычно не нужно вручную формировать `Cookie` header.

## Почему браузер отправляет не все Cookies подряд

У каждой cookie есть область действия:

```text
Domain
Path
Secure
SameSite
Expires / Max-Age
```

Браузер проверяет эти атрибуты перед отправкой.

Например:

```http
Set-Cookie: session=123; Path=/admin
```

такая cookie относится к `/admin`, а не обязательно ко всему сайту.

## Cookie и Authorization

Bearer token часто передают:

```http
Authorization: Bearer <token>
```

Такой header приложение обычно формирует самостоятельно.

Токен **не обязательно** хранить в `localStorage`. Возможные варианты:

```text
memory
HttpOnly cookie
sessionStorage
localStorage
специализированное secure storage
```

Хранение access token в `localStorage` повышает риск его кражи при XSS, потому что JavaScript страницы может читать localStorage.

---

# 4. Как защитить Cookies от атак?

Три основных атрибута:

```text
Secure
HttpOnly
SameSite
```

Они решают разные задачи.

## Secure

```http
Set-Cookie: session=abc; Secure
```

Cookie должна передаваться только через HTTPS.

```text
https://example.com
→ cookie может отправляться

http://example.com
→ cookie не должна отправляться
```

## HttpOnly

```http
Set-Cookie: session=abc; HttpOnly
```

Запрещает JavaScript получать cookie через:

```javascript
document.cookie
```

Это особенно полезно для session/authentication cookie.

Важно:

> `HttpOnly` не устраняет XSS как таковой. Он прежде всего мешает JavaScript украсть саму cookie.

## SameSite

Контролирует, будет ли cookie отправляться в cross-site context.

### Strict

```http
SameSite=Strict
```

Самый строгий вариант. Cookie почти не отправляется при переходах/запросах, инициированных с другого сайта.

### Lax

```http
SameSite=Lax
```

Компромиссный вариант. Cookie блокируется для многих cross-site запросов, но обычно допускается при определённых top-level navigation безопасными методами.

Важно:

```text
Lax ≠ "разрешает любые GET"
```

Семантика зависит и от типа navigation/request context.

### None

```http
SameSite=None; Secure
```

Cookie разрешено отправлять в cross-site context. Для современных браузеров `SameSite=None` требует `Secure`.

## Дополнительные меры

Полезно также правильно задавать:

```text
Domain
Path
Max-Age / Expires
```

Чем меньше область действия sensitive cookie, тем лучше.

---

# 5. Что такое CORS и зачем он нужен?

CORS — **Cross-Origin Resource Sharing**.

Это браузерный механизм, который определяет:

> Разрешено ли JavaScript одного origin читать response от другого origin.

## Что такое Origin

Origin определяется тройкой:

```text
scheme + host + port
```

Например:

```text
https://example.com:443
```

и:

```text
https://api.example.com:443
```

— разные origins из-за разного host.

## Same-Origin Policy

Браузер ограничивает JavaScript одного origin от произвольного чтения данных другого origin.

CORS позволяет серверу явно разрешить cross-origin доступ.

## Пример

Frontend:

```text
https://frontend.example.com
```

делает запрос к:

```text
https://api.example.com/users
```

API отвечает:

```http
Access-Control-Allow-Origin: https://frontend.example.com
```

Тогда браузер может разрешить frontend-коду читать response.

## Важное уточнение

CORS **не является firewall** и не означает, что request вообще не дойдёт до сервера.

CORS контролируется браузером и в первую очередь ограничивает JavaScript-доступ к cross-origin response.

Поэтому:

```text
curl
Postman
backend-to-backend request
```

не подчиняются браузерной CORS-политике.

## Preflight

Для некоторых запросов браузер сначала отправляет `OPTIONS`:

```http
OPTIONS /users
Origin: https://frontend.example.com
Access-Control-Request-Method: PATCH
Access-Control-Request-Headers: Authorization
```

Сервер:

```http
Access-Control-Allow-Origin: https://frontend.example.com
Access-Control-Allow-Methods: GET, POST, PATCH
Access-Control-Allow-Headers: Authorization
```

Если разрешения подходят, браузер выполняет реальный request.

## Credentials

Для credentialed CORS используется, например:

```http
Access-Control-Allow-Credentials: true
```

При таком сценарии нельзя просто заменить конкретный origin на `*`.

---

# 6. Какие основные уязвимости связаны с HTTP?

Точнее говорить не об уязвимостях самого HTTP, а о типичных web-уязвимостях приложений, работающих поверх HTTP.

## XSS — Cross-Site Scripting

Злоумышленнику удаётся заставить страницу выполнить его JavaScript.

Последствия:

```text
кража доступных JS токенов
чтение данных страницы
отправка запросов от пользователя
изменение DOM
фишинг внутри страницы
```

Защита:

```text
escaping / output encoding
не вставлять непроверенный HTML
Content-Security-Policy
HttpOnly для sensitive cookies
безопасная работа с DOM
```

## CSRF — Cross-Site Request Forgery

Пользователь авторизован на сайте, браузер хранит session cookie, а злоумышленник пытается заставить браузер выполнить нежелательный request к этому сайту.

Браузер может автоматически приложить cookie.

Защита:

```text
SameSite cookies
CSRF token
проверка Origin / Referer
правильная архитектура authentication
```

## XSS vs CSRF

```text
XSS
→ злоумышленник запускает код внутри доверенного origin

CSRF
→ злоумышленник заставляет браузер пользователя отправить запрос
   с уже существующими credentials
```

## Clickjacking

Злоумышленник встраивает страницу через `<iframe>` и визуально маскирует её, заставляя пользователя кликнуть по скрытому элементу.

Защита:

```http
Content-Security-Policy: frame-ancestors 'none'
```

или:

```http
X-Frame-Options: DENY
```

## Open Redirect

Плохой вариант:

```text
/login?redirect=https://evil.example
```

После login приложение делает redirect без проверки URL.

Защита:

```text
allowlist разрешённых redirect URL
относительные URL
не доверять произвольному redirect query parameter
```

---

# 7. Как HTTP связан с Rate Limiting?

Если клиент превысил лимит, обычно используется:

```http
429 Too Many Requests
```

## Где может находиться Rate Limiter

На инфраструктурном уровне:

```text
Nginx
Envoy
Kong
API Gateway
Ingress
```

или в самом приложении.

## По чему считать лимит

Не обязательно только IP.

Варианты:

```text
IP
User ID
API key
JWT subject
tenant
endpoint
combination
```

IP иногда плохой идентификатор, потому что множество пользователей могут находиться за одним NAT.

## Retry-After

Сервер может вернуть:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

То есть клиенту рекомендуется повторить запрос примерно через 30 секунд.

## Алгоритмы

Частые варианты:

```text
fixed window
sliding window
token bucket
leaky bucket
```

`Token Bucket` позволяет ограничивать среднюю скорость, но разрешать короткие bursts.

## Distributed Rate Limiting

Если backend имеет несколько replicas, локальный счётчик каждого процесса не даёт глобального лимита.

Нужен общий механизм:

```text
Redis
API Gateway
distributed rate limiter
```

---

# 8. Как передавать файлы по HTTP?

HTTP передаёт body как байты. Файл можно передать несколькими способами.

## multipart/form-data

Частый вариант для form upload.

```http
POST /upload
Content-Type: multipart/form-data; boundary=abc
```

Подходит, когда одновременно передаются:

```text
файл
+
metadata
+
другие form fields
```

## application/octet-stream

```http
Content-Type: application/octet-stream
```

означает произвольные бинарные данные.

Можно передать файл напрямую:

```http
PUT /files/123
Content-Type: application/octet-stream

<binary bytes>
```

## Важное уточнение про streaming

`application/octet-stream` **не делает передачу streaming автоматически**.

Streaming зависит от того, как client/server читают и пишут body.

Главная идея:

```text
не read entire file into RAM
↓
читать chunks
↓
обрабатывать/писать chunks
```

Например:

```text
64 KB
64 KB
64 KB
...
```

## Большие файлы

Для больших uploads важны:

```text
streaming
timeouts
body size limits
backpressure
checksum
retry strategy
resumable uploads
```

Для очень больших файлов часто используют object storage и presigned URLs, чтобы файл не проходил через application backend.

## Downloads и Range

Для больших downloads полезен:

```http
Range: bytes=1000000-1999999
```

Сервер может ответить:

```http
206 Partial Content
```

Это используется для докачки файлов и перемотки медиа.

## Base64

Бинарные данные кодируются в строку.

Например в JSON:

```json
{
  "file": "SGVsbG8..."
}
```

Base64 увеличивает размер примерно на **33%** до дополнительного JSON/HTTP overhead, поэтому для больших файлов это плохой вариант.

---

# 9. Как работает кэширование в HTTP?

HTTP cache может находиться в:

```text
browser
proxy
CDN
reverse proxy
```

Основной заголовок управления:

```http
Cache-Control
```

## max-age

```http
Cache-Control: max-age=3600
```

Response считается fresh 3600 секунд.

## public

```http
Cache-Control: public, max-age=3600
```

Response может храниться shared cache, например CDN.

## private

```http
Cache-Control: private, max-age=300
```

Response предназначен для private cache, например browser cache конкретного пользователя.

## no-store

```http
Cache-Control: no-store
```

Просит не сохранять response.

## no-cache

Название обманчивое.

```http
Cache-Control: no-cache
```

не обязательно означает «не хранить».

Обычно смысл:

> Перед повторным использованием cached response нужно проверить его актуальность у origin server.

## Revalidation через ETag

Сервер:

```http
ETag: "abc123"
```

Клиент позже:

```http
If-None-Match: "abc123"
```

Если ресурс не изменился:

```http
HTTP/1.1 304 Not Modified
```

Body повторно не нужен — используется cached copy.

## Last-Modified

Сервер:

```http
Last-Modified: Sun, 09 Aug 2026 10:00:00 GMT
```

Клиент:

```http
If-Modified-Since: Sun, 09 Aug 2026 10:00:00 GMT
```

При отсутствии изменений сервер может вернуть `304 Not Modified`.

## Vary

Например:

```http
Vary: Accept-Encoding
```

означает, что representation зависит от `Accept-Encoding`.

Shared cache должен учитывать это при выборе cached response.

## CDN

```text
Client
  ↓
CDN
  ↓
Origin
```

Cache hit:

```text
Client → CDN → cached response
```

Origin не вызывается.

Cache miss:

```text
Client → CDN → Origin
               ↓
             response
               ↓
              CDN stores
               ↓
             Client
```

---

# 10. В чем разница между 200, 201 и 204?

Все относятся к:

```text
2xx = successful response
```

но имеют разную семантику.

## 200 OK

Универсальный успешный ответ.

```http
GET /users/123
```

Ответ:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 123,
  "name": "Alice"
}
```

`200` также может использоваться после `POST`, `PUT`, `PATCH`, если сервер хочет вернуть representation/result.

## 201 Created

Используется, когда request создал новый ресурс.

```http
POST /users
```

Ответ:

```http
HTTP/1.1 201 Created
Location: /users/123
Content-Type: application/json

{
  "id": 123,
  "name": "Alice"
}
```

Полезный header:

```http
Location: /users/123
```

показывает URI созданного ресурса.

`201` не обязан использоваться только с `POST`: главное, что результатом request стало создание ресурса.

## 204 No Content

Операция успешна, но response body отсутствует.

```http
DELETE /users/123
```

Ответ:

```http
HTTP/1.1 204 No Content
```

`204` также может использоваться после успешного `PUT`, `PATCH` или `POST`, если body не нужен.

Главное:

> `204` не должен содержать обычное response body.

## DELETE не обязан возвращать 204

Возможны:

```text
204 → удалено, body не нужен
200 → вернуть результат/representation
202 → удаление принято, но выполняется асинхронно
```

---

# Краткая шпаргалка

```text
401
→ identity не подтверждена

403
→ identity известна, но операция запрещена

POST
→ создать / выполнить действие
→ обычно не идемпотентен

PUT
→ полная замена ресурса
→ идемпотентен

PATCH
→ частичное изменение
→ не обязан быть идемпотентным

Cookie
→ браузер хранит и автоматически отправляет
   в соответствии с Domain/Path/Secure/SameSite

Secure
→ только HTTPS

HttpOnly
→ JavaScript не читает cookie

SameSite
→ ограничивает cross-site отправку

CORS
→ браузерное ограничение cross-origin доступа к response
→ не firewall

XSS
→ выполнение чужого JS

CSRF
→ нежелательный authenticated request от браузера пользователя

Clickjacking
→ обманный click через iframe

Open Redirect
→ redirect на непроверенный внешний URL

429
→ Too Many Requests

Retry-After
→ когда повторить

multipart/form-data
→ файл + поля

application/octet-stream
→ raw binary body

Base64
→ текстовое представление binary, примерно +33%

Cache-Control
→ правила cache

ETag / If-None-Match
→ validation

304
→ cached representation актуальна

200
→ OK

201
→ Created

204
→ Success without response body
```
