## Что такое namespace

**Namespace** — механизм ядра Linux, который даёт группе процессов отдельное представление определённого системного ресурса.

Важно: нет одного общего namespace, содержащего сразу PID, сеть, mounts и hostname.

Для каждого типа ресурса существуют **отдельные namespace-объекты**:

```text
UTS namespaces:
    UTS #1
    UTS #2

NET namespaces:
    NET #1
    NET #2

PID namespaces:
    PID #1
    PID #2

MNT namespaces:
    MNT #1
    MNT #2
```

Каждый процесс одновременно состоит в одном namespace каждого типа:

```text
Process A
├── UTS → UTS #2
├── NET → NET #1
├── PID → PID #4
├── MNT → MNT #7
└── IPC → IPC #1
```

Два процесса могут разделять один namespace, но находиться в разных namespaces другого типа.

Например:

```text
Process A
├── UTS → UTS #2
├── NET → NET #1
└── MNT → MNT #7

Process B
├── UTS → UTS #2
├── NET → NET #8
└── MNT → MNT #9
```

То есть они видят одинаковый hostname, но разную сеть и разные mount points.

---

## Основные типы namespaces

| Namespace | Что изолирует |
|---|---|
| `mnt` | точки монтирования |
| `pid` | пространство PID процессов |
| `net` | сетевые интерфейсы, IP, маршруты, sockets и сетевой стек |
| `uts` | hostname и domain name |
| `ipc` | IPC-объекты |
| `user` | UID, GID и capabilities |
| `cgroup` | представление cgroup-иерархии |
| `time` | некоторые системные часы |

Namespaces не создают отдельное ядро Linux. Все процессы продолжают работать на одном kernel.

---

## Как посмотреть namespaces процесса

У каждого процесса namespace-ссылки доступны через:

```bash
ls -l /proc/<PID>/ns
```

Для текущего Bash:

```bash
ls -l /proc/$$/ns
```

Например:

```text
uts -> uts:[4026531838]
net -> net:[4026531840]
pid -> pid:[4026531836]
mnt -> mnt:[4026531841]
```

Посмотреть конкретный namespace:

```bash
readlink /proc/$$/ns/uts
```

Если у двух процессов одинаковый namespace ID соответствующего типа, они находятся в одном namespace этого типа.

Список namespaces также можно посмотреть:

```bash
lsns
```

или, например, только UTS:

```bash
sudo lsns -t uts
```

---

# `unshare`

`unshare` — CLI-утилита и одноимённый syscall Linux, позволяющий процессу перестать разделять часть execution context с другими процессами.

Упрощённо:

```text
до:

bash
└── UTS namespace A

unshare --uts

после:

bash
└── UTS namespace B
```

CLI:

```bash
unshare [OPTIONS] [COMMAND]
```

Например:

```bash
sudo unshare --uts bash
```

Упрощённо происходит:

```text
unshare(CLONE_NEWUTS)
        ↓
создан новый UTS namespace
        ↓
exec bash
```

---

## Почему после `sudo unshare --uts bash` shell становится root

Из-за `sudo`, а не из-за `unshare`.

```text
обычный shell
UID=1000
    │
    │ sudo
    ▼
unshare
UID=0
    │
    └── bash
        UID=0
```

`--uts` меняет только UTS namespace и сам по себе не меняет UID.

Проверить:

```bash
id
```

---

# UTS namespace

UTS namespace изолирует:

```text
hostname
domain name
```

Создание:

```bash
sudo unshare --uts bash
```

Проверка нового namespace:

```bash
readlink /proc/$$/ns/uts
```

ID должен отличаться от UTS namespace исходного shell.

## Важный нюанс с `hostnamectl`

Для проверки UTS namespace не стоит использовать:

```bash
hostnamectl
```

`hostnamectl` может обращаться через **D-Bus** к `systemd-hostnamed`.

Получается:

```text
shell в новом UTS namespace
        │
        │ hostnamectl
        ▼
      D-Bus
        │
        ▼
systemd-hostnamed на хосте
        │
        ▼
меняет hostname хостового UTS namespace
```

То есть сам UTS namespace не сломан: изменение выполняет другой процесс, который находится за его пределами.

Для чистого эксперимента нужно вызвать `sethostname()` из процесса внутри namespace.

Например через Python:

```bash
python -c 'import os; os.sethostname(b"container-demo")'
```

