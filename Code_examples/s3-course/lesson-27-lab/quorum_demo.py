#!/usr/bin/env python3
"""Опыт с quorum: по одному останавливает endpoint-ы ОДНОГО erasure set и после каждого шага замеряет
чтение известного объекта и запись новых.

Запускать на хосте из каталога лаборатории (рядом с compose.yaml):

    python3 quorum_demo.py --cluster a --bucket lab --key demo/big1.bin --size 4194304

--key — объект, который уже лежит в проверяемом set (его shards и определяют, какие узлы глушить).
Скрипт сам определяет набор по расположению shards и в конце запускает остановленные узлы обратно.
"""
import argparse
import json
import subprocess
import sys
import time


def sh(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"команда {' '.join(cmd)} завершилась с кодом {r.returncode}\n{r.stderr.strip()}")
    return r


def tools(*args, check=True):
    return sh(["docker", "compose", "exec", "-T", "tools", *args], check=check)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cluster", required=True, choices=["a", "b"])
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--size", type=int, help="размер объекта в байтах (проверка целостности GET)")
    ap.add_argument("--put-count", type=int, default=60, help="сколько новых объектов писать на каждом шаге")
    ap.add_argument("--put-size", type=int, default=262144)
    ap.add_argument("--pause", type=float, default=4.0, help="пауза после остановки узла, сек")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    where = json.loads(tools("labmap", "where", a.cluster, a.bucket, a.key, "--json").stdout)
    victims = sorted(where["endpoints"], key=lambda n: (n.split("-")[0], int(n.split("-n")[1])))
    if not victims:
        sys.exit("shards объекта не найдены — проверь --bucket/--key")
    if len(where["pools"]) != 1:
        sys.exit(f"объект найден в нескольких pool-ах: {where['pools']}")
    width = len(victims)
    others = [n for n in where["all_nodes"] if n not in victims]
    entry = others[0]
    pool = next(iter(where["pools"]))

    print(f"Кластер {a.cluster.upper()}, pool {pool}. Set объекта {a.key}: {width} endpoint-ов")
    print("  " + ", ".join(victims))
    print(f"Точка входа для запросов: {entry} (вне проверяемого set)")
    k_data = width // 2
    print(f"По документации RustFS при {width} дисках parity=EC:{width // 2}, data={k_data}: "
          f"чтение нужно >= {k_data} живых shards, запись >= {k_data + 1 if k_data == width - k_data else k_data}.")
    print("Ниже — что получилось на самом деле.\n")

    if a.dry_run:
        for i, v in enumerate(victims, 1):
            print(f"[dry-run] шаг {i}: docker compose --profile {a.cluster} stop -t 2 {v}; замер через {entry}")
        print(f"[dry-run] в конце: docker compose --profile {a.cluster} start {' '.join(victims)}")
        return

    head = f"{'остановлено':>11} {'живых':>6} | {'GET известного объекта':<30} | {'PUT новых объектов':<20} | ошибки PUT"
    print(head)
    print("-" * len(head))
    stopped = []
    ts = int(time.time())
    try:
        for k in range(0, width + 1):
            if k > 0:
                v = victims[k - 1]
                sh(["docker", "compose", "--profile", a.cluster, "stop", "-t", "2", v])
                stopped.append(v)
                time.sleep(a.pause)
            cmd = ["python3", "/lab/probe.py", "--cluster", a.cluster, "--entry", entry, "--bucket", a.bucket,
                   "--get", a.key, "--put-count", str(a.put_count), "--put-size", str(a.put_size),
                   "--prefix", f"quorum-{ts}/stop{k}/"]
            if a.size:
                cmd += ["--expect-size", str(a.size)]
            r = tools(*cmd, check=False)
            try:
                res = json.loads(r.stdout.strip().splitlines()[-1])
            except Exception:
                res = {"fatal": (r.stdout + r.stderr).strip()[-200:]}
            if "fatal" in res:
                print(f"{k:>11} {width - k:>6} | ОШИБКА ЗАМЕРА: {res['fatal']}")
                continue
            g = res["get"]
            gs = "ok" if g["ok"] else f"ОТКАЗ ({g['error']})"
            p = res["put"]
            ps = f"{p['ok']}/{a.put_count} ok"
            es = ", ".join(f"{c} ×{n}" for c, n in p["errors"].items()) or "-"
            print(f"{k:>11} {width - k:>6} | {gs:<30} | {ps:<20} | {es}")
    finally:
        if stopped:
            print("\nЗапускаю остановленные узлы обратно:", " ".join(stopped))
            sh(["docker", "compose", "--profile", a.cluster, "start", *stopped], check=False)
    print("\nНовые объекты опыта лежат под префиксом quorum-%d/ (удалить: s3a s3 rm s3://%s/quorum-%d/ --recursive)."
          % (ts, a.bucket, ts))


if __name__ == "__main__":
    main()
