# Snapshotter и OverlayFS

Snapshotter — containerd subsystem/plugin, отвечающий за подготовку mountable filesystem.

В рассматриваемой конфигурации Docker показывает:

```text
Storage Driver: overlayfs
driver-type: io.containerd.snapshotter.v1
```

То есть используется:

```text
containerd image store
+
containerd overlayfs snapshotter
+
Linux OverlayFS
```

Это не legacy `overlay2` graph driver, хотя underlying kernel mechanism — OverlayFS.

---

# Где лежит snapshotter

```text
/var/lib/containerd/
└── io.containerd.snapshotter.v1.overlayfs/
    ├── metadata.db
    └── snapshots/
```

`snapshots/<N>/fs` содержит реальные распакованные filesystem objects.

---

# Layer → snapshot

```text
layer A.tar.gz
     ↓ unpack
snapshot A

layer B.tar.gz
     ↓ apply on current state
snapshot B
```

Snapshotter хранит parent-child relationships.

---

# Active и committed snapshots

Image filesystem state представлен committed/read-only snapshots.

При запуске container создаётся новый active/writable snapshot.

---

# OverlayFS mount

Для container kernel получает mount configuration примерно такого вида:

```text
lowerdir=C:B:A
upperdir=U
workdir=W
```

И создаёт единый filesystem view.

---

# Реальный `mountinfo`

Для process PID:

```bash
sudo awk '$5 == "/"' /proc/"$PID"/mountinfo
```

Наблюдавшийся формат:

```text
lowerdir=.../snapshots/31/fs:.../snapshots/28/fs,
upperdir=.../snapshots/32/fs,
workdir=.../snapshots/32/work
```

Для другого container:

```text
lowerdir=.../snapshots/33/fs:.../snapshots/28/fs
upperdir=.../snapshots/34/fs
```

Из этого видно, что snapshot `28` используется обоими filesystem views.

---

# Почему lowerdir могут не совпадать полностью

Реальная snapshot chain может включать дополнительные container-specific intermediate snapshots.

Главный принцип:

```text
общие parent snapshots
+
container-specific active/upper snapshot
```

---

# `fs`

```text
snapshots/28/fs/
├── bin
├── etc
├── lib
├── usr
└── var
```

Это реальные files на диске.

Но `proc`, `sys`, `dev` внутри persistent snapshot сами по себе не являются live runtime mounts.

---

# `work`

`work` — служебный каталог kernel OverlayFS.

Он не виден приложению как часть обычного rootfs.

---

# Где хранится итоговый rootfs

Полная объединённая файловая система обычно **не копируется на диск** в отдельный каталог.

Она существует как mount.

```text
persistent snapshots
       ↓
OverlayFS mount
       ↓
runtime rootfs mount point
       ↓
container process /
```

---

# Экономия места

Два containers имеют разные logical rootfs, но общие lower image data.

Изменённые files copy-up'ятся в собственный upper.

Связано: [[06 - Filesystem layers и rootfs]], [[14 - Linux Namespaces и unshare]].
