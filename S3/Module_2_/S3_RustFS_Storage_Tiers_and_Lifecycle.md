---
title: "S3 и RustFS — Storage Tiers и Lifecycle Transition"
tags: [s3, rustfs, tiers, lifecycle, docker-compose, fish]
status: study
updated: 2026-10-21
---

# Storage Tiers в S3 и RustFS

> **Цель:** понять классы хранения и тиры, запустить два RustFS в одном Docker Compose и настроить автоматический перенос объекта по Lifecycle. **Среда:** Arch Linux, `fish`, Docker Compose, RustFS Console, AWS CLI. Практика начинается сразу; фактический перенос по правилу на 1 день проверяется позже.

## 1. Что такое Tier и Storage Class

**Tier (уровень хранения)** — слой системы, выбранный под частоту обращения к данным, скорость их получения и стоимость инфраструктуры. «Горячий» уровень обслуживает частые обращения; «холодный» предназначен для редко используемых данных. Холодное хранение не обязательно означает отсутствие доступа через API.

В **Amazon S3** класс хранения (`Storage Class`) — управляемая AWS характеристика объекта. Примеры:

- `STANDARD` — частые обращения, низкая задержка;
- `STANDARD_IA` — редкие обращения, доступ без предварительного восстановления, плата за извлечение;
- `INTELLIGENT_TIERING` — автоматическое распределение по уровням доступа;
- `GLACIER_IR` — архив с немедленным доступом;
- `GLACIER` (Glacier Flexible Retrieval) и `DEEP_ARCHIVE` — архивные классы, которым требуется операция восстановления перед обычным чтением.

У классов различаются тарифы, минимальные оплачиваемые сроки хранения, стоимость чтения и требования к восстановлению. **Lifecycle Transition** задаёт момент перехода между поддерживаемыми классами; **Expiration** задаёт удаление. Это разные действия.

## 2. Как устроено холодное хранение RustFS

В **RustFS** `Tiered Storage` — конфигурация удалённого *целевого хранилища* (например, второй RustFS, S3, MinIO). Источник регистрирует эту цель под именем `DEEPCOLD`. Затем Lifecycle ссылается на это имя, а не на имя AWS-класса `DEEP_ARCHIVE`.

```text
Клиент ── S3 GET/PUT ──> RustFS HOT (бакет tier-demo)
                           │
                           ├─ метаданные и исходный ключ: archive/demo.txt
                           │
                           └─ Lifecycle Transition: через 1 день
                                      │
                                      ▼
                           RustFS COLD (бакет cold-archive)
                           хранит перемещённые данные
```

- **До перехода:** данные находятся в исходном HOT.
- **После перехода:** HOT сохраняет метаданные объекта, его ключ и сведения о Tier; содержимое переносится в COLD. Клиент продолжает делать `GET` через HOT; HOT обращается к COLD, когда требуется содержимое.
- **Асинхронность:** правило, ставшее применимым, обрабатывается фоновым сканером. Ровно через 24 часа перенос не гарантирован.
- **Формат на COLD:** внутренние ключи могут не совпадать с исходными. Не редактируй и не удаляй объекты архива напрямую на COLD.

**Важное ограничение:** название `DEEPCOLD` не превращает второй RustFS в AWS Glacier Deep Archive. В нашем примере оба контейнера используют обычное локальное хранилище. Для физически более дешёвого или медленного Tier потребуются соответствующие диски/оборудование; механизм задержанного восстановления AWS Glacier здесь не воспроизводится. Остановка COLD нарушит чтение перенесённых объектов через HOT.

## 3. Практика: запусти HOT и COLD одним Docker Compose

Этот **отдельный лабораторный стек** использует порты `9200/9201` и `9300/9301`, поэтому не конфликтует с твоим RustFS на `9000/9001`. Внутри Compose имена сервисов — `rustfs-hot` и `rustfs-cold`; у них **разные тома**.

1. Создай папку проекта, войди в неё и помести туда приложенный `docker-compose.rustfs-tiers.yml`:

   ```fish
   mkdir -p ~/rustfs-tier-lab
   cd ~/rustfs-tier-lab
   # Скопируй сюда скачанный docker-compose.rustfs-tiers.yml
   ```

2. Создай уникальные учётные данные в `.env` (синтаксис **fish**):

   ```fish
   set HOT_ACCESS (openssl rand -hex 12 | string upper)
   set HOT_SECRET (openssl rand -hex 24)
   set COLD_ACCESS (openssl rand -hex 12 | string upper)
   set COLD_SECRET (openssl rand -hex 24)
   printf 'HOT_ACCESS=%s\nHOT_SECRET=%s\nCOLD_ACCESS=%s\nCOLD_SECRET=%s\n' \
     $HOT_ACCESS $HOT_SECRET $COLD_ACCESS $COLD_SECRET > .env
   chmod 600 .env
   printf '.env\n' > .gitignore
   ```

