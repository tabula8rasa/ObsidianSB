# HTTP/2 — streams и multiplexing

## Зачем появился HTTP/2

HTTP/1.1 умеет переиспользовать TCP-соединение, но плохо решает задачу большого количества параллельных ресурсов.

Исторический workaround — несколько TCP-соединений.

HTTP/2 предлагает другую модель:

> использовать одно TCP-соединение, но передавать внутри него несколько независимых логических HTTP-потоков — streams.

---

# Stream

**HTTP/2 stream** — логический двунаправленный канал внутри одного HTTP/2 connection.

Например клиент одновременно делает:

```text
GET /large.jpg
GET /style.css
GET /app.js
```

HTTP/2 может представить их как:

```text
TCP connection
│
├── Stream 1 → /large.jpg
├── Stream 3 → /style.css
└── Stream 5 → /app.js
```

Это не отдельные TCP-соединения.

Все streams существуют внутри одного TCP connection.

---

# HTTP/2 Frames

HTTP/2 не передаёт сообщения как обычный текст HTTP/1.1.

Он использует бинарные **frames**.

У frame есть служебная информация, включая:

```text
Length
Type
Flags
Stream ID
Payload
```

Условно:

```text
Frame:
stream_id = 3
type      = DATA
length    = 16384
payload   = ...
```

Благодаря `stream_id` получатель знает, к какому HTTP/2 stream относятся данные.

---

# Multiplexing

Пусть есть три streams:

```text
Stream A → большая картинка
Stream B → маленький CSS
Stream C → JavaScript
```

HTTP/2 frames могут передаваться вперемешку:

```text
[A1][B1][A2][C1][B2][A3][C2]...
```

HTTP/2 layer на стороне получателя читает `stream_id` и собирает:

```text
Stream A:
A1 + A2 + A3 + ...

Stream B:
B1 + B2

Stream C:
C1 + C2
```

Это называется **multiplexing**.

---

# Почему это быстрее HTTP/1.1

Пусть:

```text
A = 10 MB image
B = 30 KB CSS
C = 50 KB JavaScript
```

Упрощённый HTTP/1.1 на одном соединении:

```text
TIME →

A ████████████████████████████████████████

B                                         ██

C                                           ███
```

HTTP/2:

```text
TIME →

A ████──████──████──████──████──...

B ──██

C ────███
```

Маленький CSS может полностью приехать и начать обрабатываться, пока большая картинка ещё загружается.

---

# TCP не подтверждает каждый frame по отдельности

Важно не путать HTTP/2 frames и TCP reliability.

TCP не работает по схеме:

```text
send frame A1
wait ACK
send frame B1
wait ACK
```

TCP имеет sliding window и может отправлять много данных до получения подтверждений.

Поэтому frames разных streams действительно могут эффективно multiplex'иться.

---

# HTTP/2 frame ≠ TCP segment

Уровни:

```text
HTTP/2 Stream
      ↓
HTTP/2 Frames
      ↓
TCP byte stream
      ↓
TCP Segments
      ↓
IP Packets
```

Нет обязательного соответствия:

```text
1 HTTP/2 frame = 1 TCP segment
```

Один HTTP/2 frame может быть разбит на несколько TCP segments.

Несколько маленьких HTTP/2 frames могут оказаться в одном TCP segment.

TCP видит только байты и не понимает `stream_id`.

---

# Когда stream считается законченным

HTTP/2 имеет собственное framing.

Последний frame в определённом направлении stream может иметь флаг:

```text
END_STREAM
```

Например:

```text
Stream 5

HEADERS
↓
DATA
↓
DATA
↓
DATA + END_STREAM
```

После этого HTTP/2 знает, что в этом направлении stream завершён.

Это намного явнее, чем попытка угадывать границы по TCP segments.

---

# Проблема HTTP/2: TCP Head-of-Line Blocking

HTTP/2 streams логически независимы, но физически все они лежат внутри **одного TCP byte stream**.

Допустим TCP получил:

```text
segment containing A data     ✓
segment containing B data     ✓
next part                     X lost
later C data                  ✓
later B data                  ✓
```

Более поздние TCP-байты уже могли приехать на машину.

Но TCP обязан отдавать приложению непрерывный упорядоченный byte stream.

```text
receive buffer:

[bytes][bytes][ LOST ][later bytes][later bytes]
               ↑
             дырка
```

HTTP/2 layer находится выше TCP и пока не получает непрерывное продолжение после дырки.

Из-за этого могут временно остановиться сразу несколько HTTP/2 streams, даже если потерянные данные логически относились только к одному из них.

Это и есть **TCP-level Head-of-Line Blocking**.

---

# HTTP-level HOL и TCP-level HOL

Важно различать.

## HTTP/1.x

Проблема может возникнуть на уровне модели HTTP:

```text
Response A должен закончиться
↓
только затем Response B может занять своё место
```

## HTTP/2

HTTP/2 устраняет эту проблему с помощью multiplexing.

Но остаётся транспортная проблема:

```text
все streams
↓
один TCP byte stream
↓
потеря участка TCP
↓
временная блокировка последующих TCP-байтов
```

Именно эту проблему в значительной степени решает QUIC: [[04 QUIC и HTTP 3]].

---

# Header compression

HTTP/2 использует HPACK для сжатия HTTP headers.

Это полезно, потому что запросы часто повторяют одни и те же поля:

```text
Host
User-Agent
Accept
Cookie
Authorization
...
```

Вместо постоянной полной передачи повторяющихся строк используется более компактное представление.

---

# Главное

HTTP/2 можно запомнить так:

```text
один TCP connection
        │
        ├── stream 1
        ├── stream 3
        ├── stream 5
        └── stream 7
```

Frames разных streams перемешиваются внутри TCP byte stream.

Получатель сортирует их по `stream_id`.

Это позволяет маленьким запросам/ответам завершаться, пока большие ещё продолжаются.

Но потеря участка TCP-потока всё ещё способна временно остановить весь HTTP/2 connection.
