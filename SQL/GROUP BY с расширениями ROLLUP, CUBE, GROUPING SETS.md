Да, в PostgreSQL это есть: `GROUPING SETS`, `ROLLUP` и `CUBE` поддерживаются как расширенные возможности `GROUP BY`. Документация PostgreSQL прямо описывает их в `GROUP BY`, а feature matrix отдельно отмечает поддержку `GROUPING SETS, CUBE and ROLLUP`. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))

Сначала обычный `GROUP BY`.  
Он собирает строки в группы по указанным полям и считает агрегаты по каждой группе. Например:

```sql
SELECT region, product, SUM(amount)
FROM sales
GROUP BY region, product;
```

Тут получится одна строка на каждую пару `(region, product)`. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-select.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: SELECT"))

Расширения нужны, когда ты хочешь не одну детализацию, а сразу несколько уровней агрегации одним запросом: например, по `(region, product)`, потом только по `region`, и ещё общий итог. PostgreSQL объясняет это так: наличие `GROUPING SETS`, `ROLLUP` или `CUBE` эквивалентно выполнению нескольких `GROUP BY` и объединению результатов через `UNION ALL`. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-select.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: SELECT"))

Возьмём пример таблицы продаж:

```sql
sales(region, product, amount)
```

и данные мысленно такие:

- North, A, 10
    
- North, B, 20
    
- South, A, 15
    
- South, B, 5
    

## 1. `ROLLUP`

`ROLLUP(a, b)` строит иерархию итогов справа налево. Для двух полей это эквивалентно таким группировкам:

- `(a, b)`
    
- `(a)`
    
- `()`
    

То есть для `ROLLUP(region, product)` будут:

- суммы по каждому товару в каждом регионе,
    
- итог по региону,
    
- общий итог по всей таблице. PostgreSQL в документации показывает, что `ROLLUP` разворачивается именно в набор grouping sets такого вида. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))
    

Пример:

```sql
SELECT region, product, SUM(amount)
FROM sales
GROUP BY ROLLUP (region, product)
ORDER BY region, product;
```

Идея результата:

- `North, A -> 10`
    
- `North, B -> 20`
    
- `North, NULL -> 30` — итог по North
    
- `South, A -> 15`
    
- `South, B -> 5`
    
- `South, NULL -> 20` — итог по South
    
- `NULL, NULL -> 50` — общий итог
    

Здесь `NULL` в полях группировки означает “уровень итога”, а не обязательно настоящий `NULL` из данных. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))

## 2. `CUBE`

`CUBE(a, b)` строит все возможные комбинации группировок. Для двух полей это:

- `(a, b)`
    
- `(a)`
    
- `(b)`
    
- `()`
    

То есть для `CUBE(region, product)` будут:

- детальные суммы по региону и товару,
    
- итоги только по регионам,
    
- итоги только по товарам,
    
- общий итог. PostgreSQL прямо описывает `CUBE` как перечисление всех комбинаций grouping sets. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))
    

Пример:

```sql
SELECT region, product, SUM(amount)
FROM sales
GROUP BY CUBE (region, product)
ORDER BY region, product;
```

Дополнительно к `ROLLUP` здесь появятся строки вроде:

- `NULL, A -> 25` — итог по товару A по всем регионам
    
- `NULL, B -> 25` — итог по товару B по всем регионам
    

То есть `CUBE` шире, чем `ROLLUP`: он считает не только иерархические итоги, но вообще все срезы по указанным измерениям. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))

## 3. `GROUPING SETS`

Это самый общий и гибкий вариант. Ты сам перечисляешь, какие именно группировки нужны. Каждая подгруппа внутри `GROUPING SETS` интерпретируется так, как если бы она стояла отдельным `GROUP BY`, а пустой набор `()` означает общий итог. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))

Пример:

```sql
SELECT region, product, SUM(amount)
FROM sales
GROUP BY GROUPING SETS (
    (region, product),
    (region),
    (product),
    ()
)
ORDER BY region, product;
```

Это по смыслу почти то же, что `CUBE(region, product)`, потому что ты явно перечислил все 4 нужных набора группировки. Но сила `GROUPING SETS` в том, что можно взять только нужные комбинации. Например:

```sql
SELECT region, product, SUM(amount)
FROM sales
GROUP BY GROUPING SETS (
    (region, product),
    (region),
    ()
);
```

Это уже аналог `ROLLUP(region, product)`: детали, итоги по регионам и общий итог — без итогов только по товарам. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))

## Как это запомнить

- `ROLLUP` — иерархия итогов.  
    Пример: `страна -> город -> общий итог`. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))
    
- `CUBE` — все возможные срезы.  
    Пример: по стране и городу, только по стране, только по городу, общий итог. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))
    
- `GROUPING SETS` — ручной выбор нужных группировок. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))
    

## Почему в результате появляются `NULL`

Потому что PostgreSQL помечает агрегированные уровни таким образом. Чтобы отличать “это настоящий `NULL` в данных” от “это итоговая строка”, есть операция `GROUPING(...)`, которая используется вместе с grouping sets и родственными конструкциями для различения таких строк. ([PostgreSQL](https://www.postgresql.org/docs/9.5/functions-aggregate.html?utm_source=chatgpt.com "Documentation: 9.5: Aggregate Functions"))

Пример:

```sql
SELECT
    region,
    product,
    GROUPING(region)  AS g_region,
    GROUPING(product) AS g_product,
    SUM(amount)
FROM sales
GROUP BY ROLLUP(region, product);
```

Если `GROUPING(product) = 1`, это значит, что `product` в этой строке не детальное значение, а агрегированный уровень. ([PostgreSQL](https://www.postgresql.org/docs/9.5/functions-aggregate.html?utm_source=chatgpt.com "Documentation: 9.5: Aggregate Functions"))

## Очень коротко

Да, в PostgreSQL это есть.  
Смысл такой:

- обычный `GROUP BY` — одна схема группировки;
    
- `ROLLUP` — иерархические итоги;
    
- `CUBE` — все комбинации итогов;
    
- `GROUPING SETS` — ты сам задаёшь нужные варианты. ([PostgreSQL](https://www.postgresql.org/docs/current/queries-table-expressions.html?utm_source=chatgpt.com "PostgreSQL: Documentation: 18: 7.2. Table Expressions"))
    

Могу сразу дать тебе один готовый `DDL + DML + SELECT` для PostgreSQL, чтобы ты сам прогнал `ROLLUP`, `CUBE` и `GROUPING SETS` в онлайн-редакторе.