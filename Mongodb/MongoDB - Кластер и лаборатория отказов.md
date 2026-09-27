---
tags: [mongodb, nosql, sharding, replication, docker, python, chaos-testing, practice]
created: 2026-09-27
---
# MongoDB: self-bootstrapping кластер + лаборатория отказов на Python

Связанные заметки: [[MongoDB - Архитектура и CRUD]]

Первая часть этой заметка описывает локальный MongoDB 8 sharded cluster, который полностью разворачивается одной командой `docker compose up -d`. 

Compose автоматически подготавливает keyfile, запускает config server replica set, два shard replica set, инициирует все три replica set, запускает два `mongos`, добавляет shard'ы в кластер и создаёт администратора.

Вторая часть заметки — Python-проект `mongo_lab`, который:

1. проверяет, что кластер реально работает (индексы, CRUD, шардирование, распределение по шардам);
2. затем **сам** роняет разные части кластера через `docker compose stop` и смотрит, что происходит с выборами primary, доступностью на запись/чтение и маршрутизацией через `mongos`.

---

## Архитектура кластера

```text
                           Python / mongosh / Compass
                                      |
                    +-----------------+-----------------+
                    |                                   |
           localhost:27017                     localhost:27018
                    |                                   |
                 mongos1                             mongos2
                    |                                   |
                    +-----------------+-----------------+
                                      |
                                  configrs
                        +-------------+-------------+
                        |             |             |
                  configsvr1    configsvr2    configsvr3
                  PRIMARY/SEC   PRIMARY/SEC   PRIMARY/SEC
                                      |
                      +---------------+---------------+
                      |                               |
                   shard1rs                        shard2rs
             +---------+---------+          +---------+---------+
             |         |         |          |         |         |
          shard1a   shard1b   shard1c    shard2a   shard2b   shard2c
          P / S     P / S     P / S      P / S     P / S     P / S
```

Целевая архиткетура выглядит как показано на схеме выше и разделяет 4 уровня:

1. **`mongos1`** и **`mongos2`** — точки входа для приложения и query router.
2. **`configrs`** — replica set, хранящий метаданные sharded cluster.
3. **`shard1rs` и `shard2rs`** — два shard'а, между которыми MongoDB распределяет пользовательские данные.
4. **Replica set внутри каждого shard** — три копии данных для отказоустойчивости.

Однако помимо контейнеров данных компонент **`docker compose`** также создает дополнительные контейнеры необходимые для конфигурации кластера.

> [!Important] ВАЖНО
Выполнить данные команды в директории рядом с **`docker-compose.yaml`**. Требуется для поднятия кластера MongoDB.
>```bash
>mkdir -p secrets 
>openssl rand -base64 756 > secrets/mongo-keyfile
>```


---

# Часть 1 Docker compose

В Compose определено 16 сервисов.

## 1.1 Постоянно работающие контейнеры — 11

| Группа | Контейнеры | Количество | Назначение |
|---|---|---:|---|
| Config Server | `configsvr1`, `configsvr2`, `configsvr3` | 3 | Метаданные кластера |
| Shard 1 | `shard1a`, `shard1b`, `shard1c` | 3 | Первая часть пользовательских данных |
| Shard 2 | `shard2a`, `shard2b`, `shard2c` | 3 | Вторая часть пользовательских данных |
| Routers | `mongos1`, `mongos2` | 2 | Точка входа и маршрутизация запросов |

Итого:  **`11`** постоянно работющих процессов MongoDB

Из них: **`9`** - mongod и  **`2`** - mongos

---
## 1.2 Одноразовые init-контейнеры — 5

| Контейнер       | Задача                                   | Нормальное финальное состояние |
| --------------- | ---------------------------------------- | ------------------------------ |
| `keyfile-init`  | Подготавливает keyfile                   | `Exited (0)`                   |
| `init-configrs` | Выполняет `rs.initiate()` для `configrs` | `Exited (0)`                   |
| `init-shard1`   | Выполняет `rs.initiate()` для `shard1rs` | `Exited (0)`                   |
| `init-shard2`   | Выполняет `rs.initiate()` для `shard2rs` | `Exited (0)`                   |
| `init-cluster`  | Делает `addShard` и создаёт `admin`      | `Exited (0)`                   |

`Exited (0)` здесь означает контейнер выполнил одноразовую задачу успешно и завершился.

---
##  1.3 Как Compose исполняется во времени

Весь файл удобно воспринимать не только как декларацию контейнеров, но и как программу запуска:

```text
docker compose up -d
        |
        v
keyfile-init
        |
        | exit 0
        v
+-------------------- 9 mongod ----------------------+
| configsvr1 configsvr2 configsvr3                   |
| shard1a shard1b shard1c                            |
| shard2a shard2b shard2c                            |
+----------------------------------------------------+
        |
        | healthcheck -> healthy
        v
+---------------- bootstrap replica sets ------------+
| init-configrs -> rs.initiate(configrs)              |
| init-shard1   -> rs.initiate(shard1rs)              |
| init-shard2   -> rs.initiate(shard2rs)              |
+----------------------------------------------------+
        |
        | дождаться появления PRIMARY
        v
      mongos1
        |
        | healthy
        v
      mongos2
        |
        | healthy
        v
    init-cluster
        |
        +-> addShard(shard1rs)
        +-> addShard(shard2rs)
        +-> createUser(admin)
        |
        v
      ГОТОВО
```

