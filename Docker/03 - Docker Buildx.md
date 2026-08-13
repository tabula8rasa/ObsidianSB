# Docker Buildx

Buildx — клиентская часть современной build-системы Docker.

Команды:

```bash
docker buildx ls
docker buildx inspect
docker buildx build .
```

Buildx не является container runtime.

Его область:

```text
Dockerfile
build context
builder configuration
multi-platform builds
BuildKit invocation
output/export
```

Модель:

```text
Docker CLI
    ↓
Buildx
    ↓
BuildKit
    ↓
OCI image
```

Buildx управляет builder instances и отправляет build operations в [[04 - BuildKit]].

---

# Buildx и `docker build`

Для обучения полезно разделять:

```text
Buildx
→ интерфейс/клиент build

BuildKit
→ фактически выполняет build
```

Buildx не участвует в обычном lifecycle уже запущенного container после того, как image существует.

Связано: [[04 - BuildKit]], [[22 - Жизненный цикл build pull run]].
