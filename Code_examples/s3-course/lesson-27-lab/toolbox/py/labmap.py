#!/usr/bin/env python3
"""labmap — смотрит на диски всех endpoint-ов кластера (тома примонтированы read-only в /v).

  labmap ready [A|B]                       готовность узлов (GET /health/ready)
  labmap where A BUCKET KEY [--size N]     на каких endpoint-ах лежат shards объекта
  labmap map   A [BUCKET]                  карта pool -> erasure set -> endpoint + заполнение
  labmap tree  a1-n1 [--depth N]           дерево каталогов одного endpoint-а

Принципиально: скрипт НЕ предполагает, какие узлы образуют erasure set. Он смотрит,
где реально лежат shards, и выводит наборы из наблюдений.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.request

ROOT = os.environ.get("LAB_ROOT", "/v")
NODE_RE = re.compile(r"^([a-z])(\d+)-n(\d+)$")


def fmt(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024
    return str(n)


def list_nodes(cluster=None):
    out = []
    for name in os.listdir(ROOT):
        m = NODE_RE.match(name)
        if not m:
            continue
        c, p, i = m.group(1), int(m.group(2)), int(m.group(3))
        if cluster and c != cluster:
            continue
        out.append((c, p, i, name))
    return sorted(out)


def dir_size(path: str) -> int:
    total = 0
    for dp, _dn, fn in os.walk(path):
        for f in fn:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total


def buckets_of(node: str, only=None):
    base = os.path.join(ROOT, node)
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return []
    res = []
    for n in names:
        if n.startswith("."):
            continue
        if only and n != only:
            continue
        if os.path.isdir(os.path.join(base, n)):
            res.append(n)
    return res


def scan_node(node: str, bucket=None):
    """-> {(bucket, key): байт на этом endpoint-е}. Объект = каталог, в котором лежит xl.meta."""
    objs = {}
    base = os.path.join(ROOT, node)
    for b in buckets_of(node, bucket):
        bdir = os.path.join(base, b)
        for dp, dn, fn in os.walk(bdir):
            if "xl.meta" in fn:
                key = os.path.relpath(dp, bdir)
                objs[(b, key)] = dir_size(dp)
                dn[:] = []
    return objs


# ---------------------------------------------------------------- ready
def cmd_ready(a):
    nodes = list_nodes(a.cluster.lower() if a.cluster else None)

    def probe(n):
        try:
            with urllib.request.urlopen(f"http://{n[3]}:9000/health/ready", timeout=2) as r:
                return n, r.status == 200
        except Exception:
            return n, False

    with cf.ThreadPoolExecutor(32) as ex:
        res = list(ex.map(probe, nodes))
    groups = {}
    for (c, p, i, name), ok in res:
        groups.setdefault((c, p), []).append((name, ok))
    for (c, p), items in sorted(groups.items()):
        up = sum(1 for _n, ok in items if ok)
        bad = [n for n, ok in items if not ok]
        mark = "OK " if not bad else "..."
        print(f"{mark} кластер {c.upper()} pool {p}: готово {up}/{len(items)}" + (f"   не готовы: {', '.join(bad)}" if bad else ""))
    return 0 if all(ok for _n, ok in res) else 1


# ---------------------------------------------------------------- where
def cmd_where(a):
    c = a.cluster.lower()
    nodes = list_nodes(c)
    if not nodes:
        sys.exit(f"нет томов кластера {c} в {ROOT}")
    found = []  # (pool, name, files, size)
    for (_c, p, i, name) in nodes:
        d = os.path.join(ROOT, name, a.bucket, a.key)
        if not os.path.isdir(d):
            continue
        files = []
        for dp, _dn, fn in os.walk(d):
            for f in sorted(fn):
                fp = os.path.join(dp, f)
                files.append((os.path.relpath(fp, d), os.path.getsize(fp)))
        found.append((p, name, files, sum(s for _f, s in files)))
    all_names = [n[3] for n in nodes]
    if a.json:
        pools = {}
        for p, name, _f, _s in found:
            pools.setdefault(p, []).append(name)
        print(json.dumps({
            "cluster": c, "bucket": a.bucket, "key": a.key,
            "pools": {str(k): v for k, v in pools.items()},
            "endpoints": [n for _p, n, _f, _s in found],
            "all_nodes": all_names,
            "total_bytes": sum(s for _p, _n, _f, s in found),
        }, ensure_ascii=False))
        return 0
    print(f"Объект s3://{a.bucket}/{a.key}  (кластер {c.upper()})")
    if not found:
        print("  Не найден ни на одном endpoint-е.")
        print("  Проверь имя бакета/ключа или посмотри раскладку: labmap tree a1-n1 --depth 4")
        return 1
    per_pool_total = {}
    for (_c, p, _i, _n) in nodes:
        per_pool_total[p] = per_pool_total.get(p, 0) + 1
    for pool in sorted({p for p, *_ in found}):
        items = [f for f in found if f[0] == pool]
        print(f"\n  Pool {pool}: shards найдены на {len(items)} из {per_pool_total[pool]} endpoint-ов")
        for _p, name, files, size in items:
            parts = [f for f, _s in files if f != "xl.meta"]
            desc = "xl.meta" + (f" + {len(parts)} part-файл(а)" if parts else " (данные внутри xl.meta)")
            print(f"    {name:<8} {fmt(size):>11}   {desc}")
    total = sum(s for *_x, s in found)
    print(f"\n  Всего на дисках: {fmt(total)}")
    if a.size:
        print(f"  Размер объекта : {fmt(a.size)}  ->  занято в {total / a.size:.2f} раза больше (накладные расходы erasure coding)")
        print("  (схема 4 data + 4 parity даёт ~2.00; EC:2 из 8 дало бы ~1.33)")
    return 0


# ---------------------------------------------------------------- map
class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def cmd_map(a):
    c = a.cluster.lower()
    nodes = list_nodes(c)
    if not nodes:
        sys.exit(f"нет томов кластера {c} в {ROOT}")
    scans = {name: scan_node(name, a.bucket) for (_c, _p, _i, name) in nodes}
    pools = {}
    for (_c, p, i, name) in nodes:
        pools.setdefault(p, []).append((i, name))

    grand = {}
    for p, items in sorted(pools.items()):
        names = [n for _i, n in items]
        dsu = DSU()
        for n in names:
            dsu.find(n)
        by_obj = {}
        for n in names:
            for ok_, size in scans[n].items():
                by_obj.setdefault(ok_, []).append(n)
        for ok_, holders in by_obj.items():
            for h in holders[1:]:
                dsu.union(holders[0], h)
        comps = {}
        for n in names:
            comps.setdefault(dsu.find(n), []).append(n)
        used = {n: sum(scans[n].values()) for n in names}
        has_data = {n: bool(scans[n]) for n in names}
        sets = [sorted(v, key=lambda s: int(s.split("-n")[1])) for v in comps.values() if any(has_data[x] for x in v)]
        sets.sort(key=lambda v: int(v[0].split("-n")[1]))
        empty = [n for n in names if not has_data[n]]
        width = int(os.environ.get("LAB_DRIVES", "0")) or None
        print(f"\n=== Кластер {c.upper()} · pool {p} · {len(names)} endpoint-ов · объектов: {len({k for n in names for k in scans[n]})} ===")
        if not sets:
            print("  данных пока нет")
            continue
        maxu = max(used.values()) or 1
        for si, members in enumerate(sets):
            label = chr(ord("A") + si)
            objs = sorted({k for n in members for k in scans[n]})
            flag = ""
            if width and len(members) != width:
                flag = f"   ! ожидали {width}, найдено {len(members)} (наблюдаемых endpoint-ов, пока мало объектов?)"
            print(f"\n  Set {label}: {len(members)} endpoint-ов, объектов: {len(objs)}{flag}")
            for n in members:
                bar = "█" * int(round(20 * used[n] / maxu))
                print(f"    {n:<8} {bar:<20} {fmt(used[n]):>11}")
            if a.keys and objs:
                shown = ", ".join(f"{b}/{k}" for b, k in objs[: a.keys])
                print(f"    примеры объектов: {shown}")
            grand.setdefault(p, []).append((label, members))
        if empty:
            print(f"\n  Без данных ({len(empty)}): {', '.join(sorted(empty, key=lambda s: int(s.split('-n')[1])))}")
        inter = []
        seen = {}
        for si, members in enumerate(sets):
            for n in members:
                if n in seen:
                    inter.append(n)
                seen[n] = si
        print("  Проверка: наборы не пересекаются (каждый endpoint принадлежит одному set)." if not inter else f"  ! endpoint-ы в нескольких наборах: {inter}")
    return 0


# ---------------------------------------------------------------- tree
def cmd_tree(a):
    base = os.path.join(ROOT, a.node)
    if not os.path.isdir(base):
        sys.exit(f"нет тома {a.node}")

    def walk(path, prefix, depth):
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            return
        for idx, e in enumerate(entries):
            fp = os.path.join(path, e)
            last = idx == len(entries) - 1
            if os.path.isdir(fp):
                print(f"{prefix}{'└── ' if last else '├── '}{e}/")
                if depth > 1:
                    walk(fp, prefix + ("    " if last else "│   "), depth - 1)
            else:
                print(f"{prefix}{'└── ' if last else '├── '}{e}  ({fmt(os.path.getsize(fp))})")

    print(f"/data ({a.node})")
    walk(base, "", a.depth)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ready"); s.add_argument("cluster", nargs="?"); s.set_defaults(f=cmd_ready)
    s = sub.add_parser("where"); s.add_argument("cluster"); s.add_argument("bucket"); s.add_argument("key")
    s.add_argument("--size", type=int, help="исходный размер объекта в байтах"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_where)
    s = sub.add_parser("map"); s.add_argument("cluster"); s.add_argument("bucket", nargs="?")
    s.add_argument("--keys", type=int, default=0, help="показать N примеров ключей в каждом set"); s.set_defaults(f=cmd_map)
    s = sub.add_parser("tree"); s.add_argument("node"); s.add_argument("--depth", type=int, default=3); s.set_defaults(f=cmd_tree)
    a = ap.parse_args()
    sys.exit(a.f(a))


if __name__ == "__main__":
    main()
