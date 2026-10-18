# Раздел №1. Синтаксис SQL: соответствия PostgreSQL / Greenplum → Oracle

## Особенность №1. SELECT без FROM и таблица DUAL
В PostgreSQL можно написать `SELECT 1`. В Oracle нужно `SELECT 1 FROM DUAL`. В Oracle 23ai DUAL для этого уже не обязателен.

## Особенность №2. Ограничение числа строк: LIMIT → FETCH FIRST / ROWNUM
PostgreSQL: `LIMIT 10`. Oracle 12c+: `FETCH FIRST 10 ROWS ONLY`. До 12c использовалось `WHERE ROWNUM <= 10`.

## Особенность №3. Ловушка ROWNUM + ORDER BY
`WHERE ROWNUM <= 10 ORDER BY x` сначала режет 10 произвольных строк, и только потом сортирует их. Это классическая ловушка. Правильно: подзапрос с `ORDER BY`, а `ROWNUM` во внешнем запросе, либо `FETCH FIRST`.

## Особенность №4. NULL-функции: COALESCE → NVL, NVL2, DECODE
В Oracle привычно используют `NVL`, `NVL2` и `DECODE`. Стандартные `COALESCE` и `CASE` тоже есть.

## Особенность №5. EXCEPT → MINUS
Оператор вычитания множеств в Oracle называется `MINUS`.

## Особенность №6. Агрегация строк: string_agg → LISTAGG
Аналог `string_agg` в Oracle: `LISTAGG(col, ',') WITHIN GROUP (ORDER BY ...)`.

## Особенность №7. Генерация рядов: generate_series → CONNECT BY LEVEL
Аналог `generate_series` в Oracle: `SELECT LEVEL FROM DUAL CONNECT BY LEVEL <= N`.

## Особенность №8. Иерархии и рекурсия: WITH RECURSIVE → CONNECT BY PRIOR
В Oracle иерархические запросы пишутся через `START WITH ... CONNECT BY PRIOR ...`, с псевдостолбцом `LEVEL` и функцией `SYS_CONNECT_BY_PATH`. Рекурсивный `WITH` в Oracle тоже есть.

## Особенность №9. Текущая дата и приведение типов: now(), ::date
Вместо `now()` используют `SYSDATE`. Дату без времени получают через `TRUNC(SYSDATE)`. Для преобразований служат `TO_DATE(...)` и `CAST`. Оператора `::` в Oracle нет.

## Особенность №10. Арифметика дат: interval → SYSDATE + 1, ADD_MONTHS, MONTHS_BETWEEN
Вместо `date + interval '1 day'` пишут `SYSDATE + 1`. Для месяцев есть `ADD_MONTHS` и `MONTHS_BETWEEN`.

## Особенность №11. Последовательности и идентификаторы: serial / nextval → NEXTVAL, IDENTITY
В PostgreSQL `serial` и `nextval('seq')`. В Oracle `seq.NEXTVAL` и `GENERATED AS IDENTITY` (12c+).

## Особенность №12. Типы данных: text, int, boolean → VARCHAR2, CLOB, NUMBER
Соответствия: `text` → `VARCHAR2` / `CLOB`, `int` → `NUMBER`. Тип `boolean` в SQL появился только в 23ai.

## Особенность №13. UPDATE ... FROM
В Oracle нет `UPDATE ... FROM`. Используют `MERGE` или коррелированный подзапрос.

## Особенность №14. INSERT ... ON CONFLICT → MERGE
Upsert делается через `MERGE INTO ... USING ... WHEN MATCHED / NOT MATCHED`.

## Особенность №15. Алиас таблицы без AS
Алиас таблицы пишется без `AS`: `FROM t a`.

## Особенность №16. Регистр неквотированных идентификаторов
Неквотированные идентификаторы Oracle хранит в верхнем регистре, PostgreSQL в нижнем.

## Особенность №17. Старый синтаксис внешнего соединения (+)
В легаси-коде встречается `a.id = b.id(+)`. Это старый синтаксис внешнего соединения Oracle.

## Особенность №18. PIVOT / UNPIVOT
В Oracle есть нативные `PIVOT` и `UNPIVOT`.

## Особенность №19. KEEP (DENSE_RANK FIRST ORDER BY ...)
Конструкцию `KEEP (DENSE_RANK FIRST ORDER BY ...)` часто используют вместо оконных функций.

## Особенность №20. Flashback Query: AS OF TIMESTAMP
Flashback-запросы позволяют читать прошлое состояние данных: `SELECT ... AS OF TIMESTAMP ...`.

# Раздел №2. Продвинутые SQL-возможности для трансформаций

