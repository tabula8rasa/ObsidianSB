# HTTP framing — как определяется конец сообщения

## Главная проблема

TCP не знает, где заканчивается HTTP-запрос.

Для TCP:

```text
request 1 + request 2 + request 3
```

выглядят просто как:

```text
byte byte byte byte byte byte byte ...
```

Нет понятия:

```text
«это последний TCP segment запроса»
```

TCP segment — транспортная деталь.

Границы HTTP-сообщений определяет HTTP.

---

# Почему нельзя ориентироваться на TCP segments

Пусть HTTP-запрос занимает 5000 байт.

TCP может передать его:

```text
segment 1 → 1400 bytes
segment 2 → 1400 bytes
segment 3 → 1400 bytes
segment 4 →  800 bytes
```

Но при другой ситуации segmentation может быть другой.

HTTP-parser не должен зависеть от количества TCP segments.

Также один `recv()` не равен одному segment и не равен одному HTTP message.

---

# HTTP/1.1: конец headers

HTTP/1.1 headers заканчиваются пустой строкой:

```text
\r\n\r\n
```

Например:

```http
POST /users HTTP/1.1\r\n
Host: example.com\r\n
Content-Length: 16\r\n
\r\n
{"name":"Ilya"}
```

После `\r\n\r\n` HTTP-parser знает:

> headers закончились, дальше начинается body.

---

# Content-Length

Один из способов определить конец body:

```http
Content-Length: 16
```

После окончания headers parser должен получить ровно указанное число байтов body.

Условно:

```text
получено 5/16   → ещё ждём
получено 12/16  → ещё ждём
получено 16/16  → body полностью получен
```

HTTP-parser ориентируется на длину сообщения, а не на то, сколько TCP segments пришло.

---

# Chunked Transfer Encoding

В HTTP/1.1 также исторически существует:

```http
Transfer-Encoding: chunked
```

Каждый chunk сообщает свою длину.

Упрощённо:

```text
5
HELLO
6
 WORLD
0
```

Нулевой chunk сигнализирует завершение chunked body.

Это HTTP-level framing.

---

# Connection close

В некоторых HTTP/1.x сценариях окончание body может определяться закрытием соединения.

Это менее удобно для persistent connections, потому что соединение нельзя затем переиспользовать.

---

# HTTP/2 framing

HTTP/2 решает задачу иначе.

Он передаёт бинарные frames.

У каждого frame есть длина и stream ID.

Условно:

```text
Length
Type
Flags
Stream ID
Payload
```

Поэтому parser знает:

1. сколько байтов занимает текущий frame;
2. к какому stream он относится;
3. какие семантические flags установлены.

---

# END_STREAM

HTTP/2 использует флаг:

```text
END_STREAM
```

чтобы обозначить завершение stream в соответствующем направлении.

Например:

```text
HEADERS
DATA
DATA
DATA + END_STREAM
```

После этого HTTP/2 layer знает, что больше данных в этом направлении stream не будет.

---

# Одновременные сообщения в HTTP/2

TCP получает один byte stream:

```text
[S1 HEADERS]
[S3 HEADERS]
[S1 DATA]
[S5 HEADERS]
[S3 DATA END_STREAM]
[S1 DATA]
[S5 DATA END_STREAM]
[S1 DATA END_STREAM]
```

HTTP/2 parser смотрит на Stream ID:

```text
Stream 1 → ...
Stream 3 → complete
Stream 5 → complete
```

Stream 3 можно считать завершённым и обрабатывать, хотя Stream 1 ещё не завершён.

Именно это невозможно получить простой последовательной моделью HTTP/1.1 без дополнительных соединений.

---

# HTTP/3 framing

HTTP/3 также имеет framing на уровне HTTP/3/QUIC streams.

TCP там вообще отсутствует.

QUIC уже предоставляет streams, а HTTP/3 передаёт внутри них HTTP semantics.

Конец логического stream определяется механизмами QUIC/HTTP/3, а не закрытием UDP datagram.

---

# Framing как общая идея

Если транспорт предоставляет byte stream, прикладной протокол должен решить:

```text
где начинается сообщение?
где заканчиваются headers?
сколько body?
где заканчивается message?
```

Типовые подходы:

```text
length prefix
delimiter
fixed-length message
chunk framing
connection close
protocol frames
```

HTTP использует разные механизмы в разных версиях.

---

# Главное

Нельзя задавать вопрос:

> Как TCP узнаёт, какой segment последний в HTTP-запросе?

Правильная модель:

> TCP вообще не определяет границы HTTP-запроса. HTTP-parser поверх TCP сам понимает границы сообщения по правилам HTTP framing.