Проверить:

```bash
uname -n
```

Во втором обычном терминале hostname хоста останется прежним.

---

# Network namespace

Создать:

```bash
sudo unshare --net bash
```

Посмотреть интерфейсы:

```bash
ip addr
```

Новый network namespace имеет собственные:

```text
network interfaces
IP addresses
routes
sockets
firewall rules
network stack
```

Обычно новый namespace изначально практически пуст и содержит только loopback-интерфейс.

Docker затем связывает network namespace контейнера с хостом с помощью `veth`, bridge, маршрутизации и NAT.

Упрощённо:

```text
HOST namespace

docker bridge
     │
 veth-host
     │
     ├──────── veth pair ────────┐
                                 │
                         container eth0
                                 │
                         NET namespace
```

---

# PID namespace

PID namespace создаёт отдельное пространство PID.

Один и тот же процесс может иметь:

```text
на host:       PID 18345
в контейнере:  PID 1
```

Это один процесс ядра, а не два разных процесса.

Пример:

```bash
sudo unshare --pid --fork --mount-proc bash
```

`--fork` важен, потому что новый PID namespace применяется к будущим дочерним процессам. Первый дочерний процесс становится PID 1 внутри нового namespace.

`--mount-proc` нужен, чтобы новый `/proc` соответствовал новому PID namespace.

---

# Mount namespace

Mount namespace определяет, какие mount points видит процесс.

```bash
sudo unshare --mount bash
```

Например внутри нового namespace:

```bash
mount -t tmpfs tmpfs /mnt
```

Этот mount может быть виден только процессам данного mount namespace.

Разница с `chroot`:

```text
chroot
→ меняет, какой каталог считается /

mount namespace
→ меняет видимое дерево mounts
```

В контейнерах эти механизмы используются совместно.

---

# User namespace

User namespace изолирует UID, GID и capabilities.

Пример:

```bash
unshare --user --map-root-user bash
```

Внутри можно увидеть:

```text
uid=0(root)
```

хотя на host процесс принадлежит обычному пользователю.

Пример mapping:

```text
inside namespace     host
UID 0             →  UID 1000
```

Это не настоящий root хоста.

User namespaces являются важной частью rootless containers.

---

# IPC namespace

Изолирует механизмы межпроцессного взаимодействия, например:

```text
System V shared memory
System V semaphores
System V message queues
POSIX message queues
```

---

# Cgroup namespace

Не путать:

```text
cgroups
```

и:

```text
cgroup namespace
```

**cgroups** управляют и ограничивают ресурсы процессов:

```text
CPU
RAM
IO
число процессов
...
```

**cgroup namespace** в основном изолирует то, как процесс видит cgroup-иерархию.

Сам по себе cgroup namespace не устанавливает лимиты CPU или RAM.

---

# `clone`, `unshare`, `setns`

Три основных механизма работы с namespaces.

## `clone()`

Создать новый процесс сразу в новых namespaces:

```text
parent
   │
   │ clone(CLONE_NEWNET | CLONE_NEWUTS)
   ▼
child
├── новый NET namespace
└── новый UTS namespace
```

## `unshare()`

Отделить execution context процесса и создать для него новый namespace:

```text
process
   │
   │ unshare(CLONE_NEWNET)
   ▼
process
└── новый NET namespace
```

## `setns()`

Подключить процесс к уже существующему namespace:

```text
Process A → NET #1

Process B → NET #2
     │
     │ setns(NET #1)
     ▼
Process B → NET #1
```

CLI-утилита для этого:

```bash
nsenter
```

Она позволяет войти в namespaces другого процесса, например процесса контейнера.

---

# Связь с Docker

Контейнер — не один namespace.

Это группа процессов, которым runtime назначил определённую комбинацию namespaces:

```text
container process
├── MNT → namespace A
├── PID → namespace B
├── NET → namespace C
├── UTS → namespace D
├── IPC → namespace E
└── USER → namespace F
```

Дополнительно используются:

```text
rootfs
cgroups
capabilities
seccomp
и другие механизмы
```

Упрощённо:

```text
Docker container
=
обычный Linux process
+
отдельный rootfs
+
namespaces
+
cgroups
+
ограничение привилегий
```

Главная идея:

> Namespace не создаёт виртуальную машину или отдельное ядро. Он меняет то, какую часть конкретного системного ресурса видит процесс.
