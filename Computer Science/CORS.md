---
title: CORS
aliases: [Cross-Origin Resource Sharing, кросс-доменные запросы]
tags: [web, http, browser, security]
created: 2026-10-27
---
# CORS (Cross-Origin Resource Sharing)

> [!summary] Коротко
> CORS — механизм, с помощью которого **сервер сообщает браузеру**, что JS-коду со страницы с другого origin можно читать его ответы. Ограничение накладывает **браузер**, а сервер лишь присылает разрешающие заголовки. Это не защита сервера и не авторизация.

## Откуда берётся проблема

**Origin** = схема + хост + порт. Совпасть должны все три части.

| Страница | Адрес API | Тот же origin? |
|---|---|---|
| `http://localhost:5501` | `http://localhost:5501/api` | да |
| `http://localhost:5501` | `http://localhost:8000` | нет (порт) |
| `http://localhost:5501` | `http://127.0.0.1:5501` | нет (хост) |
| `https://site.com` | `http://site.com` | нет (схема) |

По умолчанию действует [[Same-Origin Policy]]: JS со страницы A не может прочитать ответ от origin B. Это нужно, чтобы чужой сайт не мог от имени пользователя, с его куками, запросить, например, страницу почты и прочитать её. CORS — контролируемое **послабление** этого правила.

## Какие задачи решает

- **SPA и API на разных адресах:** фронтенд на `:5501`, бэкенд на `:8000`; `app.site.com` и `api.site.com`.
- **Публичные API**, которые должны вызываться с любых сайтов.
- **Разные права для разных фронтендов** к одному API (как в демо с товарами: `:5501` может всё, `:5503` только GET и POST).
- **Ресурсы, которые браузер грузит только по CORS:** веб-шрифты с CDN, ES-модули, картинки для `<canvas>` и WebGL, скрипты с `crossorigin` и SRI.

## Как это работает

### 1. Простой запрос (без preflight)

Условия: метод `GET`, `HEAD` или `POST`, только «безопасные» заголовки, а `Content-Type` один из `text/plain`, `application/x-www-form-urlencoded`, `multipart/form-data`. Браузер отправляет запрос сразу и добавляет `Origin`:

```http
GET /products HTTP/1.1
Host: localhost:8000
Origin: http://localhost:5501
```

Сервер отвечает как обычно, плюс разрешающий заголовок:

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://localhost:5501
Vary: Origin
Content-Type: application/json
```

Браузер сверяет `Allow-Origin` со своим origin. Совпало, и JS получает ответ. Не совпало или заголовка нет, и ответ **отбрасывается**, а в консоли появляется CORS-ошибка.

### 2. Preflight (предварительный запрос)

Если запрос «непростой», браузер сначала отправляет `OPTIONS` и спрашивает разрешение. Это бывает при:

- методах `PUT`, `PATCH`, `DELETE`;
- `Content-Type: application/json`;
- заголовках `Authorization` и любых `X-*`.

```http
OPTIONS /products/1 HTTP/1.1
Origin: http://localhost:5501
Access-Control-Request-Method: PATCH
Access-Control-Request-Headers: content-type
```

Если сервер согласен:

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://localhost:5501
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE
Access-Control-Allow-Headers: Content-Type
Access-Control-Max-Age: 600
```

Только после этого браузер отправляет настоящий `PATCH`. Если ответ не 2xx или в нём нет нужных разрешений, настоящий запрос **не уходит вообще**.

### 3. Запросы с куками (credentials)

Куки и HTTP-авторизация к чужому origin не отправляются, пока скрипт явно не попросит (`credentials: "include"`). Тогда сервер обязан ответить `Access-Control-Allow-Credentials: true` и указать **конкретный** origin вместо `*`.

## Основные заголовки

| Заголовок | Кто шлёт | Смысл |
|---|---|---|
| `Origin` | браузер | откуда пришёл запрос |
| `Access-Control-Allow-Origin` | сервер | какому origin можно читать ответ (один origin или `*`) |
| `Access-Control-Allow-Methods` | сервер | разрешённые методы (в ответе на preflight) |
| `Access-Control-Allow-Headers` | сервер | разрешённые заголовки запроса |
| `Access-Control-Max-Age` | сервер | сколько секунд кэшировать результат preflight |
| `Access-Control-Allow-Credentials` | сервер | можно ли отправлять куки |
| `Access-Control-Expose-Headers` | сервер | какие заголовки ответа доступны JS |
| `Vary: Origin` | сервер | ответ зависит от Origin, кэшам важно это учитывать |

