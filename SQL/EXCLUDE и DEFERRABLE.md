
- `EXCLUDE` — **вид ограничения**;
    
- `DEFERRABLE` — **режим проверки ограничения**. ([PostgreSQL](https://www.postgresql.org/docs/current/ddl-constraints.html "PostgreSQL: Documentation: 18: 5.5. Constraints"))
    

То есть **`DEFERRABLE EXCLUSION constraint`** — это просто **exclusion constraint, которое можно проверять не сразу, а позже — в конце транзакции**. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html "PostgreSQL: Documentation: 18: CREATE TABLE"))

## 1. Что такое `EXCLUDE`

`EXCLUDE` задаёт правило вида:

> для любых двух строк не должно быть ситуации, когда **все указанные сравнения одновременно дают `TRUE`**.

Официальная формулировка PostgreSQL такая: для любых двух строк хотя бы одно из сравнений по указанным операторам должно вернуть `FALSE` или `NULL`. ([PostgreSQL](https://www.postgresql.org/docs/current/ddl-constraints.html "PostgreSQL: Documentation: 18: 5.5. Constraints"))

Простой смысл:

- `UNIQUE` запрещает одинаковые значения по `=`
    
- `EXCLUDE` умеет запрещать не только равенство, но и, например, **пересечение диапазонов** через оператор `&&`. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html?utm_source=chatgpt.com "Documentation: 18: CREATE TABLE"))
    

### Типичный пример

Нельзя бронировать **одну и ту же комнату** на **пересекающееся время**. Для этого обычно используют диапазоны `tsrange` и оператор пересечения `&&`. ([PostgreSQL](https://www.postgresql.org/docs/current/rangetypes.html?utm_source=chatgpt.com "Documentation: 18: 8.17. Range Types"))

## 2. Что такое `DEFERRABLE`

`DEFERRABLE` означает, что проверку ограничения **можно отложить** до конца транзакции через `SET CONSTRAINTS`.  
Если ограничение `NOT DEFERRABLE`, оно проверяется сразу после каждой команды. Это поведение по умолчанию. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html "PostgreSQL: Documentation: 18: CREATE TABLE"))

В PostgreSQL `DEFERRABLE` поддерживают только:

- `UNIQUE`
    
- `PRIMARY KEY`
    
- `EXCLUDE`
    
- `REFERENCES` (foreign key).  
    `CHECK` и `NOT NULL` откладывать нельзя. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html "PostgreSQL: Documentation: 18: CREATE TABLE"))
    

Также можно указать:

- `INITIALLY IMMEDIATE` — по умолчанию проверять сразу;
    
- `INITIALLY DEFERRED` — по умолчанию проверять в конце транзакции. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html "PostgreSQL: Documentation: 18: CREATE TABLE"))
    

## 3. Что значит вместе: `DEFERRABLE EXCLUDE`

Это значит:

> правило “строки не должны конфликтовать по exclusion-условию” существует,  
> но его можно проверить не после каждого `INSERT/UPDATE`, а в конце транзакции. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html "PostgreSQL: Documentation: 18: CREATE TABLE"))

Это полезно, когда в середине транзакции у тебя может быть **временное нарушение**, но к `COMMIT` всё уже станет корректно.

---

# 4. Синтаксис

Общая форма такая:

```sql
CONSTRAINT имя_ограничения
EXCLUDE USING gist (
    выражение1 WITH оператор1,
    выражение2 WITH оператор2
)
DEFERRABLE
INITIALLY IMMEDIATE
```

