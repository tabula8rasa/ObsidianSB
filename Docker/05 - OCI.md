OCI — Open Container Initiative.

Это **не программа**, а набор стандартов контейнерной экосистемы.

Ключевые спецификации:

```text
OCI Image Specification
OCI Runtime Specification
OCI Distribution Specification
```

---

# OCI Image Specification

Определяет устройство image:

```text
manifest
config
filesystem layers
digests
media types
```

Условно:

```text
OCI image
├── manifest
├── config
└── layers
    ├── sha256:A
    ├── sha256:B
    └── sha256:C
```

Подробнее: [[06 - Filesystem layers и rootfs]], [[08 - containerd Content Store]].

---

# OCI Runtime Specification

Определяет, как low-level runtime должен создать контейнер.

Ключевой объект — OCI Runtime Bundle:

```text
bundle/
├── config.json
└── rootfs/
```

`config.json` описывает, например:

```text
process.args
process.env
process.cwd
UID/GID
root filesystem
mounts
namespaces
cgroup resources
capabilities
seccomp
hostname
```

Именно этот стандарт реализует [[11 - runc]].

---

# OCI bundle не равен Docker image

Неправильно:

```text
Dockerfile
  ↓
OCI bundle
```

Правильнее:

```text
Dockerfile
   ↓
BuildKit
   ↓
OCI image
   ↓
containerd/snapshotter
   ↓
runtime filesystem
   +
runtime config
   ↓
OCI bundle/environment
   ↓
runc
```

---

# Runtime config и image config — разные вещи

Image config содержит defaults:

```text
Cmd
Entrypoint
Env
WorkingDir
User
```

Runtime config формируется ещё и из:

```text
docker run arguments
Docker defaults
security defaults
resource limits
mounts
runtime decisions
```

---

# Порты

Проброс:

```bash
docker run -p 8080:80 ...
```

не является просто стандартным OCI runtime setting.

OCI runtime может создать network namespace, но Docker выше него настраивает:

```text
veth
bridge
IP
routing
NAT/firewall
optional docker-proxy
```

Связано: [[17 - Docker Networking]].

---

# Lifecycle

OCI runtime разделяет:

```text
create
start
kill
delete
```

Это видно в `runc`.

Связано: [[11 - runc]].