Именно `depends_on` с условиями `service_healthy` и `service_completed_successfully` превращает набор контейнеров в последовательный bootstrap.

---

## 1.4 `docker-compose.yaml` без изменений

```yaml
# docker-compose.yml

x-mongod-common: &mongod-common
  image: mongo:8
  restart: unless-stopped
  networks: [mongo-cluster]
  depends_on:
    keyfile-init:
      condition: service_completed_successfully


services:

  # ============================================================
  # KEYFILE
  # ============================================================

  keyfile-init:
    image: mongo:8
    user: root

    entrypoint:
      - /bin/sh
      - -ec
      - |
        cp /keyfile-src/mongo-keyfile /keyfile/mongo-keyfile

        chown "$(id -u mongodb):$(id -g mongodb)" \
          /keyfile/mongo-keyfile

        chmod 0400 /keyfile/mongo-keyfile

        test -s /keyfile/mongo-keyfile

        echo "keyfile ready"

    volumes:
      - ./secrets/mongo-keyfile:/keyfile-src/mongo-keyfile:ro
      - mongo_keyfile:/keyfile

    restart: "no"


  # ============================================================
  # CONFIG SERVER REPLICA SET
  # ============================================================

  configsvr1:
    <<: *mongod-common

    command:
      mongod
      --configsvr
      --replSet configrs
      --port 27019
      --bind_ip_all
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro
      - configsvr1_data:/data/configdb

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27019",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s


  configsvr2:
    <<: *mongod-common

    command:
      mongod
      --configsvr
      --replSet configrs
      --port 27019
      --bind_ip_all
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro
      - configsvr2_data:/data/configdb

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27019",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s


  configsvr3:
    <<: *mongod-common

    command:
      mongod
      --configsvr
      --replSet configrs
      --port 27019
      --bind_ip_all
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro
      - configsvr3_data:/data/configdb

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27019",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s


  # ============================================================
  # CONFIG RS BOOTSTRAP
  #
  # Делит network namespace с configsvr1.
  # Поэтому 127.0.0.1:27019 == configsvr1:27019
  # ============================================================

  init-configrs:
    image: mongo:8

    network_mode: "service:configsvr1"

    depends_on:
      configsvr1:
        condition: service_healthy
      configsvr2:
        condition: service_healthy
      configsvr3:
        condition: service_healthy

    volumes:
      - bootstrap_state:/bootstrap

    entrypoint:
      - /bin/sh
      - -ec
      - |
        if [ -f /bootstrap/configrs.done ]; then
          echo "configrs already initialized"
          exit 0
        fi

        echo "Initializing configrs..."

        mongosh \
          --quiet \
          --host 127.0.0.1 \
          --port 27019 \
          --eval '
            try {
              rs.status();
              print("configrs already exists");
            } catch (e) {
              if (e.codeName !== "NotYetInitialized") {
                throw e;
              }

              printjson(
                rs.initiate({
                  _id: "configrs",
                  configsvr: true,
                  members: [
                    {
                      _id: 0,
                      host: "configsvr1:27019"
                    },
                    {
                      _id: 1,
                      host: "configsvr2:27019"
                    },
                    {
                      _id: 2,
                      host: "configsvr3:27019"
                    }
                  ]
                })
              );
            }

            while (true) {
              try {
                const s = rs.status();

                if (
                  s.members &&
                  s.members.some(
                    m => m.stateStr === "PRIMARY"
                  )
                ) {
                  print("configrs PRIMARY ready");
                  break;
                }
              } catch (e) {}

              sleep(1000);
            }
          '

        touch /bootstrap/configrs.done

        echo "configrs initialized"

    restart: "no"


  # ============================================================
  # SHARD 1
  # ============================================================

  shard1a:
    <<: *mongod-common

    command:
      mongod
      --shardsvr
      --replSet shard1rs
      --port 27018
      --bind_ip_all
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro
      - shard1a_data:/data/db

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27018",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s


  shard1b:
    <<: *mongod-common

    command:
      mongod
      --shardsvr
      --replSet shard1rs
      --port 27018
      --bind_ip_all
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro
      - shard1b_data:/data/db

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27018",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s


  shard1c:
    <<: *mongod-common

    command:
      mongod
      --shardsvr
      --replSet shard1rs
      --port 27018
      --bind_ip_all
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro
      - shard1c_data:/data/db

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27018",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s


  init-shard1:
    image: mongo:8

    network_mode: "service:shard1a"

    depends_on:
      shard1a:
        condition: service_healthy
      shard1b:
        condition: service_healthy
      shard1c:
        condition: service_healthy

    volumes:
      - bootstrap_state:/bootstrap

    entrypoint:
      - /bin/sh
      - -ec
      - |
        if [ -f /bootstrap/shard1rs.done ]; then
          echo "shard1rs already initialized"
          exit 0
        fi

        echo "Initializing shard1rs..."

        mongosh \
          --quiet \
          --host 127.0.0.1 \
          --port 27018 \
          --eval '
            try {
              rs.status();
              print("shard1rs already exists");
            } catch (e) {
              if (e.codeName !== "NotYetInitialized") {
                throw e;
              }

              printjson(
                rs.initiate({
                  _id: "shard1rs",
                  members: [
                    {
                      _id: 0,
                      host: "shard1a:27018"
                    },
                    {
                      _id: 1,
                      host: "shard1b:27018"
                    },
                    {
                      _id: 2,
                      host: "shard1c:27018"
                    }
                  ]
                })
              );
            }

            while (true) {
              try {
                const s = rs.status();

                if (
                  s.members &&
                  s.members.some(
                    m => m.stateStr === "PRIMARY"
                  )
                ) {
                  print("shard1rs PRIMARY ready");
                  break;
                }
              } catch (e) {}

              sleep(1000);
            }
          '

        touch /bootstrap/shard1rs.done

        echo "shard1rs initialized"

    restart: "no"


  # ============================================================
  # SHARD 2
  # ============================================================

  shard2a:
    <<: *mongod-common

    command:
      mongod
      --shardsvr
      --replSet shard2rs
      --port 27018
      --bind_ip_all
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro
      - shard2a_data:/data/db

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27018",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s


  shard2b:
    <<: *mongod-common

    command:
      mongod
      --shardsvr
      --replSet shard2rs
      --port 27018
      --bind_ip_all
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro
      - shard2b_data:/data/db

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27018",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s


  shard2c:
    <<: *mongod-common

    command:
      mongod
      --shardsvr
      --replSet shard2rs
      --port 27018
      --bind_ip_all
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro
      - shard2c_data:/data/db

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27018",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s


  init-shard2:
    image: mongo:8

    network_mode: "service:shard2a"

    depends_on:
      shard2a:
        condition: service_healthy
      shard2b:
        condition: service_healthy
      shard2c:
        condition: service_healthy

    volumes:
      - bootstrap_state:/bootstrap

    entrypoint:
      - /bin/sh
      - -ec
      - |
        if [ -f /bootstrap/shard2rs.done ]; then
          echo "shard2rs already initialized"
          exit 0
        fi

        echo "Initializing shard2rs..."

        mongosh \
          --quiet \
          --host 127.0.0.1 \
          --port 27018 \
          --eval '
            try {
              rs.status();
              print("shard2rs already exists");
            } catch (e) {
              if (e.codeName !== "NotYetInitialized") {
                throw e;
              }

              printjson(
                rs.initiate({
                  _id: "shard2rs",
                  members: [
                    {
                      _id: 0,
                      host: "shard2a:27018"
                    },
                    {
                      _id: 1,
                      host: "shard2b:27018"
                    },
                    {
                      _id: 2,
                      host: "shard2c:27018"
                    }
                  ]
                })
              );
            }

            while (true) {
              try {
                const s = rs.status();

                if (
                  s.members &&
                  s.members.some(
                    m => m.stateStr === "PRIMARY"
                  )
                ) {
                  print("shard2rs PRIMARY ready");
                  break;
                }
              } catch (e) {}

              sleep(1000);
            }
          '

        touch /bootstrap/shard2rs.done

        echo "shard2rs initialized"

    restart: "no"


  # ============================================================
  # MONGOS 1
  # ============================================================

  mongos1:
    image: mongo:8

    restart: unless-stopped

    networks:
      - mongo-cluster

    command:
      mongos
      --configdb configrs/configsvr1:27019,configsvr2:27019,configsvr3:27019
      --bind_ip_all
      --port 27017
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro

    ports:
      - "127.0.0.1:27017:27017"

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27017",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s

    depends_on:
      init-configrs:
        condition: service_completed_successfully

      init-shard1:
        condition: service_completed_successfully

      init-shard2:
        condition: service_completed_successfully


  # ============================================================
  # MONGOS 2
  # ============================================================

  mongos2:
    image: mongo:8

    restart: unless-stopped

    networks:
      - mongo-cluster

    command:
      mongos
      --configdb configrs/configsvr1:27019,configsvr2:27019,configsvr3:27019
      --bind_ip_all
      --port 27017
      --keyFile /etc/mongo-keyfile-dir/mongo-keyfile

    volumes:
      - mongo_keyfile:/etc/mongo-keyfile-dir:ro

    ports:
      - "127.0.0.1:27018:27017"

    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--quiet",
          "--host", "127.0.0.1",
          "--port", "27017",
          "--eval", "db.adminCommand({ping:1}).ok"
        ]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s

    depends_on:
      mongos1:
        condition: service_healthy


  # ============================================================
  # FINAL CLUSTER INITIALIZATION
  #
  # addShard + создание admin
  # ============================================================

  init-cluster:
    image: mongo:8

    network_mode: "service:mongos1"

    environment:
      MONGO_ADMIN_USER: ${MONGO_ADMIN_USER:-admin}
      MONGO_ADMIN_PASSWORD: ${MONGO_ADMIN_PASSWORD:-admin}

    volumes:
      - bootstrap_state:/bootstrap

    depends_on:
      mongos1:
        condition: service_healthy

      mongos2:
        condition: service_healthy

    entrypoint:
      - /bin/sh
      - -ec
      - |
        if [ -f /bootstrap/cluster.done ]; then
          echo "cluster already initialized"
          exit 0
        fi

        echo "Adding shard1..."

        mongosh \
          --quiet \
          --host 127.0.0.1 \
          --port 27017 \
          --eval '
            const result = db.adminCommand({
              addShard:
                "shard1rs/shard1a:27018,shard1b:27018,shard1c:27018",
              name: "shard1"
            });

            printjson(result);

            if (!result.ok) {
              quit(1);
            }
          '

        echo "Adding shard2..."

        mongosh \
          --quiet \
          --host 127.0.0.1 \
          --port 27017 \
          --eval '
            const result = db.adminCommand({
              addShard:
                "shard2rs/shard2a:27018,shard2b:27018,shard2c:27018",
              name: "shard2"
            });

            printjson(result);

            if (!result.ok) {
              quit(1);
            }
          '

        echo "Creating cluster administrator..."

        mongosh \
          --quiet \
          --host 127.0.0.1 \
          --port 27017 \
          --eval '
            const admin = db.getSiblingDB("admin");

            admin.createUser({
              user: process.env.MONGO_ADMIN_USER,
              pwd: process.env.MONGO_ADMIN_PASSWORD,
              roles: [
                {
                  role: "root",
                  db: "admin"
                }
              ]
            });

            print("admin user created");
          '

        touch /bootstrap/cluster.done

        echo "MongoDB cluster initialized successfully"

    restart: "no"


# ============================================================
# NETWORK
# ============================================================

networks:
  mongo-cluster:
    driver: bridge


# ============================================================
# VOLUMES
# ============================================================

volumes:

  mongo_keyfile:

  bootstrap_state:

  configsvr1_data:
  configsvr2_data:
  configsvr3_data:

  shard1a_data:
  shard1b_data:
  shard1c_data:

  shard2a_data:
  shard2b_data:
  shard2c_data:
```