## Особенность №21. INSERT ALL / INSERT FIRST
Oracle вставляет результат одного запроса сразу в несколько таблиц.

```sql
INSERT ALL
    WHEN amount > 100000 THEN
        INTO large_orders (id, amount)
        VALUES (id, amount)
    WHEN amount <= 100000 THEN
        INTO small_orders (id, amount)
        VALUES (id, amount)
SELECT id, amount
FROM staging_orders;
```

- `INSERT ALL` выполняет все подходящие ветки.
- `INSERT FIRST` выполняет только первую подходящую ветку.

Полезно для маршрутизации записей по таблицам и ETL-преобразований.

## Особенность №22. SQL/JSON: JSON_VALUE, JSON_QUERY, JSON_EXISTS, JSON_TABLE
В PostgreSQL ты работаешь с `jsonb`, `jsonb_array_elements`, операторами `->` и `->>`. В Oracle 19c нужно знать SQL/JSON: `JSON_VALUE`, `JSON_QUERY`, `JSON_EXISTS`, `JSON_TABLE`.

Пример превращения массива JSON в строки:

```sql
SELECT j.id, j.amount
FROM JSON_TABLE(
    '[{"id":1,"amount":100},
      {"id":2,"amount":200}]',
    '$[*]'
    COLUMNS (
        id NUMBER PATH '$.id',
        amount NUMBER PATH '$.amount'
    )
) j;
```

`JSON_TABLE` особенно полезен при обработке данных из API и полуструктурированных источников.

## Особенность №23. MATCH_RECOGNIZE
Oracle 12c+ поддерживает поиск последовательных шаблонов по строкам. Применения:
- выявление цепочек событий;
- sessionization по временным событиям;
- поиск последовательных изменений состояния;
- анализ транзакционных паттернов.

Ключевые конструкции: `PATTERN`, `DEFINE`, `MEASURES`, `AFTER MATCH SKIP`.

# Раздел №3. Типы данных, NULL и NLS

## Особенность №24. Пустая строка = NULL
В Oracle в `VARCHAR2` пустая строка и `NULL` это одно и то же. В PostgreSQL `''` и `NULL` разные значения.

## Особенность №25. Тип DATE содержит время
Тип `DATE` в Oracle содержит не только дату, но и время.

## Особенность №26. Конкатенация с NULL
Оператор `||` по-разному обрабатывает `NULL`.

```sql
-- PostgreSQL
SELECT 'abc' || NULL;
-- NULL

-- Oracle
SELECT 'abc' || NULL FROM dual;
-- 'abc'
```

Это важно при переносе SQL-трансформаций, формировании составных ключей и хешируемых строк.

## Особенность №27. Составной UNIQUE и NULL
В Oracle составной `UNIQUE` не позволяет дублировать частично заполненный ключ. Пусть на `(a, b)` создано ограничение `UNIQUE`:

| Значение | PostgreSQL | Oracle |
|---|---|---|
| `(1, NULL)` дважды | Разрешено | Ошибка |
| `(NULL, NULL)` дважды | Разрешено | Разрешено |
| `(1, 2)` дважды | Ошибка | Ошибка |

Для PostgreSQL подразумевается стандартное поведение `UNIQUE`, без `NULLS NOT DISTINCT` (PostgreSQL 15+).

Практическая ловушка: перенос таблицы с составным уникальным ключом из PostgreSQL в Oracle может завершиться нарушением ограничения.

## Особенность №28. Неявные преобразования типов и NLS
Oracle использует параметры сессии:
- `NLS_DATE_FORMAT`: формат даты;
- `NLS_TIMESTAMP_FORMAT`: формат timestamp;
- `NLS_NUMERIC_CHARACTERS`: десятичный и групповой разделители;
- `NLS_DATE_LANGUAGE`: язык названий месяцев и дней.

Например, в условии `WHERE created_at >= '01-02-2026'` результат зависит от неявного преобразования строки в дату. Корректнее:

```sql
WHERE created_at >= DATE '2026-02-01'
```

Для timestamp:

```sql
WHERE created_at >= TIMESTAMP '2026-02-01 12:30:00'
```

Дополнительно следует изучить `TIMESTAMP WITH TIME ZONE`, `TIMESTAMP WITH LOCAL TIME ZONE` и влияние часового пояса сессии. Неправильные преобразования вызывают ошибки загрузки и влияют на использование индексов.

## Особенность №29. VARCHAR2: BYTE против CHAR и MAX_STRING_SIZE
`VARCHAR2(100 BYTE)` и `VARCHAR2(100 CHAR)` это разные ограничения длины. При UTF-8 кириллица занимает несколько байтов, поэтому строка из 100 символов не обязана помещаться в `VARCHAR2(100 BYTE)`.

