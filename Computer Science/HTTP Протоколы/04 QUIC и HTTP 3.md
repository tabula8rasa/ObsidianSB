## Почему HTTP/3 не использует TCP

HTTP/2 решил проблему HTTP-level Head-of-Line Blocking с помощью streams и multiplexing.

Но все HTTP/2 streams всё равно находятся внутри одного TCP byte stream.

Если участок TCP-потока потерян:

```text
[received][received][LOST][received][received]
```

TCP не отдаёт приложению последующие байты как непрерывное продолжение, пока дырка не восстановлена.

Из-за этого независимые HTTP/2 streams могут ждать друг друга на уровне TCP.

---

# Почему не сделать «новый TCP»

Интернет-инфраструктура десятилетиями строилась вокруг:

```text
TCP
UDP
```

Между клиентом и сервером могут находиться:

- NAT;
- firewall;
- router;
- load balancer;
- ISP equipment;
- corporate gateway.

Новый IP transport protocol мог бы плохо проходить через существующие сети.

UDP уже широко поддерживается.

Поэтому QUIC реализует современный транспорт поверх UDP.

---

# Стек HTTP/3

```text
HTTP/3
  ↓
QUIC
  ↓
UDP
  ↓
IP
```

Важно:

> HTTP/3 не становится ненадёжным только потому, что UDP сам по себе ненадёжный.

UDP предоставляет datagrams.

Надёжность реализует QUIC.

---

# Что делает QUIC

QUIC реализует функции, которые обычно ожидаются от полноценного транспорта:

- надёжную доставку;
- acknowledgements;
- retransmission;
- congestion control;
- flow control;
- streams;
- connection management;
- encryption;
- интеграцию TLS 1.3.

То есть HTTP/3 не использует «сырой UDP» как замену TCP без дополнительных механизмов.

---

# QUIC Streams

Ключевая идея QUIC — независимые streams существуют уже **на транспортном уровне**.

```text
QUIC connection
│
├── stream A
├── stream B
└── stream C
```

Допустим в stream A потеряны данные:

```text
A1 ✓
A2 X
A3 ✓
```

Но stream B доставлен полностью:

```text
B1 ✓
B2 ✓
B3 ✓
```

QUIC может удерживать порядок внутри stream A, но при этом позволить stream B продолжить работу.

Упрощённо:

```text
Stream A ─────X──── waiting ─────>

Stream B ────────────────────────>

Stream C ────────────────────────>
```

Это важное отличие от HTTP/2 поверх TCP.

---

# Что именно устраняется

HTTP/3 не означает, что packet loss исчез.

Потери всё ещё происходят.

Но потеря данных одного QUIC stream не обязана блокировать доставку данных других независимых streams на том же уровне, как это происходит из-за единого ordered byte stream TCP.

---

# TLS и QUIC

В традиционном HTTPS:

```text
HTTP/2
↓
TLS
↓
TCP
```

В QUIC криптографическое согласование тесно встроено в сам транспорт.

QUIC использует TLS 1.3.

Это позволяет уменьшить количество последовательных сетевых этапов при создании защищённого соединения.

---

# 0-RTT

При повторном соединении с ранее известным сервером QUIC/TLS может в некоторых случаях позволить отправить application data очень рано с использованием 0-RTT.

Это оптимизация latency.

Но 0-RTT имеет особенности безопасности, прежде всего replay risk, поэтому не любые операции должны бездумно выполняться как 0-RTT.

---

# Connection Migration

TCP-соединение практически связано с сетевым 4-tuple:

```text
source IP
source port
destination IP
destination port
```

Если телефон переключился:

```text
Wi-Fi → 5G
```

его IP может измениться.

Обычное TCP-соединение часто приходится устанавливать заново.

QUIC использует Connection IDs и способен поддерживать migration между сетевыми путями.

Упрощённо:

```text
Wi-Fi
IP A
   \
    QUIC connection ID XYZ
                 \
                  SERVER

после переключения:

5G
IP B
   \
    QUIC connection ID XYZ
                 \
                  SERVER
```

Сам факт смены IP не обязан означать создание полностью нового логического QUIC-соединения.

---

# HTTP/3 и HTTP-семантика

HTTP/3 не изобретает заново:

```text
GET
POST
headers
status codes
body
```

Приложение всё ещё работает с HTTP-семантикой.

Меняется wire-level транспорт.

Можно представить один и тот же запрос:

```http
GET /users
```

как:

```text
HTTP/1.1
↓
TLS
↓
TCP
```

или:

```text
HTTP/2 frames
↓
TLS
↓
TCP
```

или:

```text
HTTP/3 frames
↓
QUIC streams
↓
UDP
```

---

# HTTP/3 не означает «всегда HTTP/3»

Сервер может поддерживать HTTP/3, но конкретное соединение может использовать HTTP/2 или HTTP/1.1.

Причины:

- клиент не поддерживает HTTP/3;
- UDP заблокирован;
- middlebox мешает QUIC;
- политика клиента;
- fallback после ошибки.

Поэтому production-сервер обычно предоставляет несколько вариантов.

Подробнее: [[06 HTTP в production - FastAPI, reverse proxy и версии протокола]].

---

# Главное

Эволюция:

```text
HTTP/1.1
persistent TCP connection
      ↓
HTTP/2
несколько HTTP streams
внутри одного TCP
      ↓
остаётся TCP HOL blocking
      ↓
HTTP/3
HTTP поверх QUIC
      ↓
независимые transport streams
```

QUIC следует воспринимать не как «HTTP через ненадёжный UDP», а как отдельный современный транспорт, который использует UDP datagrams как низкоуровневую основу.
