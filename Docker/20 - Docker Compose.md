# Docker Compose

Docker Compose — высокоуровневый инструмент описания набора Docker resources.

Пример:

```yaml
services:
  web:
    image: nginx
  db:
    image: postgres
```

Compose не создаёт namespaces/cgroups самостоятельно.

---

# Архитектура

```text
compose.yaml
    ↓
docker compose
    ↓
Docker API
    ↓
dockerd
```

Compose переводит YAML в операции создания networks, volumes, containers, ports и запуска services.

Ниже всё равно обычная цепочка:

```text
dockerd
 ↓
containerd
 ↓
shim
 ↓
runc
```

Для runc не существует специального понятия Compose service.

Связано: [[00 - Архитектура Docker целиком]].
