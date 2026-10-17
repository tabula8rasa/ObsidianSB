---
tags:
  - containers
  - podman
  - docker
  - linux
  - architecture
aliases:
  - Podman architecture
  - Podman vs Docker
---

# Podman vs Docker: архитектурные отличия

> [!summary] 
> Docker — **клиент-серверная** система с центральным root-демоном `dockerd` 
> Podman — **бездемонная** (daemonless): CLI сам делает fork/exec, а контейнер — обычный дочерний процесс пользователя, за которым присматривает крошечный монитор `conmon`. Низкоуровневая изоляция (namespaces, cgroups, runc/crun) та же самая; отличается всё, что находится _над_ ней.

## 1. Модель Docker (для сравнения)

```
docker CLI ──REST (unix socket)──► dockerd ──gRPC──► containerd ──► containerd-shim ──► runc ──► процесс контейнера
                                      │
                                      └─ образы, сети, тома, build (BuildKit), swarm, API
```

- `dockerd` — единый долгоживущий демон, обычно от **root**.
- Всё состояние (контейнеры, образы, сети) живёт в демоне; CLI — тонкий клиент.
- Доступ к `/var/run/docker.sock` ≈ root на хосте.
- Контейнеры — потомки `containerd-shim`, а не CLI. Падение/рестарт `dockerd` без `live-restore` затрагивает контейнеры.

## 2. Модель Podman

```
podman CLI ──fork/exec──► conmon ──► OCI runtime (runc | crun) ──► процесс контейнера
     │
     └─ напрямую использует библиотеки: containers/image, containers/storage, netavark, ...
```

- **Нет центрального демона.** `podman run` — это процесс, который сам собирает всё необходимое, запускает `conmon` и завершается/отсоединяется.
- **`conmon`** (container monitor) — маленький Си-процесс на каждый контейнер. Задачи: держать pty/stdio, собирать логи, ловить exit code, оставаться родителем контейнера после выхода CLI. Это аналог `containerd-shim`, но без `containerd` над ним.
- **OCI runtime** — `runc` или `crun` (на Fedora/RHEL по умолчанию `crun`, он на C и легче/быстрее).
- Нет `containerd`: Podman не делегирует жизненный цикл контейнера отдельному сервису, а управляет им сам через библиотеки (`libpod`).

### Сопоставление компонентов

|Роль|Docker|Podman|
|---|---|---|
|Точка входа|`docker` CLI → `dockerd`|`podman` CLI (он же «движок»)|
|Управление жизненным циклом|`containerd`|`libpod` внутри самого `podman`|
|Присмотр за процессом|`containerd-shim`|`conmon`|
|OCI-рантайм|`runc`|`crun` / `runc`|
|Образы и слои|graphdriver / containerd snapshotter|`containers/storage` + `containers/image`|
|Сеть|`libnetwork` (bridge `docker0`)|`netavark` + `aardvark-dns` (раньше CNI)|
|Сборка|BuildKit|`buildah` (библиотека)|
|Pull/push/inspect образов|внутри `dockerd`|`skopeo` / `containers/image`|

## 3. Ключевое отличие: rootless

Главная практическая причина существования Podman.

- Контейнеры можно запускать **от обычного пользователя без root-демона**.
- Основа — **user namespace**: UID 0 внутри контейнера отображается на непривилегированный UID хоста.
    - Диапазон подчинённых UID/GID берётся из `/etc/subuid` и `/etc/subgid`.
    - Для маппинга используются setuid-хелперы `newuidmap` / `newgidmap`.
- Побег из контейнера даёт атакующему права обычного пользователя, а не root.
- У каждого пользователя **своё независимое хранилище**: `~/.local/share/containers/storage` (у root — `/var/lib/containers/storage`). Образы и контейнеры разных пользователей не пересекаются.
- Docker тоже умеет rootless-режим, но он добавлен позже и является надстройкой над демоном; в Podman это базовый сценарий.

### Следствия rootless

- **Сеть**: непривилегированный процесс не может создавать bridge и iptables-правила на хосте. Используется user-space стек `pasta` (раньше `slirp4netns`) — трафик идёт через TAP внутри netns и транслируется в сокеты хоста. Это медленнее и имеет ограничения (например, порты < 1024 требуют `net.ipv4.ip_unprivileged_port_start`).
- **Файловая система**: вместо kernel overlayfs исторически применялся `fuse-overlayfs`; на современных ядрах (5.11+) работает нативный rootless overlay.
- **cgroups**: нужен cgroups v2 с делегированием контроллеров пользователю (через systemd).
- **Нет `--privileged` в полном смысле**: контейнер не может получить больше прав, чем есть у самого пользователя.

