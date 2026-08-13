## Главная идея

Docker-контейнер — не маленькая виртуальная машина.
![[Pasted image 20260813153905.png|700]]
В конечном итоге это **обычный Linux-процесс**, которому Linux kernel предоставляет:

- отдельное представление файловой системы;
- namespaces;
- cgroups;
- capabilities;
- seccomp;
- отдельные mounts;
- сетевой namespace;
- другие ограничения.

Высокоуровневые компоненты Docker лишь подготавливают данные и координируют создание этого процесса.

```text
                         USER

                          │
                          ▼
                     Docker CLI
                          │
                     Docker API
                          │
                          ▼
                       dockerd
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        │ docker build                      │ docker run
        ▼                                   ▼
 Buildx / BuildKit                      containerd
        │                                   │
        ▼                    ┌──────────────┼──────────────┐
    OCI image                ▼              ▼              ▼
                      Content Store     Snapshotter     Task/runtime
                                           │
                                           ▼
                                 containerd-shim-runc-v2
                                           │
                                           ▼
                                         runc
                                           │
                                           ▼
                                     Linux kernel
                                           │
                  ┌────────────────────────┼────────────────────────┐
                  ▼                        ▼                        ▼
             namespaces                 cgroups                mounts/rootfs
                  │                        │                        │
                  └────────────────────────┼────────────────────────┘
                                           ▼
                                  container process
                               python / nginx / bash
```

---

# Два независимых пути: build и run

## `docker build`

```text
Dockerfile
   ↓
Docker CLI / Buildx
   ↓
BuildKit
   ↓
выполнение RUN / COPY / ADD
   ↓
filesystem changesets
   ↓
OCI image layers
   +
OCI image config
   ↓
image
```

Главное: **Dockerfile не превращается напрямую в OCI runtime bundle**.

Результат build — image.

Image содержит:

```text
manifest
image config
filesystem layers
```

Подробнее: [[04 - BuildKit]], [[05 - OCI]], [[06 - Filesystem layers и rootfs]].

---

## `docker run`

```text
готовый image
    ↓
containerd
    ↓
image content + unpacked snapshots
    ↓
snapshotter создаёт writable snapshot контейнера
    ↓
Linux OverlayFS создаёт filesystem view
    ↓
OCI runtime config
    ↓
containerd-shim-runc-v2
    ↓
runc
    ↓
namespaces + cgroups + mounts + capabilities
    ↓
execve(application)
```

На этапе `docker run` **Dockerfile уже не анализируется и image не пересобирается**.

---

# Где появляется OCI bundle

Для `runc` концептуально нужен OCI Runtime Bundle:

```text
bundle/
├── config.json
└── rootfs/
```

Но `rootfs/` не обязан быть физической полной копией image.

В современной схеме это обычно **mount point**.

```text
image snapshots
       +
container writable snapshot
       ↓
OverlayFS mount
       ↓
bundle/rootfs/
```

После mount каталог выглядит как полноценный Linux root:

```text
rootfs/
├── bin
├── etc
├── lib
├── usr
└── app
```

Но файлы туда не копировались целиком.

Подробнее: [[06 - Filesystem layers и rootfs]], [[09 - Snapshotter и OverlayFS]].

---

# Физическая и runtime-часть

## Persistent data

```text
/var/lib/docker
/var/lib/containerd
```

Это данные, которые переживают перезапуск daemon.

Например:

```text
OCI blobs
image metadata
unpacked snapshots
volumes
Docker metadata
```

## Runtime state

```text
/run/docker
/run/containerd
```

Это временное состояние работающей системы:

```text
sockets
tasks
shim state
OCI runtime bundle
runtime rootfs mount points
PID/state files
```

## Kernel interfaces

```text
/proc
/sys
/sys/fs/cgroup
/dev
```

Через них runtime взаимодействует с Linux kernel.

Подробнее: [[21 - Каталоги Docker на хосте]].

---

# Что делает каждый компонент

| Компонент | Главная роль |
|---|---|
| Docker CLI | пользовательский клиент |
| `dockerd` | высокоуровневое управление Docker |
| Buildx | клиент BuildKit |
| BuildKit | сборка image |
| OCI | стандарты image/runtime/distribution |
| `containerd` | content, snapshots, tasks и runtime integration |
| Content Store | хранение OCI blobs |
| Snapshotter | подготовка mountable filesystem |
| OverlayFS | объединение lower/upper layers |
| `containerd-shim-runc-v2` | посредник между containerd и container lifecycle |
| `runc` | превращает OCI config в Linux process |
| `libcontainer` | Linux-specific реализация внутри runc |
| Linux kernel | реально предоставляет namespaces/cgroups/mounts |
| Docker networking | veth, bridge, routes, NAT |
| `docker-proxy` | опциональный userland port proxy |
| `docker-init`/tini | опциональный PID 1 |
| Compose | высокоуровневое описание нескольких Docker resources |

---

# Итоговая модель

```text
Dockerfile
   ↓
BuildKit
   ↓
OCI image
   ├── config
   └── layers
          ↓
      containerd
          ↓
      content store
          ↓ unpack
      image snapshots
          ↓
 docker run creates
 writable snapshot
          ↓
      OverlayFS
          ↓
      rootfs view
          │
          ├── OCI runtime config
          │
          ▼
containerd-shim-runc-v2
          ↓
         runc
          ↓
 Linux namespaces
 Linux cgroups
 mounts
 capabilities
 seccomp
          ↓
      execve()
          ↓
обычный Linux process
```

Ключевая мысль:

> Docker не создаёт отдельную ОС. Он строит окружение и просит Linux kernel запустить обычный процесс с определённым набором filesystem, namespace, resource и security-настроек.
