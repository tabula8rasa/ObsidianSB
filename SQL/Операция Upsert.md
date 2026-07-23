`ON CONFLICT` позволяет обработать ситуацию, когда `INSERT` нарушает ограничение уникальности. Такой запрос часто называют **UPSERT**: вставить новую строку или обновить существующую.

## Игнорирование конфликта

```sql
INSERT INTO users (id, email)
VALUES (1, 'user@example.com')
ON CONFLICT (id) DO NOTHING;
```

Если строка с таким `id` уже существует, PostgreSQL не выполнит вставку и не вернёт ошибку.

## Обновление при конфликте

```sql
INSERT INTO users (id, email, name)
VALUES (1, 'user@example.com', 'Ivan')
ON CONFLICT (id)
DO UPDATE SET
    email = EXCLUDED.email,
    name = EXCLUDED.name;
```

`EXCLUDED` содержит значения строки, которую пытались вставить:

```sql
EXCLUDED.email
EXCLUDED.name
```

Обновить `name` только тогда, когда новое значение действительно отличается от уже сохранённого:

```sql
INSERT INTO users (id, name)
VALUES (1, 'Ivan')
ON CONFLICT (id)
DO UPDATE SET
    name = EXCLUDED.name
WHERE users.name IS DISTINCT FROM EXCLUDED.name;
```

## Конфликт по нескольким столбцам

```sql
INSERT INTO subscriptions (user_id, service_id, status)
VALUES (10, 5, 'active')
ON CONFLICT (user_id, service_id)
DO UPDATE SET
    status = EXCLUDED.status;
```

Для указанных столбцов должен существовать подходящий `UNIQUE`-индекс или ограничение уникальности.

```sql
UNIQUE (user_id, service_id)
```

## Указание ограничения

```sql
INSERT INTO users (id, email)
VALUES (1, 'user@example.com')
ON CONFLICT ON CONSTRAINT users_email_key
DO NOTHING;
```

## Получение результата

```sql
INSERT INTO users (id, email)
VALUES (1, 'user@example.com')
ON CONFLICT (id)
DO UPDATE SET email = EXCLUDED.email
RETURNING *;
```

`RETURNING` возвращает строку, которая была вставлена или обновлена.