---
tags: [greenplum, pxf, etl, mpp]
aliases: [Platform Extension Framework]
---

[[pxf_ingestion_visual_lab.html]]

# PXF — параллельный доступ к внешним данным

> [!summary] Суть
> **PXF (Platform Extension Framework)** — расширение Greenplum для параллельного чтения и записи во внешние системы (S3/MinIO, HDFS, Hive, JDBC и др.). **Coordinator управляет SQL, но полный поток входных данных не проходит через него.**

**PXF в Greenplum: коротко**

- **Два разных процесса.** Чтение из источника (PXF) и распределение по хэшу ключа (Redistribute Motion перед Insert) не связаны. PXF не кладёт строку сразу на «нужный» сегмент.
- **Один PXF JVM на хост.** Он обслуживает все сегменты хоста: поток на сегмент (и на слайс) на запрос. Лимит потоков `pxf.max.threads` (по умолчанию 200), больше сегментов означает больше потоков и нагрузки на heap.
- **Fragmenter** (в PXF Server) формирует список фрагментов по метаданным источника. Число фрагментов определяет источник (сплиты HDFS, партиции JDBC), а не число сегментов.
- **Fragmentation call:** каждый сегмент вызывает локальный PXF. Первый поток на хосте выполняет Fragmenter, остальные берут результат из кэша (ключ: сервер, транзакция, путь, предикаты; живёт 10 секунд). То есть фрагментация идёт один раз на хост на запрос.
- **Выбор своих фрагментов** делает сегмент: список фрагментов делится по модулю (знает число сегментов и свой id). Точная формула в источниках не подтверждена.
- **Bridge call:** по одному вызову на фрагмент, отдельный поток PXF. Здесь работают Accessor (чтение из источника) и Resolver (перевод в типы GP).
- **Практика:** фрагментов должно быть заметно больше сегментов и примерно равного размера, иначе перекос или простой сегментов.

# PXF — Fragmentation и Dataflow

- **Когда:** во время `External Scan`, после распределения SQL-плана по сегментам.
    
- **Кто:** каждый участвующий GP Primary отправляет `fragmentation call` локальному PXF Server.
    
- **Fragmenter:** Java-класс внутри PXF, который формирует общий список логических фрагментов по метаданным источника. Физические данные не разбивает.
    
- **Кэш:** локальный для каждой JVM. При совпадении ключа первый поток выполняет Fragmenter, остальные используют результат. TTL по умолчанию — 10 секунд.
    
- **Распределение:** каждый GP Segment самостоятельно выбирает свои фрагменты с помощью modulo-based hashing.
    
- **Bridge Call:** сегмент запрашивает назначенные фрагменты. Accessor читает записи, Resolver преобразует их для Greenplum.
    
- **INSERT:** Greenplum отдельно распределяет полученные строки по ключу `DISTRIBUTED BY`, при необходимости через `Redistribute Motion`.
    
- **Mirror:** получает изменения от соответствующего Primary, не читая данные через PXF.
    

**Пример:** 2 хоста × 2 Primary = 4 fragmentation calls, но 2 выполнения Fragmenter при успешном использовании локальных кэшей.

