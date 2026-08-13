# containerd Content Store

Content Store хранит OCI content **по digest**.

На вашей системе:

```text
/var/lib/containerd/
└── io.containerd.content.v1.content/
    ├── blobs/
    │   └── sha256/
    └── ingest/
```

---

# `blobs/sha256`

Файл:

```text
blobs/sha256/<HASH>
```

является immutable content object.

Внутри может быть:

```text
OCI index
OCI manifest
image config JSON
compressed filesystem layer
```

По одному имени нельзя определить тип.

Посмотреть metadata:

```bash
sudo ctr -n moby content ls
```

Получить blob:

```bash
sudo ctr -n moby content get sha256:<digest> > /tmp/blob
file /tmp/blob
```

---

# `ingest`

`ingest/` — временная staging area.

```text
registry
   ↓
ingest
   ↓
digest verification
   ↓
commit
   ↓
blobs/sha256/<digest>
```

---

# Content Store не является rootfs

```text
Content Store
→ image distribution/storage format

Snapshotter
→ runtime filesystem format
```

Process контейнера не читает `/usr/bin/python` прямо из compressed tar blob.

Layer сначала распаковывается snapshotter'ом.

---

# Связь с image

Manifest содержит ссылки на config digest и layer digests.

Несколько images могут ссылаться на один и тот же content-addressed blob.

Связано: [[05 - OCI]], [[09 - Snapshotter и OverlayFS]].
