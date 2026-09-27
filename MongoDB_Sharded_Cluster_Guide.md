# MongoDB Sharded Cluster в Docker Compose — полный разбор и лаборатория отказоустойчивости

> [!summary]
> Эта заметка описывает локальный MongoDB 8 sharded cluster, который полностью разворачивается одной командой `docker compose up -d`.
> Compose автоматически подготавливает keyfile, запускает config server replica set, два shard replica set, инициирует все три replica set, запускает два `mongos`, добавляет shard'ы в кластер и создаёт администратора.
>
> Вторая часть заметки — Python-лаборатория. Она создаёт sharded collection, выполняет CRUD, создаёт индексы, анализирует `explain()`, а затем сама останавливает контейнеры через `docker compose stop`, наблюдает election/failover и проверяет доступность чтения и записи при разных отказах. В `finally` скрипт пытается вернуть все остановленные сервисы.

---

# 1. Что мы построили

Архитектура кластера:

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

Здесь важно разделять четыре уровня:

1. **`mongos`** — точка входа для приложения и query router.
2. **`configrs`** — replica set, хранящий метаданные sharded cluster.
3. **`shard1rs` и `shard2rs`** — два shard'а, между которыми MongoDB распределяет пользовательские данные.
4. **Replica set внутри каждого shard** — три копии данных для отказоустойчивости.

Главная формула:

```text
SHARDING = распределение разных частей данных между shard1rs и shard2rs.

REPLICATION = копирование одной и той же части данных между участниками одного replica set.
```

То есть `shard1a`, `shard1b`, `shard1c` — не три shard'а. Это три участника **одного** shard `shard1rs`.

---

# 2. Сколько контейнеров создаётся

В Compose определено 16 сервисов.

## 2.1. Постоянно работающие контейнеры — 11

| Группа | Контейнеры | Количество | Назначение |
|---|---|---:|---|
| Config Server | `configsvr1`, `configsvr2`, `configsvr3` | 3 | Метаданные кластера |
| Shard 1 | `shard1a`, `shard1b`, `shard1c` | 3 | Первая часть пользовательских данных |
| Shard 2 | `shard2a`, `shard2b`, `shard2c` | 3 | Вторая часть пользовательских данных |
| Routers | `mongos1`, `mongos2` | 2 | Точка входа и маршрутизация запросов |

Итого:

```text
3 + 3 + 3 + 2 = 11 постоянно работающих процессов MongoDB
```

Из них:

```text
9 × mongod
2 × mongos
```

## 2.2. Одноразовые init-контейнеры — 5

| Контейнер | Задача | Нормальное финальное состояние |
|---|---|---|
| `keyfile-init` | Подготавливает keyfile | `Exited (0)` |
| `init-configrs` | Выполняет `rs.initiate()` для `configrs` | `Exited (0)` |
| `init-shard1` | Выполняет `rs.initiate()` для `shard1rs` | `Exited (0)` |
| `init-shard2` | Выполняет `rs.initiate()` для `shard2rs` | `Exited (0)` |
| `init-cluster` | Делает `addShard` и создаёт `admin` | `Exited (0)` |

`Exited (0)` здесь означает не ошибку, а:

```text
контейнер выполнил одноразовую задачу успешно и завершился.
```

---

# 3. Полный docker-compose.yml БЕЗ ИЗМЕНЕНИЙ

Ниже содержимое переданного `docker-compose.yml` без изменений.

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

# 4. Как Compose исполняется во времени

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

# 5. Разбор `x-mongod-common`

Исходный блок:

```yaml
x-mongod-common: &mongod-common
  image: mongo:8
  restart: unless-stopped
  networks: [mongo-cluster]
  depends_on:
    keyfile-init:
      condition: service_completed_successfully
```

## `x-mongod-common`

Имя начинается с `x-`, поэтому это Compose extension field.

Это **не сервис** и отдельного контейнера не создаёт.

## `&mongod-common`

Это YAML anchor.

Он сохраняет блок под именем `mongod-common`.

Позже:

```yaml
configsvr1:
  <<: *mongod-common
```

означает:

> скопировать сюда все поля из anchor `mongod-common`.

Аналогия с JavaScript:

```javascript
const mongodCommon = {
    image: "mongo:8",
    restart: "unless-stopped"
};

const configsvr1 = {
    ...mongodCommon,
    command: "..."
};
```

## `image: mongo:8`

Используется официальный Docker image MongoDB major version 8.

Важно: `mongo:8` — major tag, а не фиксированная patch-версия. При новом `docker pull` содержимое тега со временем может обновиться в пределах ветки 8.x.

Для учебного стенда это удобно. Для полностью воспроизводимой production-конфигурации обычно фиксируют точную версию.

## `restart: unless-stopped`

Docker перезапустит процесс после сбоя или рестарта Docker daemon, кроме случая, когда контейнер был явно остановлен пользователем.

Это удобно для экспериментов:

```bash
docker compose stop shard1a
```

не приводит к мгновенному автоматическому возврату `shard1a`.

## `networks: [mongo-cluster]`

Контейнер подключается к общей Docker bridge network.

Внутри неё Docker DNS разрешает имена сервисов:

```text
configsvr1 -> IP контейнера configsvr1
shard1a    -> IP контейнера shard1a
mongos1    -> IP контейнера mongos1
```

Поэтому MongoDB replica set configuration может использовать:

```text
shard1a:27018
```

вместо динамического IP типа `172.20.0.5`.

## `depends_on -> keyfile-init`

```yaml
depends_on:
  keyfile-init:
    condition: service_completed_successfully
```

Каждый обычный `mongod` стартует только после успешного завершения `keyfile-init`.

Здесь важно отличие:

```yaml
condition: service_healthy
```

означает «дождаться работающего healthy-сервиса».

А:

```yaml
condition: service_completed_successfully
```

означает «дождаться завершения одноразового сервиса с exit code 0».

---

# 6. `keyfile-init` — внутренняя безопасность кластера

```yaml
keyfile-init:
  image: mongo:8
  user: root
```

Этот контейнер временно запускается от `root`, потому что ему нужно менять владельца и permissions файла.

## `entrypoint`

```yaml
entrypoint:
  - /bin/sh
  - -ec
  - |
```

Фактически Docker выполняет:

```bash
/bin/sh -ec '<скрипт>'
```

`-e`:

```text
завершить shell при первой ошибке
```

`-c`:

```text
выполнить переданный текст как shell command
```

Поэтому если `cp`, `chown`, `chmod` или `test` упадут — контейнер не напечатает ложный успех и завершится ненулевым exit code.

## Копирование keyfile

```bash
cp /keyfile-src/mongo-keyfile /keyfile/mongo-keyfile
```

Источник:

```yaml
./secrets/mongo-keyfile:/keyfile-src/mongo-keyfile:ro
```

Это bind mount с хоста.

`ro` = read-only.

Назначение:

```yaml
mongo_keyfile:/keyfile
```

Это Docker named volume.

Схема:

```text
HOST
./secrets/mongo-keyfile
        |
        | bind mount RO
        v
/keyfile-src/mongo-keyfile
        |
        | cp
        v
/keyfile/mongo-keyfile
        |
        v
Docker volume mongo_keyfile
```

## Владелец

```bash
chown "$(id -u mongodb):$(id -g mongodb)" /keyfile/mongo-keyfile
```

Вместо жёсткого UID `999` запрашивается реальный UID/GID пользователя `mongodb` внутри текущего image.

## Permissions

```bash
chmod 0400 /keyfile/mongo-keyfile
```

`0400`:

```text
owner: read
group: ---
other: ---
```

MongoDB использует этот файл как shared secret для внутренней аутентификации процессов:

```text
mongod <-> mongod
mongos <-> mongod
```

## Проверка файла

```bash
test -s /keyfile/mongo-keyfile
```

Успех только если файл:

- существует;
- имеет ненулевой размер.

Если нет — shell из-за `-e` завершается ошибкой.

## `restart: "no"`

Init-контейнер не должен работать постоянно.

Нормально:

```text
keyfile-init    Exited (0)
```

---

# 7. Config Server Replica Set — `configrs`

Создаются три процесса:

```text
configsvr1
configsvr2
configsvr3
```

