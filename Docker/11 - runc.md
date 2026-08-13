`runc` — низкоуровневый OCI runtime.

Его задача:

> превратить OCI Runtime configuration и root filesystem в реальный Linux process.

---

# Что получает runc

Классическая учебная модель:

```text
OCI bundle/
├── config.json
└── rootfs/
```

`rootfs` должен стать `/` контейнерного process.

`config.json` описывает:

```text
process args
environment
cwd
UID/GID
namespaces
mounts
cgroup resources
capabilities
seccomp
rlimits
hostname
```

---

# Что делает runc

```text
read config.json
      ↓
prepare/join namespaces
      ↓
prepare mounts/rootfs
      ↓
configure cgroup
      ↓
UID/GID
capabilities
seccomp
rlimits
      ↓
change root filesystem
      ↓
execve(application)
```

В конце приложение — обычный Linux process.

---

# Связь с уже изученным

- root isolation: [[13 - chroot]]
- namespaces: [[14 - Linux Namespaces и unshare]]
- cgroups: [[15 - cgroups]]
- rootfs/mounts: [[09 - Snapshotter и OverlayFS]]

---

# OCI lifecycle

```bash
runc create
runc start
runc run
runc state
runc list
runc exec
runc kill
runc delete
```

---

# Ручной эксперимент

```bash
mkdir -p ~/runc-demo/rootfs
cd ~/runc-demo
```

Получить rootfs:

```bash
docker pull busybox
docker create --name runc-rootfs busybox
docker export runc-rootfs | sudo tar -C rootfs -xf -
docker rm runc-rootfs
```

Сгенерировать config:

```bash
runc spec
```

Запуск:

```bash
sudo runc run demo
```

---

# Посмотреть OCI config

```bash
jq '.process' config.json
jq '.root' config.json
jq '.linux.namespaces' config.json
jq '.linux.resources' config.json
jq '.mounts' config.json
```

---

# PID namespace

Один kernel task может иметь:

```text
host PID 23456
container PID 1
```

---

# Проверка namespaces

```bash
PID=$(sudo runc state demo | jq -r '.pid')
sudo readlink /proc/$PID/ns/pid
sudo readlink /proc/$PID/ns/net
sudo readlink /proc/$PID/ns/mnt
sudo readlink /proc/$PID/ns/uts
```

---

# Проверка cgroup

```bash
cat /proc/$PID/cgroup
```

---

# `runc` не работает с image name

Неправильная модель:

```bash
runc run ubuntu:latest
```

Runc не image registry client.

Image acquisition/unpack — уровень Docker/containerd.

---

# `runc` не daemon

После создания process `runc` обычно не должен постоянно работать.

Lifecycle поддерживает [[10 - containerd-shim-runc-v2]].

Связано: [[05 - OCI]], [[12 - libcontainer]], [[16 - Linux kernel primitives]].
