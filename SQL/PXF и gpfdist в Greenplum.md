# PXF и gpfdist в Greenplum: принципы, архитектура и когда что использовать

## Коротко

**PXF** — это слой доступа Greenplum к внешним источникам данных. Он нужен, когда Greenplum должен читать или писать данные **напрямую** во внешнюю систему: Oracle, PostgreSQL, MySQL, S3, HDFS и другие. Для SQL-источников PXF обычно работает через JDBC и умеет распараллеливать чтение источника.

**gpfdist** — это отдельный файловый демон. Он не ходит в Oracle и не знает ничего о БД-источниках. Его задача — быстро и параллельно раздавать Greenplum данные из файлов или принимать данные из Greenplum в файлы через external tables.

---

## 1. Что такое PXF

PXF — это framework для federated queries и параллельного высокопроизводительного доступа Greenplum к внешним источникам через встроенные коннекторы. Важная идея в том, что внешний источник отображается в Greenplum как external table, и Greenplum может читать его без предварительной полной загрузки данных внутрь своей БД.

Для SQL-источников PXF использует JDBC-коннектор. Это значит, что Greenplum через PXF может обращаться к Oracle, MySQL, PostgreSQL и другим SQL-БД как к внешнему источнику данных. Для Oracle в документации и связанных материалах отдельно отмечена поддержка Oracle-specific parallel query execution.

### Как PXF работает на уровне архитектуры

PXF не является одним центральным прокси, через который обязательно проходит весь поток данных. Он работает как распределённый сервис рядом с Greenplum: фрагменты внешнего набора данных распределяются между сегментами Greenplum, а PXF-инстанс на segment host обслуживает работу сегментов этого хоста. В официальных материалах прямо сказано, что PXF distributes fragments among Greenplum segments, а PXF instance on a segment host spawns a thread for each segment on that host.

Из этого следует практическая модель работы:

- coordinator строит и dispatch’ит план;
    
- сегменты Greenplum получают свою часть работы;
    
- PXF на segment hosts идёт во внешний источник;
    
- данные читаются параллельно, а не “через один центральный поток”. Это вывод из архитектурного описания PXF и распределения fragments по сегментам.
    

### Параллелизм в PXF

PXF умеет распараллеливать JDBC-чтение через `PARTITION_BY`. При этом важно понимать, что `PARTITION_BY` в PXF — это не про физическое партиционирование таблицы в Oracle и не про распределение данных в Greenplum. Это подсказка PXF, что внешний набор данных можно разбить на части и читать параллельно; каждая часть читается отдельным PXF thread.

### Что умеет PXF полезного

Для JDBC-коннектора PXF поддерживает как минимум:

- column projection;
    
- filter pushdown;
    
- named queries;
    
- partitioned JDBC reads.
    

Практический смысл этого такой: если можно отфильтровать и сузить выборку на стороне Oracle, PXF может сократить объём передаваемых данных и не тащить в Greenplum всё подряд.

---

## 2. Что такое gpfdist

`gpfdist` — это parallel file distribution program. Он используется readable external tables и `gpload`, чтобы **раздавать файлы всем сегментам Greenplum параллельно**, а writable external tables используют его в обратную сторону — чтобы принимать параллельные выходные потоки от сегментов и писать их в файл.

То есть gpfdist — это не “коннектор к Oracle”, а именно **файловый сервер для external tables**. Если данные уже лежат в CSV/TXT и похожих форматах, gpfdist позволяет загрузить их в Greenplum очень быстро.

### Как gpfdist работает на уровне архитектуры

По документации Cloudberry:

- `gpfdist` запускается на хосте **не coordinator и не standby coordinator**;
    
- он отдаёт файлы из указанного каталога сегментам Greenplum;
    
- все сегменты могут читать или писать external table data параллельно.
    

Для readable external table gpfdist читает записи из файлов, упаковывает их в блоки и отдаёт сегментам по запросу. Сегменты распаковывают строки и распределяют их дальше согласно distribution policy таблицы. Для writable external table сегменты, наоборот, отправляют блоки строк в gpfdist, а он пишет их в файл.