Все имеют одинаковую роль и разные data volumes.

Пример `configsvr1`:

```yaml
command:
  mongod
  --configsvr
  --replSet configrs
  --port 27019
  --bind_ip_all
  --keyFile /etc/mongo-keyfile-dir/mongo-keyfile
```

## `mongod`

Запускает MongoDB server process.

## `--configsvr`

Обозначает процесс как config server.

Config server хранит metadata sharded cluster:

- список shard'ов;
- sharded collections;
- shard keys;
- chunks/ranges;
- размещение chunks;
- cluster metadata;
- часть данных authentication/authorization.

`mongos` использует эту информацию, чтобы понять, куда направить запрос.

## `--replSet configrs`

Сообщает MongoDB, что процесс должен входить в replica set:

```text
configrs
```

Сам по себе этот флаг **не выполняет** `rs.initiate()`.

Именно поэтому дальше существует `init-configrs`.

## `--port 27019`

Внутренний порт config server.

Все три config server могут использовать один и тот же порт, потому что находятся в разных network namespace контейнеров.

## `--bind_ip_all`

MongoDB слушает не только localhost контейнера.

Иначе `configsvr1`, `configsvr2`, `configsvr3` и `mongos` не смогли бы общаться через Docker network.

## `--keyFile`

```text
/etc/mongo-keyfile-dir/mongo-keyfile
```

Это тот же Docker volume `mongo_keyfile`, который подготовил `keyfile-init`.

---

# 8. Почему у каждого config server свой volume

```yaml
configsvr1_data:/data/configdb
configsvr2_data:/data/configdb
configsvr3_data:/data/configdb
```

Каждый replica member хранит собственную копию данных на собственном диске.

Нельзя делать:

```text
configsvr1 --+
configsvr2 --+--> один общий /data/configdb
configsvr3 --+
```

Репликация должна происходить через MongoDB protocol/oplog:

```text
PRIMARY
   |
   +---- replication ----> SECONDARY
   |
   +---- replication ----> SECONDARY
```

а не через общий filesystem.

Для `--configsvr` используется `/data/configdb`.

---

# 9. Healthcheck config server

```yaml
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
```

Docker каждые 5 секунд запускает внутри контейнера:

```bash
mongosh --quiet   --host 127.0.0.1   --port 27019   --eval 'db.adminCommand({ping:1}).ok'
```

Если `mongod` отвечает — healthcheck успешен.

Параметры:

- `interval: 5s` — период проверки;
- `timeout: 5s` — сколько максимум ждать одну проверку;
- `retries: 20` — сколько последовательных ошибок допускается;
- `start_period: 10s` — стартовое окно на инициализацию процесса.

Важно:

```text
healthy здесь означает, что mongod запущен и отвечает.
```

Это не гарантирует наличие PRIMARY replica set. Поэтому после healthcheck запускается отдельный bootstrap `init-configrs`.

---

# 10. `init-configrs` — автоматический `rs.initiate()`

Ключевая строка:

```yaml
network_mode: "service:configsvr1"
```

`init-configrs` не получает отдельный сетевой namespace, а использует network namespace `configsvr1`.

Поэтому для него:

```text
127.0.0.1:27019
```

— это `configsvr1:27019`.

Это используется для первоначального bootstrap при включённом access control.

## Зависимости

```yaml
depends_on:
  configsvr1:
    condition: service_healthy
  configsvr2:
    condition: service_healthy
  configsvr3:
    condition: service_healthy
```

`rs.initiate()` не запускается, пока все три процесса не отвечают.

## `bootstrap_state`

```yaml
volumes:
  - bootstrap_state:/bootstrap
```

Внутри него создаются маркеры `.done`.

Проверка:

```bash
if [ -f /bootstrap/configrs.done ]; then
  echo "configrs already initialized"
  exit 0
fi
```

Это не даёт init-контейнеру повторно выполнять bootstrap при каждом `docker compose up`.

## Проверка существующего replica set

```javascript
try {
    rs.status();
    print("configrs already exists");
} catch (e) {
    if (e.codeName !== "NotYetInitialized") {
        throw e;
    }
```

Если `rs.status()` уже работает — повторно `rs.initiate()` не нужен.

Если MongoDB отвечает `NotYetInitialized`, выполняется:

```javascript
rs.initiate({
  _id: "configrs",
  configsvr: true,
  members: [
    { _id: 0, host: "configsvr1:27019" },
    { _id: 1, host: "configsvr2:27019" },
    { _id: 2, host: "configsvr3:27019" }
  ]
})
```

`configsvr: true` сообщает, что это именно Config Server Replica Set.

## Election

После `rs.initiate()` replica set ещё должен выбрать PRIMARY.

Поэтому bootstrap циклически вызывает:

```javascript
const s = rs.status();
```

и ищет:

```javascript
m.stateStr === "PRIMARY"
```

Только после реального появления PRIMARY создаётся:

```bash
touch /bootstrap/configrs.done
```

Таким образом:

```text
rs.initiate() returned OK
        !=
replica set полностью готов
```

Compose ждёт более сильное условие — появление PRIMARY.

---

# 11. `shard1rs`

Сервисы:

```text
shard1a
shard1b
shard1c
```

Их command:

```yaml
mongod
--shardsvr
--replSet shard1rs
--port 27018
--bind_ip_all
--keyFile ...
```

От config server отличается главным флагом:

```text
--configsvr   -> config server
--shardsvr    -> shard server
```

Все три входят в один replica set:

```text
shard1rs
```

После election один будет PRIMARY, два — SECONDARY.

## Где лежат данные

```yaml
shard1a_data:/data/db
shard1b_data:/data/db
shard1c_data:/data/db
```

Это три независимых Docker volume.

## Healthcheck

Тот же принцип, но порт:

```text
27018
```

---

# 12. `init-shard1`

```yaml
network_mode: "service:shard1a"
```

Значит:

```text
init-shard1:127.0.0.1:27018
        =
shard1a:27018
```

После healthcheck всех трёх участников выполняется:

```javascript
rs.initiate({
  _id: "shard1rs",
  members: [
    { _id: 0, host: "shard1a:27018" },
    { _id: 1, host: "shard1b:27018" },
    { _id: 2, host: "shard1c:27018" }
  ]
})
```

После этого init-контейнер ждёт PRIMARY и создаёт:

```text
/bootstrap/shard1rs.done
```

---

# 13. `shard2rs` и `init-shard2`

Полностью симметричны `shard1rs`.

Участники:

```text
shard2a
shard2b
shard2c
```

Replica set:

```text
shard2rs
```

Данные:

```text
shard2a_data
shard2b_data
shard2c_data
```

Bootstrap:

```text
init-shard2
```

Marker:

```text
/bootstrap/shard2rs.done
```

---

# 14. Где здесь replication, а где sharding

После bootstrap:

```text
shard1rs
+-- shard1a
+-- shard1b
+-- shard1c

shard2rs
+-- shard2a
+-- shard2b
+-- shard2c
```

Внутри `shard1rs`:

```text
одни и те же данные -> три replica members
```

Внутри `shard2rs`:

```text
другая часть данных -> три replica members
```

Поэтому:

```text
                SHARDING
                   |
          +--------+--------+
          |                 |
       shard1rs          shard2rs
          |                 |
      replication       replication
     +----+----+       +----+----+
     a    b    c       a    b    c
```

---

# 15. `mongos1`

```yaml
command:
  mongos
  --configdb configrs/configsvr1:27019,configsvr2:27019,configsvr3:27019
  --bind_ip_all
  --port 27017
  --keyFile /etc/mongo-keyfile-dir/mongo-keyfile
```

`mongos` — не storage server.

Он выполняет роль router:

```text
CLIENT
   |
   v
mongos
   |
   +--> определить нужный shard
   |
   +--> отправить запрос
   |
   +--> собрать результат
   v
CLIENT
```

## `--configdb`

```text
configrs/configsvr1:27019,configsvr2:27019,configsvr3:27019
```

Формат:

```text
<replica-set-name>/<member1>,<member2>,<member3>
```

То есть `mongos` знает, где получать cluster metadata.

## Публикация порта

```yaml
ports:
  - "127.0.0.1:27017:27017"
```

Разбор:

