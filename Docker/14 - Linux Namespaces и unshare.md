# Linux Namespaces и unshare

Namespace — объект ядра Linux, который даёт группе процессов отдельное представление конкретного системного ресурса.

---

# Нет одного «namespace контейнера»

Неправильно:

```text
Namespace #1
├── pid
├── net
├── mnt
└── uts
```

Правильно:

```text
PID namespaces: PID #1, PID #2
NET namespaces: NET #1, NET #2
MNT namespaces: MNT #1, MNT #2
UTS namespaces: UTS #1, UTS #2
```

Каждый process одновременно состоит в одном namespace каждого типа.

---

# Основные namespaces

| Type | Что изолирует |
|---|---|
| `mnt` | mount tree |
| `pid` | PID space |
| `net` | network stack/interfaces/routes |
| `uts` | hostname/domain name |
| `ipc` | IPC objects |
| `user` | UID/GID/capabilities mappings |
| `cgroup` | cgroup view |
| `time` | clock offsets |

---

# Посмотреть namespaces процесса

```bash
ls -l /proc/$$/ns
```

Если два processes имеют одинаковый namespace ID конкретного типа, они разделяют этот namespace.

---

# `unshare`

```bash
sudo unshare --uts bash
```

Логически:

```text
current UTS
   ↓
unshare(CLONE_NEWUTS)
   ↓
new UTS
   ↓
bash
```

---

# Почему после `sudo unshare ... bash` shell root

Из-за `sudo`, а не из-за `unshare`.

```text
UID 1000
  ↓ sudo
UID 0
```

---

# UTS namespace и hostname

Для чистого эксперимента не стоит использовать `hostnamectl`.

`hostnamectl` может обратиться через D-Bus к host `systemd-hostnamed`, и уже host daemon поменяет host hostname.

Чистый тест:

```bash
sudo unshare --uts bash
python -c 'import os; os.sethostname(b"container-demo")'
uname -n
```

---

# D-Bus

D-Bus — IPC message bus userspace.

```text
client
  ↓ message
D-Bus broker
  ↓
service
```

Пример:

```text
hostnamectl → systemd-hostnamed
```

---

# Network namespace

```bash
sudo unshare --net bash
ip addr
```

Отдельные interfaces/IP/routes/sockets.

Docker затем добавляет veth/bridge/routing.

---

# PID namespace

```bash
sudo unshare --pid --fork --mount-proc bash
```

Один kernel process может быть host PID 18345 и container PID 1.

---

# Mount namespace

```bash
sudo unshare --mount bash
```

Отличие:

```text
chroot
→ какой каталог считается /

MNT namespace
→ какие mounts видит process
```

---

# User namespace

```bash
unshare --user --map-root-user bash
```

Возможен mapping:

```text
inside UID 0
→ host UID 1000
```

---

# clone / unshare / setns

```text
clone → создать child сразу с namespaces
unshare → отделить execution context
setns → войти в существующий namespace
```

CLI для входа в namespace другого process:

```bash
nsenter
```

Связано: [[16 - Linux kernel primitives]], [[17 - Docker Networking]].