## Ограничения: чего CORS не делает

> [!warning] Главное
> CORS ограничивает **чтение ответа в браузере**, а не выполнение запроса на сервере.

1. **Не защищает сервер.** Простой запрос с чужого сайта доходит до сервера и выполняется (в том числе с побочными эффектами), браузер лишь не покажет ответ скрипту. От подделки запросов защищает [[CSRF]]-защита, а не CORS.
2. **Работает только в браузере.** `curl`, Postman, мобильные приложения и другие серверы CORS игнорируют, а заголовок `Origin` в них можно подделать.
3. **Не заменяет авторизацию.** Доступ к данным должен проверяться токенами, сессиями и правами.
4. **`Allow-Origin` принимает одно значение или `*`.** Списка origin'ов там быть не может, поэтому серверы сверяют `Origin` со своим списком и подставляют подходящий.
5. **`*` несовместима с куками.** Для запросов с credentials нужен явный origin.
6. **JS видит не все заголовки ответа.** Остальные нужно перечислять в `Expose-Headers`.
7. **Preflight стоит времени.** Это дополнительный запрос, поэтому используют `Max-Age`, но браузеры ограничивают его сверху (Chrome примерно двумя часами).
8. **Обойти на клиенте нельзя.** Режим `no-cors` даёт «непрозрачный» ответ без доступа к содержимому.
9. **Ошибки обезличены.** JS получает просто `Failed to fetch`, подробности только в консоли браузера.

## Типичные ловушки

- `localhost` и `127.0.0.1` считаются **разными** origin.
- Сервер отражает любой пришедший `Origin` и при этом разрешает куки. Это фактически открывает API всем сайтам.
- В списке разрешённых оказался `null` (так выглядят страницы с `file://` и sandbox-iframe).
- Не разрешён `Content-Type` в `Allow-Headers`, и preflight для JSON падает.
- `OPTIONS` перехватывает авторизация или роутер, и preflight получает 401 или 405.
- Ответ 500 без CORS-заголовков выглядит как «ошибка CORS», хотя на самом деле упал сервер.
- Нет `Vary: Origin`, и кэш или CDN отдаёт ответ с чужим `Allow-Origin`.

## Пример реализации CORS на FastAPI

Команды для запуска сервера и клиентов в 4 разных терминалах через `uvicorn`

```bash
python -m uvicorn backend:app --port 8888
```

```bash
python -m http.server 5501
```

```bash
python -m http.server 5502
```

```bash
python -m http.server 5503
```

