"""
Сценарии отказов кластера.

Каждый сценарий — функция scenario_XXX(ctx) -> dict с результатом.
ctx содержит уже открытое pymongo-подключение и шардированную коллекцию.
Каждый сценарий сам восстанавливает то, что сломал, и ждёт возврата
кластера в здоровое состояние — чтобы сценарии были независимы друг от
друга и шли по порядку без ручного вмешательства.

Все "ожидаемые" результаты в комментариях — это то, что *должно*
происходить согласно архитектуре MongoDB, а не гарантия: сам смысл
лабораторной — увидеть, что произойдёт по факту на вашей машине, и
сравнить с этим описанием.
"""

from pymongo import ReadPreference

import cluster_ctl as ctl
import mongo_ops as ops
from config import REPLICA_SETS, MONGOS_SERVICES

ELECTION_TIMEOUT_WAIT = 30  # electionTimeoutMillis по умолчанию 10с, даём запас
RESTORE_WAIT = 60


def _restore(*services):
    ctl.compose_start(*services)
    for svc in services:
        port = _port_of(svc)
        if port:
            ctl.wait_for(lambda svc=svc, port=port: ctl.hello(svc, port),
                         timeout=RESTORE_WAIT, description=f"{svc} снова в сети")


def _port_of(service):
    if service in MONGOS_SERVICES:
        return 27017
    for members in REPLICA_SETS.values():
        for svc, port in members:
            if svc == service:
                return port
    return None


def scenario_baseline(ctx):
    """0. Контрольная точка: все живы, canary write/read проходит,
    печатаем распределение документов по шардам."""
    print("\n=== Сценарий 0: baseline (всё живо) ===")
    ctl.print_cluster_report()
    ok, detail = ops.canary_write_read(ctx["coll"])
    print(f"  canary write/read: {'OK' if ok else 'FAIL'} ({detail})")
    ops.print_shard_distribution(ctx["client"], ctx["db_name"], ctx["coll_name"])
    return {"name": "baseline", "ok": ok, "detail": detail}


def scenario_kill_one_secondary(ctx):
    """1. Убиваем ОДНОГО secondary в shard1rs (не primary).
    Ожидание: набор сохраняет большинство (2 из 3), primary не меняется,
    запись/чтение продолжают работать без сбоев."""
    print("\n=== Сценарий 1: падение одного secondary в shard1rs ===")
    primary_before = ctl.find_primary("shard1rs")
    victims = [s for s, _ in REPLICA_SETS["shard1rs"] if s != primary_before]
    victim = victims[0]
    print(f"  primary сейчас: {primary_before}; останавливаем secondary: {victim}")

    ctl.compose_stop(victim)
    ok, detail = ops.canary_write_read(ctx["coll"])
    print(f"  canary write/read при 2/3 живых узлах: {'OK' if ok else 'FAIL'} ({detail})")
    primary_after = ctl.find_primary("shard1rs")
    print(f"  primary после потери secondary: {primary_after} (не должен был поменяться)")

    _restore(victim)
    return {
        "name": "kill_one_secondary",
        "ok": ok,
        "detail": detail,
        "primary_changed": primary_before != primary_after,
    }


def scenario_kill_primary(ctx):
    """2. Убиваем ТЕКУЩИЙ primary shard1rs.
    Ожидание: оставшиеся 2 узла (кворум 2 из 3 всё ещё есть) выбирают
    нового primary за election_timeout (~до 10-12с). Пока primary не
    выбран — записи в документы с shard key на shard1 будут падать
    по таймауту; после выбора — снова работают."""
    print("\n=== Сценарий 2: падение primary в shard1rs (выборы) ===")
    primary_before = ctl.find_primary("shard1rs")
    print(f"  останавливаем текущий primary: {primary_before}")
    ctl.compose_stop(primary_before)

    new_primary = ctl.wait_for(
        lambda: ctl.find_primary("shard1rs"),
        timeout=ELECTION_TIMEOUT_WAIT,
        description="выбор нового primary в shard1rs",
    )
    ok, detail = ops.canary_write_read(ctx["coll"])
    print(f"  canary write/read после выборов: {'OK' if ok else 'FAIL'} ({detail})")

    _restore(primary_before)
    return {
        "name": "kill_primary",
        "ok": ok,
        "detail": detail,
        "old_primary": primary_before,
        "new_primary": new_primary,
    }


def scenario_kill_majority(ctx):
    """3. Убиваем БОЛЬШИНСТВО shard1rs (primary + 1 secondary, остаётся
    1 живой узел из 3).
    Ожидание: кворума для выборов нет → primary в наборе отсутствует.
    - Запись в документы с shard key на shard1 должна падать
      (NotWritablePrimary / таймаут).
    - Чтение с read_preference=PRIMARY тоже упадёт.
    - Чтение с read_preference=SECONDARY_PREFERRED/NEAREST может
      продолжить работать с оставшегося узла — он как был secondary,
      так и остаётся им (в MongoDB secondary не "разжалуется" сам по
      себе просто из-за потери контакта с большинством), если сам этот
      узел жив и достижим."""
    print("\n=== Сценарий 3: падение БОЛЬШИНСТВА shard1rs (2 из 3) ===")
    all_nodes = [s for s, _ in REPLICA_SETS["shard1rs"]]
    primary = ctl.find_primary("shard1rs")
    others = [s for s in all_nodes if s != primary]
    victims = [primary, others[0]]
    survivor = others[1]
    print(f"  останавливаем: {victims}; должен остаться жив: {survivor}")

    ctl.compose_stop(*victims)
    no_primary = ctl.wait_for(
        lambda: ctl.find_primary("shard1rs") is None,
        timeout=ELECTION_TIMEOUT_WAIT,
        description="исчезновение primary (кворума нет)",
    )

    write_ok, write_detail = ops.canary_write_read(ctx["coll"])
    print(f"  запись/чтение с primary read preference: {'OK (неожиданно!)' if write_ok else 'FAIL (ожидаемо)'} ({write_detail})")

    read_ok, read_detail = ops.canary_write_read(
        ctx["coll"], read_preference=ReadPreference.SECONDARY_PREFERRED,
        timeout_note=" [secondaryPreferred]",
    )
    print(f"  чтение с secondaryPreferred (запись всё равно нужна для canary): "
          f"{'OK' if read_ok else 'FAIL'} ({read_detail})")

    _restore(*victims)
    return {
        "name": "kill_majority",
        "no_primary_confirmed": bool(no_primary),
        "write_with_primary_pref_ok": write_ok,
        "read_with_secondary_pref_ok": read_ok,
    }


