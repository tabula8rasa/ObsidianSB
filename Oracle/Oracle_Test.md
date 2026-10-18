# Раздел №1. Синтаксис SQL: соответствия PostgreSQL / Greenplum → Oracle

## Вопрос №1. SELECT без FROM и таблица DUAL
Какой запрос вернёт число 1 в Oracle 19c?

- A. `SELECT 1`
- B. `SELECT 1 FROM DUAL`
- C. `VALUES (1)`
- D. `SELECT 1 FROM SYSTEM`

<details>
<summary>Ответ</summary>

**B.** В Oracle SELECT требует FROM, для таких случаев служит таблица `DUAL`. Только в 23ai её можно опускать.

</details>

## Вопрос №2. Ограничение числа строк
Как в Oracle 12c+ получить первые 10 строк результата?

- A. `LIMIT 10`
- B. `TOP 10`
- C. `FETCH FIRST 10 ROWS ONLY`
- D. `ROWS BETWEEN 1 AND 10`

<details>
<summary>Ответ</summary>

**C.** `FETCH FIRST ... ROWS ONLY` доступен с 12c. До 12c использовали `WHERE ROWNUM меньше или равно 10`

</details>

## Вопрос №3. Ловушка ROWNUM + ORDER BY
Что делает запрос `SELECT * FROM t WHERE ROWNUM <= 10 ORDER BY x`?

- A. Сортирует всю таблицу и возвращает 10 строк с наименьшим `x`
- B. Берёт 10 произвольных строк и только потом сортирует их
- C. Завершается ошибкой
- D. Возвращает 10 строк с наибольшим `x`

<details>
<summary>Ответ</summary>

**B.** `ROWNUM` применяется до `ORDER BY`. Нужен подзапрос с сортировкой и `ROWNUM` снаружи, либо `FETCH FIRST`.

</details>

## Вопрос №4. NULL-функции
Что вернёт `NVL2(x, 'A', 'B')`?

- A. `'A'`, если `x` равен NULL, иначе `'B'`
- B. `'A'`, если `x` не NULL, иначе `'B'`
- C. `x`, если он не NULL, иначе `'A'`
- D. Ошибку: такой функции нет

<details>
<summary>Ответ</summary>

**B.** `NVL2(expr, если_не_NULL, если_NULL)`. Для двух аргументов есть `NVL`. Стандартные `COALESCE` и `CASE` тоже работают.

</details>

## Вопрос №5. EXCEPT → MINUS
Какой оператор Oracle 19c соответствует `EXCEPT` из PostgreSQL?

- A. `MINUS`
- B. `EXCLUDE`
- C. `SUBTRACT`
- D. `NOT IN ALL`

<details>
<summary>Ответ</summary>

**A.** Вычитание множеств в Oracle записывается как `MINUS`.

</details>

## Вопрос №6. string_agg → LISTAGG
Что из перечисленного является аналогом `string_agg(col, ',' ORDER BY col)`?

- A. `STRING_AGG(col, ',')`
- B. `GROUP_CONCAT(col)`
- C. `LISTAGG(col, ',') WITHIN GROUP (ORDER BY col)`
- D. `CONCAT_WS(',', col)`

<details>
<summary>Ответ</summary>

**C.** В Oracle порядок задаётся в `WITHIN GROUP (ORDER BY ...)`.

</details>

## Вопрос №7. generate_series → CONNECT BY LEVEL
Как получить числа от 1 до 10 (аналог `generate_series(1,10)`)?

- A. `SELECT * FROM SERIES(1, 10)`
- B. `SELECT ROWNUM FROM DUAL`
- C. `SELECT * FROM GENERATE(10)`
- D. `SELECT LEVEL FROM DUAL CONNECT BY LEVEL <= 10`

<details>
<summary>Ответ</summary>

**D.** Иерархический запрос по `DUAL` с условием на `LEVEL` порождает нужное число строк.

</details>

## Вопрос №8. Иерархии и рекурсия
Какая конструкция является родным иерархическим синтаксисом Oracle?

- A. `START WITH ... CONNECT BY PRIOR ...`
- B. `WITH RECURSIVE ... UNION ALL`
- C. `HIERARCHY BY ...`
- D. `TREE WALK ...`

<details>
<summary>Ответ</summary>

**A.** Вместе с ней используются псевдостолбец `LEVEL` и функция `SYS_CONNECT_BY_PATH`. Рекурсивный `WITH` в Oracle тоже есть, но слова `RECURSIVE` в нём не пишут.

</details>

## Вопрос №9. Текущая дата и приведение типов
Как в Oracle получить текущую дату с обнулённым временем?

- A. `CURRENT_DATE::date`
- B. `SYSDATE::date`
- C. `TRUNC(SYSDATE)`
- D. `NOW()`

<details>
<summary>Ответ</summary>

**C.** Оператора `::` в Oracle нет, приведение делают через `CAST`, `TO_DATE` и `TRUNC`.

</details>

## Вопрос №10. Арифметика дат
Чему равно выражение `SYSDATE + 1`?

- A. Текущему моменту плюс одна секунда
- B. Текущему моменту плюс одни сутки
- C. Той же дате в следующем месяце
- D. Это ошибка: к `DATE` нельзя прибавлять число

<details>
<summary>Ответ</summary>

**B.** Целая часть числа это сутки. Для месяцев есть `ADD_MONTHS` и `MONTHS_BETWEEN`.

</details>

## Вопрос №11. Последовательности и идентификаторы
Какой вариант в Oracle 12c+ соответствует столбцу `serial` из PostgreSQL?

- A. `id SERIAL`
- B. `id AUTO_INCREMENT`
- C. `id NUMBER DEFAULT nextval('seq')`
- D. `id NUMBER GENERATED AS IDENTITY`

<details>
<summary>Ответ</summary>

**D.** Также можно вызывать `seq.NEXTVAL` у отдельной последовательности.

</details>

## Вопрос №12. Типы данных: text, int, boolean
Какое утверждение верно для Oracle 19c?

- A. Тип `BOOLEAN` для столбцов в SQL появился только в 23ai
- B. `TEXT` основной тип для длинных строк
- C. `INT` отдельный нативный 4-байтный тип, не связанный с `NUMBER`
- D. `BOOLEAN` доступен в SQL с версии 12c

<details>
<summary>Ответ</summary>

**A.** Строки хранят в `VARCHAR2` и `CLOB`, числа в `NUMBER` (`INT` для него лишь синоним).

</details>