- `MAX_STRING_SIZE = STANDARD`: максимум 4000 байт для обычного `VARCHAR2` в SQL.
- `MAX_STRING_SIZE = EXTENDED`: максимум 32767 байт.

Это критично при переносе `TEXT` и больших строк.

## Особенность №30. NUMBER(p,s), BINARY_FLOAT и BINARY_DOUBLE
- `NUMBER(p,s)`: десятичная точность и масштаб.
- `BINARY_FLOAT` и `BINARY_DOUBLE`: типы с двоичной плавающей точкой.
- `NUMBER` без указания точности и масштаба отличается от `NUMBER(38,0)`.

Это критично при переносе `NUMERIC` и больших идентификаторов.

# Раздел №4. Транзакции, изоляция и блокировки

## Особенность №31. DDL делает неявный COMMIT
В PostgreSQL DDL транзакционный, в Oracle нет. Откатить `CREATE` или `DROP` нельзя.

## Особенность №32. Автокоммита в DML нет
`UPDATE` без `COMMIT` не виден другим сессиям.

## Особенность №33. MVCC на UNDO и ORA-01555
MVCC в Oracle построен на **UNDO**, а не на версиях строк в куче. Поэтому нет `VACUUM` и bloat в привычном смысле, зато есть **ORA-01555 (snapshot too old)** на долгих запросах.

## Особенность №34. Уровни изоляции: PostgreSQL против Oracle
В Oracle отсутствует отдельный уровень `REPEATABLE READ`, привычный разработчику PostgreSQL.

| Изоляция | PostgreSQL | Oracle |
|---|---|---|
| READ COMMITTED | Есть | Есть |
| REPEATABLE READ | Есть | Нет |
| SERIALIZABLE | Есть | Есть |
| READ ONLY transaction | Есть | Есть |

## Особенность №35. Согласованный снимок: READ COMMITTED, SERIALIZABLE, READ ONLY, ORA-08177
- `READ COMMITTED` обеспечивает согласованность снимка на уровне SQL-оператора.
- `SERIALIZABLE` использует согласованный снимок транзакции.
- `SET TRANSACTION READ ONLY` фиксирует снимок для читающей транзакции.
- `ORA-08177: can't serialize access for this transaction` возникает при определённых конфликтах изменений в `SERIALIZABLE`.

```sql
SET TRANSACTION READ ONLY;

SELECT COUNT(*) FROM orders;
SELECT SUM(amount) FROM orders;

COMMIT;
```

Оба запроса читают один согласованный снимок данных, включая собственные ограничения режима read-only.

## Особенность №36. Блокировки: FOR UPDATE SKIP LOCKED / NOWAIT / WAIT, ORA-00054, ORA-00060
Очередь задач для нескольких ETL-воркеров:

```sql
SELECT *
FROM etl_tasks
WHERE status = 'NEW'
FOR UPDATE SKIP LOCKED;
```

Также есть:
- `FOR UPDATE NOWAIT`: немедленная ошибка при конфликте;
- `FOR UPDATE WAIT 5`: ожидание блокировки до 5 секунд;
- `ORA-00054`: ресурс занят, блокировка недоступна в заданных условиях;
- `ORA-00060`: обнаружен deadlock.

`SKIP LOCKED` особенно полезен при реализации очереди задач с несколькими ETL-воркерами. Но он не заменяет полноценное управление состояниями задач и гарантиями повторного исполнения.

# Раздел №5. Хранение, объекты и ограничения

## Особенность №37. High Water Mark (HWM)
`DELETE` не снижает HWM, `TRUNCATE` снижает. Full scan читает всё до HWM, поэтому после массового delete таблица остаётся «тяжёлой». Лечится `ALTER TABLE ... MOVE` или `SHRINK SPACE`.

## Особенность №38. Global Temporary Table
Структура GTT постоянная, данные живут в рамках сессии или транзакции (`ON COMMIT DELETE ROWS` / `ON COMMIT PRESERVE ROWS`). Это не то же самое, что `CREATE TEMP TABLE` в PostgreSQL.

## Особенность №39. Private Temporary Tables (18c+)
В дополнение к Global Temporary Tables в Oracle 18c+ существуют Private Temporary Tables.

```sql
CREATE PRIVATE TEMPORARY TABLE
ORA$PTT_WORK (ID NUMBER)
ON COMMIT DROP DEFINITION;
```

- Видимость определения ограничена сессией.
- Определение может удаляться в конце транзакции или сессии.
- Создание такой таблицы не фиксирует предшествующую транзакцию неявным COMMIT.

Это отдельный тип временных таблиц, ближе по жизненному циклу к привычным временным объектам PostgreSQL.