### Что важно про размещение gpfdist

gpfdist не обязан работать именно на Oracle-сервере. Он должен работать на том хосте, где лежат выгружаемые файлы и который доступен по сети всем сегментам Greenplum. Типичный вариант — ETL/staging host. Если файлы выгружаются прямо на Oracle-сервер и этот хост доступен сегментам, gpfdist можно поднять и там, но по документации ключевое ограничение — не coordinator и не standby coordinator.

### Параллелизм в gpfdist

Cloudberry прямо пишет, что `gpfdist` — fastest way to load large fact tables, потому что он обслуживает external data files по HTTP параллельно для сегментов. Одна инстанция может обслуживать порядка 200 MB/s, а процессов `gpfdist` можно запускать много, распределяя файлы и сетевые интерфейсы.

---

## 3. Главное различие по смыслу

### PXF

Используется, когда Greenplum должен работать **с внешней системой как с системой**: БД, S3, HDFS и т.д. Это именно коннекторный слой.
### gpfdist

Используется, когда данные уже **представлены в виде файлов**, и нужно быстро и параллельно загрузить их в Greenplum или выгрузить из Greenplum. Это файловый демон, а не коннектор к БД. 

---

## 4. Что происходит при загрузке в таблицу `DISTRIBUTED BY (id)`

Это важный момент.

Ни PXF, ни gpfdist в обычной схеме не гарантируют, что “каждый сегмент сразу читает только те строки, которые потом останутся у него по `id`”.

### Для gpfdist

Документация описывает процесс так:

1. coordinator парсит `INSERT INTO target SELECT * FROM ext_table`;
    
2. план dispatch’ится на primary segments;
    
3. сегменты сами подключаются к `gpfdist` и читают данные параллельно;
    
4. сегменты парсят строки, считают hash по distribution key;
    
5. строка пересылается на destination segment.
    

Это значит, что **координатор не является data pump** для такого потока, но и сегменты не обязательно читают “свои” строки. Они могут читать любую часть потока, а потом уже отправлять строку на нужный сегмент по хэшу `id`.

### Для PXF

PXF распределяет fragments внешнего источника между сегментами, а `PARTITION_BY` нужен для параллельного чтения JDBC-источника отдельными потоками. Но документация про `PARTITION_BY` прямо подчёркивает, что это не про физическое размещение данных в удалённой БД, а про возможность параллельно обработать внешний dataset.

Из этого следует практический вывод: при `INSERT` в таблицу `DISTRIBUTED BY (id)` **PXF обычно тоже читает внешний источник параллельно “по фрагментам”, а затем Greenplum при необходимости перераспределяет строки между сегментами по хэшу `id`**. Это логический вывод из того, как PXF описывает fragments и partitioned JDBC reads; это не отдельная цитата из документации про Redistribute Motion, а вывод из архитектуры.

---

## 5. Когда использовать PXF

PXF стоит использовать, когда:

- нужен **прямой доступ** из Greenplum к Oracle или другой внешней БД;
    
- не хочется делать промежуточный staging в файлы;
    
- нужно читать только часть данных, а не всю таблицу;
    
- хочется использовать pushdown фильтров и projection;
    
- источник допускает несколько параллельных JDBC-соединений и выдержит такое чтение.
    

### Типичный сценарий для PXF

`Oracle -> PXF/JDBC -> Greenplum external table -> INSERT/SELECT`

Это хороший вариант для интеграций, federated query и аккуратной выборки данных без промежуточной выгрузки.

### Ограничения PXF

PXF упирается не только в Greenplum, но и в возможности внешнего источника: JDBC, Oracle parallel query, количество соединений, пропускная способность сети, эффективность partitioning-ключа. При плохом `PARTITION_BY` или слабом источнике масштабирование может быть хуже ожидаемого. Это практический вывод из модели fragments, JDBC partitioning и Oracle parallel query support.

---

## 6. Когда использовать gpfdist

gpfdist стоит использовать, когда:

- данные уже есть в виде файлов;
    