```text
127.0.0.1 : 27017 : 27017
host IP      host     container
```

Получаем:

```text
localhost:27017 -> mongos1:27017
```

`127.0.0.1` специально не публикует MongoDB на все сетевые интерфейсы компьютера.

## Почему `mongos1` ждёт init-сервисы

```yaml
depends_on:
  init-configrs:
    condition: service_completed_successfully
  init-shard1:
    condition: service_completed_successfully
  init-shard2:
    condition: service_completed_successfully
```

Это важный момент.

`mongos` стартует только когда существуют:

```text
configrs + PRIMARY
shard1rs + PRIMARY
shard2rs + PRIMARY
```

---

# 16. `mongos2`

Внутри контейнера он тоже слушает:

```text
27017
```

Но на host опубликован как:

```yaml
127.0.0.1:27018:27017
```

То есть:

```text
localhost:27018 -> mongos2:27017
```

Не путать host `27018` здесь с внутренним портом shard'ов `27018`.

Это просто два разных network namespace.

## Зачем два `mongos`

Если приложение знает только:

```text
localhost:27017
```

то остановка `mongos1` разрывает доступ приложения.

Если connection string содержит оба:

```text
localhost:27017,localhost:27018
```

PyMongo может выбрать доступный router.

---

# 17. `init-cluster`

Это финальный bootstrap.

Он запускается только после:

```text
mongos1 healthy
mongos2 healthy
```

И снова использует:

```yaml
network_mode: "service:mongos1"
```

Поэтому подключение:

```text
127.0.0.1:27017
```

идёт в `mongos1`.

## Защита от повторного bootstrap

```bash
if [ -f /bootstrap/cluster.done ]; then
  echo "cluster already initialized"
  exit 0
fi
```

## Добавление первого shard

```javascript
db.adminCommand({
  addShard:
    "shard1rs/shard1a:27018,shard1b:27018,shard1c:27018",
  name: "shard1"
})
```

Теперь metadata кластера содержит:

```text
logical shard name: shard1
replica set: shard1rs
members: shard1a/b/c
```

## Добавление второго shard

То же для:

```text
shard2
shard2rs
```

## Создание пользователя

```yaml
environment:
  MONGO_ADMIN_USER: ${MONGO_ADMIN_USER:-admin}
  MONGO_ADMIN_PASSWORD: ${MONGO_ADMIN_PASSWORD:-admin}
```

Compose syntax:

```text
${VAR:-default}
```

означает:

```text
если VAR определена -> использовать её;
иначе -> default.
```

По умолчанию получается:

```text
admin / admin
```

Далее:

```javascript
admin.createUser({
  user: process.env.MONGO_ADMIN_USER,
  pwd: process.env.MONGO_ADMIN_PASSWORD,
  roles: [
    {
      role: "root",
      db: "admin"
    }
  ]
})
```

После успеха:

```bash
touch /bootstrap/cluster.done
```

---

# 18. Docker network

```yaml
networks:
  mongo-cluster:
    driver: bridge
```

Создаётся user-defined bridge network.

Она решает сразу две задачи:

1. изолирует внутреннее взаимодействие MongoDB;
2. даёт DNS по service name.

Внутренний traffic:

```text
mongos1 -> configsvr1:27019
mongos1 -> shard1a:27018
shard1a -> shard1b:27018
...
```

не требует публикации этих портов на host.

На host опубликованы только точки входа приложения:

```text
27017 -> mongos1
27018 -> mongos2
```

---

# 19. Docker volumes

Compose создаёт 11 named volumes.

## Служебные

```text
mongo_keyfile
bootstrap_state
```

`mongo_keyfile` хранит подготовленный security key.

`bootstrap_state` хранит:

```text
configrs.done
shard1rs.done
shard2rs.done
cluster.done
```

## Config data

```text
configsvr1_data
configsvr2_data
configsvr3_data
```

## Shard data

```text
shard1a_data
shard1b_data
shard1c_data
shard2a_data
shard2b_data
shard2c_data
```

---

# 20. `docker compose down` против `down -v`

## Обычный down

```bash
docker compose down
```

Удаляет контейнеры/network, но сохраняет named volumes.

После нового:

```bash
docker compose up -d
```

MongoDB продолжит работать с прежними данными.

## Полный reset

```bash
docker compose down -v
```

Удаляет также named volumes.

После него кластер создаётся с нуля.

Для этого Compose важно удалять **все** связанные volumes одновременно. Если удалить MongoDB data volume, но сохранить `bootstrap_state`, `.done`-файл может утверждать, что replica set уже инициализирован, хотя его data volume уже пуст.

Для полного учебного reset:

```bash
docker compose down -v
docker compose up -d
```

---

# 21. Что происходит при записи документа

Допустим Python делает:

```python
collection.insert_one({"user_id": 123, "name": "Alice"})
```

Путь:

```text
Python
  |
  v
mongos
  |
  | shard key + metadata
  v
нужный shard replica set
  |
  v
PRIMARY
  |
  +------> SECONDARY
  |
  +------> SECONDARY
```

Если коллекция sharded по:

```javascript
{ user_id: "hashed" }
```

`mongos` хеширует shard key и определяет нужный chunk/shard.

---

# 22. Что происходит при чтении

По умолчанию MongoDB/PyMongo использует:

```text
readPreference = primary
```

То есть на каждом затронутом shard чтение идёт в PRIMARY этого replica set.

При:

```text
secondary
```

или:

```text
secondaryPreferred
```

`mongos` применяет read preference при выборе replica set member внутри shard.

SECONDARY может немного отставать, потому что replication asynchronous.

---

# 23. Targeted query и scatter-gather

Если запрос содержит shard key:

```python
find_one({"user_id": 123})
```

`mongos` обычно может отправить его только в нужный shard:

```text
mongos -> shard1
```

или:

```text
mongos -> shard2
```

Это targeted operation.

Если:

```python
find({"city": "Batumi"})
```

а `city` не shard key, router может не знать, где лежат документы.

Тогда:

```text
              +--> shard1
mongos -------+
              +--> shard2
```

Это broadcast/scatter-gather.

---

# ЧАСТЬ II. Python-проект для проверки кластера

# 24. Минимальная структура проекта

Рекомендуемая структура:

```text
mongo-lab/
|
+-- docker-compose.yml
+-- secrets/
|   +-- mongo-keyfile
|
+-- .venv/
|
+-- mongo_cluster_lab.py
+-- requirements.txt
```