## Особенность №40. Схема = пользователь, синонимы, DB LINK, табличные пространства
Схема в Oracle это пользователь. Также нужно знать синонимы (`PUBLIC SYNONYM`), `DB LINK` и табличные пространства.

## Особенность №41. Корзина (recycle bin)
`DROP TABLE` кладёт таблицу в recycle bin. Вернуть можно через `FLASHBACK TABLE ... TO BEFORE DROP`, удалить насовсем через `PURGE`.

## Особенность №42. Жизненный цикл ограничений
При массовых загрузках важно понимать:
- `ENABLE VALIDATE`: ограничение включено, существующие данные проверены;
- `ENABLE NOVALIDATE`: новые изменения проверяются, существующие данные могут не соответствовать ограничению;
- `DISABLE NOVALIDATE`: ограничение не обеспечивается;
- `RELY`: объявленная достоверность ограничения может использоваться оптимизатором в предусмотренных режимах.

Эти состояния важны для больших исторических таблиц и построения DWH.

## Особенность №43. Последовательности: CACHE, NOCACHE, ORDER, NOORDER
Нужно знать `CACHE`, `NOCACHE`, `ORDER`, `NOORDER`.
- Кеширование ускоряет генерацию значений.
- При аварийном завершении экземпляра возможны пропуски в последовательности.
- `NOORDER` не гарантирует глобальный порядок выдачи значений между RAC-экземплярами.
- Нельзя использовать значение sequence как гарантированный признак хронологии событий.

## Особенность №44. Физическое сжатие и колоночные механизмы
У Oracle есть разные механизмы хранения:
- Basic Table Compression;
- Advanced Row Compression;
- Hybrid Columnar Compression (HCC);
- In-Memory Column Store;
- Exadata Smart Scan.

В отличие от Greenplum с его AO/AOCO-хранением, эти механизмы Oracle различаются по физической организации, поддерживаемому оборудованию и лицензированию.

## Особенность №45. Лицензирование опций
В Oracle 19c Partitioning, Advanced Compression и Database In-Memory имеют отдельные условия лицензирования.

# Раздел №6. Производительность и оптимизатор

## Особенность №46. Хинты: синтаксис и поведение
Хинты пишутся как `/*+ ... */` сразу после `SELECT`, `INSERT`, `UPDATE`, `MERGE` или `DELETE`. Неверный хинт молча игнорируется, без ошибки.

```sql
SELECT /*+ PARALLEL(t 8) FULL(t) USE_HASH(t d) LEADING(d t) */ ...
```

## Особенность №47. Самые употребимые хинты
- `PARALLEL`
- `FULL`, `INDEX`, `NO_INDEX`
- `USE_HASH`, `USE_NL`, `USE_MERGE`, `LEADING`, `ORDERED`
- `APPEND` (direct-path insert)
- `MATERIALIZE` / `INLINE` для CTE
- `NO_MERGE`, `PUSH_PRED`
- `CARDINALITY`, `DYNAMIC_SAMPLING`
- `GATHER_PLAN_STATISTICS`

## Особенность №48. Direct-path загрузка и parallel DML
```sql
ALTER SESSION ENABLE PARALLEL DML;
INSERT /*+ APPEND PARALLEL(t 8) */ INTO t SELECT ... ;
COMMIT;  -- до коммита эту таблицу в этой сессии читать нельзя (ORA-12838)
```

Здесь же стоит упомянуть `NOLOGGING` и то, что parallel DML по умолчанию выключен и включается отдельно.

## Особенность №49. Планы выполнения: EXPLAIN PLAN, DBMS_XPLAN, ALLSTATS LAST
- `EXPLAIN PLAN FOR ...` и `DBMS_XPLAN.DISPLAY`.
- `DBMS_XPLAN.DISPLAY_CURSOR(NULL, NULL, 'ALLSTATS LAST')`: сравнивают E-Rows и A-Rows, это главный способ найти ошибку оптимизатора. Для A-Rows нужен хинт `GATHER_PLAN_STATISTICS`.

## Особенность №50. Мониторинг и трассировка
- SQL Monitor, AWR/ASH-отчёты.
- Представления `V$SQL`, `V$SESSION`, `V$SESSION_LONGOPS`.
- Трассировка 10046 и TKPROF.

## Особенность №51. Управление планами
SQL Profile, SQL Plan Baseline (SPM), `SQL Tuning Advisor`.

## Особенность №52. Статистика: DBMS_STATS
Вместо `ANALYZE` используется `DBMS_STATS.GATHER_TABLE_STATS(..., degree => 8, method_opt => ...)`. Про гистограммы и расширенную статистику (extended stats) спросят отдельно.