[Front с полными правами](http://localhost:5501/front_all.html)
[Front без прав](http://localhost:5502/front_all.html)
[Front с частичными правами](http://localhost:5503/front_all.html)

---

### Backend

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

api = FastAPI(title="CORS demo: products")

# Разные правила CORS для разных фронтендов.
# CORSMiddleware сам обрабатывает OPTIONS (preflight) и CORS-заголовки.
CORS_CONFIG = {
    "http://localhost:5501": ["GET", "POST", "PUT", "PATCH", "DELETE"],
    "http://localhost:5503": ["GET", "POST"],
}


class CorsByOrigin:
    """Выбирает CORSMiddleware по Origin; сам CORS не реализует."""

    def __init__(self, fastapi_app: FastAPI):
        self.fastapi_app = fastapi_app
        self.handlers = {
            origin: CORSMiddleware(
                app=fastapi_app,
                allow_origins=[origin],
                allow_methods=methods,
                allow_headers=["Content-Type"],
                max_age=600,
            )
            for origin, methods in CORS_CONFIG.items()
        }

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.fastapi_app(scope, receive, send)

        # Origin автоматически отправляет браузер. curl может его подделать:
        # CORS не является авторизацией на сервере.
        headers = dict(scope.get("headers", []))
        origin = headers.get(b"origin", b"").decode("latin-1")
        handler = self.handlers.get(origin, self.fastapi_app)
        return await handler(scope, receive, send)


class Product(BaseModel):
    name: str
    price: float = Field(ge=0)


class ProductPatch(BaseModel):
    name: str | None = None
    price: float | None = Field(default=None, ge=0)


products = {
    1: {"name": "Гидромолот", "price": 120000},
    2: {"name": "Ковш", "price": 45000},
    3: {"name": "Пика", "price": 9000},
}


def get_product(product_id: int):
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return products[product_id]


@api.get("/products")
def list_products():
    return products


@api.get("/products/{product_id}")
def read_product(product_id: int):
    return get_product(product_id)


@api.post("/products", status_code=201)
def create_product(product: Product):
    product_id = max(products, default=0) + 1
    products[product_id] = product.model_dump()
    return {"id": product_id, **products[product_id]}


@api.put("/products/{product_id}")
def replace_product(product_id: int, product: Product):
    get_product(product_id)
    products[product_id] = product.model_dump()
    return {"id": product_id, **products[product_id]}


@api.patch("/products/{product_id}")
def update_product(product_id: int, patch: ProductPatch):
    existing = get_product(product_id)
    existing.update(patch.model_dump(exclude_unset=True))
    return {"id": product_id, **existing}


@api.delete("/products/{product_id}")
def delete_product(product_id: int):
    get_product(product_id)
    del products[product_id]
    return {"deleted_id": product_id}


# Сохраняем прежнюю команду запуска: uvicorn backend:app --port 8000
app = CorsByOrigin(api)
```

### Fronend_All

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Frontend A — полный доступ</title>
  <style>
    body { font: 16px/1.5 system-ui, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 16px; }
    input { padding: 8px; width: 130px; margin: 4px; }
    button { padding: 9px 13px; margin: 4px; cursor: pointer; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f1f2f5; color: #222; padding: 16px; border-radius: 8px; min-height: 90px; }
    .note { padding: 12px; border-left: 4px solid #2b9d68; background: #f1f2f5; color: #222; }
  </style>
</head>
<body>
  <h1>Frontend A — полный доступ</h1>
  <p class="note">Разрешены GET, POST, PUT, PATCH, DELETE.</p>
  <p>Текущий Origin: <strong id="origin"></strong></p>
  <label>ID <input id="id" type="number" min="1" value="1"></label>
  <label>Название <input id="name" value="Новый товар"></label>
  <label>Цена <input id="price" type="number" min="0" value="1000"></label>
  <div>
    <button onclick="request('GET', '/products')">GET все</button>
    <button onclick="request('GET', '/products/' + idValue())">GET по ID</button>
    <button onclick="request('POST', '/products')">POST создать</button>
    <button onclick="request('PUT', '/products/' + idValue())">PUT заменить</button>
    <button onclick="request('PATCH', '/products/' + idValue())">PATCH изменить цену</button>
    <button onclick="request('DELETE', '/products/' + idValue())">DELETE удалить</button>
  </div>
  <h3>Результат fetch()</h3>
  <pre id="result">Нажми любую кнопку. Ошибки CORS смотри также в DevTools → Console / Network.</pre>
  <script>
    const API = 'http://localhost:8888';
    document.getElementById('origin').textContent = location.origin;
    const idValue = () => document.getElementById('id').value;
    const payload = () => ({
      name: document.getElementById('name').value,
      price: Number(document.getElementById('price').value)
    });

    async function request(method, path) {
      const output = document.getElementById('result');
      output.textContent = `${method} ${path} → запрос...`;
      const options = { method };
      if (['POST', 'PUT', 'PATCH'].includes(method)) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify(method === 'PATCH' ? { price: payload().price } : payload());
      }
      try {
        const response = await fetch(API + path, options);
        const text = await response.text();
        output.textContent = `${method} ${path}
HTTP ${response.status}
${text}`;
      } catch (error) {
        output.textContent = `${method} ${path}
${error.name}: ${error.message}

Проверь DevTools → Console. Если сервер запущен, это может быть блокировка CORS.`;
      }
    }
  </script>
</body>
</html>
```
### Fronend_None

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Frontend B — без доступа</title>
  <style>
    body { font: 16px/1.5 system-ui, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 16px; }
    input { padding: 8px; width: 130px; margin: 4px; }
    button { padding: 9px 13px; margin: 4px; cursor: pointer; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f1f2f5; color: #222; padding: 16px; border-radius: 8px; min-height: 90px; }
    .note { padding: 12px; border-left: 4px solid #d94848; background: #f1f2f5; color: #222; }
  </style>
</head>
<body>
  <h1>Frontend B — без доступа</h1>
  <p class="note">CORS не разрешает ни один метод. GET может дойти до сервера, но браузер не отдаст ответ JavaScript.</p>
  <p>Текущий Origin: <strong id="origin"></strong></p>
  <label>ID <input id="id" type="number" min="1" value="1"></label>
  <label>Название <input id="name" value="Новый товар"></label>
  <label>Цена <input id="price" type="number" min="0" value="1000"></label>
  <div>
    <button onclick="request('GET', '/products')">GET все</button>
    <button onclick="request('GET', '/products/' + idValue())">GET по ID</button>
    <button onclick="request('POST', '/products')">POST создать</button>
    <button onclick="request('PUT', '/products/' + idValue())">PUT заменить</button>
    <button onclick="request('PATCH', '/products/' + idValue())">PATCH изменить цену</button>
    <button onclick="request('DELETE', '/products/' + idValue())">DELETE удалить</button>
  </div>
  <h3>Результат fetch()</h3>
  <pre id="result">Нажми любую кнопку. Ошибки CORS смотри также в DevTools → Console / Network.</pre>
  <script>
    const API = 'http://localhost:8888';
    document.getElementById('origin').textContent = location.origin;
    const idValue = () => document.getElementById('id').value;
    const payload = () => ({
      name: document.getElementById('name').value,
      price: Number(document.getElementById('price').value)
    });

    async function request(method, path) {
      const output = document.getElementById('result');
      output.textContent = `${method} ${path} → запрос...`;
      const options = { method };
      if (['POST', 'PUT', 'PATCH'].includes(method)) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify(method === 'PATCH' ? { price: payload().price } : payload());
      }
      try {
        const response = await fetch(API + path, options);
        const text = await response.text();
        output.textContent = `${method} ${path}
HTTP ${response.status}
${text}`;
      } catch (error) {
        output.textContent = `${method} ${path}
${error.name}: ${error.message}

Проверь DevTools → Console. Если сервер запущен, это может быть блокировка CORS.`;
      }
    }
  </script>
</body>
</html>
```
### Fronend_partial

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Frontend C — частичный доступ</title>
  <style>
    body { font: 16px/1.5 system-ui, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 16px; }
    input { padding: 8px; width: 130px; margin: 4px; }
    button { padding: 9px 13px; margin: 4px; cursor: pointer; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f1f2f5; color: #222; padding: 16px; border-radius: 8px; min-height: 90px; }
    .note { padding: 12px; border-left: 4px solid #e3a122; background: #f1f2f5; color: #222; }
  </style>
</head>
<body>
  <h1>Frontend C — частичный доступ</h1>
  <p class="note">Разрешены только GET и POST. PUT, PATCH и DELETE блокируются браузером на preflight.</p>
  <p>Текущий Origin: <strong id="origin"></strong></p>
  <label>ID <input id="id" type="number" min="1" value="1"></label>
  <label>Название <input id="name" value="Новый товар"></label>
  <label>Цена <input id="price" type="number" min="0" value="1000"></label>
  <div>
    <button onclick="request('GET', '/products')">GET все</button>
    <button onclick="request('GET', '/products/' + idValue())">GET по ID</button>
    <button onclick="request('POST', '/products')">POST создать</button>
    <button onclick="request('PUT', '/products/' + idValue())">PUT заменить</button>
    <button onclick="request('PATCH', '/products/' + idValue())">PATCH изменить цену</button>
    <button onclick="request('DELETE', '/products/' + idValue())">DELETE удалить</button>
  </div>
  <h3>Результат fetch()</h3>
  <pre id="result">Нажми любую кнопку. Ошибки CORS смотри также в DevTools → Console / Network.</pre>
  <script>
    const API = 'http://localhost:8888';
    document.getElementById('origin').textContent = location.origin;
    const idValue = () => document.getElementById('id').value;
    const payload = () => ({
      name: document.getElementById('name').value,
      price: Number(document.getElementById('price').value)
    });

    async function request(method, path) {
      const output = document.getElementById('result');
      output.textContent = `${method} ${path} → запрос...`;
      const options = { method };
      if (['POST', 'PUT', 'PATCH'].includes(method)) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify(method === 'PATCH' ? { price: payload().price } : payload());
      }
      try {
        const response = await fetch(API + path, options);
        const text = await response.text();
        output.textContent = `${method} ${path}
HTTP ${response.status}
${text}`;
      } catch (error) {
        output.textContent = `${method} ${path}
${error.name}: ${error.message}

Проверь DevTools → Console. Если сервер запущен, это может быть блокировка CORS.`;
      }
    }
  </script>
</body>
</html>
```