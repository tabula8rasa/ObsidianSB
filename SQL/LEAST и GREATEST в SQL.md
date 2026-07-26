
Функции `LEAST` и `GREATEST` сравнивают несколько значений в пределах одной строки.

- `LEAST(...)` — возвращает **минимальное** значение.
    
- `GREATEST(...)` — возвращает **максимальное** значение.
    

## Синтаксис

```sql
LEAST(column_name_1, column_name_2, ...)
GREATEST(column_name_1, column_name_2, ...)
```

## Пример с числами
```sql
SELECT
    LEAST(10, 25, 5) AS min_value,
    GREATEST(10, 25, 5) AS max_value;
```

Результат:

|min_value|max_value|
|---|---|
|5|25|
## Пример с колонками
```sql
SELECT
    product_name,
    LEAST(store_price, online_price) AS lowest_price,
    GREATEST(store_price, online_price) AS highest_price
FROM products;
```

Функции сравнивают значения `store_price` и `online_price` **для каждой строки отдельно**.

## Ограничение значения

Например, не позволить скидке быть больше `50`:

```sql
SELECT LEAST(discount, 50)
FROM products;
```

Или установить минимальную цену `100`:

```sql
SELECT GREATEST(price, 100)
FROM products;
```

## Работа с датами

```sql
SELECT
    LEAST(created_at, updated_at) AS earlier_date,
    GREATEST(created_at, updated_at) AS later_date
FROM documents;
```

## Работа с NULL

Поведение `NULL` зависит от СУБД.

В PostgreSQL значения `NULL` игнорируются, если присутствует хотя бы одно ненулевое значение:

```sql
SELECT GREATEST(10, NULL, 20);
-- 20
```

В некоторых других СУБД наличие `NULL` может привести к результату `NULL`. Для предсказуемого поведения можно использовать `COALESCE`:

```sql
SELECT GREATEST(
    COALESCE(price_1, 0),
    COALESCE(price_2, 0)
);
```

> [!NOTE]  
> `MIN` и `MAX` обычно сравнивают значения из **разных строк**, а `LEAST` и `GREATEST` — несколько значений **внутри одной строки**.