- нужна **максимально быстрая bulk load** больших таблиц;
    
- допустим двухшаговый pipeline: сначала выгрузить из источника в файлы, потом загрузить в Greenplum;
    
- есть возможность разложить файлы по нескольким ETL-хостам, дискам и сетевым интерфейсам.

### Типичный сценарий для gpfdist

`Oracle -> unload в CSV/TXT -> gpfdist -> external table -> INSERT INTO target`

Это уже не прямой доступ к Oracle, а staged loading через файлы. Зато именно для больших факт-таблиц документация прямо рекомендует external tables с `gpfdist` как самый быстрый путь загрузки.

### Почему gpfdist часто быстрее на очень больших объёмах

Причина в том, что:

- чтение идёт с файлов, а не через JDBC;
    
- сегменты Greenplum читают параллельно напрямую;
    
- можно запускать несколько `gpfdist` на нескольких хостах и интерфейсах;
    
- можно заранее порезать один большой файл на равные куски и убрать узкие места сети и диска.
    

---

## 7. Что лучше для большой таблицы

### Если нужен прямой путь без staging

Лучше **PXF**. Он проще по архитектуре интеграции: Greenplum читает Oracle напрямую через JDBC-коннектор PXF. Это удобно, когда нужен не полный дамп, а регулярное чтение части данных, инкременты или фильтрованные выборки.

### Если нужен максимальный throughput для bulk load

Часто лучше схема **Oracle unload -> files -> gpfdist -> Greenplum**. Для больших факт-таблиц file-based external loading через `gpfdist` обычно быстрее и стабильнее, чем тянуть гигантский объём через JDBC. Документация Cloudberry прямо выделяет `gpfdist` как fastest way to load large fact tables.

### Практический вывод

- **PXF** — когда нужен удобный и прямой доступ к Oracle.
    
- **gpfdist** — когда нужен максимально быстрый массовый перенос, и промежуточные файлы допустимы.
    

---

## 8. Простая формулировка для запоминания

**PXF** — это “Greenplum ходит во внешний источник через коннектор”.  
**gpfdist** — это “Greenplum забирает или отдаёт данные через параллельный файловый сервер”.

---

## 9. Мои практические правила выбора

1. Если источник — **Oracle/Postgres/MySQL**, и нужно читать **напрямую**, начинаю с **PXF**.
    
2. Если объём очень большой и цель — **быстрый перенос сотен гигабайт или терабайтов**, чаще смотрю в сторону **выгрузки в файлы и `gpfdist`**.
3. Если нужно уменьшить нагрузку на Oracle и избежать длинных JDBC-сессий, staged pipeline через файлы часто безопаснее. Это инженерный вывод из того, что PXF читает источник напрямую, а `gpfdist` работает уже с выгруженными файлами.
    
4. Если целевая таблица `DISTRIBUTED BY (id)`, надо помнить: **и PXF, и gpfdist обычно читают данные параллельно не по “родному” хэшу Greenplum, поэтому при вставке возможно перераспределение строк между сегментами**. Для `gpfdist` это прямо описано, для PXF это логический вывод из fragment-based чтения.
    
---