---

## 1.5 Построчный разбор `docker-compose.yaml`

### 1.5.1 Общий якорь `x-mongod-common`

```yaml
x-mongod-common: &mongod-common
  image: mongo:8
  restart: unless-stopped
  networks: [mongo-cluster]
  depends_on:
    keyfile-init:
      condition: service_completed_successfully
```

- `x-mongod-common` — это YAML-расширение (`x-` — соглашение Compose Specification для "не сервисов", которые можно переиспользовать через `&якорь`/`<<: *якорь`). Сюда вынесено то, что одинаково для всех 9 `mongod`: образ, политика перезапуска, сеть и зависимость от готового keyfile.

- `restart: unless-stopped` — если процесс внутри контейнера упадёт (или Docker демон перезапустится), контейнер поднимется сам; но если вы намеренно остановили его (`docker compose stop`), докер не будет пытаться его поднять, пока вы явно не сделаете `start` — это именно то поведение, которое нужно и для прода, и для наших экспериментов с "уронить и посмотреть".

- `depends_on: keyfile-init: condition: service_completed_successfully` — Compose не просто "запусти после", а "дождись КОДА ВЫХОДА 0" у одноразового контейнера. Пока keyfile не готов — ни один `mongod` не стартует.

### 1.5.2 `keyfile-init`