## Особенность №53. Bind-переменные и parsing
Hard parse и soft parse, shared pool, bind peeking, `CURSOR_SHARING`. В Oracle литералы вместо биндов реально убивают производительность.

## Особенность №54. Adaptive Cursor Sharing
Это развитие bind peeking. Один SQL с одним `SQL_ID` может иметь несколько child cursors и разные планы исполнения для разных значений параметров.

```sql
SELECT *
FROM orders
WHERE customer_id = :customer_id;
```

- Для клиента с 10 заказами оптимальным может быть index range scan.
- Для клиента с 10 млн заказов оптимизатор может выбрать full table scan.

Нужно знать: `BIND_SENSITIVE`, `BIND_AWARE`, `CHILD_NUMBER`, `PLAN_HASH_VALUE`, `V$SQL_SHARED_CURSOR`. Это объясняет, почему идентичный SQL с разными значениями параметров выполняется по-разному.

## Особенность №55. Индексы: виды
B-tree, bitmap (для DWH), function-based, local и global на партициях, IOT, invisible index.

## Особенность №56. Clustering Factor и характеристики B-tree индекса
B-tree индекс может быть малоэффективным даже при высокой селективности. Показатель `CLUSTERING_FACTOR` характеризует, насколько порядок строк в таблице соответствует порядку ключей индекса.
- Значение близко к числу блоков: данные хорошо сгруппированы.
- Значение близко к числу строк: доступ по индексу приводит к большому числу переходов между блоками.

Дополнительно изучи `BLEVEL`, `LEAF_BLOCKS`, `TABLE ACCESS BY INDEX ROWID BATCHED`, а также reverse key indexes для последовательных ключей.

## Особенность №57. Parallel Execution: соответствие Greenplum → Oracle
В Greenplum ты привык к `Motion`, `Redistribute Motion`, `Broadcast Motion`, `Gather Motion`. В Oracle аналогичные операции выполняются через механизм Parallel Execution (PX).

| Greenplum | Oracle |
|---|---|
| Query Dispatcher | Query Coordinator (QC) |
| Segment worker | PX Server |
| Redistribute Motion | `PX SEND HASH` |
| Broadcast Motion | `PX SEND BROADCAST` |
| Gather Motion | `PX SEND QC` |
| Data skew | PX data skew |

## Особенность №58. Элементы PX-плана и степень параллелизма (DOP)
- `PX COORDINATOR` управляет параллельным планом.
- `PX SEND` передаёт данные между группами PX-процессов.
- `PX RECEIVE` принимает данные.
- `PX BLOCK ITERATOR` распределяет блоки таблицы между обработчиками.
- Один запрос с DOP 8 может задействовать 16 PX-процессов, когда одновременно работают две группы.

## Особенность №59. V$PQ_TQSTAT, data skew и PQ_DISTRIBUTE
Критически важное представление:

```sql
SELECT *
FROM V$PQ_TQSTAT;
```

Оно позволяет определить, сколько строк и байтов передавалось между PX-процессами. Если один обработчик получает 80% данных, а остальные простаивают, проблема в data skew. Увеличение DOP её не решает. В Oracle также существует хинт `PQ_DISTRIBUTE` для управления распределением данных при соединениях.

## Особенность №60. Partition Pruning
Oracle может исключать ненужные партиции из сканирования.
- Static pruning: нужные партиции определяются при построении плана.
- Dynamic pruning: определяются во время исполнения, в том числе с помощью bind-переменных.

В плане нужно смотреть:

| Операция | Значение |
|---|---|
| `PARTITION RANGE SINGLE` | Одна партиция |
| `PARTITION RANGE ITERATOR` | Подмножество партиций |
| `PARTITION RANGE ALL` | Все партиции |
| `PSTART` / `PSTOP` | Диапазон читаемых партиций |
| `KEY` | Динамическое определение партиций |

## Особенность №61. Partition-Wise Join
Если две большие таблицы совместимо партиционированы по ключу соединения, Oracle может выполнять соединение соответствующих партиций без полного перераспределения данных. Для Greenplum это знакомая проблема локальности данных.

## Особенность №62. SGA, PGA, workarea и TEMP
В PostgreSQL есть `work_mem`, в Greenplum работают механизмы распределения памяти между операторами. В Oracle нужно знать:
- SGA: общая память экземпляра, включая buffer cache и shared pool;
- PGA: память серверного процесса;
- Workarea: память для сортировок, hash join, агрегаций;
- TEMP tablespace: временные сегменты для операций, не помещающихся в память;
- `PGA_AGGREGATE_TARGET`: целевой объём PGA на уровне экземпляра.