`EXCLUDE` реализуется через индекс, который PostgreSQL создаёт автоматически. На практике чаще всего используют `GiST` или `SP-GiST`; `GIN` для exclusion constraint нельзя использовать. Если все операторы — это просто равенство, то это похоже на `UNIQUE`, но обычный `UNIQUE` обычно быстрее. ([PostgreSQL](https://www.postgresql.org/docs/current/ddl-constraints.html "PostgreSQL: Documentation: 18: 5.5. Constraints"))

---

# 5. Самый важный пример: запрет пересечения бронирований

Для сочетания обычного скалярного поля `room` и диапазона времени часто нужен модуль `btree_gist`. Официальная документация PostgreSQL прямо показывает такой сценарий. ([PostgreSQL](https://www.postgresql.org/docs/current/btree-gist.html?utm_source=chatgpt.com "F.8. btree_gist — GiST operator classes with B-tree behavior"))

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE room_reservation (
    id     bigint generated always as identity primary key,
    room   text    not null,
    during tsrange not null,
    CONSTRAINT room_reservation_no_overlap
        EXCLUDE USING gist (
            room   WITH =,
            during WITH &&
        )
        DEFERRABLE
        INITIALLY IMMEDIATE
);
```

### Что это означает

Для двух строк не может быть одновременно так, что:

- `room = room`
    
- `during && during`
    

То есть **для одной и той же комнаты** интервалы времени **не могут пересекаться**. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html?utm_source=chatgpt.com "Documentation: 18: CREATE TABLE"))

---

# 6. Как это работает без `DEFERRABLE`

Допустим, есть две соседние брони:

```sql
INSERT INTO room_reservation (room, during) VALUES
('A', '[2026-03-24 10:00, 2026-03-24 11:00)'),
('A', '[2026-03-24 11:00, 2026-03-24 12:00)');
```

Они валидны, потому что интервалы **соприкасаются**, но не пересекаются. Для range-типов это нормальная история. ([PostgreSQL](https://www.postgresql.org/docs/current/rangetypes.html?utm_source=chatgpt.com "Documentation: 18: 8.17. Range Types"))

Теперь хотим сдвинуть обе брони на час вперёд:

- первая: `[10:00,11:00)` → `[11:00,12:00)`
    
- вторая: `[11:00,12:00)` → `[12:00,13:00)`
    

Если ограничение проверяется **сразу после каждой команды**, то первый `UPDATE` временно создаст конфликт с ещё не сдвинутой второй записью, и команда упадёт.

---

# 7. Как `DEFERRABLE` помогает

Если ограничение `DEFERRABLE`, можно в транзакции отложить проверку:

```sql
BEGIN;

SET CONSTRAINTS room_reservation_no_overlap DEFERRED;

UPDATE room_reservation
SET during = '[2026-03-24 11:00, 2026-03-24 12:00)'
WHERE id = 1;

UPDATE room_reservation
SET during = '[2026-03-24 12:00, 2026-03-24 13:00)'
WHERE id = 2;

COMMIT;
```

Что происходит:

- после первого `UPDATE` конфликт временно есть;
    
- PostgreSQL пока не ругается, потому что проверка отложена;
    
- после второго `UPDATE` итоговое состояние снова корректно;
    
- на `COMMIT` ограничение проверяется, и транзакция проходит. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html "PostgreSQL: Documentation: 18: CREATE TABLE"))
    

Вот это и есть главный смысл **deferrable exclusion constraint**.

---

# 8. Чем `EXCLUDE` отличается от `UNIQUE`

`UNIQUE` — это частный случай логики “не допускай совпадений”, но только по равенству.  
`EXCLUDE` умеет более общие вещи:

- не допускать пересечения диапазонов `&&`
    
- не допускать нахождения геометрических объектов друг на друга
    
- комбинировать несколько условий сразу. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html?utm_source=chatgpt.com "Documentation: 18: CREATE TABLE"))
    

Например, в документации `btree_gist` есть пример:

```sql
CREATE TABLE zoo (
  cage   integer,
  animal text,
  EXCLUDE USING gist (cage WITH =, animal WITH <>)
);
```

Это означает: в одной клетке нельзя держать животных **разных видов**. Два `zebra` в одной клетке допустимы, а `zebra` и `lion` — нет. ([PostgreSQL](https://www.postgresql.org/docs/current/btree-gist.html?utm_source=chatgpt.com "F.8. btree_gist — GiST operator classes with B-tree behavior"))

---

# 9. Важные практические моменты

### Операторы должны подходить для индекса

Для `EXCLUDE` каждый оператор должен быть связан с подходящим operator class для выбранного метода индекса. На практике чаще всего это `GiST`, иногда `SP-GiST`. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html?utm_source=chatgpt.com "Documentation: 18: CREATE TABLE"))

### Часто нужен `btree_gist`

Если ты хочешь совместить:

- обычное поле вроде `room text`
    
- и range-поле вроде `during tsrange`
    

то обычно подключают `btree_gist`. Это официальный рекомендуемый путь для таких exclusion constraints. ([PostgreSQL](https://www.postgresql.org/docs/current/btree-gist.html?utm_source=chatgpt.com "F.8. btree_gist — GiST operator classes with B-tree behavior"))

### `ON CONFLICT DO UPDATE` тут не помощник

Exclusion constraints **не поддерживаются как arbiters** для `ON CONFLICT DO UPDATE`, и вообще deferrable constraints нельзя использовать как conflict arbiters в `INSERT ... ON CONFLICT`. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-createtable.html "PostgreSQL: Documentation: 18: CREATE TABLE"))

---

# 10. Короткое определение для экзамена

Можно ответить так:

> `EXCLUDE` — это ограничение PostgreSQL, которое запрещает существование двух строк, для которых все указанные сравнения одновременно истинны.  
> `DEFERRABLE` означает, что проверку такого ограничения можно отложить до конца транзакции.  
> `DEFERRABLE EXCLUDE` особенно полезно для задач вроде бронирований, расписаний и интервалов, когда в середине транзакции возможен временный конфликт, но итоговое состояние остаётся корректным. ([PostgreSQL](https://www.postgresql.org/docs/current/ddl-constraints.html "PostgreSQL: Documentation: 18: 5.5. Constraints"))
