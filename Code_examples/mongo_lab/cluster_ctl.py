"""
Управление контейнерами кластера и интроспекция replica set'ов напрямую,
в обход mongos.

Важное архитектурное решение: для проверки "кто сейчас primary" мы НЕ можем
подключиться к отдельному узлу шарда и пройти аутентификацию тем же admin-
пользователем, что создан через mongos — в шардированном кластере
пользователи, созданные через mongos, хранятся в admin-базе config-серверов
и валидны только при подключении через mongos. Прямое подключение к узлу
шарда требует отдельного "shard local user" (см. MongoDB Security: Users —
Sharded Cluster Users / Shard Local Users), которого в этом стенде никто не
заводил, и заводить не будем, чтобы не трогать compose-файл.

Вместо этого используем команду `hello` (бывший isMaster) — единственную
команду, которая НЕ требует аутентификации даже при включённом --keyFile/
--auth (она специально сделана такой, чтобы драйверы могли делать handshake
до логина). `hello` уже говорит нам всё, что нужно: isWritablePrimary,
secondary, setName, кто сейчас primary с точки зрения этого узла и т.д.
"""

import json
import subprocess
import time

from config import REPLICA_SETS, COMPOSE_PROJECT_DIR

COMPOSE_BASE = ["docker", "compose"]
if COMPOSE_PROJECT_DIR and COMPOSE_PROJECT_DIR != ".":
    COMPOSE_BASE += ["--project-directory", COMPOSE_PROJECT_DIR]


def _run(cmd, timeout=15):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def compose_stop(*services):
    print(f"    [docker] stop:  {', '.join(services)}")
    _run(COMPOSE_BASE + ["stop", *services], timeout=60)


def compose_start(*services):
    print(f"    [docker] start: {', '.join(services)}")
    _run(COMPOSE_BASE + ["start", *services], timeout=60)


def hello(service, port):
    """db.hello() на конкретном узле, без аутентификации. None, если узел
    недоступен (контейнер остановлен / не отвечает)."""
    cmd = COMPOSE_BASE + [
        "exec", "-T", service,
        "mongosh", "--quiet",
        "--host", "127.0.0.1", "--port", str(port),
        "--eval", "JSON.stringify(db.hello())",
    ]
    result = _run(cmd, timeout=8)
    if not result or result.returncode != 0:
        return None
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except ValueError:
        return None


def topology(rs_name):
    """{service_name: hello()-документ или None} по всем узлам набора."""
    return {svc: hello(svc, port) for svc, port in REPLICA_SETS[rs_name]}


def find_primary(rs_name):
    """Имя сервиса текущего primary, либо None, если primary не выбран
    (или недостижим ни с одного из опрошенных узлов)."""
    for svc, info in topology(rs_name).items():
        if info and info.get("isWritablePrimary"):
            return svc
    return None


def reachable_nodes(rs_name):
    return [svc for svc, info in topology(rs_name).items() if info is not None]


def describe_cluster():
    """Короткий отчёт по всем трём replica set'ам: кто жив, кто primary."""
    report = {}
    for rs_name in REPLICA_SETS:
        nodes = topology(rs_name)
        alive = [s for s, i in nodes.items() if i is not None]
        primary = next((s for s, i in nodes.items() if i and i.get("isWritablePrimary")), None)
        report[rs_name] = {"alive": alive, "total": len(nodes), "primary": primary}
    return report


def print_cluster_report(report=None):
    report = report or describe_cluster()
    for rs_name, info in report.items():
        print(f"  {rs_name:10s}  живы: {len(info['alive'])}/{info['total']}"
              f"  ({', '.join(info['alive']) or '-'})"
              f"  primary: {info['primary'] or 'НЕТ'}")


def wait_for(predicate, timeout=60, interval=2, description="condition"):
    """Ждать, пока predicate() не вернёт что-то truthy. Возвращает это
    значение либо None по таймауту."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            value = predicate()
        except Exception:
            value = None
        if value:
            print(f"    [wait] {description}: OK за {time.time()-start:.1f}с")
            return value
        time.sleep(interval)
    print(f"    [wait] {description}: TIMEOUT ({timeout}с)")
    return None
