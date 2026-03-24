**Data-modifying CTE** или по-простому **writeable CTE**: когда внутри `WITH` стоит не `SELECT`, а `INSERT`, `UPDATE` или `DELETE`, и чаще всего вместе с `RETURNING`. В PostgreSQL это поддерживается официально. В `WITH` можно использовать `INSERT`, `UPDATE`, `DELETE` и `MERGE`; если у модифицирующего запроса есть `RETURNING`, именно его результат становится временной таблицей, доступной дальше в основном запросе. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

## Идея

Обычный CTE:

```sql
WITH x AS (
    SELECT ...
)
SELECT * FROM x;
```

Модифицирующий CTE:

```sql
WITH x AS (
    UPDATE ...
    RETURNING ...
)
SELECT * FROM x;
```

Смысл такой:

1. внутри `WITH` ты меняешь данные;
    
2. через `RETURNING` сразу получаешь изменённые строки;
    
3. эти строки можно тут же использовать в следующем `SELECT`, `INSERT`, `UPDATE` или `DELETE`. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))
    

---

# 1. `WITH ... INSERT ... RETURNING`

Самый частый сценарий — вставили строку и сразу забрали её `id`.

```sql
WITH new_user AS (
    INSERT INTO users(name, email)
    VALUES ('Иван', 'ivan@example.com')
    RETURNING id, name, email
)
SELECT *
FROM new_user;
```

Что происходит:

- `INSERT` создаёт строку;
    
- `RETURNING` возвращает вставленные значения;
    
- основной `SELECT` читает их как временную таблицу. `RETURNING` особенно полезен, чтобы без отдельного запроса получить сгенерированные по умолчанию значения, например `serial`/`identity`-id. ([PostgreSQL](https://www.postgresql.org/docs/current/dml-returning.html?utm_source=chatgpt.com "Documentation: 18: 6.4. Returning Data from Modified Rows"))
    

### Практический пример: вставка в одну таблицу и логирование в другую

```sql
WITH ins AS (
    INSERT INTO users(name, email)
    VALUES ('Анна', 'anna@example.com')
    RETURNING id, email
)
INSERT INTO user_log(user_id, action, details)
SELECT id, 'create', email
FROM ins;
```

То есть одна команда:

- вставила пользователя,
    
- тут же записала лог,
    
- без второго запроса с поиском нужного `id`. ([PostgreSQL](https://www.postgresql.org/docs/current/dml-returning.html?utm_source=chatgpt.com "Documentation: 18: 6.4. Returning Data from Modified Rows"))
    

---

# 2. `WITH ... UPDATE ... RETURNING`

Можно обновить строки и сразу передать изменённые записи дальше.

```sql
WITH upd AS (
    UPDATE products
    SET price = price * 1.10
    WHERE category = 'books'
    RETURNING id, name, price
)
SELECT *
FROM upd;
```

`UPDATE ... RETURNING` возвращает строки, которые реально были обновлены. По умолчанию в `RETURNING` доступны новые, уже обновлённые значения. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-update.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: UPDATE"))

### Пример: обновить и записать аудит

```sql
WITH upd AS (
    UPDATE accounts
    SET balance = balance - 100
    WHERE id = 1
    RETURNING id, balance
)
INSERT INTO audit(account_id, action, new_balance)
SELECT id, 'debit', balance
FROM upd;
```

---

# 3. `WITH ... DELETE ... RETURNING`

Очень удобно для “переместить удалённые строки в архив”.

Официальный пример PostgreSQL именно такой: удалить строки из одной таблицы и сразу вставить их в другую через `DELETE ... RETURNING`. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

```sql
WITH moved_rows AS (
    DELETE FROM products
    WHERE date >= DATE '2025-01-01'
      AND date <  DATE '2025-02-01'
    RETURNING *
)
INSERT INTO products_log
SELECT * FROM moved_rows;
```

Смысл:

- строки удалились из `products`,
    
- их старые значения вернулись через `RETURNING`,
    
- потом сразу вставились в `products_log`. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))
    

---

# Что делает `RETURNING`

Очень важный момент:

**временной таблицей становится не сама изменяемая таблица, а результат `RETURNING`.**  
Если `RETURNING` нет, запрос всё равно выполнится, но на него нельзя будет сослаться дальше как на таблицу. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

Пример без `RETURNING`:

```sql
WITH t AS (
    DELETE FROM foo
)
DELETE FROM bar;
```

Такой запрос допустим:

- `DELETE FROM foo` выполнится,
    
- `DELETE FROM bar` тоже выполнится,
    
- но `t` нельзя читать в основном запросе, потому что `RETURNING` не было. PostgreSQL прямо это оговаривает. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))
    