```yaml
keyfile-init:
  image: mongo:8
  user: root
  entrypoint:
    - /bin/sh
    - -ec
    - |
      cp /keyfile-src/mongo-keyfile /keyfile/mongo-keyfile
      chown "$(id -u mongodb):$(id -g mongodb)" /keyfile/mongo-keyfile
      chmod 0400 /keyfile/mongo-keyfile
      test -s /keyfile/mongo-keyfile
      echo "keyfile ready"
  volumes:
    - ./secrets/mongo-keyfile:/keyfile-src/mongo-keyfile:ro
    - mongo_keyfile:/keyfile
  restart: "no"
```

- `user: root` — обязательно, иначе `chown` на что угодно, кроме собственных файлов, не сработает.

- `entrypoint: [/bin/sh, -ec, "..."]` — `-e` останавливает скрипт на первой же ошибке, `-c` говорит прочитать команду из следующего аргумента; сама команда — многострочный YAML `|` (literal block scalar), то есть переносы строк внутри сохраняются буквально, и это ровно тот shell-скрипт, что выполнится.

- `id -u mongodb` / `id -g mongodb` — узнаём UID/GID пользователя `mongodb` **внутри самого образа**, а не подставляем число `999` руками (как было в предыдущей версии этой заметки) — так надёжнее, если Docker Hub когда-нибудь поменяет UID в образе.