## Источники:
- Apache Airflow issue `#49646` — Worker always return Invalid auth token when setting up demo environment using docker compose. ([GitHub](https://github.com/apache/airflow/issues/49646 "Worker always return Invalid auth token when setting up demo environment using docker compose · Issue #49646 · apache/airflow · GitHub"))
    
- Airflow Configuration Reference. ([Apache Airflow](https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html "Configuration Reference — Airflow 3.1.8 Documentation"))
    
- Apache Airflow issue `#59373` — `Invalid auth token: Signature verification failed` in docker compose stack with celery worker. ([GitHub](https://github.com/apache/airflow/issues/59373 "'Invalid auth token: Signature verification failed' in docker compose stack with celery worker · Issue #59373 · apache/airflow · GitHub"))
    
- Official Airflow `docker-compose.yaml`. ([GitHub](https://github.com/apache/airflow/blob/main/airflow-core/docs/howto/docker-compose/docker-compose.yaml "airflow/airflow-core/docs/howto/docker-compose/docker-compose.yaml at main · apache/airflow · GitHub"))
    
- Upgrading to Airflow 3. ([Apache Airflow](https://airflow.apache.org/docs/apache-airflow/stable/installation/upgrading_to_airflow3.html "Upgrading to Airflow 3 — Airflow 3.1.8 Documentation"))
    
- Apache Airflow Task SDK Concepts. ([Apache Airflow](https://airflow.apache.org/docs/task-sdk/stable/concepts.html "Concepts — Apache Airflow Task SDK Documentation"))
    
- Oracle Java Tutorial — JDBC Introduction. ([Oracle Documentation](https://docs.oracle.com/javase/tutorial/jdbc/overview/index.html "Lesson: JDBC Introduction (The Java™ Tutorials > JDBC Database Access)"))
    
- Oracle Java Tutorial — Establishing a Connection with JDBC. ([Oracle Documentation](https://docs.oracle.com/javase/tutorial/jdbc/basics/connecting.html "Establishing a Connection (The Java™ Tutorials >        
    JDBC Database Access > JDBC Basics)"))
    
- Go standard package `database/sql`. ([Go Packages](https://pkg.go.dev/database/sql "sql package - database/sql - Go Packages"))
    
- Oracle — Developing Python Applications for Oracle Database. ([Oracle](https://www.oracle.com/database/technologies/appdev/python/quickstartpythononprem.html "Developing Python Applications for Oracle Database"))
    
- SQLAlchemy Unified Tutorial. ([SQLAlchemy Documentation](https://docs.sqlalchemy.org/tutorial/index.html "SQLAlchemy Unified Tutorial
    —
    SQLAlchemy 2.0 Documentation"))
    
- VMware Tanzu blog — Platform Extension Framework (PXF): Enabling Parallel Query Processing Over Heterogeneous Data Sources In Greenplum. ([VMware Blogs](https://blogs.vmware.com/tanzu/platform-extension-framework-pxf-enabling-parallel-query-processing-over-heterogeneous-data-sources-in-greenplum/ "Platform Extension Framework (PXF): Enabling Parallel Query Processing Over Heterogeneous Data Sources In Greenplum"))
    
- VMware Tanzu blog — Greenplum PXF for federated queries gets data quickly from diverse sources. ([VMware Blogs](https://blogs.vmware.com/tanzu/greenplum-pxf-for-federated-queries-gets-data-quickly-from-diverse-sources/ "VMware Tanzu Greenplum PXF for federated queries gets data quickly from diverse sources - Tanzu"))
    
- Apache Cloudberry — Load Data Using `gpfdist`. ([Apache Cloudberry](https://cloudberry.apache.org/docs/data-loading/load-data-using-gpfdist "Load Data Using gpfdist | Apache Cloudberry (Incubating)"))
    
- Apache Cloudberry — `gpfdist`. ([Apache Cloudberry](https://cloudberry.apache.org/docs/sys-utilities/gpfdist/ "gpfdist | Apache Cloudberry (Incubating)"))
    
- Apache Cloudberry — Load Data Best Practices. ([Apache Cloudberry](https://cloudberry.apache.org/docs/next/tutorials/best-practices/load-data-best-practices "Load Data | Apache Cloudberry (Incubating)"))
    
- Apache Cloudberry — About Parallel Data Loading. ([Apache Cloudberry](https://cloudberry.apache.org/docs/next/tutorials/product-principles/about-data-loading/ "About Parallel Data Loading | Apache Cloudberry (Incubating)"))
    
- Apache Cloudberry — Crash Course. ([Apache Cloudberry](https://cloudberry.apache.org/docs/next/tutorials/crash-course/ "Apache Cloudberry Crash Course | Apache Cloudberry (Incubating)"))
    
- Apache Cloudberry — `COPY`. ([Apache Cloudberry](https://cloudberry.apache.org/docs/1.x/sql-stmts/copy/ "COPY | Apache Cloudberry (Incubating)"))