"""
Общая конфигурация для mongo_lab.

Ничего не меняет в docker-compose.yaml — только описывает то, что там уже
объявлено (имена сервисов/портов), чтобы скрипты могли:
  1) подключаться к кластеру через mongos как обычный клиент;
  2) дергать docker compose stop/start по именам сервисов;
  3) опрашивать db.hello() на каждом узле напрямую (без аутентификации —
     hello/isMaster специально не требует auth, это handshake-команда).
"""

import os

# --- Подключение приложения к кластеру (через mongos, как и положено) ---
MONGOS_HOSTS = os.environ.get("MONGO_HOSTS", "localhost:27017,localhost:27018")
ADMIN_USER = os.environ.get("MONGO_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("MONGO_ADMIN_PASSWORD", "admin")

MONGO_URI = (
    f"mongodb://{ADMIN_USER}:{ADMIN_PASSWORD}@{MONGOS_HOSTS}/"
    f"?authSource=admin&retryWrites=true"
    f"&serverSelectionTimeoutMS=4000&connectTimeoutMS=4000&socketTimeoutMS=4000"
)

DB_NAME = "labdb"
COLLECTION_NAME = "orders"

# --- Топология кластера (как в docker-compose.yaml) ---
# service_name -> port внутри контейнера
REPLICA_SETS = {
    "configrs": [
        ("configsvr1", 27019),
        ("configsvr2", 27019),
        ("configsvr3", 27019),
    ],
    "shard1rs": [
        ("shard1a", 27018),
        ("shard1b", 27018),
        ("shard1c", 27018),
    ],
    "shard2rs": [
        ("shard2a", 27018),
        ("shard2b", 27018),
        ("shard2c", 27018),
    ],
}

MONGOS_SERVICES = ["mongos1", "mongos2"]

# docker compose должен запускаться из каталога с docker-compose.yaml.
# Если скрипт лежит рядом с ним — ничего указывать не нужно.
COMPOSE_PROJECT_DIR = os.environ.get("COMPOSE_PROJECT_DIR", ".")
