"""
Базовые операции поверх шардированного кластера — то, что "обычное"
приложение делает через mongos: индексы, CRUD, проверка распределения
чанков по шардам.
"""

import uuid

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.errors import PyMongoError


def ensure_sharded_collection(client, db_name, coll_name):
    """Идемпотентно: enableSharding + hashed-индекс + shardCollection.
    Если коллекция уже шардирована — просто убедится, что индекс на месте.
    Это то, что в самом compose-файле сознательно не сделано: решение о
    shard key — прикладное, а не инфраструктурное."""
    db = client[db_name]
    coll = db[coll_name]

    coll.create_index([("customerId", ASCENDING)])

    admin = client["admin"]
    try:
        admin.command("enableSharding", db_name)
    except PyMongoError as e:
        if "already enabled" not in str(e):
            raise

    try:
        admin.command(
            "shardCollection",
            f"{db_name}.{coll_name}",
            key={"customerId": "hashed"},
        )
        print(f"  коллекция {db_name}.{coll_name} шардирована (hashed: customerId)")
    except PyMongoError as e:
        if "already sharded" in str(e).lower():
            print(f"  коллекция {db_name}.{coll_name} уже шардирована — ок")
        else:
            raise

    return coll


def seed_data(coll, n=200):
    """Насеять n документов с разными customerId, чтобы данные реально
    разъехались по обоим шардам (hashed-ключ на пустой коллекции и так
    пресплитит чанки по шардам, но без данных это не проверить глазами)."""
    docs = [
        {
            "customerId": f"cust-{uuid.uuid4().hex[:8]}",
            "sku": f"SKU{i:04d}",
            "qty": (i % 5) + 1,
            "price": round(9.99 + i * 0.37, 2),
        }
        for i in range(n)
    ]
    coll.insert_many(docs)
    print(f"  вставлено {n} документов")


def shard_distribution(client, db_name, coll_name):
    """Аналог db.<coll>.getShardDistribution() из mongosh — тот же самый
    $collStats, который использует сам mongosh-хелпер под капотом.
    На шардированной коллекции агрегация возвращает один документ на
    каждый шард с полем "shard" и запрошенной статистикой ("count")."""
    coll = client[db_name][coll_name]
    try:
        docs = list(coll.aggregate([{"$collStats": {"count": {}}}]))
    except PyMongoError as e:
        return {"_error": f"{type(e).__name__}: {e}"}
    return {d.get("shard", "?"): d.get("count", "?") for d in docs}


def print_shard_distribution(client, db_name, coll_name):
    dist = shard_distribution(client, db_name, coll_name)
    if not dist:
        print("  коллекция не шардирована или не удалось получить $collStats")
        return
    if "_error" in dist:
        print(f"  не удалось получить распределение по шардам: {dist['_error']}")
        return
    for shard, count in dist.items():
        print(f"    {shard}: {count} документов")


def canary_write_read(coll, read_preference=None, timeout_note=""):
    """Пишет один маркерный документ и сразу читает его обратно.
    Возвращает (ok: bool, detail: str). Ничего не бросает наружу —
    сценарии как раз и хотят видеть падения, а не ловить traceback."""
    marker = str(ObjectId())
    try:
        coll.insert_one({"customerId": "canary", "marker": marker, "kind": "canary"})
    except PyMongoError as e:
        return False, f"WRITE FAILED{timeout_note}: {type(e).__name__}: {e}"

    try:
        target = coll if read_preference is None else coll.with_options(read_preference=read_preference)
        doc = target.find_one({"marker": marker})
        if doc is None:
            return False, "запись прошла, но чтение не вернуло документ (репликация не успела?)"
        return True, "ok"
    except PyMongoError as e:
        return False, f"READ FAILED{timeout_note}: {type(e).__name__}: {e}"


def targeted_find(coll, customer_id):
    """Запрос с фильтром по shard key — mongos должен обратиться только
    к одному шарду."""
    try:
        return True, list(coll.find({"customerId": customer_id}).limit(5))
    except PyMongoError as e:
        return False, f"{type(e).__name__}: {e}"


def scatter_gather_count(coll):
    """Запрос БЕЗ фильтра по shard key — mongos обязан опросить все шарды
    и склеить результат, поэтому падение любого шарда должно быть видно
    именно здесь."""
    try:
        return True, coll.count_documents({})
    except PyMongoError as e:
        return False, f"{type(e).__name__}: {e}"