## Вопрос №13. UPDATE ... FROM
Как в Oracle выполнить обновление, аналогичное `UPDATE ... FROM` в PostgreSQL?

- A. `UPDATE t SET ... FROM s WHERE ...`
- B. `UPDATE t JOIN s ON ... SET ...`
- C. Через `MERGE` или коррелированный подзапрос
- D. Только циклом в PL/SQL

<details>
<summary>Ответ</summary>

**C.** Синтаксиса `UPDATE ... FROM` в Oracle нет.

</details>

## Вопрос №14. INSERT ... ON CONFLICT → MERGE
Чем в Oracle заменяют `INSERT ... ON CONFLICT`?

- A. `INSERT ... ON DUPLICATE KEY UPDATE`
- B. `INSERT OR REPLACE`
- C. `UPSERT INTO`
- D. `MERGE INTO ... USING ... WHEN MATCHED / NOT MATCHED`

<details>
<summary>Ответ</summary>

**D.** Upsert в Oracle делается через `MERGE`.

</details>

## Вопрос №15. Алиас таблицы без AS
Какая запись корректна в Oracle?

- A. `FROM orders AS o`
- B. `FROM orders o`
- C. `FROM orders = o`
- D. `FROM orders (o)`

<details>
<summary>Ответ</summary>

**B.** Перед алиасом таблицы слово `AS` писать нельзя (для алиасов столбцов можно).

</details>

## Вопрос №16. Регистр неквотированных идентификаторов
В каком виде Oracle хранит имя `Orders`, написанное без кавычек?

- A. `ORDERS`
- B. `orders`
- C. `Orders`
- D. Зависит от `NLS_LANGUAGE`

<details>
<summary>Ответ</summary>

**A.** Oracle приводит неквотированные идентификаторы к верхнему регистру, PostgreSQL к нижнему.

</details>

## Вопрос №17. Старый синтаксис внешнего соединения
Что означает условие `a.id = b.id(+)`?

- A. INNER JOIN
- B. RIGHT OUTER JOIN
- C. FULL OUTER JOIN
- D. LEFT OUTER JOIN: строки `a` сохраняются, `b` может отсутствовать

<details>
<summary>Ответ</summary>

**D.** Знак `(+)` ставится у необязательной стороны. Такой синтаксис часто встречается в легаси.

</details>

## Вопрос №18. PIVOT / UNPIVOT
Что делает `PIVOT` в Oracle?

- A. Превращает столбцы в строки
- B. Объединяет результаты двух запросов
- C. Превращает значения столбца в отдельные столбцы с агрегацией
- D. Разбивает таблицу на партиции

<details>
<summary>Ответ</summary>

**C.** Обратную операцию выполняет `UNPIVOT`. Оба оператора встроены в Oracle.

</details>

## Вопрос №19. KEEP (DENSE_RANK FIRST ORDER BY ...)
Что делает выражение `MAX(sal) KEEP (DENSE_RANK FIRST ORDER BY hire_date)`?

- A. Сохраняет текущую транзакцию открытой
- B. Считает агрегат только по строкам, занявшим первое место по `hire_date`
- C. Фиксирует план выполнения запроса
- D. Сортирует результат по `sal`

<details>
<summary>Ответ</summary>

**B.** Конструкцию часто используют вместо оконных функций.

</details>

## Вопрос №20. Flashback Query
Что делает запрос `SELECT * FROM t AS OF TIMESTAMP (SYSTIMESTAMP - INTERVAL '10' MINUTE)`?

- A. Читает состояние таблицы, каким оно было 10 минут назад
- B. Блокирует таблицу на 10 минут
- C. Физически откатывает таблицу на 10 минут назад
- D. Возвращает только строки, изменённые за последние 10 минут

<details>
<summary>Ответ</summary>

**A.** Это flashback-запрос: он только читает прошлое состояние и ничего не откатывает.

</details>

# Раздел №2. Продвинутые SQL-возможности для трансформаций

## Вопрос №21. INSERT ALL / INSERT FIRST
Строка подходит под условия двух веток `WHEN`. Что произойдёт?

- A. `INSERT ALL` выполнит первую ветку, `INSERT FIRST` обе
- B. Оба варианта выполнят только первую ветку
- C. Оба варианта вернут ошибку
- D. `INSERT ALL` выполнит обе ветки, `INSERT FIRST` только первую подходящую

<details>
<summary>Ответ</summary>

**D.** Так можно за один проход по источнику раскладывать записи по нескольким таблицам.

</details>

## Вопрос №22. SQL/JSON: JSON_TABLE и другие функции
Какая функция Oracle превращает JSON-массив в строки и столбцы?

- A. `JSON_VALUE`
- B. `JSON_EXISTS`
- C. `JSON_TABLE`
- D. `JSON_QUERY`

<details>
<summary>Ответ</summary>

**C.** `JSON_VALUE` достаёт скаляр, `JSON_QUERY` фрагмент JSON, `JSON_EXISTS` проверяет наличие пути.

</details>

## Вопрос №23. MATCH_RECOGNIZE
Какие конструкции являются ключевыми в `MATCH_RECOGNIZE`?

- A. `PIVOT`, `UNPIVOT`, `KEEP`
- B. `PATTERN`, `DEFINE`, `MEASURES`, `AFTER MATCH SKIP`
- C. `CONNECT BY`, `START WITH`
- D. `MODEL`, `RULES`

<details>
<summary>Ответ</summary>

**B.** Применения: цепочки событий, sessionization, последовательные изменения состояния, анализ транзакционных паттернов. Доступно с 12c.

</details>

# Раздел №3. Типы данных, NULL и NLS

## Вопрос №24. Пустая строка = NULL
Вернёт ли строку запрос `SELECT 1 FROM dual WHERE '' IS NULL`?

- A. Да: пустая строка в Oracle это NULL
- B. Нет: пустая строка не NULL
- C. Нет: запрос завершится ошибкой
- D. Зависит от `NLS_COMP`

<details>
<summary>Ответ</summary>

**A.** В PostgreSQL `''` и `NULL` разные значения, в Oracle (для `VARCHAR2`) одно и то же.

</details>

## Вопрос №25. Тип DATE содержит время
Что хранит тип `DATE` в Oracle?

- A. Только дату, как в PostgreSQL
- B. Только время
- C. Дату и время с долями секунды
- D. Дату и время (без долей секунды)

<details>
<summary>Ответ</summary>

**D.** Для долей секунды нужен `TIMESTAMP`.

</details>

## Вопрос №26. Конкатенация с NULL
Что вернёт `'abc' || NULL` в PostgreSQL и в Oracle?

