Основные host directories Docker Engine/Linux без углубления во внутреннее дерево.

---

# `/var/lib/docker`

Persistent data самого Docker daemon: Docker metadata, volumes, network/build-related state и другие Docker-managed данные.

---

# `/var/lib/containerd`

Persistent root containerd:

```text
OCI content
image metadata
snapshotter data
unpacked snapshots
plugin persistent data
```

---

# `/run/docker`

Ephemeral runtime state dockerd.

---

# `/run/containerd`

Ephemeral state containerd/runtime:

```text
runtime v2 tasks
shim state
runtime bundles
rootfs mount points
sockets
PID/state files
```

---

# `/etc/docker`

Конфигурация Docker daemon.

---

# `/etc/containerd`

Конфигурация containerd.

---

# `~/.docker`

User-side Docker CLI configuration.

---

# `/sys/fs/cgroup`

Виртуальная cgroup filesystem.

---

# `/proc`

Kernel process/filesystem interface. Здесь видны PID, namespaces, mountinfo, cgroups и process root.

---

# `/sys`

Kernel/device/system interface.

---

# `/dev`

Host device interface.

---

# `/var/log/journal`

Может использоваться для logs при journald configuration.

---

# `/var/lib/buildkit`

Может быть persistent root отдельного `buildkitd`.

---

# Rootless paths

Для rootless Docker используются user-scoped locations, например:

```text
~/.local/share/docker
~/.config/docker
/run/user/$UID
```

---

# Самая важная четвёрка

```text
/var/lib/docker
→ persistent Docker data

/var/lib/containerd
→ persistent containerd image/snapshot data

/run/docker
→ live dockerd state

/run/containerd
→ live containerd/runtime state
```