## Особенность №63. Режимы workarea и диагностика нехватки памяти
Oracle различает три режима выполнения операций:

| Режим | Что происходит |
|---|---|
| OPTIMAL | Данные обрабатываются в памяти |
| ONE PASS | Требуется дополнительный проход с использованием диска |
| MULTI-PASS | Требуются многократные проходы с использованием диска |

Диагностика:

```sql
SELECT
    sql_id,
    operation_type,
    last_execution,
    last_memory_used,
    last_tempseg_size
FROM v$sql_workarea;
```

Ошибки: `ORA-01652` (невозможно выделить нужный временный сегмент) и `ORA-04036` (превышен установленный лимит PGA).

Типичная ситуация: HASH JOIN начал активно писать во временное пространство. Нужно проверить объёмы входных данных, оценку кардинальности, доступную память и DOP.

## Особенность №64. Database Resource Manager
Oracle позволяет задавать ресурсные группы и управлять:
- приоритетами выполнения запросов;
- долями CPU;
- пределами параллельных серверов;
- очередями параллельных запросов;
- ограничениями на длительность ожидания ресурсов.

Ключевые понятия: `CONSUMER GROUP`, `RESOURCE PLAN`, `PARALLEL_SERVERS_TARGET`, `PARALLEL_DEGREE_POLICY`.

# Раздел №7. ETL: партиционирование, загрузка и выгрузка данных

## Особенность №65. Виды партиционирования
Range, list, hash, composite, **interval** (партиции создаются автоматически), reference.

## Особенность №66. EXCHANGE PARTITION, TRUNCATE PARTITION, UPDATE GLOBAL INDEXES
Ключевой приём в ETL: `ALTER TABLE t EXCHANGE PARTITION p WITH TABLE stg ...` для мгновенной подмены данных. Также используются `TRUNCATE PARTITION` и `UPDATE GLOBAL INDEXES`.

## Особенность №67. Materialized views
`REFRESH FAST` / `COMPLETE`, MV Logs, `ON COMMIT` / `ON DEMAND`, query rewrite.

## Особенность №68. External Tables, SQL*Loader, Data Pump
External Tables (`ORACLE_LOADER`, `ORACLE_DATAPUMP`), SQL*Loader (`sqlldr`), Data Pump (`expdp` / `impdp`). Аналоги из мира Greenplum: gpfdist / gpload.

## Особенность №69. DML Error Logging (LOG ERRORS)
Одна из наиболее полезных возможностей Oracle для построения ETL. Oracle позволяет записывать ошибки отдельных строк в специальную таблицу, не останавливая всю загрузку при поддерживаемых типах ошибок.

```sql
BEGIN
    DBMS_ERRLOG.CREATE_ERROR_LOG('ORDERS');
END;
/

INSERT INTO orders (id, amount)
SELECT id, amount
FROM staging_orders
LOG ERRORS INTO err$_orders ('batch_001')
REJECT LIMIT UNLIMITED;
```

После загрузки:

```sql
SELECT
    ORA_ERR_NUMBER$,
    ORA_ERR_MESG$,
    ORA_ERR_TAG$
FROM err$_orders;
```

- Корректные строки загружаются.
- Ошибочные строки, поддерживаемые этим механизмом, попадают в `ERR$_ORDERS`.
- `ORA_ERR_TAG$` позволяет идентифицировать пакет загрузки.
- Есть ограничения: например, нарушение уникальности при direct-path `INSERT` не обрабатывается построчно этим механизмом.

В PostgreSQL нет прямого встроенного аналога `LOG ERRORS` для обычного `INSERT ... SELECT`.

## Особенность №70. Планировщик DBMS_SCHEDULER
`DBMS_SCHEDULER`: jobs, chains.

## Особенность №71. Python: python-oracledb
`python-oracledb` (бывший `cx_Oracle`), биндинг `:1` / `:name`, `executemany`, `arraysize`.

## Особенность №72. Репликация, CDC и ETL-инструменты
Репликация: GoldenGate, CDC. Из ETL-инструментов часто ODI и Informatica.

# Раздел №8. PL/SQL

## Особенность №73. Пакеты, анонимные блоки, исключения
PL/SQL это отдельный навык, и о нём обязательно спросят. Нужно знать пакеты (spec и body), анонимные блоки и обработку исключений.

## Особенность №74. BULK COLLECT + FORALL
`BULK COLLECT` + `FORALL` применяют вместо построчной обработки («slow-by-slow»).

## Особенность №75. RETURNING ... INTO и PRAGMA AUTONOMOUS_TRANSACTION
`RETURNING ... INTO` возвращает значения изменённых строк. `PRAGMA AUTONOMOUS_TRANSACTION` запускает независимую транзакцию.