- `test -s /keyfile/mongo-keyfile` — проверка "файл существует и не пустой"; если `cp` по какой-то причине скопировал 0 байт, скрипт упадёт на этой строке (из-за `-e`) и весь `keyfile-init` завершится с ошибкой, а значит ни один `mongod` не стартует — fail-fast вместо тихого запуска с битым ключом.

- Оба volume-маунта решают ровно ту проблему, которую решала предыдущая версия заметки: `chown`/`chmod`, сделанные **на хосте**, не гарантированно переживают bind-mount (особенно на Docker Desktop). Здесь права выставляются **внутри** контейнера, в volume `mongo_keyfile`, которым потом ro-делятся все остальные сервисы — это надёжно на любой ОС хоста.

- `restart: "no"` — одноразовые job-контейнеры не должны перезапускаться сами; они либо выполнили задачу (exit 0) и остаются в статусе `Exited (0)`, либо упали, и это будет явно видно в `docker compose ps`.

### 1.5.3 Config server (`configsvr1/2/3`)

```yaml
configsvr1:
  <<: *mongod-common
  command:
    mongod
    --configsvr
    --replSet configrs
    --port 27019
    --bind_ip_all
    --keyFile /etc/mongo-keyfile-dir/mongo-keyfile
  volumes:
    - mongo_keyfile:/etc/mongo-keyfile-dir:ro
    - configsvr1_data:/data/configdb
  healthcheck:
    test: ["CMD","mongosh","--quiet","--host","127.0.0.1","--port","27019",
           "--eval","db.adminCommand({ping:1}).ok"]
    interval: 5s
    timeout: 5s
    retries: 20
    start_period: 10s
```

- `<<: *mongod-common` — подмешивает образ/restart/networks/depends_on из якоря; всё, что объявлено ниже явно (`command`, `volumes`, `healthcheck`), не мёржится по ключам, а полностью переопределяет одноимённый ключ якоря (в якоре этих ключей и не было, так что тут просто "добавление").

- `--configsvr` — говорит `mongod`, что это узел **config server replica set**, а не рядовой `mongod` и не `--shardsvr`. Это меняет набор разрешённых операций и обязательные ограничения (например, у config-server replica set не может быть арбитров и delayed-членов).

- `--replSet configrs` — имя replica set; должно совпадать во всех трёх `configsvr*` и с именем, которое использует `init-configrs` в `rs.initiate`.

- `--port 27019` — порт config-серверов по конвенции (не обязателен, но общепринят); отличается от 27018 у шардов и 27017 у mongos, чтобы не путать в логах/дампах.

- `--bind_ip_all` — слушать на всех интерфейсах контейнера (внутри docker-сети это безопасно, порт наружу всё равно не публикуется).

- `--keyFile ...` — путь к keyfile **внутри** этого контейнера, в volume, который подготовил
  `keyfile-init`. Именно это включает внутреннюю аутентификацию узлов друг перед другом (и, как следствие, требование аутентификации для клиентов).

- `volumes: configsvr1_data:/data/configdb` — обратите внимание: путь `/data/configdb`, а не `/data/db`,
  который используется для обычных `mongod`/шардов. Это официальный путь для данных config-сервера в
  образе `mongo`.

- `healthcheck` — раз в 5с (после 10с прогрева) дергает `ping` с указанием **`--host 127.0.0.1 --port 127019`** явно (а не полагается на дефолтный порт 27017 у `mongosh`, который тут не тот). 20 попыток × 5с = почти 2 минуты на то, чтобы узел поднялся, прежде чем Docker посчитает его `unhealthy` — с запасом на медленный старт на слабом железе.

- Узлы `configsvr2`/`configsvr3` — дословно то же самое с другим именем сервиса/volume.

### 1.5.4 `init-configrs` — самоинициализация config server replica set

```yaml
init-configrs:
  image: mongo:8
  network_mode: "service:configsvr1"
  depends_on:
    configsvr1: { condition: service_healthy }
    configsvr2: { condition: service_healthy }
    configsvr3: { condition: service_healthy }
  volumes:
    - bootstrap_state:/bootstrap
  entrypoint: [/bin/sh, -ec, |
    if [ -f /bootstrap/configrs.done ]; then exit 0; fi
    mongosh --quiet --host 127.0.0.1 --port 27019 --eval '
      try { rs.status(); } catch (e) {
        if (e.codeName !== "NotYetInitialized") { throw e; }
        rs.initiate({ _id: "configrs", configsvr: true, members: [...] });
      }
      while (true) {
        try {
          if (rs.status().members.some(m => m.stateStr === "PRIMARY")) break;
        } catch (e) {}
        sleep(1000);
      }
    '
    touch /bootstrap/configrs.done
  ]
  restart: "no"
```

