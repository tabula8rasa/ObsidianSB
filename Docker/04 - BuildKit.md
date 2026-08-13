BuildKit — build engine Docker.

Его задача:

> выполнить Dockerfile и получить image.

---

# Пример

```dockerfile
FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

BuildKit обрабатывает инструкции и получает:

```text
image config
+
filesystem layers
```

---

# Что происходит с filesystem-инструкциями

Инструкции:

```dockerfile
RUN ...
COPY ...
ADD ...
```

изменяют filesystem.

Например `RUN pip install ...` выполняется на **полном текущем filesystem view**.

После выполнения BuildKit сохраняет в новый layer **только filesystem delta**.

Он не записывает всю файловую систему заново.

Подробнее: [[06 - Filesystem layers и rootfs]].

---

# Build cache

Допустим:

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

Если изменился только `main.py`, но `requirements.txt` прежний:

```text
Layer A — base
Layer B — requirements
Layer C — dependencies
Layer D1 — old source
Layer D2 — new source
```

Новый image может переиспользовать A/B/C и создать только D2.

```text
A → B → C ──┬→ D1 old image
            └→ D2 new image
```

Поэтому dependencies обычно копируют/устанавливают до исходников.

---

# Metadata-инструкции

Инструкции вроде:

```dockerfile
CMD
ENTRYPOINT
ENV
USER
WORKDIR
```

в основном влияют на **image config**, а не обязательно создают filesystem layer с файлами.

Например:

```dockerfile
CMD ["python", "main.py"]
```

становится image metadata.

---

# BuildKit и container runtime

BuildKit создаёт image.

Он не отвечает за последующий запуск image через `runc`.

```text
BuildKit
   ↓
image

containerd + runc
   ↓
container
```

Связано: [[03 - Docker Buildx]], [[05 - OCI]], [[22 - Жизненный цикл build pull run]].