- A. В обеих NULL
- B. PostgreSQL: NULL, Oracle: `'abc'`
- C. PostgreSQL: `'abc'`, Oracle: NULL
- D. В обеих `'abc'`

<details>
<summary>Ответ</summary>

**B.** Это важно при переносе трансформаций, составных ключей и хешируемых строк.

</details>

## Вопрос №27. Составной UNIQUE и NULL
В таблицу с `UNIQUE (a, b)` дважды вставляют `(1, NULL)`. Что произойдёт?

- A. Обе СУБД разрешат
- B. Обе СУБД вернут ошибку
- C. PostgreSQL разрешит, Oracle вернёт ошибку
- D. PostgreSQL вернёт ошибку, Oracle разрешит

<details>
<summary>Ответ</summary>

**C.** `(NULL, NULL)` дважды разрешено в обеих, `(1, 2)` дважды запрещено в обеих. Для PostgreSQL имеется в виду поведение без `NULLS NOT DISTINCT` (15+).

</details>

## Вопрос №28. Неявные преобразования и NLS
Как избежать зависимости условия по дате от `NLS_DATE_FORMAT`?

- A. Использовать литерал `DATE '2026-02-01'`
- B. Сравнивать со строкой `'01-02-2026'`
- C. Применить `TO_CHAR` к столбцу даты
- D. Положиться на настройки клиента

<details>
<summary>Ответ</summary>

**A.** Для timestamp аналогично: `TIMESTAMP '2026-02-01 12:30:00'`. `TO_CHAR` на столбце к тому же мешает использованию индекса.

</details>

## Вопрос №29. VARCHAR2: BYTE против CHAR
Строка из 100 кириллических символов в UTF-8 вставляется в `VARCHAR2(100 BYTE)`. Что верно?

- A. Всегда помещается
- B. Помещается только при `MAX_STRING_SIZE = EXTENDED`
- C. Помещается, потому что 100 символов это 100 байт
- D. Может не поместиться: кириллица занимает несколько байтов

<details>
<summary>Ответ</summary>

**D.** `VARCHAR2(100 CHAR)` ограничивает символы. `MAX_STRING_SIZE`: `STANDARD` даёт 4000 байт, `EXTENDED` 32767 байт.

</details>

## Вопрос №30. NUMBER, BINARY_FLOAT, BINARY_DOUBLE
Чем `NUMBER` без параметров отличается от `NUMBER(38,0)`?

- A. Ничем
- B. `NUMBER` без точности и масштаба допускает дробные значения, `NUMBER(38,0)` только целые
- C. `NUMBER` целочисленный, `NUMBER(38,0)` дробный
- D. `NUMBER` двоичная плавающая точка

<details>
<summary>Ответ</summary>

**B.** Двоичную плавающую точку дают `BINARY_FLOAT` и `BINARY_DOUBLE`. Это критично при переносе `NUMERIC` и больших идентификаторов.

</details>

# Раздел №4. Транзакции, изоляция и блокировки

## Вопрос №31. DDL делает неявный COMMIT
В транзакции выполнен `UPDATE` без `COMMIT`, затем `CREATE TABLE`. Что произойдёт с `UPDATE`?

- A. Откатится
- B. Останется в транзакции и откатится вместе с DDL
- C. Будет зафиксирован неявным COMMIT
- D. `CREATE TABLE` завершится ошибкой

<details>
<summary>Ответ</summary>

**C.** В PostgreSQL DDL транзакционный, в Oracle нет. `CREATE` или `DROP` откатить нельзя.

</details>

## Вопрос №32. Автокоммита в DML нет
Что видят другие сессии после `UPDATE` без `COMMIT`?

- A. Старые данные
- B. Новые данные
- C. Строки блокируются для чтения
- D. Ошибку ORA-00054

<details>
<summary>Ответ</summary>

**A.** Читатели не блокируются и видят согласованный снимок до изменения.

</details>

## Вопрос №33. MVCC на UNDO и ORA-01555
На чём построен MVCC в Oracle и какая ошибка возможна на долгих запросах?

- A. Версии строк в куче; ORA-00060
- B. Версии строк в куче; ORA-01555
- C. UNDO; ORA-00060
- D. UNDO; ORA-01555 (snapshot too old)

<details>
<summary>Ответ</summary>

**D.** Поэтому нет `VACUUM` и bloat в привычном смысле.

</details>

## Вопрос №34. Уровни изоляции
Какого уровня изоляции из привычных разработчику PostgreSQL в Oracle нет?

- A. `READ COMMITTED`
- B. `REPEATABLE READ`
- C. `SERIALIZABLE`
- D. Нет ни одного из них

<details>
<summary>Ответ</summary>

**B.** В Oracle есть `READ COMMITTED`, `SERIALIZABLE` и режим `READ ONLY` транзакции.

</details>

## Вопрос №35. Согласованный снимок и ORA-08177
Что верно про согласованность чтения в Oracle?

- A. `READ COMMITTED`: на уровне транзакции; ошибка ORA-01555
- B. `READ COMMITTED`: на уровне транзакции; ошибка ORA-00060
- C. `READ COMMITTED`: на уровне SQL-оператора; в `SERIALIZABLE` возможна ORA-08177
- D. `READ COMMITTED`: на уровне SQL-оператора; ORA-08177 бывает только в `READ ONLY`

<details>
<summary>Ответ</summary>

**C.** `SET TRANSACTION READ ONLY` фиксирует снимок для всей читающей транзакции.

</details>

## Вопрос №36. Блокировки: SKIP LOCKED, NOWAIT, WAIT
Какой синтаксис позволяет нескольким ETL-воркерам брать задачи из очереди, не дожидаясь друг друга?

- A. `FOR UPDATE SKIP LOCKED`
- B. `FOR UPDATE NOWAIT`
- C. `FOR UPDATE WAIT 5`
- D. `LOCK TABLE ... IN EXCLUSIVE MODE`

<details>
<summary>Ответ</summary>

**A.** `NOWAIT` сразу вернёт ORA-00054, `WAIT 5` подождёт до 5 секунд. Взаимная блокировка даёт ORA-00060. `SKIP LOCKED` не заменяет управление состояниями задач и гарантии повторного исполнения.

</details>

# Раздел №5. Хранение, объекты и ограничения

## Вопрос №37. High Water Mark (HWM)
После массового `DELETE` full scan таблицы остался медленным. Почему и что делать?