(здесь эта команда показана сокращённо для разбора — дословный текст см. в блоке compose выше).

- **`network_mode: "service:configsvr1"`** — ключевой трюк: этот контейнер не получает свой собственный
  сетевой namespace, а **живёт внутри сетевого namespace `configsvr1`**. Поэтому `127.0.0.1:27019` из этого
  контейнера — это буквально `configsvr1:27019`, без необходимости резолвить DNS-имя сервиса или ждать,
  пока Docker поднимет отдельный сетевой интерфейс. Это же значит, что `init-configrs` не указан в секции
  `networks:` — сеть ему в принципе не нужна отдельно, он одалживает чужую.
- `depends_on: ...: service_healthy` на все три `configsvr*` — инициировать replica set есть смысл, только
  когда все три узла уже отвечают на `ping`.
- **Идемпотентность через `/bootstrap/configrs.done`** на общем volume `bootstrap_state`: при первом
  запуске файла нет → инициализируем; при повторном `docker compose up` (например, после перезагрузки
  хоста, когда данные в `configsvr*_data` уже никуда не делись) файл уже есть → скрипт сразу выходит с
  кодом 0, **не пытаясь повторно инициировать уже существующий replica set** (повторный `rs.initiate()` на
  уже проинициализированном наборе — ошибка, поэтому важно не звать его вслепую).
- Внутри `mongosh --eval`: `try { rs.status() } catch(e) { if (e.codeName !== "NotYetInitialized") throw
  e; ... }` — это дополнительная защита на случай, если `.done`-файл почему-то потерялся, а replica set
  на самом деле уже инициализирован (например, volume `bootstrap_state` пересоздали, а `configsvrN_data`
  — нет): скрипт сначала спрашивает `rs.status()`, и только если MongoDB прямо говорит "ещё не
  инициализирован" — вызывает `rs.initiate(...)`. Любая другая ошибка (например, сетевая) — пробрасывается
  дальше и уронит весь контейнер (что и должно произойти: непонятно, что случилось, лучше упасть явно).
- Цикл `while(true) { ... rs.status().members.some(primary) ... sleep(1000) }` — не полагается на то, что
  primary выберется мгновенно после `rs.initiate()` (выборы занимают время), и **ждёт**, пока хоть кто-то
  не станет `PRIMARY`, прежде чем считать бутстрап завершённым. Это важно: если бы скрипт написал
  `.done`-файл сразу после `rs.initiate()`, не дожидаясь primary, следующие сервисы (`mongos1` через цепочку
  зависимостей) могли бы попытаться работать с ещё не готовым набором.
- `touch /bootstrap/configrs.done` — маркер успеха, ставится только в самом конце, после того, как
  primary подтверждён.
- `init-shard1` и `init-shard2` устроены **дословно так же** (см. полный YAML выше), только
  `network_mode: "service:shard1a"` / `"service:shard2a"`, порт `27018` вместо `27019`, `replSet` —
  `shard1rs`/`shard2rs`, и в `rs.initiate` — три члена соответствующего шарда.

### 1.5.5 Шарды (`shard1a/b/c`, `shard2a/b/c`)

Отличия от config-сервера — только флаг и порт:

```yaml
command:
  mongod
  --shardsvr          # вместо --configsvr
  --replSet shard1rs
  --port 27018         # вместо 27019
  --bind_ip_all
  --keyFile /etc/mongo-keyfile-dir/mongo-keyfile
volumes:
  - mongo_keyfile:/etc/mongo-keyfile-dir:ro
  - shard1a_data:/data/db   # обычный /data/db, а не /data/configdb
```

- `--shardsvr` — говорит `mongod`, что это узел одного из шардов сharded-кластера (а не одиночный
  standalone/replica set сам по себе). Технически на данные это не влияет напрямую, но нужен для
  корректной работы `addShard`/маршрутизации `mongos` и некоторых внутренних проверок согласованности
  кластера.
- Остальное — как в конфиг-серверах: keyfile, healthcheck на `ping`, volume под данные.

### 1.5.6 `mongos1` / `mongos2`

```yaml
mongos1:
  image: mongo:8
  restart: unless-stopped
  networks: [mongo-cluster]
  command:
    mongos
    --configdb configrs/configsvr1:27019,configsvr2:27019,configsvr3:27019
    --bind_ip_all
    --port 27017
    --keyFile /etc/mongo-keyfile-dir/mongo-keyfile
  volumes:
    - mongo_keyfile:/etc/mongo-keyfile-dir:ro
  ports:
    - "127.0.0.1:27017:27017"
  depends_on:
    init-configrs: { condition: service_completed_successfully }
    init-shard1: { condition: service_completed_successfully }
    init-shard2: { condition: service_completed_successfully }
```

- `mongos` — единственный сервис, у которого команда не `mongod`, а `mongos` (роутер, сам не хранит
  данные, только маршрутизирует).
