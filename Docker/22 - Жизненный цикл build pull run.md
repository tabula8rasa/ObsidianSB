Эта заметка соединяет physical storage и runtime.

---

# `docker build`

```text
Dockerfile
   ↓
Buildx
   ↓
BuildKit
   ↓
execute build steps
   ↓
filesystem changes
   ↓
OCI layers
+
image config
+
manifest
   ↓
image
```

Важное:

```text
RUN/COPY/ADD
→ filesystem changes

CMD/ENTRYPOINT/ENV/USER
→ mainly image metadata/config
```

---

# `docker pull`

```text
registry
   ↓
manifest/config/layer blobs
   ↓
containerd Content Store
   ↓
/var/lib/containerd/.../blobs/sha256
```

После unpack:

```text
layer blobs
   ↓
snapshotter
   ↓
committed image snapshots
```

На диске могут одновременно существовать compressed layer form и unpacked snapshot form.

---

# `docker run`

Dockerfile уже не участвует.

```text
ready image
   ↓
containerd
   ↓
existing image snapshot chain
   ↓
new writable active snapshot
   ↓
mount specification
   ↓
OverlayFS mount
   ↓
rootfs view
```

Параллельно:

```text
image config
+
docker run options
+
runtime defaults
    ↓
OCI runtime config
```

Далее:

```text
containerd
  ↓
containerd-shim-runc-v2
  ↓
runc
  ↓
Linux kernel setup
  ↓
execve(application)
```

---

# Что появляется только после `run`

До запуска image уже может иметь:

```text
manifest
config
compressed layers
unpacked image snapshots
```

После запуска появляются:

```text
container writable snapshot
runtime task
shim
runtime rootfs mount
namespaces
cgroup
container process
```

---

# Stop/remove

`docker stop` останавливает process/task.

`docker rm` удаляет container-specific state/storage согласно lifecycle.

Shared image data остаётся, пока оно ещё нужно images/containers.

---

# Главная модель

```text
BUILD
Dockerfile → image

PULL
registry → content store → image snapshots

RUN
image snapshots + new writable snapshot
             ↓
          rootfs mount
             ↓
           runc
             ↓
          process
```