Установка:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt`:

```text
pymongo>=4.15
```

---

# 25. Почему Python знает оба mongos

В расширенном скрипте:

```python
DEFAULT_URI = (
    "mongodb://admin:admin@localhost:27017,localhost:27018/"
    "admin?authSource=admin"
)
```

В отличие от соединения только с:

```text
localhost:27017
```

этот URI содержит два seed router:

```text
mongos1 -> localhost:27017
mongos2 -> localhost:27018
```

Поэтому можно реально проверить отказ одного router.

---

# 26. Полный Python-скрипт

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pymongo import ASCENDING, DESCENDING, HASHED, MongoClient, ReadPreference
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from pymongo.write_concern import WriteConcern

DEFAULT_URI = (
    "mongodb://admin:admin@localhost:27017,localhost:27018/"
    "admin?authSource=admin"
)
DB_NAME = "cluster_lab"
COLLECTION_NAME = "users"


@dataclass
class TestContext:
    client: MongoClient
    compose_file: Path
    stopped_services: set[str]
    shard_keys: dict[str, int]

    @property
    def db(self):
        return self.client[DB_NAME]

    @property
    def collection(self) -> Collection:
        return self.db[COLLECTION_NAME]

    @property
    def majority_collection(self) -> Collection:
        return self.collection.with_options(
            write_concern=WriteConcern(w="majority", wtimeout=5000)
        )


def heading(text: str) -> None:
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def info(text: str) -> None:
    print(f"[INFO] {text}")


def ok(text: str) -> None:
    print(f"[ OK ] {text}")


def warn(text: str) -> None:
    print(f"[WARN] {text}")


def fail(text: str) -> None:
    print(f"[FAIL] {text}")


def compose(ctx: TestContext, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["docker", "compose", "-f", str(ctx.compose_file), *args]
    info("$ " + " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def stop_services(ctx: TestContext, services: Iterable[str]) -> None:
    services = list(services)
    if not services:
        return
    result = compose(ctx, "stop", *services, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker compose stop failed")
    ctx.stopped_services.update(services)
    ok("Остановлены: " + ", ".join(services))


def start_services(ctx: TestContext, services: Iterable[str]) -> None:
    services = list(services)
    if not services:
        return
    result = compose(ctx, "start", *services, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker compose start failed")
    ctx.stopped_services.difference_update(services)
    ok("Запущены: " + ", ".join(services))


def restore_everything(ctx: TestContext) -> None:
    if ctx.stopped_services:
        services = sorted(ctx.stopped_services)
        warn("Восстанавливаю остановленные контейнеры: " + ", ".join(services))
        start_services(ctx, services)
    # Повторный up помогает вернуть сервисы, которые могли остановиться из-за зависимостей.
    compose(ctx, "up", "-d", check=False)


def wait_until(description: str, predicate, timeout: float = 45.0, interval: float = 1.0):
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except Exception as exc:  # expected while topology is changing
            last_error = exc
        time.sleep(interval)
    suffix = f"; last error: {last_error}" if last_error else ""
    raise TimeoutError(f"Timeout while waiting for {description}{suffix}")


def ping_cluster(ctx: TestContext) -> bool:
    return ctx.client.admin.command("ping").get("ok") == 1


def wait_for_cluster(ctx: TestContext, timeout: float = 60.0) -> None:
    wait_until("mongos/cluster ping", lambda: ping_cluster(ctx), timeout=timeout)


def router_host(ctx: TestContext) -> str:
    try:
        status = ctx.client.admin.command("serverStatus")
        return str(status.get("host", "unknown"))
    except PyMongoError:
        return "unknown"


def list_shards(ctx: TestContext) -> list[dict[str, Any]]:
    return ctx.client.admin.command("listShards").get("shards", [])


def replica_set_members(ctx: TestContext, rs_name: str) -> list[dict[str, Any]]:
    """Return mongos' view of replica set members using connPoolStats.

    Field names differ slightly between MongoDB versions, so this parser accepts
    both old and new spellings.
    """
    stats = ctx.client.admin.command("connPoolStats")
    rs_info = stats.get("replicaSets", {}).get(rs_name, {})
    members = rs_info.get("hosts") or rs_info.get("host") or []
    normalized: list[dict[str, Any]] = []
    for member in members:
        addr = member.get("addr") or member.get("host") or "unknown"
        is_primary = bool(
            member.get("isWritablePrimary")
            or member.get("ismaster")
            or member.get("isMaster")
        )
        normalized.append(
            {
                "addr": addr,
                "service": str(addr).split(":", 1)[0],
                "primary": is_primary,
                "secondary": bool(member.get("secondary")),
                "ok": member.get("ok", True),
            }
        )
    return normalized


def print_replica_set(ctx: TestContext, rs_name: str) -> None:
    members = replica_set_members(ctx, rs_name)
    print(f"{rs_name}:")
    if not members:
        print("  (mongos пока не вернул сведения о members)")
        return
    for member in members:
        if member["primary"]:
            state = "PRIMARY"
        elif member["secondary"]:
            state = "SECONDARY"
        elif not member["ok"]:
            state = "DOWN"
        else:
            state = "OTHER"
        print(f"  {member['addr']:<24} {state}")


def current_primary(ctx: TestContext, rs_name: str) -> str | None:
    for member in replica_set_members(ctx, rs_name):
        if member["primary"] and member["ok"]:
            return member["service"]
    return None


def secondaries(ctx: TestContext, rs_name: str) -> list[str]:
    return [
        m["service"]
        for m in replica_set_members(ctx, rs_name)
        if m["secondary"] and m["ok"]
    ]


def wait_for_new_primary(ctx: TestContext, rs_name: str, old_primary: str | None, timeout: float = 45.0) -> str:
    def probe() -> str | None:
        # Force mongos to touch the shard and refresh topology information.
        try:
            ctx.collection.find_one({"user_id": ctx.shard_keys.get(rs_name.replace("rs", ""), 1)})
        except PyMongoError:
            pass
        primary = current_primary(ctx, rs_name)
        if primary and primary != old_primary:
            return primary
        return None

    return wait_until(f"new PRIMARY for {rs_name}", probe, timeout=timeout)


def recursive_values(value: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k == key:
                found.append(v)
            found.extend(recursive_values(v, key))
    elif isinstance(value, list):
        for item in value:
            found.extend(recursive_values(item, key))
    return found


def shard_route_for_key(ctx: TestContext, user_id: int, read_preference=ReadPreference.PRIMARY) -> dict[str, set[str]]:
    explain = ctx.db.command(
        {
            "explain": {
                "find": COLLECTION_NAME,
                "filter": {"user_id": user_id},
                "limit": 1,
            },
            "verbosity": "queryPlanner",
        },
        read_preference=read_preference,
    )

    shard_names = set(str(v) for v in recursive_values(explain, "shardName"))

    # In sharded explain output, the serverInfo nested beside shardName identifies
    # the member that processed that shard's portion of the query.
    shard_hosts: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if "shardName" in obj and isinstance(obj.get("serverInfo"), dict):
                host = obj["serverInfo"].get("host")
                if host:
                    shard_hosts.add(str(host))
            for child in obj.values():
                walk(child)
        elif isinstance(obj, list):
            for child in obj:
                walk(child)

    walk(explain)
    return {"shards": shard_names, "hosts": shard_hosts}


def find_key_for_shard(ctx: TestContext, shard_name: str, start: int = 1, limit: int = 10000) -> int:
    for user_id in range(start, start + limit):
        route = shard_route_for_key(ctx, user_id)
        if route["shards"] == {shard_name}:
            return user_id
    raise RuntimeError(f"Не удалось найти shard key, который маршрутизируется только в {shard_name}")


def show_distribution(ctx: TestContext) -> None:
    stats = ctx.db.command({"collStats": COLLECTION_NAME})
    print("Распределение коллекции по shard'ам:")
    shards = stats.get("shards", {})
    if not shards:
        print(json.dumps(stats, indent=2, default=str)[:4000])
        return
    for shard_name, shard_stats in shards.items():
        print(
            f"  {shard_name}: count={shard_stats.get('count')}, "
            f"size={shard_stats.get('size')}, storageSize={shard_stats.get('storageSize')}"
        )


def prepare_collection(ctx: TestContext) -> None:
    heading("1. Подготовка sharded collection")
    wait_for_cluster(ctx)
    ok(f"Кластер отвечает через mongos; текущий router: {router_host(ctx)}")

    shards = list_shards(ctx)
    print("Зарегистрированные shard'ы:")
    for shard in shards:
        print(f"  {shard.get('_id')}: {shard.get('host')}")

    ctx.collection.drop()
    ok(f"Старая {DB_NAME}.{COLLECTION_NAME} удалена (если существовала)")

    # Explicitly create supporting shard-key index so the example also teaches indexes.
    ctx.collection.create_index([("user_id", HASHED)], name="user_id_hashed")
    ctx.client.admin.command(
        {
            "shardCollection": f"{DB_NAME}.{COLLECTION_NAME}",
            "key": {"user_id": "hashed"},
        }
    )
    ok("Коллекция зашардирована по {user_id: 'hashed'}")

    # Determine deterministic keys that target one shard each before inserting data.
    shard1_key = find_key_for_shard(ctx, "shard1")
    shard2_key = find_key_for_shard(ctx, "shard2", start=shard1_key + 1)
    ctx.shard_keys["shard1"] = shard1_key
    ctx.shard_keys["shard2"] = shard2_key
    # Precompute extra targeted keys while the whole cluster is healthy.
    # During failure scenarios we should not need an explain against a broken shard.
    ctx.shard_keys["shard1_failover_write"] = find_key_for_shard(ctx, "shard1", start=3_000_000)
    ctx.shard_keys["shard1_no_majority_write"] = find_key_for_shard(ctx, "shard1", start=4_000_000)
    ctx.shard_keys["shard2_survive_write"] = find_key_for_shard(ctx, "shard2", start=5_000_000)
    info(f"Ключ для shard1: user_id={shard1_key}")
    info(f"Ключ для shard2: user_id={shard2_key}")

    docs = []
    cities = ["Batumi", "Tbilisi", "Moscow", "Kazan"]
    for i in range(1, 1001):
        docs.append(
            {
                "user_id": i,
                "name": f"User {i}",
                "age": 18 + (i % 50),
                "city": cities[i % len(cities)],
                "email": f"user{i}@example.test",
                "score": i % 101,
            }
        )

    result = ctx.majority_collection.insert_many(docs, ordered=False)
    ok(f"insert_many: записано {len(result.inserted_ids)} документов с w='majority'")

    # Additional application indexes. The hashed shard-key index already exists.
    ctx.collection.create_index([("age", ASCENDING)], name="age_1")
    ctx.collection.create_index(
        [("city", ASCENDING), ("age", DESCENDING)],
        name="city_1_age_-1",
    )
    ctx.collection.create_index([("email", ASCENDING)], name="email_1")
    ok("Созданы индексы age_1, city_1_age_-1, email_1")

    show_distribution(ctx)


def basic_crud_and_indexes(ctx: TestContext) -> None:
    heading("2. CRUD, find(), индексы и explain()")

    key = ctx.shard_keys["shard1"]
    user = ctx.collection.find_one({"user_id": key})
    print("find_one:", user)

    update = ctx.majority_collection.update_one(
        {"user_id": key},
        {"$set": {"checked": True}, "$inc": {"score": 1}},
    )
    ok(f"update_one: matched={update.matched_count}, modified={update.modified_count}")

    temp_id = find_key_for_shard(ctx, "shard2", start=2_000_000)
    insert = ctx.majority_collection.insert_one(
        {
            "user_id": temp_id,
            "name": "Temporary user",
            "age": 30,
            "city": "Batumi",
            "email": f"temporary-{temp_id}@example.test",
        }
    )
    ok(f"insert_one: _id={insert.inserted_id}; route={shard_route_for_key(ctx, temp_id)['shards']}")

    delete = ctx.majority_collection.delete_one({"user_id": temp_id})
    ok(f"delete_one: deleted={delete.deleted_count}")

    print("\nИндексы:")
    for index in ctx.collection.list_indexes():
        print(" ", index.get("name"), index.get("key"))

    explain = ctx.db.command(
        {
            "explain": {
                "find": COLLECTION_NAME,
                "filter": {"city": "Batumi", "age": {"$gte": 30}},
            },
            "verbosity": "executionStats",
        }
    )
    stats = explain.get("executionStats", {})
    print("\nexplain для {city: 'Batumi', age: {$gte: 30}}:")
    print("  nReturned:", stats.get("nReturned"))
    print("  totalDocsExamined:", stats.get("totalDocsExamined"))
    print("  totalKeysExamined:", stats.get("totalKeysExamined"))
    indexes_used = sorted(set(str(v) for v in recursive_values(explain, "indexName")))
    print("  indexesUsed:", indexes_used)

    print("\nМаршрутизация чтения по shard key:")
    for shard_name in ("shard1", "shard2"):
        k = ctx.shard_keys[shard_name]
        primary_route = shard_route_for_key(ctx, k, ReadPreference.PRIMARY)
        print(f"  user_id={k}, primary read -> {primary_route}")
        try:
            secondary_route = shard_route_for_key(ctx, k, ReadPreference.SECONDARY)
            print(f"  user_id={k}, secondary read -> {secondary_route}")
        except PyMongoError as exc:
            warn(f"secondary explain для {shard_name} не выполнен: {type(exc).__name__}: {exc}")


def try_operation(label: str, func) -> tuple[bool, Any]:
    started = time.monotonic()
    try:
        result = func()
        elapsed = time.monotonic() - started
        ok(f"{label}: SUCCESS ({elapsed:.2f}s) -> {result}")
        return True, result
    except Exception as exc:
        elapsed = time.monotonic() - started
        warn(f"{label}: ERROR ({elapsed:.2f}s) -> {type(exc).__name__}: {exc}")
        return False, exc


def scenario_mongos_failover(ctx: TestContext) -> None:
    heading("3. Отказ mongos1: клиент должен продолжить через mongos2")
    before = router_host(ctx)
    info(f"Router перед отказом: {before}")
    stop_services(ctx, ["mongos1"])
    try:
        wait_for_cluster(ctx, timeout=20)
        after = router_host(ctx)
        ok(f"После остановки mongos1 кластер отвечает. Router: {after}")
        try_operation(
            "find через оставшийся mongos",
            lambda: ctx.collection.find_one({"user_id": ctx.shard_keys["shard2"]}),
        )
    finally:
        start_services(ctx, ["mongos1"])
        wait_for_cluster(ctx)


def scenario_all_mongos_down(ctx: TestContext) -> None:
    heading("4. Падение обоих mongos: routing layer недоступен")
    victims = ["mongos1", "mongos2"]
    stop_services(ctx, victims)
    try:
        try_operation("cluster ping без mongos", lambda: ctx.client.admin.command("ping"))
    finally:
        start_services(ctx, victims)
        wait_for_cluster(ctx, timeout=60)


def scenario_shard_primary_failover(ctx: TestContext) -> None:
    heading("5. Падение PRIMARY shard1rs: election и продолжение работы")
    print_replica_set(ctx, "shard1rs")
    old_primary = current_primary(ctx, "shard1rs")
    if not old_primary:
        warn("Не удалось определить PRIMARY shard1rs через connPoolStats; сценарий пропущен")
        return

    info(f"Текущий PRIMARY shard1rs: {old_primary}")
    stop_services(ctx, [old_primary])
    try:
        new_primary = wait_for_new_primary(ctx, "shard1rs", old_primary, timeout=45)
        ok(f"Новый PRIMARY shard1rs: {new_primary}")
        print_replica_set(ctx, "shard1rs")

        key = ctx.shard_keys["shard1"]
        try_operation(
            "targeted read с shard1 после election",
            lambda: ctx.collection.find_one({"user_id": key}),
        )

        new_key = ctx.shard_keys["shard1_failover_write"]
        try_operation(
            "targeted majority write на shard1 после election",
            lambda: ctx.majority_collection.insert_one(
                {
                    "user_id": new_key,
                    "name": "After shard1 failover",
                    "age": 40,
                    "city": "Batumi",
                    "email": f"failover-{new_key}@example.test",
                }
            ).inserted_id,
        )
    finally:
        start_services(ctx, [old_primary])
        wait_for_cluster(ctx)
        time.sleep(3)


def scenario_shard_majority_loss(ctx: TestContext) -> None:
    heading("6. Потеря majority одного shard: 1 из 3 узлов остаётся")
    print_replica_set(ctx, "shard1rs")
    primary = current_primary(ctx, "shard1rs")
    secs = secondaries(ctx, "shard1rs")
    if not primary or not secs:
        warn("Не удалось определить PRIMARY/SECONDARY shard1rs; сценарий пропущен")
        return

    victims = [primary, secs[0]]
    survivor = next(
        service
        for service in ["shard1a", "shard1b", "shard1c"]
        if service not in victims
    )
    info(f"Останавливаем {victims}; остаётся {survivor}")
    stop_services(ctx, victims)
    try:
        # Primary that loses majority normally steps down after election timeout.
        time.sleep(12)
        print_replica_set(ctx, "shard1rs")
        key1 = ctx.shard_keys["shard1"]
        key2 = ctx.shard_keys["shard2"]

        try_operation(
            "read PRIMARY по данным shard1 без majority",
            lambda: ctx.collection.find_one({"user_id": key1}),
        )

        secondary_collection = ctx.collection.with_options(
            read_preference=ReadPreference.SECONDARY_PREFERRED
        )
        try_operation(
            "read secondaryPreferred по данным shard1 без majority",
            lambda: secondary_collection.find_one({"user_id": key1}, max_time_ms=5000),
        )

        new_key = ctx.shard_keys["shard1_no_majority_write"]
        try_operation(
            "majority write в shard1 без majority",
            lambda: ctx.majority_collection.insert_one(
                {
                    "user_id": new_key,
                    "name": "Should fail without majority",
                    "age": 33,
                    "city": "Batumi",
                    "email": f"no-majority-{new_key}@example.test",
                }
            ).inserted_id,
        )

        try_operation(
            "targeted read в исправный shard2",
            lambda: ctx.collection.find_one({"user_id": key2}),
        )
    finally:
        start_services(ctx, victims)
        wait_for_cluster(ctx)
        time.sleep(5)


def scenario_entire_shard_down(ctx: TestContext) -> None:
    heading("7. Полное падение shard1rs")
    victims = ["shard1a", "shard1b", "shard1c"]
    stop_services(ctx, victims)
    try:
        time.sleep(3)
        key1 = ctx.shard_keys["shard1"]
        key2 = ctx.shard_keys["shard2"]

        try_operation(
            "targeted read в недоступный shard1",
            lambda: ctx.collection.find_one({"user_id": key1}, max_time_ms=5000),
        )

        try_operation(
            "targeted read в доступный shard2",
            lambda: ctx.collection.find_one({"user_id": key2}, max_time_ms=5000),
        )

        write_key = ctx.shard_keys["shard2_survive_write"]
        try_operation(
            "targeted write в доступный shard2",
            lambda: ctx.majority_collection.insert_one(
                {
                    "user_id": write_key,
                    "name": "Shard2 survives",
                    "age": 29,
                    "city": "Tbilisi",
                    "email": f"shard2-alive-{write_key}@example.test",
                }
            ).inserted_id,
        )

        try_operation(
            "broadcast find без allowPartialResults",
            lambda: list(ctx.collection.find({}).limit(20)),
        )

        def partial_find():
            response = ctx.db.command(
                {
                    "find": COLLECTION_NAME,
                    "filter": {},
                    "limit": 20,
                    "allowPartialResults": True,
                }
            )
            cursor = response.get("cursor", {})
            return {
                "partialResultsReturned": cursor.get("partialResultsReturned", False),
                "documents": len(cursor.get("firstBatch", [])),
            }

        try_operation("broadcast find с allowPartialResults", partial_find)
    finally:
        start_services(ctx, victims)
        wait_for_cluster(ctx)
        time.sleep(5)


def scenario_config_primary_failover(ctx: TestContext) -> None:
    heading("8. Падение PRIMARY configrs")
    print_replica_set(ctx, "configrs")
    primary = current_primary(ctx, "configrs")
    if not primary:
        warn("Не удалось определить PRIMARY configrs; сценарий пропущен")
        return

    stop_services(ctx, [primary])
    try:
        new_primary = wait_for_new_primary(ctx, "configrs", primary, timeout=45)
        ok(f"Новый PRIMARY configrs: {new_primary}")
        try_operation(
            "обычный targeted read после configrs failover",
            lambda: ctx.collection.find_one({"user_id": ctx.shard_keys["shard2"]}),
        )
    finally:
        start_services(ctx, [primary])
        wait_for_cluster(ctx)
        time.sleep(3)


def scenario_config_majority_loss(ctx: TestContext) -> None:
    heading("9. Потеря majority configrs: расширенный сценарий")
    primary = current_primary(ctx, "configrs")
    secs = secondaries(ctx, "configrs")
    if not primary or not secs:
        warn("Не удалось определить PRIMARY/SECONDARY configrs; сценарий пропущен")
        return

    victims = [primary, secs[0]]
    info("Останавливаем majority configrs: " + ", ".join(victims))
    stop_services(ctx, victims)
    try:
        time.sleep(12)
        # Existing CRUD may continue for some time using cached routing metadata,
        # while metadata/DDL operations require the config server replica set.
        try_operation(
            "targeted read при потере majority configrs",
            lambda: ctx.collection.find_one({"user_id": ctx.shard_keys["shard2"]}, max_time_ms=5000),
        )
        try_operation(
            "targeted write при потере majority configrs",
            lambda: ctx.majority_collection.update_one(
                {"user_id": ctx.shard_keys["shard2"]},
                {"$inc": {"score": 1}},
            ).modified_count,
        )
        try_operation(
            "DDL createIndex при потере majority configrs",
            lambda: ctx.collection.create_index([("config_majority_test", ASCENDING)]),
        )
    finally:
        start_services(ctx, victims)
        wait_for_cluster(ctx, timeout=60)
        time.sleep(5)


def final_state(ctx: TestContext) -> None:
    heading("10. Итоговое состояние")
    wait_for_cluster(ctx)
    ok(f"Cluster ping OK; router={router_host(ctx)}")
    for rs in ("configrs", "shard1rs", "shard2rs"):
        try:
            print_replica_set(ctx, rs)
        except PyMongoError as exc:
            warn(f"Не удалось получить {rs}: {exc}")
    show_distribution(ctx)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MongoDB sharded cluster functional + failover laboratory"
    )
    parser.add_argument(
        "--uri",
        default=DEFAULT_URI,
        help="MongoDB URI. По умолчанию содержит оба mongos.",
    )
    parser.add_argument(
        "--compose-file",
        default="docker-compose.yml",
        help="Путь к docker-compose.yml",
    )
    parser.add_argument(
        "--no-chaos",
        action="store_true",
        help="Выполнить только CRUD/index/sharding проверки, не останавливать контейнеры.",
    )
    parser.add_argument(
        "--skip-config-failover",
        action="store_true",
        help="Не останавливать PRIMARY configrs.",
    )
    parser.add_argument(
        "--include-config-majority-loss",
        action="store_true",
        help="Дополнительно остановить 2 из 3 config server и проверить поведение CRUD/DDL.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    compose_file = Path(args.compose_file).resolve()
    if not compose_file.exists():
        print(f"Compose file not found: {compose_file}", file=sys.stderr)
        return 2

    client = MongoClient(
        args.uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=3000,
        socketTimeoutMS=10000,
        retryWrites=True,
        retryReads=True,
    )
    ctx = TestContext(
        client=client,
        compose_file=compose_file,
        stopped_services=set(),
        shard_keys={},
    )

    try:
        prepare_collection(ctx)
        basic_crud_and_indexes(ctx)

        if not args.no_chaos:
            scenario_mongos_failover(ctx)
            scenario_all_mongos_down(ctx)
            scenario_shard_primary_failover(ctx)
            scenario_shard_majority_loss(ctx)
            scenario_entire_shard_down(ctx)
            if not args.skip_config_failover:
                scenario_config_primary_failover(ctx)
            if args.include_config_majority_loss:
                scenario_config_majority_loss(ctx)

        final_state(ctx)
        heading("ГОТОВО")
        print("Лаборатория завершена. Все остановленные скриптом сервисы восстановлены.")
        return 0

    except KeyboardInterrupt:
        warn("Прервано пользователем")
        return 130
    except Exception as exc:
        fail(f"Лаборатория завершилась ошибкой: {type(exc).__name__}: {exc}")
        return 1
    finally:
        try:
            restore_everything(ctx)
        except Exception as exc:
            fail(f"Не удалось полностью восстановить Docker-сервисы: {exc}")
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
```