- `--configdb configrs/host1:port,host2:port,host3:port` — обязательный аргумент: имя replica set
  config-серверов и полный список его членов. Если тут указать не все три (или указать не тот `replSet`
  name) — `mongos` откажется стартовать.
- `ports: ["127.0.0.1:27017:27017"]` — публикуется **только на localhost хоста** (не `0.0.0.0`), то есть
  снаружи машины этот порт недоступен в принципе, только с самого хоста — разумный дефолт для локального
  стенда.
- `depends_on` на все три `init-*` с `service_completed_successfully` — `mongos` есть смысл поднимать,
  только когда все три replica set уже существуют (иначе `--configdb` будет указывать на
  ещё-не-инициализированный набор, и `mongos` не сможет пройти handshake).
- `mongos2` — то же самое, но `ports: ["127.0.0.1:27018:27017"]` (наружу — другой порт хоста, `27018`,
  внутри контейнера всё так же `27017`) и `depends_on: mongos1: service_healthy` (запускается вторым, хотя
  оба независимы друг от друга после старта — просто чтобы не создавать двух одновременных "гонок" за
  первое подключение к ещё тёплому кластеру).

### 1.5.7 `init-cluster` — addShard и создание администратора

```yaml
init-cluster:
  image: mongo:8
  network_mode: "service:mongos1"
  environment:
    MONGO_ADMIN_USER: ${MONGO_ADMIN_USER:-admin}
    MONGO_ADMIN_PASSWORD: ${MONGO_ADMIN_PASSWORD:-admin}
  depends_on:
    mongos1: { condition: service_healthy }
    mongos2: { condition: service_healthy }
  entrypoint: [ ... addShard x2, затем createUser ... ]
  restart: "no"
```

- `network_mode: "service:mongos1"` — тот же трюк, что и у `init-*rs`: этот контейнер общается с
  `127.0.0.1:27017`, потому что живёт в сетевом namespace `mongos1`.
- `environment: MONGO_ADMIN_USER: ${MONGO_ADMIN_USER:-admin}` — Compose-синтаксис "переменная окружения
  хоста/`.env`, а если не задана — дефолт `admin`". Отсюда и логин/пароль `admin`/`admin` в вашем
  `test_mongo.py` "из коробки", если вы не завели `.env`.
- Порядок операций в скрипте: **сначала `addShard` x2, потом `createUser`.** Это важно: пока не
  пройден `addShard`, кластер не готов держать пользовательские данные, а `admin`-пользователь создаётся
  **после**, пока ещё действует "localhost exception" (см. предыдущую заметку) — то есть создание
  проходит без пароля, через доверенное локальное подключение внутри сетевого namespace `mongos1`.
- `db.adminCommand({addShard: "shard1rs/shard1a:27018,shard1b:27018,shard1c:27018", name: "shard1"})` —
  явно перечисляет все три узла шарда (а не один — так `mongos` сразу знает полный состав набора и не
  зависит от того, кто из трёх окажется живым в момент добавления) и даёт человекочитаемое имя `"shard1"`
  вместо автоматически подставляемого `shard1rs`.
- `if (!result.ok) { quit(1); }` — если `addShard` не удался, скрипт завершается ненулевым кодом, и вся
  цепочка `depends_on: service_completed_successfully` для `mongos`-уровня (в данном случае для будущих
  сервисов, если бы они от него зависели) корректно считает бутстрап проваленным — `docker compose up`
  покажет ошибку, а не тихо продолжит с наполовину собранным кластером.
- Важное отличие от предыдущей версии заметки: там мы вручную заводили ещё и отдельного
  прикладного пользователя (`app_user`/`readWrite`) — здесь этого нет, `init-cluster` создаёт только
  `root`. Для учебного стенда это ок; для настоящего прода стоило бы добавить сюда ещё один
  `createUser` с ролью `readWrite` на конкретную БД — но раз задача была "описать файл как есть", в
  заметке это зафиксировано как факт, а не молча исправлено.

### 1.5.8 Сеть и volumes

```yaml
networks:
  mongo-cluster:
    driver: bridge

volumes:
  mongo_keyfile:
  bootstrap_state:
  configsvr1_data: {}  # и т.д. для всех 9 узлов
```

- Одна общая bridge-сеть на всё — узлы обращаются друг к другу по DNS-именам сервисов (`shard1a`,
  `configsvr2`, ...), которые Docker Compose разрешает автоматически внутри пользовательской сети (в
  отличие от сети `default`/`bridge` без явного объявления, где резолвинг по имени сервиса не гарантирован).
  `init-*`/`init-cluster` не входят в `networks:` — им сеть не нужна, они переиспользуют чужую через
  `network_mode: service:...`.
- `bootstrap_state` — единственный volume, который не хранит данные MongoDB, а хранит **флаги
  идемпотентности** ("этот шаг уже сделан") между перезапусками `docker compose up`.
