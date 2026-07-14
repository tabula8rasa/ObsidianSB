---

tags:

- databases
    
- indexes
    
- postgresql
    
- mysql
    
- soft-delete
    

---
## Проблема

При использовании паттерна **Soft Delete** строки не удаляются физически, а помечаются специальным флагом:

```sql
is_deleted = true
```

Предположим, поле `email` должно быть уникальным только среди активных пользователей.

Обычный уникальный индекс:

```sql
CREATE UNIQUE INDEX users_email_uq
ON users (email);
```

учитывает все строки, включая удалённые. Поэтому зарегистрировать нового пользователя с email, который уже находится в «корзине», не получится.

---

## PostgreSQL: частичный уникальный индекс

PostgreSQL позволяет включать в индекс только строки, соответствующие условию:

```sql
CREATE UNIQUE INDEX users_active_email_uq
ON users (email)
WHERE is_deleted = false;
```

Теперь:

- среди активных пользователей `email` остаётся уникальным;
    
- soft-deleted записи не участвуют в проверке;
    
- email удалённого пользователя можно использовать повторно.
    

Если вместо флага используется дата удаления:

```sql
CREATE UNIQUE INDEX users_active_email_uq
ON users (email)
WHERE deleted_at IS NULL;
```

Такой индекс называется **частичным индексом** — `partial index`.

---

## MySQL: эмуляция через Generated Column

MySQL не поддерживает условие `WHERE` в команде `CREATE INDEX`. Аналогичное поведение можно реализовать через вычисляемую колонку:

```sql
ALTER TABLE users
ADD COLUMN active_email VARCHAR(255)
GENERATED ALWAYS AS (
    CASE
        WHEN is_deleted = false THEN email
        ELSE NULL
    END
) STORED;
```

После этого создаётся уникальный индекс:

```sql
CREATE UNIQUE INDEX users_active_email_uq
ON users (active_email);
```

Для активных пользователей `active_email` содержит email. Для удалённых записей значение равно `NULL`.

Поскольку уникальный индекс MySQL допускает несколько значений `NULL`, soft-deleted строки не конфликтуют между собой.

---

## Почему составной индекс может не подойти

Иногда предлагают использовать индекс:

```sql
CREATE UNIQUE INDEX users_email_deleted_uq
ON users (email, is_deleted);
```

Но при булевом `is_deleted` он допускает только:

- одну активную строку с конкретным email;
    
- одну удалённую строку с тем же email.
    

Повторное удаление и создание пользователя с этим email приведёт к конфликту между удалёнными строками.

Составной индекс лучше работает с уникальной меткой удаления:

```sql
CREATE UNIQUE INDEX users_email_deleted_at_uq
ON users (email, deleted_at);
```

Однако его поведение зависит от СУБД и правил обработки `NULL`. Поэтому частичный индекс или Generated Column обычно понятнее и надёжнее.
