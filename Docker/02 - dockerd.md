# dockerd

`dockerd` — основной daemon Docker Engine.

Проверить:

```bash
ps -ef | grep '[d]ockerd'
systemctl status docker
```

Он постоянно работает в фоне и предоставляет Docker API.

---

# Роль

`dockerd` отвечает за высокоуровневые Docker-сущности:

```text
containers
images
networks
volumes
build coordination
Docker API
authentication/configuration
```

Он не является тем процессом, который вручную вызывает все Linux syscalls для контейнера.

Для низкоуровневого lifecycle он использует [[07 - containerd]].

Упрощённо:

```text
docker CLI
    ↓
dockerd
    ↓
containerd
```

---

# `docker run`

Когда приходит:

```bash
docker run -p 8080:80 --memory=512m myapp
```

`dockerd` должен интерпретировать высокоуровневые Docker-параметры:

```text
image = myapp
memory = 512 MiB
port publication = 8080:80
network attachment
volumes
environment
command override
```

Затем часть информации передаётся вниз в containerd/runtime, а часть реализуется Docker-уровнем.

Например:

```text
memory limit
    ↓
OCI resources
    ↓
cgroup

network namespace
    ↓
runtime

-p 8080:80
    ↓
Docker networking
    ↓
host routing/NAT/proxy
```

Проброс портов не является просто полем `runc config.json`.

---

# Persistent и runtime directories

Основные:

```text
/etc/docker
/var/lib/docker
/run/docker
```

При containerd image store значительная часть image filesystem data хранится уже в:

```text
/var/lib/containerd
```

Подробнее: [[21 - Каталоги Docker на хосте]].

---

# Связь с containerd

```text
dockerd
    ↓
containerd
    ↓
containerd-shim-runc-v2
    ↓
runc
```

`dockerd` — Docker-specific management layer.

`containerd` — generic container lifecycle/content layer.

`runc` — OCI low-level runtime.

Связано: [[07 - containerd]], [[11 - runc]].