- A. `DELETE` повышает HWM; нужен `ANALYZE`
- B. `DELETE` не снижает HWM; помогут `TRUNCATE`, `ALTER TABLE ... MOVE` или `SHRINK SPACE`
- C. Не выполнен `COMMIT`; достаточно его сделать
- D. Сломан индекс; нужно его пересоздать

<details>
<summary>Ответ</summary>

**B.** Full scan читает все блоки до HWM, даже если они пусты.

</details>

## Вопрос №38. Global Temporary Table
Что верно про Global Temporary Table?

- A. Структура временная и исчезает после сессии
- B. Данные видны всем сессиям
- C. Это точный аналог `CREATE TEMP TABLE` в PostgreSQL
- D. Структура постоянная, данные живут в рамках сессии или транзакции

<details>
<summary>Ответ</summary>

**D.** Поведение задаётся `ON COMMIT DELETE ROWS` или `ON COMMIT PRESERVE ROWS`.

</details>

## Вопрос №39. Private Temporary Tables
Что верно про Private Temporary Table?

- A. Появились в 12c, `CREATE` делает неявный COMMIT
- B. Определение хранится постоянно между сессиями
- C. Доступны с 18c, определение живёт в сессии или транзакции, создание не фиксирует транзакцию
- D. Видны всем сессиям

<details>
<summary>Ответ</summary>

**C.** Имя должно начинаться с префикса `ORA$PTT_`. По жизненному циклу ближе к временным объектам PostgreSQL.

</details>

## Вопрос №40. Схема = пользователь, синонимы, DB LINK
Чему соответствует схема в Oracle?

- A. Пользователю: схема и пользователь это одно и то же
- B. Отдельному каталогу в файловой системе
- C. Контейнеру PDB
- D. Табличному пространству

<details>
<summary>Ответ</summary>

**A.** Рядом нужно знать синонимы (`PUBLIC SYNONYM`), `DB LINK` и табличные пространства.

</details>

## Вопрос №41. Корзина (recycle bin)
Как вернуть случайно удалённую командой `DROP TABLE` таблицу (без `PURGE`)?

- A. `ROLLBACK`
- B. `FLASHBACK TABLE ... TO BEFORE DROP`
- C. `UNDROP TABLE`
- D. Никак

<details>
<summary>Ответ</summary>

**B.** Таблица попадает в recycle bin. Окончательно удаляет `PURGE`.

</details>

## Вопрос №42. Жизненный цикл ограничений
Какое состояние ограничения проверяет новые изменения, но не проверяет уже существующие данные?

- A. `ENABLE VALIDATE`
- B. `DISABLE NOVALIDATE`
- C. `RELY`
- D. `ENABLE NOVALIDATE`

<details>
<summary>Ответ</summary>

**D.** `RELY` лишь объявляет оптимизатору, что ограничению можно доверять. Эти состояния важны для больших исторических таблиц и DWH.

</details>

## Вопрос №43. Последовательности: CACHE и ORDER в RAC
Что верно для последовательности с `CACHE` и `NOORDER` в RAC?

- A. Значения выдаются строго без пропусков
- B. Значение отражает хронологию событий
- C. Возможны пропуски, глобальный порядок между экземплярами не гарантируется
- D. Порядок гарантируется всегда

<details>
<summary>Ответ</summary>

**C.** Значение sequence нельзя считать гарантированным признаком хронологии.

</details>

## Вопрос №44. Физическое сжатие и колоночные механизмы
Что из перечисленного является механизмом сжатия или колоночного хранения Oracle?

- A. Hybrid Columnar Compression (HCC)
- B. AO/AOCO
- C. `VACUUM FULL`
- D. TOAST

<details>
<summary>Ответ</summary>

**A.** Ещё есть Basic Table Compression, Advanced Row Compression, In-Memory Column Store и Exadata Smart Scan. AO/AOCO это хранение Greenplum.

</details>

## Вопрос №45. Лицензирование опций
Что верно о лицензировании Oracle 19c?

- A. Всё включено в базовую лицензию
- B. Partitioning, Advanced Compression и Database In-Memory имеют отдельные условия лицензирования
- C. Платным является только RAC
- D. Лицензирование не влияет на выбор механизмов хранения

<details>
<summary>Ответ</summary>

**B.** Механизмы различаются по физической организации, поддерживаемому оборудованию и лицензированию.

</details>

# Раздел №6. Производительность и оптимизатор

## Вопрос №46. Хинты: синтаксис и поведение
Что произойдёт, если в хинте допущена опечатка в его имени?

- A. Ошибка ORA с остановкой запроса
- B. Предупреждение в `alert.log`
- C. Запрос будет отклонён оптимизатором
- D. Хинт будет молча проигнорирован

<details>
<summary>Ответ</summary>

**D.** Хинты пишут как `/*+ ... */` сразу после `SELECT`, `INSERT`, `UPDATE`, `MERGE` или `DELETE`.

</details>

## Вопрос №47. Самые употребимые хинты
Какой хинт включает direct-path вставку?

- A. `PARALLEL`
- B. `FULL`
- C. `APPEND`
- D. `NO_MERGE`

<details>
<summary>Ответ</summary>

**C.** Остальные: `USE_HASH`, `USE_NL`, `USE_MERGE`, `LEADING`, `MATERIALIZE` / `INLINE`, `PUSH_PRED`, `CARDINALITY`, `DYNAMIC_SAMPLING`, `GATHER_PLAN_STATISTICS`.

</details>

## Вопрос №48. Direct-path загрузка и parallel DML
Что нужно сделать, чтобы `INSERT /*+ APPEND PARALLEL(t 8) */` выполнялся параллельно?

- A. `ALTER SESSION ENABLE PARALLEL DML`
- B. Достаточно одного хинта `PARALLEL`
- C. Ничего: parallel DML включён по умолчанию
- D. Указать `NOLOGGING`

<details>
<summary>Ответ</summary>

**A.** До `COMMIT` читать эту таблицу в этой же сессии нельзя (ORA-12838).

</details>

## Вопрос №49. Планы выполнения и ALLSTATS LAST
Что показывает E-Rows и A-Rows последнего выполнения запроса?

- A. `EXPLAIN PLAN FOR` + `DBMS_XPLAN.DISPLAY`
- B. `DBMS_XPLAN.DISPLAY_CURSOR(NULL, NULL, 'ALLSTATS LAST')`
- C. `V$SESSION`
- D. `TKPROF`

<details>
<summary>Ответ</summary>

**B.** Сравнение оценки и факта главный способ найти ошибку оптимизатора. Для A-Rows нужен хинт `GATHER_PLAN_STATISTICS`.