3. Проверь конфигурацию и запусти **оба** контейнера:

   ```fish
   docker compose -f docker-compose.rustfs-tiers.yml config --quiet
   docker compose -f docker-compose.rustfs-tiers.yml up -d
   docker compose -f docker-compose.rustfs-tiers.yml ps
   curl -f http://127.0.0.1:9200/health
   curl -f http://127.0.0.1:9300/health
   ```

   | Экземпляр | S3 API | Console |
   |---|---|---|
   | HOT | `http://127.0.0.1:9200` | `http://127.0.0.1:9201` |
   | COLD | `http://127.0.0.1:9300` | `http://127.0.0.1:9301` |

   В обеих Console выбери вход **Key Login** и используй соответствующие `*_ACCESS` / `*_SECRET` из `.env`. Если Console предлагает **Server Configuration**, укажи S3 API того же экземпляра из таблицы.

4. Настрой отдельные профили AWS CLI для последующих проверок (они хранят ключи в `~/.aws/credentials`):

   ```fish
   aws configure set aws_access_key_id $HOT_ACCESS --profile rustfs-hot
   aws configure set aws_secret_access_key $HOT_SECRET --profile rustfs-hot
   aws configure set region us-east-1 --profile rustfs-hot

   aws configure set aws_access_key_id $COLD_ACCESS --profile rustfs-cold
   aws configure set aws_secret_access_key $COLD_SECRET --profile rustfs-cold
   aws configure set region us-east-1 --profile rustfs-cold
   ```

   Если не хочешь хранить ключи в AWS CLI, этот пункт пропусти и проверяй объекты через Console; команды ниже потребуют профилей.

## 4. Подготовь бакеты через Console

1. Открой **COLD Console** (`:9301`) → **Buckets** → **Create Bucket** → имя `cold-archive` → **Create**. Оставь `Version` и `Object Lock` выключенными для этого опыта.
2. Открой **HOT Console** (`:9201`) → **Buckets** → **Create Bucket** → имя `tier-demo` → **Create**. Здесь тоже отключи `Version` и `Object Lock`, чтобы не смешивать обычные и noncurrent версии.
3. Проверка через `fish`:

   ```fish
   aws --profile rustfs-cold --endpoint-url http://127.0.0.1:9300 s3api head-bucket --bucket cold-archive
   aws --profile rustfs-hot --endpoint-url http://127.0.0.1:9200 s3api head-bucket --bucket tier-demo
   ```

Если UI не даёт создать бакет, выполни соответственно `aws ... s3api create-bucket --bucket cold-archive` и `aws ... s3api create-bucket --bucket tier-demo` с адресами и профилями из проверок выше.

## 5. Подключи COLD как Tier в HOT Console

Открой **HOT Console** (`:9201`) → **Tiered Storage** → **Add Tier** → провайдер **RustFS / RustFS built-in cold storage** (подпись зависит от версии Console). Заполни:

| Поле | Значение |
|---|---|
| **Name** | `DEEPCOLD` |
| **Endpoint** | `http://rustfs-cold:9000` |
| **Access Key** | значение `COLD_ACCESS` из `.env` |
| **Secret Key** | значение `COLD_SECRET` из `.env` |
| **Bucket** | `cold-archive` |
| **Prefix** | оставить пустым |
| **Region** | `us-east-1` |
| **Storage Class** (если есть) | оставить значение по умолчанию |

**Почему не `localhost:9300`?** Запрос к COLD отправляет **контейнер HOT**, а не браузер. В его Docker-сети `rustfs-cold:9000` — адрес второго сервиса; `127.0.0.1` внутри HOT обозначает сам HOT.

Нажми **Save**. При сохранении RustFS проверяет доступность COLD тестовой записью, чтением и удалением. **Tier должен появиться в списке**. Регистрация Tier сама по себе ещё не переносит файлы.

## 6. Настрой Lifecycle → Transition и загрузи объект

1. **HOT Console** → **Buckets** → `tier-demo` → **Settings** → **Lifecycle** → **Add Lifecycle Rule**.
2. Перейди на вкладку **Transition** и задай:
   - **Days:** `1` (через 1 день после создания объекта);
   - **Prefix:** `archive/`;
   - **Storage Type / Storage Class:** `DEEPCOLD` (зарегистрированный Tier);
   - **Status:** Enabled, если есть отдельный переключатель.