## Особенность №76. Коллекции
Nested table, varray, associative array.

## Особенность №77. Pipelined table functions
Конвейерные табличные функции (pipelined table functions).

## Особенность №78. Системные пакеты
`DBMS_OUTPUT`, `UTL_FILE`, `DBMS_LOB`, `DBMS_STATS`, `DBMS_PARALLEL_EXECUTE`.

## Особенность №79. Права внутри PL/SQL: AUTHID DEFINER и CURRENT_USER
В PL/SQL существуют два режима исполнения:
- `AUTHID DEFINER`: код исполняется с правами владельца. Это режим по умолчанию.
- `AUTHID CURRENT_USER`: код исполняется с правами вызывающего пользователя.

```sql
CREATE OR REPLACE PROCEDURE process_orders
AUTHID CURRENT_USER
AS
BEGIN
    NULL;
END;
/
```

Главное отличие: для статического SQL внутри хранимой процедуры с `AUTHID DEFINER` права на используемые объекты должны быть предоставлены владельцу напрямую, а не только через роли. Поэтому обычный SELECT под пользователем может работать, но компиляция процедуры, использующей ту же таблицу, завершится ошибкой.

# Раздел №9. Словарь и ошибки

## Особенность №80. Словарь данных
`USER_TABLES`, `ALL_TAB_COLUMNS`, `DBA_SEGMENTS`, `V$...`, `USER_TAB_PARTITIONS`. Это аналог `information_schema` и `pg_catalog`.

## Особенность №81. Ошибки, которые знают те, кто работал: основной список
- `ORA-00942`: таблица не найдена;
- `ORA-01722`: неверное число;
- `ORA-00001`: нарушение уникальности;
- `ORA-01555`: snapshot too old;
- `ORA-12838`: нельзя читать таблицу после direct-path / parallel DML до коммита;
- **`ORA-30926`**: MERGE, нестабильный набор строк;
- `ORA-01427`: подзапрос вернул больше одной строки.

## Особенность №82. Ошибки из дополнительных тем
- `ORA-08177`: can't serialize access for this transaction (конфликт в `SERIALIZABLE`);
- `ORA-01652`: невозможно выделить нужный временный сегмент (TEMP);
- `ORA-04036`: превышен установленный лимит PGA;
- `ORA-00054`: ресурс занят, блокировка недоступна в заданных условиях;
- `ORA-00060`: обнаружен deadlock.

# Раздел №10. Архитектура, восстановление и инфраструктура

## Особенность №83. Multitenant: CDB и PDB
- CDB (Container Database): контейнерная база.
- PDB (Pluggable Database): самостоятельная логическая база внутри CDB.
- `CDB$ROOT`: корневой контейнер.
- `ALTER SESSION SET CONTAINER = ...`: переключение контейнера при наличии прав.

Это важно, потому что подключение к разным PDB одной CDB даёт доступ к разным наборам пользовательских объектов.

## Особенность №84. Real Application Clusters (RAC)
Oracle RAC не эквивалентен Greenplum MPP.
- Greenplum распределяет данные по сегментам.
- RAC позволяет нескольким экземплярам Oracle работать с одной общей базой данных.
- Для согласования доступа к блокам между экземплярами используется Cache Fusion.
- В RAC появляются ожидания `gc` и межузловое взаимодействие.
- Существуют `GV$`-представления с `INST_ID`, содержащие сведения по экземплярам кластера.

## Особенность №85. Oracle Net: service name, SID, listener
Отдельно стоит понимать Oracle Net, service names, `SERVICE_NAME`, `SID` и работу listener.

## Особенность №86. Распределённые запросы: DRIVING_SITE и Two-Phase Commit
Раз ты знаком с Greenplum и PXF, добавь два понятия:
- `DRIVING_SITE`: хинт, позволяющий влиять на место выполнения распределённого запроса между Oracle-базами;
- Two-Phase Commit (2PC): согласование фиксации транзакции, изменяющей данные в нескольких базах.

## Особенность №87. SCN, redo, RMAN, Data Guard
С точки зрения DE необходимо понимать не только транзакции, но и механизм восстановления.
- SCN (System Change Number): логическая отметка изменений, используемая для согласованности и восстановления.
- Redo Log: журнал изменений, обеспечивающий восстановление.
- Archived Redo Logs: архивированные журналы.
- LGWR: процесс записи redo.
- DBWR: процесс записи изменённых блоков из buffer cache.
- RMAN: штатный инструмент резервного копирования и восстановления.
- Data Guard: поддержание резервных баз на основе передачи и применения redo.

