# Expand–Contract Pattern

**Expand–Contract** — паттерн для безопасного изменения схемы БД без остановки production-сервиса.

Главная идея: **не делать breaking change за один деплой**. Старая и новая структура некоторое время существуют одновременно, чтобы разные версии приложения могли работать параллельно.

Допустим, нужно переименовать колонку:

```text
users.email → users.email_address
```

Нельзя сразу выполнить:

```sql
ALTER TABLE users
RENAME COLUMN email TO email_address;
```

При rolling deployment некоторое время одновременно работают разные версии приложения:

```text
Service v1
Service v2
Service v2
Service v1
```

Старые экземпляры сервиса всё ещё обращаются к `email`. Если колонку мгновенно переименовать, они начнут падать.

Поэтому переход выполняется постепенно:

```text
OLD
 ↓
OLD + NEW
 ↓
NEW
```

---

## 1. Старый сервис

Изначально таблица выглядит так:

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT
);
```

Старый сервис знает только о колонке `email`.

### Запись

```python
import asyncpg


async def update_user_email(
    pool: asyncpg.Pool,
    user_id: int,
    new_email: str,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET email = $1
            WHERE id = $2
            """,
            new_email,
            user_id,
        )
```

### Чтение

```python
async def get_user_email(
    pool: asyncpg.Pool,
    user_id: int,
) -> str | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT email
            FROM users
            WHERE id = $1
            """,
            user_id,
        )

    return row["email"] if row else None
```

То есть:

```text
WRITE → email
READ  ← email
```

---

## 2. Expand

Сначала добавляем новую колонку, **не удаляя старую**:

```sql
ALTER TABLE users
ADD COLUMN email_address TEXT;
```

Теперь таблица содержит:

```text
users

id
email
email_address
```

Старый сервис продолжает работать, потому что колонка `email` никуда не исчезла.

---

## 3. Промежуточный сервис — Dual Write

Теперь деплоим промежуточную версию приложения, которая знает сразу о двух колонках.

Главное изменение — **dual write**: при изменении email значение записывается одновременно в старую и новую колонку.

### Запись

```python
async def update_user_email(
    pool: asyncpg.Pool,
    user_id: int,
    new_email: str,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET email = $1,
                email_address = $1
            WHERE id = $2
            """,
            new_email,
            user_id,
        )
```

Теперь:

```text
              ┌→ email
WRITE value ──┤
              └→ email_address
```

Но чтение пока оставляем через старую колонку.

### Чтение

```python
async def get_user_email(
    pool: asyncpg.Pool,
    user_id: int,
) -> str | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT email
            FROM users
            WHERE id = $1
            """,
            user_id,
        )

    return row["email"] if row else None
```

Получаем:

```text
WRITE → email
      → email_address

READ  ← email
```

Это позволяет старой и промежуточной версиям сервиса работать одновременно.

Например:

```text
old service
intermediate service
old service
intermediate service
```

Старому сервису по-прежнему нужна колонка `email`, поэтому удалять её пока нельзя.

---

## 4. Backfill старых данных

После включения dual write все **новые изменения** записываются сразу в обе колонки.

Но старые строки были созданы до появления `email_address`:

```text
id | email        | email_address
---|--------------|--------------
1  | re@gmail.com | NULL
2  | tr@gmail.com | NULL
```

Поэтому старые данные нужно перенести:

```text
email → email_address
```

Например, batch'ами по 1000 строк:

```sql
UPDATE users
SET email_address = email
WHERE id IN (
    SELECT id
    FROM users
    WHERE email_address IS NULL
    ORDER BY id
    LIMIT 1000
);
```

Запрос выполняется повторно, пока строк с:

```text
email_address IS NULL
```

не останется.

После backfill:

```text
id | email        | email_address
---|--------------|----------------
1  | re@gmail.com | re@gmail.com
2  | tr@gmail.com | tr@gmail.com
```

На больших production-таблицах backfill обычно выполняют небольшими batch'ами, чтобы не создавать одну огромную транзакцию и лишнюю нагрузку на БД.

---

## 5. Переключение чтения

После backfill мы убедились, что `email_address` заполнен для всех нужных записей.

Теперь можно перевести **чтение** на новую колонку.

Запись пока остаётся двойной.

### Запись

```python
async def update_user_email(
    pool: asyncpg.Pool,
    user_id: int,
    new_email: str,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET email = $1,
                email_address = $1
            WHERE id = $2
            """,
            new_email,
            user_id,
        )
```

### Чтение

```python
async def get_user_email(
    pool: asyncpg.Pool,
    user_id: int,
) -> str | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT email_address
            FROM users
            WHERE id = $1
            """,
            user_id,
        )

    return row["email_address"] if row else None
```

Теперь:

```text
WRITE → email
      → email_address

READ  ← email_address
```

Почему мы всё ещё записываем в старый `email`?

Потому что во время rolling deployment где-то ещё может работать старая версия приложения:

```text
OLD SERVICE

READ ← email
```

Если новый сервис перестанет обновлять `email`, старые экземпляры начнут читать устаревшие данные.

---

## 6. Новый сервис

Когда гарантировано, что старые версии приложения больше не работают, зависимость от `email` можно полностью убрать.

Теперь и запись, и чтение работают только через `email_address`.

### Запись

```python
async def update_user_email(
    pool: asyncpg.Pool,
    user_id: int,
    new_email: str,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET email_address = $1
            WHERE id = $2
            """,
            new_email,
            user_id,
        )
```

### Чтение

```python
async def get_user_email(
    pool: asyncpg.Pool,
    user_id: int,
) -> str | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT email_address
            FROM users
            WHERE id = $1
            """,
            user_id,
        )

    return row["email_address"] if row else None
```

Теперь:

```text
WRITE → email_address
READ  ← email_address
```

Старая колонка `email` приложению больше не нужна.

---

## 7. Contract

Когда ни одна версия приложения больше не использует `email`, старую колонку можно удалить:

```sql
ALTER TABLE users
DROP COLUMN email;
```

Окончательная схема:

```text
users

id
email_address
```

---

# Полный процесс

```text
1. OLD SERVICE

WRITE → email
READ  ← email


2. EXPAND

email
email_address


3. INTERMEDIATE SERVICE

WRITE → email
      → email_address

READ  ← email


4. BACKFILL

email → email_address


5. SWITCH READS

WRITE → email
      → email_address

READ  ← email_address


6. NEW SERVICE

WRITE → email_address
READ  ← email_address


7. CONTRACT

DROP email
```

То есть обычное на первый взгляд переименование:

```text
email → email_address
```

в production превращается в несколько безопасных шагов:

```text
email
 ↓
email + email_address
 ↓
dual write
 ↓
backfill
 ↓
read email_address
 ↓
write only email_address
 ↓
DROP email
 ↓
email_address
```

## Главное

**Expand–Contract = добавить новое → начать поддерживать старое и новое одновременно → перенести данные → переключить чтение → переключить запись → удалить старое.**

Старую структуру нельзя удалять, пока существует хотя бы одна работающая версия приложения, которая от неё зависит.

Именно поэтому Expand–Contract особенно полезен при **rolling deployment**, когда разные версии сервиса некоторое время работают одновременно.