**Источник:** [PXF: Enabling Parallel Query Processing](https://blogs.vmware.com/tanzu/wp-content/uploads/sites/154/2025/04/pxf-paper.pdf), разделы 4.1 и 5.6.

Разберём на твоём кластере: 4 Primary Segment на двух физических хостах.

Предположим, Fragmenter нашёл 8 фрагментов данных в S3:

`F0, F1, F2, F3, F4, F5, F6, F7`.

Каждый участвующий Primary получает полный список, но самостоятельно выбирает только те фрагменты, которые ему назначены.

## 1. Упрощённый алгоритм

Формула:

\[ \text{segment\_id} = I \bmod N \]

Где:

- \(I\) — индекс фрагмента, начиная с нуля.
    
- \(N\) — число участвующих сегментов, в нашем случае 4.
    
- `mod` — остаток от деления.
    

Например:

|Фрагмент|Расчёт|Назначенный сегмент|
|---|---|---|
|F0|0 % 4 = 0|Segment 0|
|F1|1 % 4 = 1|Segment 1|
|F2|2 % 4 = 2|Segment 2|
|F3|3 % 4 = 3|Segment 3|
|F4|4 % 4 = 0|Segment 0|
|F5|5 % 4 = 1|Segment 1|
|F6|6 % 4 = 2|Segment 2|
|F7|7 % 4 = 3|Segment 3|

Fragmenter → F0, F1, F2, F3, F4, F5, F6, F7

Одинаковый упорядоченный список на каждом сегменте

Host 1

Primary 0

F0

F4

Primary 1

F1

F5

Host 2

Primary 2

F2

F6

Primary 3

F3

F7

Результат: каждый Primary читает по два фрагмента. Никакого центрального диспетчера, который вручную назначает фрагменты сегментам, не требуется.

## 2. Реальная формула в исходном коде Greenplum

В опубликованной реализации `pxf_fragment.c` используется дополнительное смещение:

\[ S=(I+(session\_id\bmod N)+command\_count)\bmod N \]

Где:

- `session_id` — идентификатор сессии Greenplum.
    
- `command_count` — счётчик команд.
    
- `S` — сегмент, которому назначается фрагмент.
    

Например, при `session_id = 13`, `command_count = 2` и четырёх сегментах:

\[ S=(I+3)\bmod4 \]

Тогда распределение изменится:

|Segment|Фрагменты|
|---|---|
|0|F1, F5|
|1|F2, F6|
|2|F3, F7|
|3|F0, F4|

Зачем добавляется смещение? Чтобы при повторных запросах небольшие наборы фрагментов не назначались постоянно одним и тем же сегментам.

Это не случайное назначение: все сегменты одного запроса используют одинаковые исходные значения и получают согласованный результат.

Формула подтверждается исходным кодом функции `FilterFragmentsForSegment()` в `pxf_fragment.c`.

![](https://www.google.com/s2/favicons?domain=https://www.seaxiang.com&sz=32)

seaxiang.com

## 3. Что происходит после назначения

Например, `Primary 0` получил `F1` и `F5`.

1. `Primary 0` оставляет в своём списке только F1 и F5.
    
2. Отправляет PXF Server `bridge call` для F1.
    
3. PXF через Accessor считывает F1 и возвращает записи сегменту.
    
4. Сегмент выполняет `bridge call` для F5.
    
5. После чтения строки могут быть перераспределены через `Redistribute Motion` перед вставкой в целевую таблицу.
    

Важно: формула использует индекс фрагмента, а не значение `customer_id`, содержимое файла или ключ `DISTRIBUTED BY`.

В современных версиях PXF JDBC существуют дополнительные политики распределения фрагментов: `ROUND-ROBIN`, `ACTIVE-SEGMENT`, `IMPROVED-ROUND-ROBIN` и `RANDOM`. Поэтому точное правило для установленной версии и профиля следует проверять отдельно.

![](https://www.google.com/s2/favicons?domain=https://greengagedb.org&sz=32)

Greengage DB Docs

Главный вывод: каждый GP Segment получает список фрагментов, применяет одинаковую детерминированную формулу и оставляет свои элементы. После этого он самостоятельно инициирует чтение назначенных фрагментов через PXF.
## Архитектура

- **Greenplum**: Coordinator планирует запрос; **Primary-сегменты** исполняют план и хранят данные; **Mirror** поддерживает резервную копию своего Primary.
- **PXF Extension**: нативный обработчик протокола `pxf://` в Greenplum.
- **PXF Server**: отдельный **Java/JVM-сервис**, типично один на *физическом сегментном хосте*, даже если на нём несколько сегментов. При иной топологии размещение сервиса настраивается.
- **`PROFILE`** выбирает классы обработки; **`SERVER`** выбирает именованную конфигурацию доступа к источнику (это **не** отдельный Java-процесс).

| Компонент | Функция |
|---|---|
| **Fragmenter** | Определяет независимые части исходного набора (файлы, splits, диапазоны JDBC). |
| **Accessor** | Читает/записывает данные конкретной части через API источника. |
| **Resolver** | Преобразует внешние записи в поля Greenplum и обратно. |
| **Profile** | Связывает реализации компонентов для формата/источника. |

## Dataflow: загрузка в обычную таблицу GP

```mermaid
flowchart TD
  A[Источник: S3 / HDFS / JDBC] --> B[PXF: Fragmenter определяет фрагменты]
  B --> C[Участвующие Primary: назначение фрагментов]
  C --> D[Локальный PXF: Accessor + Resolver]
  A --> D
  D --> E[External Scan: строки на читающих Primary]
  E --> F{Совпадает распределение с целью?}
  F -->|нет| G[Redistribute Motion по ключу цели]
  F -->|да| H[INSERT на целевых Primary]
  G --> H
  H --> I[Репликация Primary → Mirror]
```

1. Клиент выполняет `INSERT INTO target SELECT ... FROM ext_source` через **Coordinator**.
2. **Fragmenter** формирует описания частей **независимо от ключа распределения целевой таблицы**.
3. Участвующие Primary вызывают PXF; **Accessor** получает данные; **Resolver** представляет их в формате полей Greenplum.
4. Строки поступают в `External Scan` сегментов **потоково**; весь источник не накапливается в RAM.
5. **Greenplum**, а не PXF, определяет целевой Primary по `DISTRIBUTED BY`; если нужно, выполняет **Redistribute Motion** (проверяется через `EXPLAIN`).
6. Primary физически вставляет строки, Mirror получает изменения посредством репликации Greenplum; **PXF не пишет напрямую в Mirror**.

> [!important] Два независимых распределения
> **Фрагмент PXF → кто читает данные.** `DISTRIBUTED BY` → **где строка будет храниться**. Это разные решения; `Redistribute Motion` не требует предварительно выгружать весь источник в память.

## Пример SQL: S3 → Greenplum

```sql
-- На выбранной БД, после установки PXF администраторами:
CREATE EXTENSION IF NOT EXISTS pxf;

CREATE EXTERNAL TABLE ext_orders (
    order_id BIGINT,
    customer_id BIGINT,
    amount NUMERIC(12,2)
)
LOCATION ('pxf://bucket/orders/?PROFILE=s3:csv&SERVER=s3_prod&SKIP_HEADER_COUNT=1')
FORMAT 'CSV';

CREATE TABLE orders (
    order_id BIGINT,
    customer_id BIGINT,
    amount NUMERIC(12,2)
) DISTRIBUTED BY (customer_id);

EXPLAIN INSERT INTO orders SELECT * FROM ext_orders;
INSERT INTO orders SELECT * FROM ext_orders;
ANALYZE orders;
```

`SERVER=s3_prod` требует предварительно настроенного каталога `$PXF_BASE/servers/s3_prod/`. Параметры URI и формат зависят от PXF-профиля.

## Минимальный CLI / диагностика

```bash
pxf version               # установленная версия
pxf status                # состояние сервиса на текущем хосте
pxf cluster status        # состояние сервисов в кластере
pxf cluster sync          # распространить конфигурацию с Coordinator
pxf cluster restart       # перезапустить после изменений конфигурации
# pxf cluster start / stop — управление сервисами кластера
```

```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'pxf';
EXPLAIN (COSTS OFF) INSERT INTO orders SELECT * FROM ext_orders;
SELECT gp_segment_id, COUNT(*) FROM orders GROUP BY 1 ORDER BY 1;
```

- **Конфигурация**: `$PXF_BASE/conf/`, `$PXF_BASE/servers/<name>/`; журналы — в каталоге логов PXF.
- **Ограничители**: сеть до источника, CPU/RAM JVM, число и размер фрагментов, мощность внешней БД, операции Motion.
- **`DROP EXTERNAL TABLE`** удаляет метаданные внешней таблицы, но **не файлы S3/HDFS**.
- **Версионность**: приведён современный CLI для PXF 6.x; у старых поставок другие переменные окружения (`PXF_CONF`) и команды первичной инициализации. Проверять `pxf help` и версию сервиса.

## Источники
- [EDB: PXF CLI](https://www.enterprisedb.com/docs/pxf/latest/reference/commands/)
- [Документация PXF: профили и архитектура](https://www.enterprisedb.com/docs/pxf/latest/)
- Связанное: [[gpfdist_Greenplum|gpfdist — параллельный файловый сервер]]
