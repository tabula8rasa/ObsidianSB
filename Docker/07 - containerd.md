# containerd

`containerd` — системный daemon для управления container content, snapshots и container tasks.

Проверить:

```bash
ps -ef | grep '[c]ontainerd'
systemctl status containerd
```

Архитектурно:

```text
dockerd
    ↓
containerd
    ↓
containerd-shim-runc-v2
    ↓
runc
```

---

# Основные обязанности

```text
Content Store
Image metadata
Snapshotters
Containers
Tasks
Runtime v2
Shim management
Namespaces
Garbage collection
```

---

# Content и filesystem — разные вещи

```text
content store
    ↓
compressed OCI blobs

snapshotter
    ↓
unpacked mountable filesystem data
```

Подробнее: [[08 - containerd Content Store]], [[09 - Snapshotter и OverlayFS]].

---

# Persistent и runtime storage

Persistent root:

```text
/var/lib/containerd
```

Runtime state:

```text
/run/containerd
```

---

# Docker namespace `moby`

Docker использует containerd namespace:

```text
moby
```

Поэтому для Docker-managed objects через `ctr` часто используется:

```bash
sudo ctr -n moby ...
```

---

# Container и task

В containerd полезно различать metadata container object и реально запущенный task/process.

---

# Что происходит при запуске

```text
containerd
    │
    ├── находит image
    ├── использует snapshotter
    ├── создаёт writable snapshot
    ├── получает mount specification
    ├── готовит runtime config/environment
    └── запускает shim
            ↓
        runc
```

---

# Почему containerd не просто вызывает runc и забывает

Для долгоживущего lifecycle используется Runtime v2 и shim.

Подробнее: [[10 - containerd-shim-runc-v2]].
