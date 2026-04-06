## Что это
**UPSERT** — это операция:
- если строки **нет** → `INSERT`
- если строка **есть** → `UPDATE`

Делается через:

```sql
INSERT ... ON CONFLICT ... DO UPDATE
````

---

## Базовый шаблон

```sql
INSERT INTO users (id, name, email, updated_at)
VALUES (1, 'Ivan', 'ivan@example.com', NOW())
ON CONFLICT (id)
DO UPDATE SET
    name = EXCLUDED.name,
    email = EXCLUDED.email,
    updated_at = NOW();
```

---

## Как это работает

- `ON CONFLICT (id)` — если конфликт по `id`
    
- `DO UPDATE` — обновить существующую строку
    
- `EXCLUDED.name` — новое значение из `VALUES`
---

## Важно

`ON CONFLICT (...)` работает только по полю, на котором есть:

- `PRIMARY KEY`
    
- или `UNIQUE`
    

Пример:

```sql
CREATE TABLE users (
    id bigint PRIMARY KEY,
    name text,
    email text UNIQUE,
    updated_at timestamp
);
```

---

## Проверка по email

```sql
INSERT INTO users (name, email, updated_at)
VALUES ('Ivan', 'ivan@example.com', NOW())
ON CONFLICT (email)
DO UPDATE SET
    name = EXCLUDED.name,
    updated_at = NOW();
```

---

## Ничего не делать при конфликте

```sql
INSERT INTO users (id, name, email)
VALUES (1, 'Ivan', 'ivan@example.com')
ON CONFLICT (id)
DO NOTHING;
```