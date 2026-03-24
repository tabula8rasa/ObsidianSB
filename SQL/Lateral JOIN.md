Латеральный join в PostgreSQL — это способ сделать подзапрос в `FROM` зависимым от строки, которая уже выбрана слева.

Проще говоря:

- обычный подзапрос в `FROM` работает сам по себе;
    
- `LATERAL`-подзапрос выполняется **для каждой строки левой таблицы отдельно** и может брать из неё значения.
    

Это удобно, когда нужно:

- для каждой строки найти **последнюю запись**,
    
- выбрать **top 1 / top N** связанных строк,
    
- передать значение из текущей строки в функцию или подзапрос.
    

---

## Идея на простом языке

Представь две таблицы:

- `customers` — клиенты
    
- `orders` — заказы
    

Ты хочешь для **каждого клиента** взять **его самый последний заказ**.

Без `LATERAL` это неудобно, потому что подзапрос в `FROM` не видит текущего клиента слева.

С `LATERAL` можно написать так:

```sql
SELECT c.id, c.name, o.id AS last_order_id, o.created_at
FROM customers c
LEFT JOIN LATERAL (
    SELECT id, created_at
    FROM orders
    WHERE customer_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) o ON true;
```

Здесь важный момент:

```sql
WHERE customer_id = c.id
```

Подзапрос справа использует `c.id` из таблицы `customers`, которая стоит слева. Это и есть смысл `LATERAL`.

---

# Чем отличается от обычного JOIN

## Обычный подзапрос в `FROM`

Так писать нельзя:

```sql
SELECT *
FROM customers c
LEFT JOIN (
    SELECT *
    FROM orders
    WHERE customer_id = c.id
) o ON true;
```

Ошибка будет потому, что подзапрос внутри `JOIN (...)` не видит `c.id`.

---

## `LATERAL`

А вот так уже можно:

```sql
SELECT *
FROM customers c
LEFT JOIN LATERAL (
    SELECT *
    FROM orders
    WHERE customer_id = c.id
) o ON true;
```

Почему? Потому что `LATERAL` разрешает подзапросу ссылаться на таблицы, перечисленные раньше в `FROM`.

---

# Как это мысленно работает

PostgreSQL делает примерно так:

1. берёт одну строку из `customers`,
    
2. подставляет её значения в lateral-подзапрос,
    
3. выполняет этот подзапрос,
    
4. присоединяет результат,
    
5. переходит к следующему клиенту.
    

То есть это похоже на цикл:

```text
для каждого клиента:
    выполнить подзапрос только для него
    присоединить результат
```

---

# Когда использовать `CROSS JOIN LATERAL`, а когда `LEFT JOIN LATERAL`

## `CROSS JOIN LATERAL`

Используй, когда строка справа **обязана быть**.

Если подзапрос ничего не вернул, строка слева пропадёт.

Пример:

```sql
SELECT c.name, o.id
FROM customers c
CROSS JOIN LATERAL (
    SELECT id
    FROM orders
    WHERE customer_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) o;
```

Если у клиента нет заказов, его не будет в результате.

---

## `LEFT JOIN LATERAL`

Используй, когда хочешь оставить все строки слева, даже если справа ничего нет.

Пример:

```sql
SELECT c.name, o.id
FROM customers c
LEFT JOIN LATERAL (
    SELECT id
    FROM orders
    WHERE customer_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) o ON true;
```

Если заказов нет, поля из `o` будут `NULL`.

`ON true` пишут потому, что условие связи уже фактически находится внутри подзапроса.

---

# Пример 1. Последний заказ каждого клиента

Таблицы:

### customers

|id|name|
|---|---|
|1|Иван|
|2|Анна|
|3|Олег|

### orders

|id|customer_id|created_at|amount|
|---|--:|---|--:|
|10|1|2026-03-01|1000|
|11|1|2026-03-05|1500|
|12|2|2026-03-03|700|

Запрос:

```sql
SELECT
    c.id,
    c.name,
    o.id AS last_order_id,
    o.created_at,
    o.amount
FROM customers c
LEFT JOIN LATERAL (
    SELECT id, created_at, amount
    FROM orders
    WHERE customer_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) o ON true
ORDER BY c.id;
```

Результат:

|id|name|last_order_id|created_at|amount|
|---|---|--:|---|--:|
|1|Иван|11|2026-03-05|1500|
|2|Анна|12|2026-03-03|700|
|3|Олег|NULL|NULL|NULL|

Почему это удобно:

- не нужен отдельный `window function`,
    
- очень наглядно,
    
- легко делать `LIMIT 1`, `LIMIT 3`, сортировку и фильтрацию прямо по каждой строке слева.
    

---

# Пример 2. Top 2 заказа для каждого клиента

```sql
SELECT
    c.name,
    o.id AS order_id,
    o.created_at,
    o.amount
FROM customers c
LEFT JOIN LATERAL (
    SELECT id, created_at, amount
    FROM orders
    WHERE customer_id = c.id
    ORDER BY amount DESC
    LIMIT 2
) o ON true
ORDER BY c.name, o.amount DESC;
```