</details>

## Вопрос №50. Мониторинг и трассировка
Какая пара используется для трассировки сессии и разбора её результата?

- A. `V$SQL` и `V$SESSION`
- B. AWR и ASH
- C. SQL Profile и SPM
- D. Событие 10046 и TKPROF

<details>
<summary>Ответ</summary>

**D.** Для мониторинга служат SQL Monitor, AWR/ASH-отчёты, `V$SQL`, `V$SESSION`, `V$SESSION_LONGOPS`.

</details>

## Вопрос №51. Управление планами
Какой механизм позволяет зафиксировать проверенный план выполнения?

- A. SQL Plan Baseline (SPM)
- B. `DBMS_STATS`
- C. `PGA_AGGREGATE_TARGET`
- D. MV Log

<details>
<summary>Ответ</summary>

**A.** Также есть SQL Profile и `SQL Tuning Advisor`.

</details>

## Вопрос №52. Статистика: DBMS_STATS
Чем рекомендуется собирать статистику для оптимизатора в Oracle?

- A. `ANALYZE TABLE`
- B. `VACUUM ANALYZE`
- C. `DBMS_STATS.GATHER_TABLE_STATS`
- D. `UPDATE STATISTICS`

<details>
<summary>Ответ</summary>

**C.** Можно задавать `degree` и `method_opt`. Про гистограммы и extended stats спросят отдельно.

</details>

## Вопрос №53. Bind-переменные и parsing
Почему литералы вместо bind-переменных вредят производительности Oracle?

- A. Не используются индексы
- B. Это лишь вопрос безопасности
- C. Всегда растёт TEMP
- D. Каждый уникальный текст запроса требует hard parse и засоряет shared pool

<details>
<summary>Ответ</summary>

**D.** Нужно различать hard и soft parse. Рядом: bind peeking и параметр `CURSOR_SHARING`.

</details>

## Вопрос №54. Adaptive Cursor Sharing
Что такое Adaptive Cursor Sharing?

- A. Один SQL всегда использует один и тот же план
- B. Один `SQL_ID` может иметь несколько child cursors с разными планами в зависимости от значений биндов
- C. Перенос курсоров между узлами RAC
- D. Кеширование результатов запроса

<details>
<summary>Ответ</summary>

**B.** Признаки: `BIND_SENSITIVE`, `BIND_AWARE`, `CHILD_NUMBER`, `PLAN_HASH_VALUE`, `V$SQL_SHARED_CURSOR`.

</details>

## Вопрос №55. Индексы: виды
Какой тип индекса характерен для DWH и столбцов с низкой кардинальностью?

- A. Bitmap
- B. Reverse key
- C. IOT
- D. Function-based

<details>
<summary>Ответ</summary>

**A.** Также бывают B-tree, function-based, local и global на партициях, IOT и invisible index.

</details>

## Вопрос №56. Clustering Factor
`CLUSTERING_FACTOR` индекса близок к числу строк в таблице. Что это значит?

- A. Индекс идеален
- B. Индекс повреждён
- C. Порядок строк плохо соответствует порядку ключей, доступ по индексу даёт много переходов между блоками
- D. Нужно всегда увеличивать `BLEVEL`

<details>
<summary>Ответ</summary>

**C.** Значение, близкое к числу блоков, означает хорошую сгруппированность данных.

</details>

## Вопрос №57. Parallel Execution: соответствие Greenplum → Oracle
Какая операция Oracle соответствует `Gather Motion` из Greenplum?

- A. `PX SEND HASH`
- B. `PX SEND BROADCAST`
- C. `PX BLOCK ITERATOR`
- D. `PX SEND QC`

<details>
<summary>Ответ</summary>

**D.** `PX SEND HASH` соответствует Redistribute Motion, `PX SEND BROADCAST` Broadcast Motion. Query Dispatcher это Query Coordinator (QC).

</details>

## Вопрос №58. Элементы PX-плана и DOP
Сколько PX-процессов может задействовать запрос с DOP 8?

- A. Строго 8
- B. До 16, когда одновременно работают две группы
- C. Не более 4
- D. Всегда 64

<details>
<summary>Ответ</summary>

**B.** `PX COORDINATOR` управляет планом, `PX SEND` и `PX RECEIVE` передают и принимают данные, `PX BLOCK ITERATOR` раздаёт блоки таблицы.

</details>

## Вопрос №59. V$PQ_TQSTAT, data skew, PQ_DISTRIBUTE
Один PX-процесс получает 80% данных, остальные простаивают. Что это и что делать?

- A. Data skew: увеличение DOP не поможет, смотреть `V$PQ_TQSTAT` и применять `PQ_DISTRIBUTE`
- B. Нехватка PGA: увеличить `PGA_AGGREGATE_TARGET`
- C. Нехватка параллелизма: увеличить DOP
- D. Deadlock: перезапустить запрос

<details>
<summary>Ответ</summary>

**A.** `V$PQ_TQSTAT` показывает, сколько строк и байтов передавалось между PX-процессами.

</details>

## Вопрос №60. Partition Pruning
Что означает `PARTITION RANGE ALL` в плане?

- A. Читается одна партиция
- B. Читается подмножество партиций
- C. Читаются все партиции, отсечения нет
- D. Партиции определяются динамически через `KEY`

<details>
<summary>Ответ</summary>

**C.** `SINGLE` одна партиция, `ITERATOR` подмножество, `PSTART` / `PSTOP` диапазон, `KEY` динамическое определение.

</details>

## Вопрос №61. Partition-Wise Join
При каком условии Oracle может соединять соответствующие партиции без полного перераспределения данных?

- A. Таблицы лежат в разных табличных пространствах
- B. Обе таблицы совместимо партиционированы по ключу соединения
- C. Обе таблицы глобальные временные
- D. Указан хинт `USE_HASH`

<details>
<summary>Ответ</summary>

**B.** Для Greenplum это знакомая проблема локальности данных.

</details>

## Вопрос №62. SGA, PGA, workarea и TEMP
Как называется память для сортировок, hash join и агрегаций в Oracle?

- A. Shared pool
- B. Buffer cache
- C. Undo
- D. Workarea в PGA

<details>
<summary>Ответ</summary>

**D.** SGA общая память экземпляра, PGA память серверного процесса. То, что не помещается в память, уходит в TEMP. Целевой объём PGA: `PGA_AGGREGATE_TARGET`.

</details>

## Вопрос №63. Режимы workarea и диагностика
Какой режим выполнения операции самый быстрый?