## Особенность №88. Ловушка NOLOGGING
Ускорение загрузки за счёт уменьшения redo (`NOLOGGING`) может сделать загруженные данные невосстановимыми при определённых сценариях media recovery. Поэтому при проектировании ETL нужно согласовывать стратегию быстрого наполнения с требованиями восстановления и резервирования.

# Раздел №11. Типичные вопросы на собеседовании и опорные ответы

## Особенность №89. Как загрузить 100 млн строк быстро?
`INSERT /*+ APPEND PARALLEL */`, `NOLOGGING`, отключить или перестроить индексы. Лучше загрузка в staging и `EXCHANGE PARTITION`.

## Особенность №90. Запрос внезапно стал медленным
Сначала проверить актуальность статистики, потом `ALLSTATS LAST` и сравнение E-Rows с A-Rows, потом смену плана (bind peeking, baseline).

## Особенность №91. Чем TRUNCATE отличается от DELETE?
`TRUNCATE` это DDL с неявным коммитом, сбрасывает HWM, не создаёт undo.

## Особенность №92. Чем PostgreSQL отличается от Oracle по MVCC?
Undo против версий строк в куче. Нет vacuum, но есть ORA-01555.

## Особенность №93. Как сделать upsert?
`MERGE`, и нужно знать, что делать с ORA-30926.

## Особенность №94. Почему два SELECT в одной транзакции вернули разные данные?
Вопрос на собеседовании: почему два последовательных SELECT внутри одной Oracle-транзакции могут вернуть разные данные?

Ответ: в `READ COMMITTED` каждый SQL-оператор получает собственный согласованный снимок. Если другая транзакция зафиксировала изменения между запросами, второй SELECT их увидит.

## Особенность №95. Почему join двух партиционированных таблиц по 500 млн строк медленный?
Нужно проверять не только тип JOIN, но и наличие partition-wise join, количество читаемых партиций, data skew и межпроцессную передачу данных.

## Особенность №96. Удалённая база: пересылать 100 млн строк или агрегировать на месте?
Практический вопрос: стоит ли пересылать 100 млн строк из удалённой базы или выполнить агрегацию на удалённой стороне и передать только результат? Здесь пригодится `DRIVING_SITE` и понимание объёма передаваемых данных.

# Раздел №12. Подготовка к собеседованию

## Особенность №97. Совет: как честно подать свой опыт
Скажи честно, что основной опыт у тебя в PostgreSQL и Greenplum, но Oracle ты знаешь на уровне маппинга: «в PG я делал так, в Oracle это `MERGE`, `APPEND`, `EXCHANGE PARTITION`, `DBMS_STATS`». Заявить промышленный опыт без него опасно: два-три уточняющих вопроса про планы, хинты или PL/SQL вскрывают это быстро. А вот осознанное знание отличий и умение быстро переключиться на собеседованиях обычно ценится.

## Особенность №98. Что учить в первую очередь
| Приоритет | Тема | Зачем DE |
|---|---|---|
| 1 | PX, data redistribution, data skew | Оптимизация больших JOIN и GROUP BY |
| 2 | Partition pruning и partition-wise join | Работа с большими фактами |
| 3 | PGA, TEMP, memory spills | Диагностика медленных запросов |
| 4 | DML Error Logging | Отказоустойчивые загрузки |
| 5 | Adaptive Cursor Sharing | Нестабильность планов |
| 6 | SCN, REDO, восстановление | Надёжность ETL |
| 7 | CDB/PDB и RAC | Понимание инфраструктуры |
| 8 | JSON_TABLE, MATCH_RECOGNIZE | Продвинутые трансформации |
| 9 | Изоляция и блокировки | Конкурентные пайплайны |
| 10 | NLS, типы, constraints | Корректность данных |

## Особенность №99. Практический кейс для подготовки
Лучше всего разобрать один конкретный сценарий: загрузка 100 млн строк из staging, проверка качества, преобразования, партиционирование, параллельное выполнение и диагностика деградации SQL. Такой кейс проверяет большую часть перечисленных особенностей одновременно.

## Особенность №100. Итог: сильные стороны опыта Greenplum
Основное преимущество опыта Greenplum при переходе в Oracle: понимание MPP-запросов, распределения данных, hash joins и статистики. Наиболее важные новые навыки для собеседования: уметь читать Oracle PX-план, диагностировать TEMP spills, понимать SCN/redo и особенности конкурентного выполнения ETL.

## Особенность №101. Ориентир по версиям Oracle
Материал ориентирован прежде всего на Oracle 19c. Функциональность новых версий отмечена отдельно: 23ai (SELECT без DUAL, `boolean` в SQL), 12c+ (`FETCH FIRST`, `IDENTITY`, `MATCH_RECOGNIZE`), 18c+ (Private Temporary Tables).

