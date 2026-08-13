# Docker CLI

`docker` — пользовательский клиент Docker Engine.

Примеры:

```bash
docker run nginx
docker ps
docker pull alpine
docker build .
docker exec container sh
docker network ls
```

Сам Docker CLI **не создаёт namespaces, cgroups или контейнерные процессы**.

Он:

```text
читает аргументы пользователя
        ↓
формирует Docker API request
        ↓
отправляет запрос dockerd
```

Типичная связь:

```text
docker CLI
    ↓
Unix socket
/run/docker.sock
    ↓
dockerd
```

Проверить:

```bash
ls -l /var/run/docker.sock
```

Часто `/var/run` является ссылкой на `/run`.

---

# Что CLI знает

CLI работает с высокоуровневыми Docker-сущностями:

```text
images
containers
networks
volumes
builds
contexts
plugins
```

При:

```bash
docker run alpine
```

CLI не вызывает `runc` напрямую.

Цепочка значительно длиннее:

```text
docker
  ↓
dockerd
  ↓
containerd
  ↓
shim
  ↓
runc
```

---

# Docker CLI и environment

Клиентская конфигурация пользователя обычно находится в:

```text
~/.docker
```

Там могут храниться:

```text
config.json
contexts
registry credential settings
```

Это не daemon storage и не image storage.

Связано: [[02 - dockerd]], [[21 - Каталоги Docker на хосте]].