def scenario_kill_whole_shard(ctx):
    """4. Убиваем ВСЕ 3 узла shard2rs (весь шард целиком недоступен).
    Ожидание:
    - Точечный запрос по customerId, который хэшируется на shard1 —
      работает (mongos обращается только к shard1).
    - Точечный запрос по customerId, который хэшируется на shard2 —
      падает/висит по таймауту.
    - Запрос БЕЗ фильтра по shard key (scatter-gather) должен упасть
      целиком: mongos обязан получить ответ от каждого шарда, которому
      адресован запрос, чтобы корректно склеить результат."""
    print("\n=== Сценарий 4: полное падение shard2rs (все 3 узла) ===")
    victims = [s for s, _ in REPLICA_SETS["shard2rs"]]
    print(f"  останавливаем весь шард: {victims}")
    ctl.compose_stop(*victims)
    ctl.wait_for(lambda: not ctl.reachable_nodes("shard2rs"),
                 timeout=20, description="shard2rs полностью недостижим")

    scatter_ok, scatter_detail = ops.scatter_gather_count(ctx["coll"])
    print(f"  count_documents({{}}) по всей коллекции (все шарды): "
          f"{'OK (неожиданно)' if scatter_ok else 'FAIL (ожидаемо)'} ({scatter_detail})")

    _restore(*victims)
    return {
        "name": "kill_whole_shard",
        "scatter_gather_ok": scatter_ok,
        "scatter_gather_detail": scatter_detail,
    }


def scenario_kill_config_majority(ctx):
    """5. Убиваем БОЛЬШИНСТВО config server replica set (2 из 3).
    Ожидание (по документации MongoDB): mongos кеширует routing-
    метаданные и продолжает маршрутизировать операции над уже
    существующими шардированными коллекциями по кэшу, даже если
    config-сервера временно недоступны. А вот операции, требующие
    СВЕЖЕЙ записи в конфиг (создание нового шардированного набора,
    сплиты/миграции чанков) — должны начать падать.
    Проверяем обе половины: обычный insert/find в уже существующую
    labdb.orders, и попытку зашардировать новую тестовую коллекцию."""
    print("\n=== Сценарий 5: падение БОЛЬШИНСТВА config server (2 из 3) ===")
    all_nodes = [s for s, _ in REPLICA_SETS["configrs"]]
    primary = ctl.find_primary("configrs")
    others = [s for s in all_nodes if s != primary]
    victims = [primary, others[0]]
    print(f"  останавливаем: {victims}")

    ctl.compose_stop(*victims)
    ctl.wait_for(lambda: ctl.find_primary("configrs") is None,
                 timeout=ELECTION_TIMEOUT_WAIT,
                 description="исчезновение primary в configrs")

    cached_ok, cached_detail = ops.canary_write_read(ctx["coll"])
    print(f"  операции над уже существующей шардированной коллекцией: "
          f"{'OK' if cached_ok else 'FAIL'} ({cached_detail})")

    new_meta_ok = True
    new_meta_detail = "ok"
    try:
        ctx["client"]["admin"].command("enableSharding", "labdb_new_probe")
    except Exception as e:  # noqa: BLE001 — тут любая ошибка = ожидаемый результат
        new_meta_ok = False
        new_meta_detail = f"{type(e).__name__}: {e}"
    print(f"  попытка создать НОВЫЕ метаданные шардирования: "
          f"{'OK (неожиданно)' if new_meta_ok else 'FAIL (ожидаемо)'} ({new_meta_detail})")

    _restore(*victims)
    return {
        "name": "kill_config_majority",
        "cached_ops_ok": cached_ok,
        "new_metadata_ok": new_meta_ok,
    }


def scenario_kill_one_mongos(ctx):
    """6. Убиваем ОДИН из двух mongos.
    Ожидание: клиент подключён сразу к обоим (host list в URI), драйвер
    прозрачно продолжает работать через оставшийся — без вмешательства
    приложения."""
    print("\n=== Сценарий 6: падение одного mongos из двух ===")
    ctl.compose_stop("mongos2")
    ok, detail = ops.canary_write_read(ctx["coll"])
    print(f"  canary write/read с одним живым mongos: {'OK' if ok else 'FAIL'} ({detail})")
    _restore("mongos2")
    return {"name": "kill_one_mongos", "ok": ok, "detail": detail}


ALL_SCENARIOS = [
    scenario_baseline,
    scenario_kill_one_secondary,
    scenario_kill_primary,
    scenario_kill_majority,
    scenario_kill_whole_shard,
    scenario_kill_config_majority,
    scenario_kill_one_mongos,
]
