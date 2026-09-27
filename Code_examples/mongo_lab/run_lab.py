"""
Лаборатория отказоустойчивости шардированного MongoDB-кластера.

Запуск (из каталога, где лежит docker-compose.yaml, либо с
COMPOSE_PROJECT_DIR=/путь/к/кластеру):

    pip install -r requirements.txt
    python run_lab.py

Что делает:
  1. Подключается к кластеру через оба mongos.
  2. Базовые проверки: индексы, шардирование коллекции, вставка данных,
     распределение документов по шардам, простой find().
  3. Прогоняет по очереди сценарии отказов (см. scenarios.py), каждый раз
     сам "ломая" контейнеры через `docker compose stop`, наблюдая за
     реакцией кластера (через прямой опрос db.hello() на узлах) и
     реакцией приложения (через pymongo), и сам всё восстанавливает перед
     следующим сценарием.
  4. Печатает сводный отчёт по всем сценариям.

Скрипт ничего не меняет в docker-compose.yaml — только управляет уже
поднятыми контейнерами (`docker compose stop/start <service>`).
"""

import sys
import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError

import cluster_ctl as ctl
import mongo_ops as ops
from config import MONGO_URI, DB_NAME, COLLECTION_NAME
from scenarios import ALL_SCENARIOS


def wait_full_health(timeout=120):
    print("\nЖдём, пока весь кластер станет полностью здоров...")

    def all_healthy():
        report = ctl.describe_cluster()
        return all(
            info["primary"] is not None and len(info["alive"]) == info["total"]
            for info in report.values()
        )

    ok = ctl.wait_for(all_healthy, timeout=timeout, description="весь кластер здоров")
    ctl.print_cluster_report()
    return bool(ok)


def main():
    if not wait_full_health(timeout=180):
        print("\nКластер не поднялся полностью за отведённое время — "
              "проверьте `docker compose ps` перед повторным запуском.")
        sys.exit(1)

    print(f"\nПодключаемся к кластеру: {MONGO_URI.split('@')[-1]}")
    client = MongoClient(MONGO_URI)
    try:
        client.admin.command("ping")
    except PyMongoError as e:
        print(f"Не удалось подключиться через mongos: {e}")
        sys.exit(1)
    print("  подключение через mongos установлено")

    print("\n=== Базовые проверки ===")
    coll = ops.ensure_sharded_collection(client, DB_NAME, COLLECTION_NAME)
    if coll.count_documents({}) < 50:
        ops.seed_data(coll, n=200)
    print(f"  документов в коллекции сейчас: {coll.count_documents({})}")
    ops.print_shard_distribution(client, DB_NAME, COLLECTION_NAME)

    ok, sample = ops.targeted_find(coll, coll.find_one()["customerId"])
    print(f"  find() по конкретному customerId: {'OK' if ok else 'FAIL'}, "
          f"найдено {len(sample) if ok else 0} документ(ов)")

    ctx = {
        "client": client,
        "coll": coll,
        "db_name": DB_NAME,
        "coll_name": COLLECTION_NAME,
    }

    results = []
    for scenario in ALL_SCENARIOS:
        results.append(scenario(ctx))
        # даём кластеру немного времени устаканиться перед следующим сценарием
        time.sleep(3)
        wait_full_health(timeout=90)

    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 60)
    for r in results:
        print(f"  {r['name']:24s} -> {r}")

    client.close()


if __name__ == "__main__":
    main()