Здесь для каждого клиента берутся его 2 самых дорогих заказа.

Это частая задача, и `LATERAL` для неё очень удобен.

---

# Пример 3. Использование с функцией

`LATERAL` часто применяют с функциями, которым нужен параметр из текущей строки.

Например:

```sql
SELECT t.n, g.val
FROM (VALUES (2), (4), (1)) AS t(n)
CROSS JOIN LATERAL generate_series(1, t.n) AS g(val);
```

Результат:

|n|val|
|--:|--:|
|2|1|
|2|2|
|4|1|
|4|2|
|4|3|
|4|4|
|1|1|

Для каждой строки `t` функция `generate_series` вызывается со своим `t.n`.

---

# Когда `LATERAL` особенно полезен

Он хорош, когда справа нужно:

- взять `LIMIT 1` или `LIMIT N` для каждой строки,
    
- отсортировать связанные записи по-своему,
    
- вызвать функцию с аргументом из текущей строки,
    
- распаковать JSON/массивы по каждой строке,
    
- избежать более тяжёлой и менее читаемой конструкции.
    

---

# Короткое сравнение с оконными функциями

Иногда ту же задачу можно решить через `row_number()`:

```sql
SELECT *
FROM (
    SELECT
        c.name,
        o.id,
        o.created_at,
        row_number() OVER (
            PARTITION BY c.id
            ORDER BY o.created_at DESC
        ) AS rn
    FROM customers c
    LEFT JOIN orders o ON o.customer_id = c.id
) t
WHERE rn = 1;
```

Это тоже нормально.

Но `LATERAL` часто:

- проще читается,
    
- удобнее для `LIMIT`,
    
- удобнее, когда справа сложная логика.
    

---

# Главное правило

`LATERAL` позволяет правой части `JOIN` видеть левую часть.

Запомнить можно так:

> `LATERAL` = “подзапрос справа зависит от текущей строки слева”.

---

# Полный пример DDL + DML для онлайн PostgreSQL

Ниже готовый код. Его можно целиком вставить в онлайн PostgreSQL и выполнить.

```sql
-- Очистка, если таблицы уже были
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

-- DDL
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    created_at DATE NOT NULL,
    amount NUMERIC(10,2) NOT NULL
);

-- DML
INSERT INTO customers (name) VALUES
('Иван'),
('Анна'),
('Олег'),
('Мария');

INSERT INTO orders (customer_id, created_at, amount) VALUES
(1, DATE '2026-03-01', 1000.00),
(1, DATE '2026-03-05', 1500.00),
(1, DATE '2026-03-10', 900.00),
(2, DATE '2026-03-03', 700.00),
(2, DATE '2026-03-08', 1200.00),
(4, DATE '2026-03-02', 500.00);

-- Проверка данных
SELECT * FROM customers ORDER BY id;
SELECT * FROM orders ORDER BY customer_id, created_at;

-- 1. Последний заказ каждого клиента
SELECT
    c.id AS customer_id,
    c.name,
    o.id AS last_order_id,
    o.created_at,
    o.amount
FROM customers c
LEFT JOIN LATERAL (
    SELECT id, created_at, amount
    FROM orders
    WHERE customer_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) o ON true
ORDER BY c.id;

-- 2. Два самых дорогих заказа каждого клиента
SELECT
    c.id AS customer_id,
    c.name,
    o.id AS order_id,
    o.created_at,
    o.amount
FROM customers c
LEFT JOIN LATERAL (
    SELECT id, created_at, amount
    FROM orders
    WHERE customer_id = c.id
    ORDER BY amount DESC
    LIMIT 2
) o ON true
ORDER BY c.id, o.amount DESC;

-- 3. Только те клиенты, у которых есть хотя бы один заказ
--    Здесь CROSS JOIN LATERAL, поэтому клиенты без заказов исчезнут
SELECT
    c.id AS customer_id,
    c.name,
    o.id AS last_order_id,
    o.created_at,
    o.amount
FROM customers c
CROSS JOIN LATERAL (
    SELECT id, created_at, amount
    FROM orders
    WHERE customer_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) o
ORDER BY c.id;
```

---

# Что ты увидишь в этом примере

### В запросе 1

Все клиенты останутся в результате.  
У `Олега` будет `NULL`, потому что у него нет заказов.

### В запросе 2

Для каждого клиента покажутся максимум 2 заказа.

### В запросе 3

`Олег` исчезнет, потому что `CROSS JOIN LATERAL` требует, чтобы справа что-то нашлось.

---

# Самая короткая памятка

- `LATERAL` нужен, когда подзапрос справа использует значения слева.
    
- `LEFT JOIN LATERAL` — сохранить все строки слева.
    
- `CROSS JOIN LATERAL` — оставить только те, для которых справа нашлись строки.
    
- Частый кейс: “для каждой строки взять top 1 / top N связанных строк”.
    