- `mongo_keyfile` — volume с готовым (правильные права/владелец) keyfile, общий для всех mongod/mongos на
  чтение.
- Остальные 9 volume — по одному на каждый узел config server/шардов, обычные volumes для данных.

---

# Часть 2 Python-проект `mongo_lab`

> [!Important] Папка проекта `mongo_lab` лежит в `Code_examples`

```
mongo_lab/
├── config.py         # подключение, топология кластера, имена сервисов/портов
├── cluster_ctl.py     # docker compose stop/start + опрос db.hello() на узлах
├── mongo_ops.py       # индексы, CRUD, шардирование, canary write/read
├── scenarios.py       # 7 сценариев отказов
├── run_lab.py         # точка входа: baseline-проверки → все сценарии → отчёт
└── requirements.txt
```

## 2.1 Что проверяют базовые проверки (перед сценариями)

`run_lab.py` перед тем, как что-либо ломать:

1. Дожидается, что все три replica set видят своего primary (иначе бессмысленно начинать эксперименты).
2. Подключается через `mongos` (оба хоста сразу в URI: `localhost:27017,localhost:27018`).
3. `ensure_sharded_collection` — включает шардирование для `labdb`, создаёт hashed-индекс на `customerId`
   и шардирует `labdb.orders`. **Это то, чего сознательно нет в самом compose-файле** (решение о shard key
   — прикладное, а не инфраструктурное) — поэтому в `test_mongo.py` коллекция `shop.users` до сих пор
   обычная, нешардированная, и целиком лежит на одном (случайно выбранном) шарде.
4. Насевает 200 документов со случайными `customerId` — на пустой коллекции с hashed-ключом MongoDB сама
   пресплитит и раскидывает начальные чанки по обоим шардам, так что 200 разных ключей действительно
   разъезжаются на оба шарда, а не оседают на одном.
5. Печатает распределение через `$collStats` (аналог `getShardDistribution()` из `mongosh`, доступный из
   `pymongo`).

## 2.2 Сценарии отказов (`scenarios.py`)

| №   | Сценарий               | Что ломаем                                      | Ожидание по архитектуре MongoDB                                                                                                                                                                                        |
| --- | ---------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0   | `baseline`             | ничего                                          | canary write/read проходит, данные видны на обоих шардах                                                                                                                                                               |
| 1   | `kill_one_secondary`   | 1 secondary в `shard1rs`                        | кворум 2/3 сохранён, primary не меняется, запись/чтение работают без сбоев                                                                                                                                             |
| 2   | `kill_primary`         | текущий primary `shard1rs`                      | оставшиеся 2 узла (кворум есть) выбирают нового primary за время до `electionTimeoutMillis` (~10-12с); до выборов запись падает по таймауту                                                                            |
| 3   | `kill_majority`        | primary + 1 secondary в `shard1rs` (жив 1 из 3) | кворума для выборов нет → primary отсутствует; запись падает; чтение с `secondaryPreferred` может продолжить работать с одинокого survivor'а, т.к. secondary не "разжалуется" сам из-за потери контакта с большинством |
| 4   | `kill_whole_shard`     | все 3 узла `shard2rs`                           | точечный запрос по ключу, попавшему на `shard1`, работает; запрос без фильтра (scatter-gather) должен упасть целиком — `mongos` обязан получить ответ от каждого адресуемого шарда                                     |
| 5   | `kill_config_majority` | 2 из 3 config-серверов                          | операции над уже существующей шардированной коллекцией обычно продолжают работать (mongos кеширует routing-метаданные), а вот создание НОВЫХ метаданных шардирования должно упасть                                     |
| 6   | `kill_one_mongos`      | `mongos2`                                       | клиент подключён сразу к обоим mongos, драйвер прозрачно переключается на оставшийся                                                                                                                                   |

Каждый сценарий:
1. печатает состояние кластера до вмешательства (`ctl.print_cluster_report()`);
2. останавливает нужные контейнеры (`ctl.compose_stop(...)`);
3. ждёт ожидаемого изменения состояния (`ctl.wait_for(...)`) — например, появления/исчезновения primary;
4. пробует canary write/read (или более специфичную операцию — scatter-gather `count_documents({})`,
   попытку `enableSharding` на новой БД) и печатает, удался ли он;
5. **сам восстанавливает** остановленные контейнеры (`ctl.compose_start(...)`) и ждёт возврата в строй,
   прежде чем перейти к следующему сценарию — сценарии независимы и идут по порядку без ручного
   вмешательства.

## 2.3 Запуск

```bash
cd mongo_lab
python3 -m venv .venv && source .venv/bin/activate
pip install -r mongo_lab/requirements.txt
python3 run_lab.py
```

Учётные данные и хосты можно переопределить переменными окружения (по умолчанию соответствуют дефолтам
самого `docker-compose.yaml`):

```bash
export MONGO_HOSTS="localhost:27017,localhost:27018"
export MONGO_ADMIN_USER=admin
export MONGO_ADMIN_PASSWORD=admin
```