3. Сохрани правило; убедись, что оно отображается в списке Lifecycle. Не добавляй правило Expiration — в этом опыте **переносим, но не удаляем** данные по сроку.
4. Через HOT Console открой **Object Browser** → `tier-demo` → создай папку `archive` и загрузи `demo.txt` внутрь. Либо выполни в `fish`:

   ```fish
   printf 'RustFS hot-to-cold lifecycle test\n' > demo.txt
   aws --profile rustfs-hot --endpoint-url http://127.0.0.1:9200 \
     s3 cp demo.txt s3://tier-demo/archive/demo.txt
   ```

5. Прочитай сохранённое правило и состояние файла:

   ```fish
   aws --profile rustfs-hot --endpoint-url http://127.0.0.1:9200 \
     s3api get-bucket-lifecycle-configuration --bucket tier-demo

   aws --profile rustfs-hot --endpoint-url http://127.0.0.1:9200 \
     s3api head-object --bucket tier-demo --key archive/demo.txt
   ```

В правиле должны присутствовать `Transitions`, `Days: 1`, `StorageClass: DEEPCOLD` и фильтр `archive/`. **Сразу после загрузки StorageClass не обязан быть DEEPCOLD:** объект ещё не достиг возраста 1 день. Контрольное чтение конфигурации доказывает только настройку правила, а не факт переноса.

## 7. Проверь фактический перенос (после 1 дня + фоновой обработки)

Проверяй **не по времени на часах**, а по двум независимым признакам:

1. На HOT выполнено:

   ```fish
   aws --profile rustfs-hot --endpoint-url http://127.0.0.1:9200 \
     s3api head-object --bucket tier-demo --key archive/demo.txt
   ```

   При успешном переходе поле `StorageClass` станет `DEEPCOLD`.

2. На COLD появились архивные данные:

   ```fish
   aws --profile rustfs-cold --endpoint-url http://127.0.0.1:9300 \
     s3api list-objects-v2 --bucket cold-archive --query 'Contents[].Key'
   ```

   **Не ожидай ключ `archive/demo.txt`:** RustFS использует собственные внутренние ключи архива.

3. Прочитай **через HOT**, не через COLD:

   ```fish
   aws --profile rustfs-hot --endpoint-url http://127.0.0.1:9200 \
     s3 cp s3://tier-demo/archive/demo.txt downloaded.txt
   sha256sum demo.txt downloaded.txt
   ```

   Совпадающие SHA-256 подтверждают, что клиент получил исходное содержимое через HOT после перехода. Если спустя день `StorageClass` остался прежним — переход ещё не подтверждён; смотри логи и ошибки ниже.

## 8. Ограничения, диагностика и источники

- **Это две независимые инсталляции, а не репликация.** HOT хранит сведения о перенесённом объекте; COLD хранит его данные. Потеря исходных метаданных или целевого архива нарушит доступ. Бэкап и репликация — другие задачи.
- **`DEEPCOLD` — логическое имя Tier, а не физический класс диска.** На одной машине с одинаковыми томами нет экономии на классе хранения или защиты от отказа хоста. Для реального холодного Tier нужен отдельный носитель / сервер / провайдер и соответствующая политика доступа.
- **Не путай Transition с Expiration:** первое перемещает содержимое; второе удаляет объект согласно срокам и версиям. Для включённого Versioning отдельно существуют действия над noncurrent-версиями.
- **Перенос фоновой:** проверь, что у объекта возраст более 1 дня; проверь правило и зарегистрированный Tier; затем журналы: `docker compose -f docker-compose.rustfs-tiers.yml logs --tail=100 rustfs-hot`.
- **Сбой регистрации Tier:** проверь `http://rustfs-cold:9000` (именно в поле HOT), ключи COLD, наличие бакета `cold-archive`, права `Put/Get/List/Delete`, а также сетевую доступность сервиса.
- **Отказ по диску/правам:** в логах RustFS ищи `permission denied`; официальный контейнер использует UID/GID `10001`. В этом примере используются Docker *named volumes* вместо bind-mount путей.
- **Остановка без удаления данных:** `docker compose -f docker-compose.rustfs-tiers.yml down`. **Не используй `down -v`**, если хочешь сохранить бакеты и данные. Не удаляй COLD или сам Tier, пока там есть перенесённые объекты.

**Самопроверка:** почему S3 `DEEP_ARCHIVE` и RustFS `DEEPCOLD` не одно и то же? Почему `GET` после перехода идёт через HOT? Почему успешный `PUT LifecycleConfiguration` не доказывает, что файл уже перемещён?

**Источники (проверено 21.10.2026):**

- [RustFS — Tiered Storage](https://docs.rustfs.com/en/administration/data/tiered-storage)
- [RustFS — Lifecycle Management](https://docs.rustfs.com/en/administration/data/lifecycle-management)
- [RustFS — Docker](https://docs.rustfs.com/en/installation/container/docker)
- [AWS — Storage Classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)
- [AWS — S3 Lifecycle Transitions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)