---

# 27. Что делает Python-лаборатория

Скрипт состоит из двух больших частей:

```text
FUNCTIONAL TESTS
+
CHAOS / FAILOVER TESTS
```

## Functional tests

Скрипт:

1. подключается через оба `mongos`;
2. проверяет `ping`;
3. получает `listShards`;
4. удаляет старую тестовую коллекцию;
5. создаёт hashed index по `user_id`;
6. делает коллекцию sharded;
7. находит shard key, маршрутизирующийся в `shard1`, и другой ключ для `shard2`;
8. вставляет 1000 документов;
9. использует `w: "majority"`;
10. создаёт дополнительные индексы;
11. показывает распределение по shard'ам;
12. делает `find_one`;
13. делает `update_one`;
14. делает `insert_one`;
15. делает `delete_one`;
16. выводит список индексов;
17. запускает `explain("executionStats")`;
18. показывает, какой shard и какой replica member обрабатывает targeted query.

---

# 28. Почему используется hashed shard key

```python
collection.create_index(
    [("user_id", HASHED)],
    name="user_id_hashed"
)
```

и:

```python
client.admin.command(
    {
        "shardCollection": "cluster_lab.users",
        "key": {"user_id": "hashed"}
    }
)
```

Hashed sharding нужен, чтобы значения вроде:

```text
1
2
3
4
5
...
```

не создавали постоянно растущий hot range.

MongoDB хеширует `user_id` и распределяет keyspace между shard'ами.

---

# 29. Дополнительные индексы

Скрипт создаёт:

```python
age_1
city_1_age_-1
email_1
```

Пример compound index:

```python
[("city", ASCENDING), ("age", DESCENDING)]
```

Он предназначен для запросов вроде:

```python
{"city": "Batumi", "age": {"$gte": 30}}
```

`explain()` показывает:

```text
nReturned
totalDocsExamined
totalKeysExamined
indexName
```

Это позволяет увидеть не просто «запрос работает», а какой query plan использовала MongoDB.

---

# 30. Как определяется, на каком shard лежит ключ

Скрипт запускает MongoDB `explain` для targeted query:

```python
{
    "find": "users",
    "filter": {"user_id": user_id}
}
```

В sharded `explain` MongoDB возвращает для затронутых shard'ов:

```text
shardName
serverInfo.host
```

Поэтому можно определить:

```text
user_id=X -> shard1 -> shard1b
```

или:

```text
user_id=Y -> shard2 -> shard2a
```

Это лучше, чем пытаться подключаться к shard напрямую.

---

# 31. Как скрипт видит PRIMARY и SECONDARY

