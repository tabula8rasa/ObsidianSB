В PostgreSQL пользовательские типы данных — это типы, которые ты создаёшь сам поверх стандартной системы типов. Базово PostgreSQL позволяет добавлять новые типы через `CREATE TYPE`, а домены — через `CREATE DOMAIN`. У `CREATE TYPE` есть пять форм: **composite**, **enum**, **range**, **base** и **shell**. Отдельно **domain** тоже считается пользовательским типом, но создаётся другой командой. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtype.html "PostgreSQL: Documentation: 18: CREATE TYPE"))

Самые важные для обычного SQL-пользователя — это такие:

**1. Domain**  
Домен — это тип на основе другого типа, но с дополнительными ограничениями. Он ведёт себя почти как исходный тип, но при записи значения проверяет свои `CHECK`-условия. Это удобно, когда один и тот же бизнес-ограничитель нужен во многих таблицах. ([PostgreSQL](https://www.postgresql.org/docs/current/domains.html "PostgreSQL: Documentation: 18: 8.18. Domain Types"))

Пример:

```sql
CREATE DOMAIN positive_price AS numeric
CHECK (VALUE > 0);

CREATE TABLE products (
    id bigint,
    price positive_price
);
```

Здесь `price` по сути `numeric`, но отрицательное значение вставить уже нельзя. В документации даже приведён аналогичный пример с доменом для положительных целых чисел. ([PostgreSQL](https://www.postgresql.org/docs/current/domains.html "PostgreSQL: Documentation: 18: 8.18. Domain Types"))

Это самый практичный тип, когда нужно сказать:  
“у нас есть не просто `text`, а, например, `email_text`”,  
“не просто `numeric`, а `positive_price`”,  
“не просто `integer`, а `rating_1_5`”. ([PostgreSQL](https://www.postgresql.org/docs/current/domains.html "PostgreSQL: Documentation: 18: 8.18. Domain Types"))

**2. Enum**  
`enum` — это конечный, заранее заданный и **упорядоченный** набор значений. Хорошо подходит для статусов, категорий, уровней доступа, стадий процесса. Значения перечисляются один раз при создании типа, и их порядок важен для сравнений. ([PostgreSQL](https://www.postgresql.org/docs/current/datatype-enum.html "PostgreSQL: Documentation: 18: 8.7. Enumerated Types"))

Пример:

```sql
CREATE TYPE order_status AS ENUM ('new', 'paid', 'shipped', 'done');

CREATE TABLE orders (
    id bigint,
    status order_status
);
```

Теперь в `status` можно записать только одно из четырёх значений. При этом порядок тоже работает:

```sql
SELECT *
FROM orders
WHERE status > 'new';
```

Порядок сравнения будет таким, в каком значения были перечислены при `CREATE TYPE`. ([PostgreSQL](https://www.postgresql.org/docs/current/datatype-enum.html "PostgreSQL: Documentation: 18: 8.7. Enumerated Types"))

`enum` удобен, когда набор значений небольшой и относительно стабильный. Для очень “живых” справочников чаще берут отдельную таблицу-справочник, а не `enum`. Последнее — уже практический совет, а не правило PostgreSQL.

**3. Composite type**  
Составной тип — это структура вида “строка с полями”. PostgreSQL описывает его как список имён полей и их типов. Такой тип можно использовать как тип колонки, аргумент функции или возвращаемое значение функции. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtype.html "PostgreSQL: Documentation: 18: CREATE TYPE"))

Пример:

```sql
CREATE TYPE address_t AS (
    city text,
    street text,
    house text
);

CREATE TABLE customers (
    id bigint,
    name text,
    address address_t
);
```

Вставка может выглядеть так:

```sql
INSERT INTO customers
VALUES (1, 'Иван', ROW('Москва', 'Тверская', '10'));
```

Composite type полезен, когда у тебя есть логически единый объект с несколькими полями. ([PostgreSQL](https://www.postgresql.org/docs/current/rowtypes.html "PostgreSQL: Documentation: 18: 8.16. Composite Types"))

Важный нюанс: когда ты создаёшь обычную таблицу, PostgreSQL **автоматически** создаёт и составной тип строки этой таблицы. Но ограничения таблицы вроде `CHECK` и `NOT NULL` не “переезжают” автоматически во внешний composite type, если ты используешь его отдельно от таблицы. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html?utm_source=chatgpt.com "Documentation: 18: CREATE TABLE"))

**4. Range type**  
Range type — это тип “интервал значений”: не одно значение, а диапазон. Подходит для периодов времени, интервалов цен, диапазонов номеров, уровней и т.д. У range есть subtype — базовый тип элементов диапазона, и этот subtype должен иметь полный порядок. ([PostgreSQL](https://www.postgresql.org/docs/current/rangetypes.html "PostgreSQL: Documentation: 18: 8.17. Range Types"))

Встроенные range-типы у PostgreSQL уже есть, например `int4range`, `numrange`, `tsrange`, `tstzrange`, `daterange`. Кроме того, можно создавать и свои range-типы. У каждого range-типа есть соответствующий multirange-тип. ([PostgreSQL](https://www.postgresql.org/docs/current/rangetypes.html "PostgreSQL: Documentation: 18: 8.17. Range Types"))

Пример использования встроенного range:

```sql
CREATE TABLE reservation (
    room int,
    during tsrange
);

INSERT INTO reservation
VALUES (101, '[2026-03-24 10:00, 2026-03-24 11:00)');
```

У range есть специальные операторы и функции, например проверка вхождения, пересечения, верхней границы и пустоты диапазона. В документации приведены примеры вроде `@>`, `&&`, `upper(...)`, `isempty(...)`. ([PostgreSQL](https://www.postgresql.org/docs/current/rangetypes.html "PostgreSQL: Documentation: 18: 8.17. Range Types"))

Это очень удобный класс типов, если ты работаешь с временными окнами и интервалами.

**5. Base type**  
Base type — это уже низкоуровневая история: ты создаёшь полностью новый скалярный тип и обязан описать для него как минимум функции ввода и вывода, а также другие параметры хранения и поведения. Синтаксис `CREATE TYPE` для base type включает `INPUT`, `OUTPUT`, длину хранения, выравнивание и прочие детали. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtype.html "PostgreSQL: Documentation: 18: CREATE TYPE"))

Пример формы:

```sql
CREATE TYPE mytype (
    INPUT = mytype_in,
    OUTPUT = mytype_out
);
```

На практике base type обычно нужен не обычному SQL-пользователю, а при разработке расширений и серверной логики.

**6. Shell type**  
Shell type — это просто “заглушка” по имени типа, чтобы потом доопределить настоящий тип. PostgreSQL пишет, что shell type нужен как forward reference, в частности при создании range и base types. Это технический механизм, а не тип для хранения бизнес-данных. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtype.html "PostgreSQL: Documentation: 18: CREATE TYPE"))

---

Как это запомнить по смыслу:

- **domain** — “тот же тип, но с правилами”
    
- **enum** — “фиксированный список значений”
    
- **composite** — “мини-структура / record”
    
- **range** — “интервал”
    
- **base** — “свой низкоуровневый скалярный тип”
    
- **shell** — “временная заглушка для определения типа” ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtype.html "PostgreSQL: Documentation: 18: CREATE TYPE"))
    

Ещё полезно знать, что PostgreSQL поддерживает массивы не только встроенных типов, но и пользовательских: можно делать массивы `enum`, `domain`, `composite`, `range` и так далее. ([PostgreSQL](https://www.postgresql.org/docs/current/arrays.html "PostgreSQL: Documentation: 18: 8.15. Arrays"))

### Что чаще всего используют на практике

Чаще всего в обычных БД-проектах реально применяют:

- **domain** — для переиспользуемых ограничений,
    
- **enum** — для статусов,
    
- **composite** — реже, но полезно для функций и вложенных структур,
    
- **range** — когда есть периоды и интервалы. ([PostgreSQL](https://www.postgresql.org/docs/current/domains.html "PostgreSQL: Documentation: 18: 8.18. Domain Types"))
    

Если совсем коротко:  
в PostgreSQL пользовательские типы нужны, чтобы сделать модель данных **более предметной**. Вместо “просто `text` и `int`” ты можешь хранить “статус заказа”, “валидную цену”, “адрес как единый объект” или “период бронирования” как самостоятельные типы. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtype.html "PostgreSQL: Documentation: 18: CREATE TYPE"))