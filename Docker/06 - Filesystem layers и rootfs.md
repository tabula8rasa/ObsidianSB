Это ключевая тема для понимания физики Docker image и container filesystem.

---

# Что такое filesystem layer физически

OCI filesystem layer — **filesystem changeset**.

При передаче/хранении image это обычно tar-архив, часто сжатый.

Layer содержит реальные:

```text
files
directories
symlinks
metadata
whiteout entries
```

Он не содержит набор команд вроде:

```text
pip install fastapi
COPY main.py
```

Команды уже были выполнены во время build.

Layer хранит **результат изменений filesystem**.

---

# Пример `pip install`

Dockerfile:

```dockerfile
FROM python:3.12-alpine

COPY requirements.txt .
RUN pip install -r requirements.txt
```

Во время `RUN` команда работает с полным текущим rootfs.

После команды появляются, например:

```text
/usr/local/lib/python.../site-packages/fastapi/
/usr/local/lib/python.../site-packages/pydantic/
/usr/local/lib/python.../site-packages/starlette/
```

Layer `RUN pip install ...` содержит только новые/изменённые filesystem objects.

Он не содержит снова весь Python/Alpine root.

---

# Layer — delta относительно текущего состояния

Пусть:

```text
A = base image
B = dependencies
C = source
```

Технически:

```text
B = delta относительно состояния A
C = delta относительно состояния A+B
```

---

# Изменение существующего файла

Layer A:

```text
/etc/app.conf = MODE=dev
```

Layer B:

```text
/etc/app.conf = MODE=prod
```

Итоговый view берёт верхнюю версию.

---

# Удаление файла

Если верхний layer должен удалить файл из нижнего, используются whiteout entries.

Условно:

```text
lower:
/app/old.py

upper:
/app/.wh.old.py
```

---

# Image layer и snapshot — разные представления

## Image form

```text
compressed tar blob
```

Хранится в content store:

```text
/var/lib/containerd/io.containerd.content.v1.content/blobs/sha256/
```

## Runtime filesystem form

Layer распаковывается через snapshotter:

```text
layer blob
   ↓ unpack
snapshot
```

Подробнее: [[08 - containerd Content Store]], [[09 - Snapshotter и OverlayFS]].

---

# Что такое rootfs контейнера

`rootfs` — файловая система, которую process контейнера в итоге видит как `/`.

Очень важно:

> rootfs контейнера не обязан существовать на диске как полная отдельная копия всех файлов image.

В рассматриваемой схеме он создаётся как OverlayFS mount.

```text
image lower snapshots
        +
container writable upper snapshot
        ↓
OverlayFS mount
        ↓
rootfs view
```

---

# Почему два контейнера не требуют две полные копии image

Пусть image занимает:

```text
Python + Alpine     300 MB
dependencies        400 MB
application          20 MB
--------------------------
image data          720 MB
```

Два container rootfs логически разные:

```text
container 1 = common image + upper1
container 2 = common image + upper2
```

Но physical lower files общие.

---

# Rootfs как mount, а не copy

Аналогия:

```bash
mount /dev/sdb1 /mnt/disk
```

После mount `/mnt/disk` содержит дерево файлов, но Linux не копировал диск в каталог.

То же самое с container rootfs.

---

# Чтение файла через OverlayFS

Если process открывает:

```text
/usr/bin/python
```

OverlayFS проверяет слои сверху вниз до первого найденного объекта.

---

# Запись и copy-up

Если container меняет файл из shared lower layer, OverlayFS копирует его в container-specific upper.

После этого один container видит изменённую upper version, остальные продолжают видеть shared lower version.

---

# Связь с mount namespace

OverlayFS отвечает:

> как объединить lower snapshots и upper snapshot в единый filesystem?

Mount namespace отвечает:

> какое дерево mount'ов видит конкретный process?

Связано: [[14 - Linux Namespaces и unshare]], [[09 - Snapshotter и OverlayFS]].