Используется:

```python
client.admin.command("connPoolStats")
```

`mongos` держит topology information о replica set'ах.

Скрипт анализирует:

```text
configrs
shard1rs
shard2rs
```

и печатает приблизительно:

```text
shard1rs:
  shard1a:27018   PRIMARY
  shard1b:27018   SECONDARY
  shard1c:27018   SECONDARY
```

После failover можно увидеть изменение:

```text
до:
shard1a PRIMARY

после:
shard1b PRIMARY
```

---

# 32. Как Python управляет Docker

Используется стандартный модуль:

```python
subprocess
```

Например:

```python
subprocess.run([
    "docker",
    "compose",
    "-f",
    ".../docker-compose.yml",
    "stop",
    "shard1a"
])
```

То есть Python не использует Docker SDK.

Он вызывает ту же CLI-команду, которую ты сам ввёл бы в shell:

```bash
docker compose stop shard1a
```

Для восстановления:

```bash
docker compose start shard1a
```

---

# 33. Почему `finally` критически важен

В конце:

```python
finally:
    restore_everything(ctx)
```

Если:

- тест завершился успешно;
- MongoDB вернула ошибку;
- Python выбросил exception;
- пользователь нажал `Ctrl+C`;

скрипт всё равно пытается вернуть остановленные сервисы.

Это не стопроцентная гарантия против, например, `kill -9` самого Python процесса или выключения компьютера, но защищает от обычных ошибок сценария.

---

# 34. Сценарий №1 — падение одного mongos

Скрипт:

```text
mongos1 STOP
mongos2 UP
```

Connection string содержит оба router'а.

Ожидается:

```text
Python
   X--> mongos1
   |
   +--> mongos2 -> cluster
```

Чтение должно продолжиться.

После проверки:

```text
mongos1 START
```

---

# 35. Сценарий №2 — падение обоих mongos

```text
mongos1 STOP
mongos2 STOP
```

При этом сами:

```text
configrs
shard1rs
shard2rs
```

могут быть полностью исправны.

Но приложение не имеет routing layer:

```text
Python -X-> mongos
```

Поэтому `ping` через обычный connection string должен завершиться ошибкой server selection.

После проверки оба router возвращаются.

Это показывает важное различие:

```text
DATA LAYER может быть healthy,
но без ROUTING LAYER приложение всё равно недоступно.
```

---

# 36. Сценарий №3 — падает PRIMARY одного shard

Сначала скрипт определяет:

```text
shard1rs PRIMARY = shard1a
```

Затем:

```bash
docker compose stop shard1a
```

Остаётся:

```text
shard1b
shard1c
```

Это:

```text
2 из 3 voting members
```

то есть majority существует.

Replica set запускает election:

```text
shard1b -> PRIMARY
```

или:

```text
shard1c -> PRIMARY
```

Во время election возможна краткая пауза записи.

После появления нового PRIMARY targeted read/write должны продолжиться.

---

# 37. Почему новый PRIMARY вообще может появиться

Для replica set из трёх voting nodes:

```text
majority = 2
```

После потери одного:

```text
2 / 3 alive
```

Оставшиеся имеют большинство и способны провести election.

---

# 38. Сценарий №4 — потеря majority shard

Скрипт останавливает:

```text
PRIMARY
+
один SECONDARY
```

Остаётся один процесс:

```text
1 / 3
```

Majority отсутствует.

Следовательно, replica set не может иметь рабочий PRIMARY.

## Что проверяется

### Default read

Default:

```text
readPreference = primary
```

PRIMARY отсутствует — targeted read в этот shard должен быть недоступен.

### `secondaryPreferred`

Оставшийся member может продолжать существовать как SECONDARY.

Поэтому read с:

```python
ReadPreference.SECONDARY_PREFERRED
```

может быть доступен.

Но это read с SECONDARY:

- он может быть stale;
- он не означает, что shard способен принимать записи.

Скрипт не жёстко «угадывает» ответ, а выводит фактический результат операции.

### Write

Без PRIMARY запись невозможна.

`w: "majority"` дополнительно требует подтверждения majority.

### Другой shard

`shard2rs` остаётся healthy.

Targeted query, который `mongos` может направить только в `shard2`, должен иметь шанс работать независимо от недоступного `shard1`.

---

# 39. Сценарий №5 — полностью падает shard1

```text
shard1a STOP
shard1b STOP
shard1c STOP
```

Весь `shard1` недоступен.

Проверяются четыре класса операций.

## Targeted read -> shard1

Недоступен.

## Targeted read -> shard2

Может работать, потому что этот запрос не требует обращения в shard1.

## Targeted write -> shard2

Может работать.

Это очень важное свойство sharded cluster:

```text
падение одного shard не обязательно делает недоступными данные других shard'ов.
```

## Broadcast query

Например:

```python
find({})
```

требует данных со всех shard'ов.

Если один shard недоступен, обычный запрос не может гарантировать полный результат и обычно возвращает ошибку.

---

# 40. `allowPartialResults`

Скрипт дополнительно выполняет raw `find`:

```python
{
    "find": "users",
    "filter": {},
    "allowPartialResults": True
}
```

При недоступном shard MongoDB может вернуть документы из оставшихся shard'ов.

В ответе проверяется:

```text
cursor.partialResultsReturned
```

Это принципиально другой контракт:

```text
обычный find:
"дай полный корректный результат или ошибку"

allowPartialResults:
"если часть shard'ов недоступна — верни то, что смог получить"
```

Для обычной бизнес-логики такой режим нельзя включать без понимания, что результат может быть неполным.

---

# 41. Сценарий №6 — падение PRIMARY configrs

Config server тоже replica set:

```text
configsvr1
configsvr2
configsvr3
```

Скрипт пытается определить текущий PRIMARY и остановить его.

Если остаётся:

```text
2 / 3
```

configrs способен провести election.

После появления нового config PRIMARY проверяется обычное чтение пользовательских данных.

Config server хранит metadata, а не сами документы `cluster_lab.users`.

---

# 42. Расширенный сценарий — потеря majority configrs

Он не включён по умолчанию и запускается флагом:

```bash
./mongo_cluster_lab.py --include-config-majority-loss
```

Скрипт останавливает 2 из 3 config servers.

Проверяются:

1. targeted read существующих данных;
2. targeted write существующих данных;
3. DDL `createIndex`.

Здесь особенно интересно **наблюдаемое** поведение.

`mongos` кеширует routing metadata, поэтому часть операций с уже известной topology может некоторое время вести себя иначе, чем metadata/DDL operations.

Скрипт именно измеряет результат и печатает `SUCCESS` или конкретное MongoDB exception вместо того, чтобы заранее скрывать эту разницу.

---

# 43. Read Preference, которые нужно знать

## `primary`

```text
читать только с PRIMARY
```

Default.

Плюсы:

- самая простая consistency-модель;
- read-your-own-write проще обеспечить.

Минус:

- read load идёт на PRIMARY.