- A. OPTIMAL: всё в памяти
- B. ONE PASS
- C. MULTI-PASS
- D. Все режимы одинаковы

<details>
<summary>Ответ</summary>

**A.** Диагностика через `v$sql_workarea`. Ошибки: `ORA-01652` (временный сегмент) и `ORA-04036` (лимит PGA).

</details>

## Вопрос №64. Database Resource Manager
Какой механизм управляет приоритетами запросов, долями CPU, пределами параллельных серверов и очередями параллельных запросов?

- A. SQL Plan Management
- B. AWR
- C. Database Resource Manager
- D. PGA Advisor

<details>
<summary>Ответ</summary>

**C.** Ключевые понятия: `CONSUMER GROUP`, `RESOURCE PLAN`, `PARALLEL_SERVERS_TARGET`, `PARALLEL_DEGREE_POLICY`.

</details>

# Раздел №7. ETL: партиционирование, загрузка и выгрузка данных

## Вопрос №65. Виды партиционирования
Какой тип партиционирования создаёт новые партиции автоматически?

- A. Range
- B. Hash
- C. Reference
- D. Interval

<details>
<summary>Ответ</summary>

**D.** Также есть list, composite и reference.

</details>

## Вопрос №66. EXCHANGE PARTITION и операции над партициями
Какая операция мгновенно подменяет данные партиции данными staging-таблицы?

- A. `ALTER TABLE t EXCHANGE PARTITION p WITH TABLE stg`
- B. `INSERT /*+ APPEND */ ... SELECT`
- C. `TRUNCATE PARTITION`
- D. `MERGE`

<details>
<summary>Ответ</summary>

**A.** Обмен меняет только метаданные. Рядом используют `TRUNCATE PARTITION` и `UPDATE GLOBAL INDEXES`.

</details>

## Вопрос №67. Materialized views
Что нужно для инкрементального обновления `REFRESH FAST` (в общем случае)?

- A. Режим `NOLOGGING`
- B. Bitmap-индекс
- C. MV Log на базовых таблицах
- D. External Table

<details>
<summary>Ответ</summary>

**C.** Режимы обновления: `ON COMMIT` и `ON DEMAND`. Ещё нужно знать `COMPLETE` и query rewrite.

</details>

## Вопрос №68. External Tables, SQL*Loader, Data Pump
Что из перечисленного ближе всего к `gpfdist` / `gpload` из Greenplum?

- A. `DBMS_SCHEDULER`
- B. External Tables и SQL*Loader
- C. GoldenGate
- D. `TKPROF`

<details>
<summary>Ответ</summary>

**B.** External Tables работают через `ORACLE_LOADER` или `ORACLE_DATAPUMP`. Data Pump это `expdp` / `impdp`.

</details>

## Вопрос №69. DML Error Logging
Какая конструкция записывает ошибочные строки в таблицу и не останавливает `INSERT ... SELECT`?

- A. `EXCEPTIONS INTO err_table`
- B. `ON ERROR CONTINUE`
- C. `SAVE EXCEPTIONS`
- D. `LOG ERRORS INTO err$_orders (...) REJECT LIMIT UNLIMITED`

<details>
<summary>Ответ</summary>

**D.** Сначала нужно создать таблицу ошибок через `DBMS_ERRLOG.CREATE_ERROR_LOG`. `ORA_ERR_TAG$` идентифицирует пакет загрузки. Нарушение уникальности при direct-path `INSERT` построчно не обрабатывается. `SAVE EXCEPTIONS` относится к `FORALL`.

</details>

## Вопрос №70. Планировщик DBMS_SCHEDULER
Какой компонент Oracle отвечает за jobs и chains?

- A. `DBMS_SCHEDULER`
- B. `UTL_FILE`
- C. `DBMS_LOB`
- D. `DBMS_ERRLOG`

<details>
<summary>Ответ</summary>

**A.** `DBMS_SCHEDULER` встроенный планировщик заданий.

</details>

## Вопрос №71. Python: python-oracledb
Как называется драйвер, ранее известный как `cx_Oracle`?

- A. `oracle-py`
- B. `python-oracledb`
- C. `pyoracle`
- D. `ora-connect`

<details>
<summary>Ответ</summary>

**B.** Биндинг: `:1` / `:name`. Для пакетной вставки есть `executemany`, для чтения настраивают `arraysize`.

</details>

## Вопрос №72. Репликация, CDC и ETL-инструменты
Какой продукт относится к репликации и CDC в экосистеме Oracle?

- A. `TKPROF`
- B. RMAN
- C. GoldenGate
- D. `DBMS_XPLAN`

<details>
<summary>Ответ</summary>

**C.** Из ETL-инструментов часто встречаются ODI и Informatica.

</details>

# Раздел №8. PL/SQL

## Вопрос №73. Пакеты, анонимные блоки, исключения
Из чего состоит пакет PL/SQL?

- A. Из спецификации (spec) и тела (body)
- B. Только из тела
- C. Из таблицы и индекса
- D. Из триггера и последовательности

<details>
<summary>Ответ</summary>

**A.** Кроме пакетов нужно знать анонимные блоки и обработку исключений.

</details>

## Вопрос №74. BULK COLLECT + FORALL
Что применяют вместо построчной обработки («slow-by-slow») в PL/SQL?

- A. Курсорный цикл с `COMMIT` на каждой строке
- B. `PRAGMA AUTONOMOUS_TRANSACTION`
- C. `DBMS_OUTPUT`
- D. `BULK COLLECT` и `FORALL`

<details>
<summary>Ответ</summary>

**D.** Пакетная обработка резко сокращает переключения между PL/SQL и SQL.

</details>

## Вопрос №75. RETURNING INTO и AUTONOMOUS_TRANSACTION
Что делает `PRAGMA AUTONOMOUS_TRANSACTION`?

- A. Запускает запрос в параллельном режиме
- B. Запускает независимую транзакцию, чей коммит не зависит от вызывающей
- C. Отключает undo
- D. Включает двухфазный коммит

<details>
<summary>Ответ</summary>

**B.** `RETURNING ... INTO` возвращает значения изменённых строк.

</details>

## Вопрос №76. Коллекции
Какие типы коллекций есть в PL/SQL?

- A. tuple, list, set
- B. array, stack, queue
- C. nested table, varray, associative array
- D. vector, map, bag

<details>
<summary>Ответ</summary>

**C.** Это три основных вида коллекций PL/SQL.

</details>

## Вопрос №77. Pipelined table functions
Что делает pipelined table function?

