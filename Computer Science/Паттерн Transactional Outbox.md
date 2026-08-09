**Transactional Outbox** — паттерн для надёжной публикации событий в брокер сообщений (`Kafka`, `RabbitMQ` и т. д.) одновременно с изменением данных в БД.

Он решает классическую проблему:

> Как гарантировать, что изменение в БД произошло **и соответствующее событие обязательно будет опубликовано**, несмотря на падение сервиса между этими действиями?

---

## Проблема

Допустим сервис создаёт заказ:

```text
Order Service
    │
    ├── PostgreSQL
    │
    └── Kafka
```

Наивная реализация:

```python
await db.create_order(order)

await kafka.send(
    "order-created",
    order
)
```

Физически это **две независимые операции**:

```text
1. COMMIT в PostgreSQL
2. отправка сообщения в Kafka
```

И между ними процесс может упасть.

Например:

```text
BEGIN

INSERT order
COMMIT
       │
       │  ← процесс упал здесь
       X

Kafka.send(...)
```

Получаем:

```text
PostgreSQL:

order_id = 123
✓ существует


Kafka:

OrderCreated(123)
✗ отсутствует
```

Другие сервисы никогда не узнают о создании заказа.

---

# А если отправлять Kafka сначала?

```python
await kafka.send(...)

await db.create_order(...)
```

Теперь возможна обратная проблема:

```text
Kafka.send()
✓

DB INSERT
X ошибка
```

Получаем:

```text
Kafka:

OrderCreated(123)
✓


PostgreSQL:

Order 123
✗ не существует
```

То есть consumer получил событие о сущности, которой на самом деле нет.

---

# Почему нельзя просто сделать одну транзакцию

PostgreSQL умеет:

```sql
BEGIN;

INSERT ...;
UPDATE ...;

COMMIT;
```

Потому что обе операции выполняются **одной СУБД**.

Но:

```text
PostgreSQL
+
Kafka
```

— разные системы.

Обычная SQL-транзакция не может сделать:

```text
BEGIN

PostgreSQL INSERT
Kafka SEND

COMMIT everything
```

без использования гораздо более сложных distributed transaction mechanisms вроде 2PC.

Transactional Outbox предлагает более простой подход.

---

# Главная идея Outbox

Вместо:

```text
DB update
+
Kafka send
```

мы внутри **одной DB transaction** выполняем:

```text
DB update
+
INSERT event INTO outbox
```

То есть появляется дополнительная таблица:

```text
outbox
```

Например:

```sql
CREATE TABLE outbox (
    id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    aggregate_id BIGINT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    published_at TIMESTAMP
);
```

Теперь создание заказа:

```sql
BEGIN;

INSERT INTO orders (
    id,
    user_id,
    amount
)
VALUES (
    123,
    42,
    1000
);

INSERT INTO outbox (
    id,
    event_type,
    aggregate_id,
    payload,
    created_at
)
VALUES (
    gen_random_uuid(),
    'OrderCreated',
    123,
    '{"order_id": 123}',
    NOW()
);

COMMIT;
```

Ключевой момент:

```text
orders
+
outbox

находятся в одной PostgreSQL
```

Поэтому они участвуют **в одной ACID transaction**.

Результат возможен только такой:

```text
Order создан
+
Outbox event создан
```

или:

```text
ни Order
ни Outbox event
```

Состояния:

```text
Order есть
Outbox event нет
```

уже не возникнет.

---

# Что происходит дальше

Отдельный worker читает `outbox`:

```text
PostgreSQL
     │
     │ SELECT unpublished events
     ▼
Outbox Worker
     │
     │ publish
     ▼
Kafka
```

Например:

```python
while True:
    events = await load_unpublished_events()

    for event in events:
        await kafka.send(
            topic=event.event_type,
            value=event.payload,
        )

        await mark_as_published(event.id)
```

Полная архитектура:

```text
                Order Service

                     │
                     ▼

              PostgreSQL

        ┌────────────┴─────────────┐
        │                          │
     orders                     outbox
        │                          │
        │                     OrderCreated
        │                          │
        │                          ▼
        │                    Outbox Worker
        │                          │
        │                          ▼
        │                        Kafka
        │                          │
        │                  ┌───────┼───────┐
        │                  ▼       ▼       ▼
        │              Billing  Email  Analytics
```

---

# Самое важное: Outbox не даёт exactly-once delivery

Допустим worker сделал:

```text
1. отправил event в Kafka
2. должен отметить published_at
```

Но упал между этими действиями:

```text
Kafka.send(event)
✓

        ← CRASH

UPDATE outbox
SET published_at = ...
X
```

После рестарта worker снова увидит:

```text
published_at IS NULL
```

и отправит сообщение повторно.

Получаем:

```text
Kafka:

OrderCreated #123
OrderCreated #123
```

Поэтому Transactional Outbox обычно даёт:

```text
at-least-once delivery
```

а consumer должен быть **идемпотентным**.

---

# Idempotent Consumer

Каждое событие должно иметь уникальный `event_id`:

```json
{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "OrderCreated",
    "order_id": 123
}
```

Consumer хранит обработанные IDs:

```text
processed_events

event_id
------------------------------------
550e8400-e29b-41d4-a716-446655440000
```

При повторном событии:

```python
if await already_processed(event.id):
    return
```

Получается:

```text
event приходит 2 раза
        ↓
consumer применяет бизнес-операцию 1 раз
```

Это очень распространённая связка:

```text
Transactional Outbox
+
At-least-once
+
Idempotent Consumer
```

---

# Два способа доставлять Outbox в Kafka

Есть два основных варианта.

|Вариант|Как работает|
|---|---|
|Polling Publisher|приложение периодически делает `SELECT` из `outbox`|
|CDC|изменения `outbox` читаются из WAL/binlog|

---

# 1. Polling Publisher

Worker периодически выполняет:

```sql
SELECT *
FROM outbox
WHERE published_at IS NULL
ORDER BY created_at
LIMIT 100;
```

Потом:

```text
publish Kafka
↓
mark published
```

Очень простой вариант.

Но появляются вопросы:

```text
как несколько workers поделят строки?
как не отправить одно событие одновременно?
как чистить outbox?
какой polling interval?
```

В PostgreSQL часто используют:

```sql
SELECT *
FROM outbox
WHERE published_at IS NULL
FOR UPDATE SKIP LOCKED
LIMIT 100;
```

Это позволяет нескольким workers безопасно делить работу:

```text
Worker A → events 1-100

Worker B → events 101-200

Worker C → events 201-300
```

---

# 2. Outbox + CDC

Более production-oriented вариант:

```text
Application
     │
     ▼
PostgreSQL
     │
     │ WAL
     ▼
Debezium
     │
     ▼
Kafka Connect
     │
     ▼
Kafka
```

Application только пишет:

```text
business table
+
outbox
```

в одной транзакции.

После этого CDC-инструмент читает изменения из transaction log БД.

Например:

```text
PostgreSQL WAL
```

и публикует outbox events в Kafka.

Тогда application вообще не делает:

```python
kafka.send(...)
```

---

# Почему CDC-вариант хорош

Убирается polling:

```text
SELECT every 500 ms
```

и вместо этого изменения читаются непосредственно из WAL.

Можно получить меньшую latency и меньше нагрузки на таблицу.

Очень распространённый стек:

```text
PostgreSQL
+
Outbox table
+
Debezium
+
Kafka Connect
+
Kafka
```

---

# Где должна создаваться Outbox запись

Очень важно:

```text
изменение бизнес-данных
+
outbox INSERT
```

должны находиться **в одной DB transaction**.

Например Python:

```python
async with connection.transaction():

    await connection.execute(
        """
        INSERT INTO orders(...)
        VALUES (...)
        """
    )

    await connection.execute(
        """
        INSERT INTO outbox(...)
        VALUES (...)
        """
    )
```

Так делать правильно.

А вот так:

```python
await create_order()

await create_outbox_event()
```

если это две отдельные transactions — уже ломает главную гарантию паттерна.

---

# Outbox и Domain Events

Часто service сначала создаёт domain event:

```python
event = OrderCreated(
    order_id=123,
    user_id=42,
)
```

И внутри transaction сохраняет:

```text
Order
+
OrderCreated event
```

Outbox становится persistent storage для событий, которые должны выйти за пределы сервиса.

---

# Что обычно хранится в outbox

Например:

```sql
CREATE TABLE outbox (
    id UUID PRIMARY KEY,

    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,

    event_type TEXT NOT NULL,

    payload JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,

    published_at TIMESTAMPTZ
);
```

Пример строки:

```text
id
550e8400...

aggregate_type
Order

aggregate_id
123

event_type
OrderCreated

payload
{
    "order_id": 123,
    "user_id": 42,
    "amount": 1000
}

created_at
2026-08-09 19:00

published_at
NULL
```

---

# Что такое aggregate_id

Это ID сущности, породившей событие.

Например:

```text
Order 123
```

создал:

```text
OrderCreated
OrderPaid
OrderShipped
OrderCancelled
```

Все события имеют:

```text
aggregate_id = 123
```

Это особенно полезно для Kafka partitioning:

```text
Kafka key = order_id
```

Тогда все события одного заказа попадут в одну partition:

```text
partition 7:

OrderCreated(123)
OrderPaid(123)
OrderShipped(123)
```

и Kafka сохраняет их порядок внутри partition.

---

# Очистка Outbox

Таблица будет постоянно расти:

```text
1 million
10 million
100 million events
```

Поэтому нужна cleanup policy.

Например:

```sql
DELETE FROM outbox
WHERE published_at < NOW() - INTERVAL '7 days';
```

Или:

```text
partitioning by date
+
drop old partitions
```

При CDC часто таблицу также регулярно очищают после того, как downstream гарантированно получил изменения.

---

# Что Outbox гарантирует, а что нет

Transactional Outbox гарантирует главное:

```text
если business transaction committed
→ event точно записан в outbox
```

Он **не гарантирует автоматически**:

```text
ровно одну доставку
ровно одну обработку
порядок между всеми событиями системы
отсутствие задержек
```

Эти задачи решаются отдельно:

```text
idempotency
partitioning
consumer offsets
retries
DLQ
monitoring
```

---

# Что будет при разных падениях

### Сервис упал до COMMIT

```text
orders ❌
outbox ❌
Kafka ❌
```

Всё согласованно.

### Сервис упал после COMMIT

```text
orders ✓
outbox ✓
Kafka пока ❌
```

После восстановления publisher/CDC всё равно доставит событие.

### Publisher отправил Kafka и упал до отметки published

```text
orders ✓
outbox ✓
Kafka ✓
```

После рестарта событие может быть отправлено ещё раз.

Поэтому consumer должен быть идемпотентным.