---

# Важные нюансы

## 1. Data-modifying CTE должен быть привязан к верхнеуровневому запросу

То есть модифицирующие команды в `WITH` разрешены только у `WITH`, который относится к top-level statement. Это отдельное правило PostgreSQL. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

---

## 2. Выполняется ровно один раз и до конца

В отличие от `SELECT`-CTE, который может вычисляться настолько, насколько его реально читает основной запрос, модифицирующий CTE выполняется **ровно один раз и полностью**, даже если основной запрос потом не прочитал ни одной строки из его результата. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

Это важно запомнить:

- `SELECT` в `WITH` — ленивее;
    
- `INSERT/UPDATE/DELETE` в `WITH` — нет, они выполняются полностью. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))
    

---

## 3. Подзапросы в `WITH` и основной запрос работают в одной snapshot

PostgreSQL пишет, что подзапросы в таком `WITH` выполняются “concurrently” друг с другом и с основным запросом, а все они используют **одну и ту же snapshot**. Поэтому они не видят изменения друг друга через чтение базовых таблиц; обмен данными между ними идёт именно через `RETURNING`. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

Это один из самых важных нюансов.

### Неправильная интуиция

Можно подумать так:

```sql
WITH a AS (
    UPDATE items
    SET qty = qty - 1
    WHERE id = 10
    RETURNING *
)
SELECT *
FROM items
WHERE id = 10;
```

Интуитивно хочется ожидать, что `SELECT` ниже увидит уже изменённую строку. Но правило про единую snapshot означает, что надёжно передавать результат надо через `RETURNING` из `a`, а не надеяться “увидеть” изменение через повторное чтение таблицы. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

Правильнее так:

```sql
WITH a AS (
    UPDATE items
    SET qty = qty - 1
    WHERE id = 10
    RETURNING id, qty
)
SELECT *
FROM a;
```

---

## 4. Не стоит пытаться изменить одну и ту же строку дважды в одной команде

PostgreSQL отдельно предупреждает, что если в одной общей команде попытаться несколько раз изменить одну и ту же строку, результат непредсказуем с точки зрения того, какая модификация реально сработает. На практике так делать не надо. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

---

## 5. Рекурсивная самоссылка для модифицирующего CTE не разрешена

Рекурсивно ссылаться на сам модифицирующий CTE нельзя. PostgreSQL это прямо запрещает. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

---

# Как это обычно спрашивают на экзамене

Можно отвечать так:

> Модифицирующий CTE — это `WITH`, внутри которого используется `INSERT`, `UPDATE` или `DELETE` с `RETURNING`.  
> `RETURNING` формирует временный результирующий набор, который можно использовать дальше в том же SQL-операторе.  
> Это удобно для цепочек “изменить данные и сразу использовать изменённые строки”: логирование, перенос в архив, каскадная вставка, получение id после insert.  
> В PostgreSQL такие CTE выполняются ровно один раз и до конца, а обмен результатами между частями команды делается через `RETURNING`. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html?utm_source=chatgpt.com "18: 7.8. WITH Queries (Common Table Expressions)"))

---

# Короткие шаблоны

## Insert + returning

```sql
WITH x AS (
    INSERT INTO t(col1, col2)
    VALUES (...)
    RETURNING id, col1
)
SELECT * FROM x;
```

## Update + returning

```sql
WITH x AS (
    UPDATE t
    SET col = ...
    WHERE ...
    RETURNING id, col
)
SELECT * FROM x;
```

## Delete + returning

```sql
WITH x AS (
    DELETE FROM t
    WHERE ...
    RETURNING *
)
INSERT INTO t_archive
SELECT * FROM x;
```

---

# Самая короткая суть

**`WITH + INSERT/UPDATE/DELETE + RETURNING`** нужен, когда ты хочешь в одной команде:

- изменить данные,
    
- сразу получить изменённые строки,
    
- и тут же передать их дальше.
    