## `primaryPreferred`

```text
PRIMARY, а если его нет -> SECONDARY
```

## `secondary`

```text
только SECONDARY
```

Удобно для отчётности/ETL, когда допустимо небольшое отставание.

## `secondaryPreferred`

```text
предпочитать SECONDARY,
но при их отсутствии можно использовать PRIMARY
```

## `nearest`

Выбирает подходящего member по latency window независимо от PRIMARY/SECONDARY.

---

# 44. Write Concern

Лаборатория использует:

```python
WriteConcern(
    w="majority",
    wtimeout=5000
)
```

Смысл:

```text
успешный ответ только когда запись подтверждена majority
```

В replica set из 3 data-bearing members обычно:

```text
majority = 2
```

Поэтому:

```text
3/3 -> write possible
2/3 -> write possible
1/3 -> majority write impossible
```

`wtimeout=5000` ограничивает ожидание подтверждения.

---

# 45. Почему `w: 1` и `w: majority` ведут себя по-разному

`w: 1`:

```text
PRIMARY применил запись -> клиент может получить ACK
```

Если PRIMARY умрёт до репликации этой записи и произойдёт rollback, такой ACK не гарантирует majority durability.

`w: majority` сильнее:

```text
запись должна попасть на majority replica set
```

Для лаборатории отказоустойчивости это более показательная настройка.

---

# 46. Как запускать

Из каталога с Compose:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Если файл executable:

```bash
chmod +x mongo_cluster_lab.py
```

Полный тест:

```bash
./mongo_cluster_lab.py
```

Если Compose называется иначе:

```bash
./mongo_cluster_lab.py   --compose-file docker-compose.yml
```

---

# 47. Только CRUD/индексы без остановки контейнеров

```bash
./mongo_cluster_lab.py --no-chaos
```

Этот режим:

- создаёт sharded collection;
- вставляет документы;
- выполняет CRUD;
- создаёт индексы;
- показывает distribution;
- делает `explain`;

но не выполняет `docker compose stop`.

---

# 48. Полный chaos test

```bash
./mongo_cluster_lab.py
```

Проверяются:

```text
1. один mongos down
2. оба mongos down
3. PRIMARY shard down
4. shard теряет majority
5. весь shard down
6. configrs PRIMARY down
```

---

# 49. Максимальный вариант

```bash
./mongo_cluster_lab.py   --include-config-majority-loss
```

Дополнительно:

```text
2 из 3 config server down
```

---

# 50. Что должно быть перед запуском Python

Проверить:

```bash
docker compose ps -a
```

Должны работать:

```text
configsvr1
configsvr2
configsvr3

shard1a
shard1b
shard1c

shard2a
shard2b
shard2c

mongos1
mongos2
```

А init-контейнеры должны быть:

```text
Exited (0)
```

Проверить оба router:

```bash
nc -vz 127.0.0.1 27017
nc -vz 127.0.0.1 27018
```

---

# 51. Что Python-скрипт намеренно НЕ делает

Он не удаляет Docker volumes.

Нет:

```bash
docker compose down -v
```

Он не выполняет произвольные direct writes в shard nodes.

Нет обычной клиентской схемы:

```text
Python -> shard1a
```

Все cluster-level операции выполняются:

```text
Python -> mongos
```

Это принципиально правильная точка входа в sharded cluster.

---

# 52. Важное ограничение лабораторной отказоустойчивости

Логически у нас:

```text
3 config nodes
3 shard1 nodes
3 shard2 nodes
2 mongos
```

Но физически всё находится на **одном компьютере и одном Docker Engine**.

Поэтому этот стенд демонстрирует:

- process/container failure;
- MongoDB election;
- replica set majority;
- failover;
- router failure;
- shard failure.

Но он не защищает от:

```text
выключился ноутбук
сломался диск
упал Docker daemon
сломалась host network
```

Потому что тогда одновременно исчезнут все контейнеры.

Настоящая production HA требует размещать replica members на разных failure domains/hosts.

---

# 53. Что стоит наблюдать во время теста вручную

В отдельном терминале:

```bash
watch -n 1 'docker compose ps'
```

Также можно смотреть логи:

```bash
docker compose logs -f shard1a shard1b shard1c
```

Во время election особенно интересно видеть:

```text
PRIMARY -> DOWN
SECONDARY -> PRIMARY
```

---

# 54. Полезные команды для ручной проверки

Кластер:

```bash
docker compose ps -a
```

Логи:

```bash
docker compose logs --tail=100 mongos1
```

Войти в mongos:

```bash
docker compose exec mongos1   mongosh "mongodb://admin:admin@127.0.0.1:27017/admin?authSource=admin"
```

Внутри:

```javascript
sh.status()
```

Проверить, что это router:

```javascript
db.hello()
```

У `mongos`:

```text
msg: "isdbgrid"
```

---

# 55. Интерпретация основных результатов

| Сбой | Read данных этого shard | Write данных этого shard | Другой shard |
|---|---|---|---|
| 1 SECONDARY down | Да | Да | Да |
| PRIMARY down, остаётся 2/3 | После election да | После election да | Да |
| 2/3 shard nodes down | `primary` — нет; secondary read может быть возможен | Нет | Да для targeted ops |
| 3/3 shard nodes down | Нет | Нет | Да для targeted ops |
| 1 mongos down | Да через второй | Да через второй | Да |
| 2 mongos down | Клиент не имеет точки входа | Нет | Нет через обычный клиент |
| 1 config server down | Config RS сохраняет majority | Обычно кластер продолжает работу | Да |
| 2 config server down | Metadata layer теряет majority | Поведение части cached operations нужно измерять; DDL особенно затронут | Зависит от операции/cache |

Последняя строка намеренно сформулирована осторожно: именно для этого в расширенном тесте операция выполняется и фиксируется фактический ответ сервера.

---

# 56. Главная ментальная модель

```text
                    CLIENT
                       |
              +--------+--------+
              |                 |
           mongos1           mongos2
              |                 |
              +--------+--------+
                       |
                    configrs
               "карта кластера"
                       |
              +--------+--------+
              |                 |
           shard1rs          shard2rs
              |                 |
      +-------+-------+ +-------+-------+
      |       |       | |       |       |
      A       B       C A       B       C
```

Запрос:

```text
CLIENT
  |
  v
MONGOS
  |
  | routing metadata
  v
CONFIGRS
  |
  v
НУЖНЫЙ SHARD
  |
  v
PRIMARY / SECONDARY по readPreference
```

Запись:

```text
mongos -> shard PRIMARY -> oplog -> SECONDARY + SECONDARY
```

---

# 57. Официальная документация для дальнейшего изучения

- Sharded Cluster Components:
  https://www.mongodb.com/docs/v8.0/core/sharded-cluster-components/

- Config Servers:
  https://www.mongodb.com/docs/v8.0/core/sharded-cluster-config-servers/

- Shards:
  https://www.mongodb.com/docs/v8.0/core/sharded-cluster-shards/

- Replica Set Elections:
  https://www.mongodb.com/docs/v8.0/core/replica-set-elections/

- Read Preference:
  https://www.mongodb.com/docs/v8.0/core/read-preference/

- Write Concern:
  https://www.mongodb.com/docs/v8.0/reference/write-concern/

- Hashed Sharding:
  https://www.mongodb.com/docs/v8.0/core/hashed-sharding/

- Explain Results:
  https://www.mongodb.com/docs/v8.0/reference/explain-results/

- Docker Compose startup order / depends_on:
  https://docs.docker.com/compose/how-tos/startup-order/

---

# 58. Итог

Текущий стенд позволяет одной командой:

```bash
docker compose up -d
```

получить:

```text
secured sharded MongoDB cluster
+ 3-member config replica set
+ 2 × 3-member shard replica set
+ 2 mongos router
+ automatic replica-set bootstrap
+ automatic addShard
+ automatic admin creation
+ persistent volumes
+ healthchecks
```

А `mongo_cluster_lab.py` превращает его уже не просто в инфраструктуру, а в полноценную лабораторию для изучения:

```text
CRUD
indexes
explain
hashed sharding
routing
read preference
write concern
election
failover
loss of majority
partial shard availability
partial query results
mongos redundancy
config server failover
```