- A. Отдаёт строки по мере готовности и вызывается как таблица через `TABLE(...)`
- B. Возвращает только `CLOB`
- C. Выполняет parallel DML
- D. Работает только вне пакетов

<details>
<summary>Ответ</summary>

**A.** Это конвейерные табличные функции.

</details>

## Вопрос №78. Системные пакеты
Какой пакет используется для чтения и записи файлов на сервере БД?

- A. `DBMS_OUTPUT`
- B. `DBMS_LOB`
- C. `DBMS_STATS`
- D. `UTL_FILE`

<details>
<summary>Ответ</summary>

**D.** `DBMS_OUTPUT` вывод, `DBMS_LOB` большие объекты, `DBMS_STATS` статистика, `DBMS_PARALLEL_EXECUTE` параллельная обработка кусками.

</details>

## Вопрос №79. Права внутри PL/SQL: AUTHID
Процедура создана с `AUTHID DEFINER`. Владелец получил право на таблицу только через роль. Что произойдёт?

- A. Всё заработает
- B. Статический SQL не скомпилируется: права владельцу нужны напрямую
- C. Заработает только в RAC
- D. Процедура автоматически станет `CURRENT_USER`

<details>
<summary>Ответ</summary>

**B.** `AUTHID DEFINER` режим по умолчанию. При этом обычный SELECT под пользователем работает, а компиляция процедуры нет.

</details>

# Раздел №9. Словарь и ошибки

## Вопрос №80. Словарь данных
Что в Oracle соответствует `information_schema` и `pg_catalog`?

- A. Таблица `DUAL`
- B. Recycle bin
- C. Представления `USER_TABLES`, `ALL_TAB_COLUMNS`, `DBA_SEGMENTS`, `V$...`
- D. Только отчёты AWR

<details>
<summary>Ответ</summary>

**C.** Ещё полезно `USER_TAB_PARTITIONS`.

</details>

## Вопрос №81. Ошибки из основного списка
Какая ошибка возникает при `MERGE`, если одной целевой строке соответствует несколько исходных (нестабильный набор строк)?

- A. ORA-30926
- B. ORA-01427
- C. ORA-00942
- D. ORA-01722

<details>
<summary>Ответ</summary>

**A.** Остальные: `ORA-00942` таблица не найдена, `ORA-01722` неверное число, `ORA-00001` нарушение уникальности, `ORA-01555` snapshot too old, `ORA-12838` чтение после direct-path до коммита, `ORA-01427` подзапрос вернул больше одной строки.

</details>

## Вопрос №82. Ошибки из дополнительных тем
Какая ошибка означает, что не удалось выделить временный сегмент (проблема TEMP)?

- A. ORA-08177
- B. ORA-00054
- C. ORA-04036
- D. ORA-01652

<details>
<summary>Ответ</summary>

**D.** `ORA-08177` конфликт в `SERIALIZABLE`, `ORA-04036` лимит PGA, `ORA-00054` ресурс занят, `ORA-00060` deadlock.

</details>

# Раздел №10. Архитектура, восстановление и инфраструктура

## Вопрос №83. Multitenant: CDB и PDB
Что такое PDB?

- A. Узел кластера RAC
- B. Подключаемая база данных внутри контейнерной базы (CDB)
- C. Табличное пространство
- D. Резервная база Data Guard

<details>
<summary>Ответ</summary>

**B.** Корневой контейнер `CDB$ROOT`, переключение: `ALTER SESSION SET CONTAINER = ...`. Разные PDB одной CDB дают доступ к разным наборам пользовательских объектов.

</details>

## Вопрос №84. Real Application Clusters (RAC)
Что обеспечивает Cache Fusion?

- A. Сжатие данных
- B. Репликацию redo на резервную базу
- C. Согласование доступа к блокам между экземплярами RAC
- D. Партиционирование

<details>
<summary>Ответ</summary>

**C.** RAC это несколько экземпляров с одной общей БД, а не MPP, как Greenplum. Для обзора кластера используют `GV$`-представления с `INST_ID`, а в ожиданиях видны `gc`.

</details>

## Вопрос №85. Oracle Net: service name, SID, listener
Какой процесс принимает входящие клиентские соединения в Oracle Net?

- A. Listener
- B. LGWR
- C. DBWR
- D. PX coordinator

<details>
<summary>Ответ</summary>

**A.** К базе подключаются по `SERVICE_NAME` (или `SID`).

</details>

## Вопрос №86. Распределённые запросы: DRIVING_SITE и 2PC
Какой хинт влияет на то, где будет выполнен распределённый запрос между Oracle-базами?

- A. `PQ_DISTRIBUTE`
- B. `LEADING`
- C. `USE_HASH`
- D. `DRIVING_SITE`

<details>
<summary>Ответ</summary>

**D.** Two-Phase Commit согласует фиксацию транзакции, изменяющей данные в нескольких базах.

</details>

## Вопрос №87. SCN, redo, RMAN, Data Guard
Какую роль выполняет процесс LGWR?

- A. Записывает изменённые блоки из buffer cache на диск
- B. Записывает redo в журнал
- C. Делает резервную копию
- D. Парсит SQL

<details>
<summary>Ответ</summary>

**B.** Изменённые блоки пишет DBWR. SCN логическая отметка изменений, RMAN резервное копирование, Data Guard передаёт и применяет redo на резервные базы.

</details>

## Вопрос №88. Ловушка NOLOGGING
Чем опасен `NOLOGGING` при быстрой загрузке?

- A. Таблицу нельзя будет читать
- B. Таблица блокируется навсегда
- C. Загруженные данные могут оказаться невосстановимыми при media recovery
- D. Отключается undo для всей базы

<details>
<summary>Ответ</summary>

**C.** Стратегию быстрой загрузки нужно согласовывать с требованиями восстановления и резервирования.

</details>

# Раздел №11. Типичные вопросы на собеседовании и опорные ответы

## Вопрос №89. Как загрузить 100 млн строк быстро?
Какой подход ближе всего к опорному ответу?

- A. Staging, `INSERT /*+ APPEND PARALLEL */`, `NOLOGGING`, отключить или перестроить индексы, `EXCHANGE PARTITION`
- B. Построчный `INSERT` в цикле PL/SQL с `COMMIT` на каждой строке
- C. Один `INSERT` без хинтов при включённых индексах
- D. `DELETE` старых данных и повторный `INSERT`

<details>
<summary>Ответ</summary>

**A.** Лучше грузить в staging и подменять партицию.