## 4. Модель процессов: fork/exec вместо клиент-сервера

- В Docker контейнер — потомок демона. `ps` показывает `dockerd → containerd → shim → процесс`.
- В Podman дерево процессов естественное: контейнер принадлежит пользователю, запустившему его, и виден в `ps` под его UID.
- Поскольку демона нет, нет единой точки отказа и не нужен постоянно висящий процесс (и сокет с root-правами).
- Побочный эффект: аудит. Так как это обычный fork/exec, в журналах (`auditd`, `loginuid`) остаётся реальный пользователь, запустивший контейнер. В Docker действие выполняет демон от root, и исходный пользователь теряется.

## 5. Интеграция с systemd вместо собственного supervisor'а

Нет демона → нет и встроенного `--restart=always`, который бы работал при перезагрузке. Роль супервизора отдана **systemd**:

- **Quadlet** (актуальный способ): `.container`-файлы в `~/.config/containers/systemd/` (rootless) или `/etc/containers/systemd/` (root). Генератор превращает их в systemd-юниты.
- Раньше использовался `podman generate systemd`, сейчас он считается устаревшим в пользу Quadlet.
- Контейнеры становятся обычными сервисами: зависимости, `journalctl`, socket activation, `systemctl --user`.
- Если контейнер запущен от пользователя и нужно, чтобы он жил без логина — `loginctl enable-linger <user>`.

## 6. Pods — концепция из Kubernetes

В Podman есть сущность **pod**: группа контейнеров с общими namespaces (обычно network, IPC, иногда UTS/PID).

- В pod'е автоматически создаётся «infra»-контейнер (`pause`), который держит общие namespaces.
- Контейнеры внутри видят друг друга по `localhost`.
- `podman generate kube` / `podman kube play` — экспорт и запуск YAML в формате Kubernetes. Удобный мост между локальной разработкой и k8s.
- В Docker аналога нет (есть только compose-проекты без общих namespaces).

## 7. Совместимость с Docker

- **CLI почти идентичен**: `alias docker=podman` в большинстве случаев работает.
- **Docker-compatible API**: `podman system service` поднимает REST-сокет (по запросу, через socket activation, а не постоянным демоном). Через него работают `docker-compose`, Testcontainers и прочие клиенты Docker API.
- **Compose**: поддерживается через `podman compose` (внешний провайдер) или `docker-compose` поверх сокета.
- Формат образов — **OCI**, образы полностью взаимозаменяемы; registry те же.
- Отличия: нет Swarm, часть сетевых фич и `docker network`-поведения реализована иначе, `--link` не поддерживается.

## 8. Дополнительные детали, которые стоит знать

- **Конфигурация**: `containers.conf`, `storage.conf`, `registries.conf`, `policy.json` — общие для семейства инструментов (podman, buildah, skopeo, CRI-O).
- **Образы**: Podman не использует `containerd`-хранилище; слои лежат в `containers/storage`. Это же хранилище разделяют `buildah` и `CRI-O`.
- **Fully-qualified имена**: из соображений безопасности Podman предпочитает полные имена (`docker.io/library/nginx`) и спрашивает/настраивает `unqualified-search-registries`.
- **SELinux**: тома нужно монтировать с `:z` / `:Z`, иначе контейнер не получит доступ на SELinux-системах (Fedora/RHEL).
- **На macOS/Windows**: Podman запускает Linux VM (`podman machine`), как и Docker Desktop.

## 9. Итоговое сравнение

|Аспект|Docker|Podman|
|---|---|---|
|Архитектура|клиент-сервер, демон|daemonless, fork/exec|
|Привилегии по умолчанию|root-демон|rootless-first|
|Родитель контейнера|containerd-shim|conmon|
|Супервизор|демон (`--restart`)|systemd / Quadlet|
|Группировка|compose|pods (как в k8s)|
|Сборка|BuildKit|Buildah|
|Хранилище|у демона, одно на хост|у каждого пользователя своё|
|Сеть|`docker0` bridge, `libnetwork`|`netavark`, в rootless — `pasta`|
|Kubernetes|—|`kube play` / `generate kube`|
|Единая точка отказа|`dockerd`|нет|

## 10. Мысленная модель

Docker = **«платформа-сервис»**: один привилегированный демон знает всё и выполняет команды клиентов. Podman = **«набор библиотек + CLI»**: каждая команда сама выполняет работу под вашим UID, а долгоживущие функции (мониторинг, автозапуск) отдаются `conmon` и `systemd`.

## Связанное

- [[Linux namespaces]]
- [[cgroups v2]]
- [[OCI runtime-spec]]
- [[Buildah]], [[Skopeo]], [[CRI-O]]