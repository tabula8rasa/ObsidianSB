#!/usr/bin/env python3
"""Генератор compose.yaml для урока 27.

Строит два независимых кластера RustFS (a и b):
    кластер -> P pool -> S erasure set в каждом pool -> D endpoint в каждом set,
где один endpoint = один контейнер = один Docker volume.

По умолчанию: 2 кластера x 2 pool x 3 set x 8 endpoint = 96 контейнеров RustFS
(+ 1 контейнер tools).

    python3 generate.py                          # 2 x 2 x 3 x 8
    python3 generate.py --pools 2 --sets 1 --drives 4   # мини-стенд на 16 контейнеров
"""
import argparse
from pathlib import Path

CLUSTERS = ["a", "b"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--pools", type=int, default=2, help="pool в каждом кластере (по умолчанию 2)")
    ap.add_argument("--sets", type=int, default=3, help="erasure set в каждом pool (по умолчанию 3)")
    ap.add_argument("--drives", type=int, default=8, help="endpoint в каждом set (по умолчанию 8)")
    ap.add_argument("--out", default="compose.yaml")
    args = ap.parse_args()

    P, S, D = args.pools, args.sets, args.drives
    if not (2 <= D <= 16):
        ap.error("--drives: RustFS допускает от 2 до 16 дисков в erasure set")
    if P < 1 or S < 1:
        ap.error("--pools и --sets должны быть >= 1")
    per_pool = S * D
    if per_pool < 2:
        ap.error("pool должен содержать минимум 2 endpoint-а")

    all_nodes = [
        (c, p, i) for c in CLUSTERS for p in range(1, P + 1) for i in range(1, per_pool + 1)
    ]
    total = len(all_nodes)

    def name(c, p, i):
        return f"{c}{p}-n{i}"

    def pool_expr(c, p):
        # ellipsis-синтаксис RustFS: node{1...24}
        return f"http://{c}{p}-n{{1...{per_pool}}}:9000/data"

    def ports(ci, p):
        s3 = 9000 + 100 * (ci + 1) + 10 * (p - 1)
        return s3, s3 + 1

    L = []
    w = L.append
    w("# СГЕНЕРИРОВАНО generate.py — не редактируй вручную, меняй параметры генератора.")
    w(f"# {len(CLUSTERS)} кластера x {P} pool x {S} erasure set x {D} endpoint = {total} контейнеров RustFS")
    w("name: lesson27")
    w("")

    for ci, c in enumerate(CLUSTERS):
        up = c.upper()
        vols = " ".join(pool_expr(c, p) for p in range(1, P + 1))
        w(f"x-{c}-env: &{c}-env")
        w(f'  RUSTFS_VOLUMES: "{vols}"')
        w('  RUSTFS_ADDRESS: ":9000"')
        w('  RUSTFS_CONSOLE_ADDRESS: ":9001"')
        w('  RUSTFS_CONSOLE_ENABLE: "false"')
        w(f"  RUSTFS_ACCESS_KEY: ${{{up}_ACCESS_KEY:?set in .env}}")
        w(f"  RUSTFS_SECRET_KEY: ${{{up}_SECRET_KEY:?set in .env}}")
        w(f'  RUSTFS_ERASURE_SET_DRIVE_COUNT: "{D}"')
        w('  RUSTFS_OBS_LOGGER_LEVEL: "info"')
        w('  RUSTFS_UNSAFE_BYPASS_DISK_CHECK: "true"')
        w("")

    w("x-node: &node")
    w("  image: rustfs/rustfs:latest")
    w("  restart: unless-stopped")
    w("  stop_grace_period: 5s")
    w("")
    w("services:")

    for ci, c in enumerate(CLUSTERS):
        for p in range(1, P + 1):
            s3, con = ports(ci, p)
            w(f"  # ---- кластер {c.upper()}, pool {p}: {per_pool} endpoint-ов = {S} set x {D} ----")
            for i in range(1, per_pool + 1):
                n = name(c, p, i)
                w(f"  {n}:")
                w("    <<: *node")
                w(f"    hostname: {n}")
                w(f'    profiles: ["{c}"]')
                w("    environment:")
                w(f"      <<: *{c}-env")
                if i == 1:
                    w('      RUSTFS_CONSOLE_ENABLE: "true"')
                    w("    ports:")
                    w(f'      - "127.0.0.1:{s3}:9000"')
                    w(f'      - "127.0.0.1:{con}:9001"')
                w("    volumes:")
                w(f"      - {n}:/data")
            w("")

    w("  tools:")
    w("    build: ./toolbox")
    w("    image: rustfs-lab-tools:27")
    w("    hostname: tools")
    w("    init: true")
    w('    command: ["sleep", "infinity"]')
    w("    environment:")
    for c in CLUSTERS:
        up = c.upper()
        w(f"      {up}_ACCESS_KEY: ${{{up}_ACCESS_KEY:?set in .env}}")
        w(f"      {up}_SECRET_KEY: ${{{up}_SECRET_KEY:?set in .env}}")
    w("      LAB_ROOT: /v")
    w(f"      LAB_DRIVES: \"{D}\"")
    w("    volumes:")
    w("      - ./toolbox/py:/lab:ro")
    for c, p, i in all_nodes:
        n = name(c, p, i)
        w(f"      - {n}:/v/{n}:ro")
    w("")
    w("volumes:")
    for c, p, i in all_nodes:
        w(f"  {name(c, p, i)}:")
    w("")

    Path(args.out).write_text("\n".join(L), encoding="utf-8")
    sets = len(CLUSTERS) * P * S
    print(f"{args.out}: {total} контейнеров RustFS, {len(CLUSTERS) * P} pool-ов, {sets} erasure set-ов по {D} endpoint-ов")


if __name__ == "__main__":
    main()