</details>

## Вопрос №90. Запрос внезапно стал медленным
С чего начинать диагностику внезапно замедлившегося запроса?

- A. Сразу увеличить DOP
- B. Пересоздать таблицу
- C. Добавить хинты
- D. Проверить актуальность статистики, затем `ALLSTATS LAST` (E-Rows против A-Rows), потом смену плана

<details>
<summary>Ответ</summary>

**D.** Причиной смены плана могут быть bind peeking или baseline.

</details>

## Вопрос №91. Чем TRUNCATE отличается от DELETE?
Что верно?

- A. `TRUNCATE` это DML, его можно откатить
- B. `TRUNCATE` это DDL с неявным коммитом, сбрасывает HWM, не создаёт undo
- C. `TRUNCATE` не снижает HWM
- D. `TRUNCATE` вызывает построчные триггеры

<details>
<summary>Ответ</summary>

**B.** `DELETE` не снижает HWM и порождает undo.

</details>

## Вопрос №92. Чем PostgreSQL отличается от Oracle по MVCC?
Выберите верное сравнение.

- A. Oracle хранит версии в куче и требует `VACUUM`
- B. Реализации одинаковы
- C. Oracle использует undo вместо версий в куче: нет `VACUUM`, но есть ORA-01555
- D. В Oracle MVCC нет

<details>
<summary>Ответ</summary>

**C.** Это опорный ответ на вопрос.

</details>

## Вопрос №93. Как сделать upsert?
Как делают upsert в Oracle и что означает ORA-30926?

- A. `MERGE`; ошибка возникает при нестабильном (неоднозначном) наборе строк источника
- B. `MERGE`; ошибка означает, что таблица не найдена
- C. `INSERT ... ON CONFLICT`; ошибка означает дубликат
- D. `UPDATE ... FROM`; ошибка означает deadlock

<details>
<summary>Ответ</summary>

**A.** Нужно знать, что делать с ORA-30926: убрать неоднозначность в источнике.

</details>

## Вопрос №94. Почему два SELECT в одной транзакции вернули разные данные?
В `READ COMMITTED` два последовательных `SELECT` внутри одной Oracle-транзакции вернули разные данные. Почему?

- A. Это баг
- B. Сработала ORA-01555
- C. Включён `SERIALIZABLE`
- D. Каждый оператор получает свой согласованный снимок, а чужой коммит между запросами виден второму

<details>
<summary>Ответ</summary>

**D.** Чтобы оба запроса читали один снимок, нужен `SET TRANSACTION READ ONLY` или `SERIALIZABLE`.

</details>

## Вопрос №95. Join двух партиционированных таблиц по 500 млн строк медленный
Что проверять в первую очередь?

- A. Только тип JOIN
- B. Наличие partition-wise join, число читаемых партиций, data skew и межпроцессную передачу данных
- C. Только наличие индексов
- D. Размер буфера журнала

<details>
<summary>Ответ</summary>

**B.** Партиционирование само по себе скорость join не гарантирует.

</details>

## Вопрос №96. Удалённая база: пересылать данные или агрегировать на месте
Нужно получить агрегат по 100 млн строк из удалённой базы. Что разумнее?

- A. Переслать все строки и агрегировать локально
- B. Скопировать таблицу целиком в локальную базу
- C. Агрегировать на удалённой стороне и передать только результат, при необходимости управляя местом выполнения через `DRIVING_SITE`
- D. Всегда использовать 2PC

<details>
<summary>Ответ</summary>

**C.** Важно понимать объём данных, передаваемых по сети.

</details>

# Раздел №12. Подготовка к собеседованию

## Вопрос №97. Совет: как честно подать свой опыт
Как стоит описывать опыт работы с Oracle, если основной опыт в PostgreSQL и Greenplum?

- A. Честно: знание на уровне маппинга («в PG так, в Oracle `MERGE`, `APPEND`, `EXCHANGE PARTITION`, `DBMS_STATS`») плюс осознанное понимание отличий
- B. Заявить промышленный опыт в Oracle
- C. Не упоминать PostgreSQL и Greenplum
- D. Говорить только про PL/SQL

<details>
<summary>Ответ</summary>

**A.** Два-три уточняющих вопроса про планы, хинты или PL/SQL быстро вскрывают завышенный опыт.

</details>

## Вопрос №98. Что учить в первую очередь
Какая тема стоит первой в списке приоритетов подготовки для DE?

- A. NLS, типы, constraints
- B. CDB/PDB и RAC
- C. `JSON_TABLE` и `MATCH_RECOGNIZE`
- D. PX, data redistribution, data skew

<details>
<summary>Ответ</summary>

**D.** Дальше идут: partition pruning и partition-wise join, PGA/TEMP, DML Error Logging, Adaptive Cursor Sharing, SCN/REDO, CDB/PDB и RAC, JSON_TABLE и MATCH_RECOGNIZE, изоляция и блокировки, NLS/типы/constraints.

</details>

## Вопрос №99. Практический кейс для подготовки
Какой сценарий рекомендован для комплексной практики?

- A. Установка RAC-кластера
- B. Загрузка 100 млн строк из staging, проверка качества, преобразования, партиционирование, параллельное выполнение и диагностика деградации SQL
- C. Миграция PDB между контейнерами
- D. Настройка Data Guard

<details>
<summary>Ответ</summary>

**B.** Такой кейс проверяет большую часть перечисленных особенностей одновременно.

</details>

## Вопрос №100. Итог: сильные стороны опыта Greenplum
Что составляет главное преимущество опыта Greenplum при переходе в Oracle?

- A. Знание PL/SQL
- B. Знание RMAN
- C. Понимание MPP-запросов, распределения данных, hash joins и статистики
- D. Знание RAC

<details>
<summary>Ответ</summary>

**C.** Новые навыки для собеседования: читать PX-план, диагностировать TEMP spills, понимать SCN/redo и конкурентное выполнение ETL.

</details>

## Вопрос №101. Ориентир по версиям Oracle
Что из перечисленного доступно только начиная с Oracle 23ai?

- A. `SELECT` без `FROM DUAL` и тип `BOOLEAN` в SQL
- B. `FETCH FIRST ... ROWS ONLY`
- C. `GENERATED AS IDENTITY`
- D. Private Temporary Tables

<details>
<summary>Ответ</summary>

**A.** `FETCH FIRST`, `IDENTITY` и `MATCH_RECOGNIZE` появились в 12c, Private Temporary Tables в 18c. Материал ориентирован на Oracle 19c.

</details>

