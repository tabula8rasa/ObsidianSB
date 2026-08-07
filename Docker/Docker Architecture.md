## Что такое Docker

**Docker** — это платформа для создания, запуска и управления контейнерами.

Контейнер позволяет запустить приложение в изолированном окружении вместе с его зависимостями:

```text
Application
├── Python / Java / Node.js
├── Libraries
├── Configuration
└── System dependencies
```

При этом контейнер, в отличие от полноценной виртуальной машины, обычно **не содержит собственного ядра ОС**. Контейнеры используют ядро хостовой Linux-системы.

Основная идея:

```text
Virtual Machine
───────────────
Application
Libraries
Guest OS
Guest Kernel
Hypervisor
Host OS
Hardware


Container
─────────
Application
Libraries
Container isolation
Host Linux Kernel
Hardware
```

Docker в первую очередь предоставляет удобный высокоуровневый интерфейс над механизмами контейнеризации Linux.

---

## Docker на Linux, Windows и macOS

### Linux

На Linux Docker работает **нативно**, потому что необходимые механизмы контейнеризации находятся непосредственно в ядре Linux.

Docker использует, в частности:

- **namespaces** — изоляция процессов;
- **cgroups** — ограничение и учет ресурсов;
- Linux capabilities;
- seccomp;
- файловые системы и mount namespaces;
- сетевые возможности ядра Linux.

Схематично:

```text
Docker
   ↓
Linux Kernel
   ↓
Hardware
```

---

### macOS

macOS не использует Linux kernel, поэтому Linux-контейнер нельзя запустить непосредственно на ядре macOS.

Docker Desktop запускает небольшую Linux-виртуальную машину:

```text
macOS
  ↓
Docker Desktop
  ↓
Linux VM
  ↓
Docker Engine
  ↓
Containers
```

Когда пользователь выполняет:

```bash
docker run nginx
```

команда отправляется Docker Engine, который работает внутри Linux-среды Docker Desktop.

---

### Windows

На Windows возможны разные варианты.

Для **Linux-контейнеров** Docker Desktop обычно использует **WSL 2**, внутри которого работает Linux kernel.

Упрощенно:

```text
Windows
  ↓
Docker Desktop
  ↓
WSL 2 / Linux kernel
  ↓
Docker Engine
  ↓
Linux containers
```

Windows также поддерживает отдельный механизм **Windows Containers**, которые используют Windows kernel.

Поэтому утверждение:

> Docker всегда требует Linux

верно только для **Linux-контейнеров**.

---

# Общая архитектура Docker

Docker использует клиент-серверную архитектуру.

Основные компоненты:

```text
Docker CLI
    ↓
Docker API
    ↓
dockerd
    ↓
containerd
    ↓
containerd-shim
    ↓
runc
    ↓
Linux Kernel
```

Основные уровни:

1. `docker` — клиент командной строки.
2. `dockerd` — Docker Daemon.
3. `containerd` — управление жизненным циклом контейнеров.
4. `containerd-shim` — промежуточный процесс между containerd и контейнером.
5. `runc` — низкоуровневое создание контейнера.
6. Linux kernel — реальная изоляция процессов.

---

# Docker Client

**Docker Client** — программа, которой пользователь управляет Docker.

Обычно это команда:

```bash
docker
```

Например:

```bash
docker run nginx
```

или:

```bash
docker ps
```

или:

```bash
docker build -t my-app .
```

Docker CLI сам контейнеры не создает.

Он превращает команды пользователя в запросы к **Docker Engine API**.

Упрощенно:

```text
docker run nginx

        ↓

HTTP request

        ↓

Docker Daemon
```

---

# Docker API

Docker Client взаимодействует с Docker Daemon через HTTP API.

Если клиент и демон находятся на одном Linux-хосте, обычно используется Unix socket:

```text
/var/run/docker.sock
```

Например:

```text
Docker CLI
    │
    │ HTTP over Unix socket
    ▼
/var/run/docker.sock
    │
    ▼
dockerd
```

То есть даже локальная команда:

```bash
docker ps
```

по сути является API-запросом к Docker Daemon.

---

## Docker socket

Файл:

```text
/var/run/docker.sock
```

является Unix domain socket.

Через него можно управлять Docker Engine.

Например:

```bash
curl --unix-socket /var/run/docker.sock \
  http://localhost/containers/json
```

Docker CLI просто предоставляет удобный интерфейс поверх такого API.

---

## Безопасность docker.sock

Доступ к:

```text
/var/run/docker.sock
```

фактически дает очень высокие привилегии на хосте.

Пользователь, способный управлять Docker Daemon, во многих случаях может получить практически root-доступ к машине.

Поэтому не следует без необходимости:

```text
mount /var/run/docker.sock
```

внутрь контейнеров.

---

# Docker Daemon — dockerd

Основной серверный процесс Docker называется:

```text
dockerd
```

Он часто и называется **Docker Daemon** или частью **Docker Engine**.

Он отвечает за высокоуровневое управление объектами Docker:

- containers;
- images;
- networks;
- volumes;
- build operations;
- Docker API;
- взаимодействие с registry;
- взаимодействие с `containerd`.

Схематично:

```text
Docker CLI
    ↓
dockerd
    ├── images
    ├── containers
    ├── volumes
    ├── networks
    └── containerd
```

---

# containerd

**containerd** — отдельный контейнерный runtime-демон.

Docker использует его для управления жизненным циклом контейнеров.

Упрощенно containerd отвечает за:

- получение и хранение образов;
- управление snapshot-ами файловой системы;
- создание и запуск контейнеров через OCI runtime;
- остановку контейнеров;
- удаление контейнеров;
- отслеживание состояния контейнерных процессов.

Docker Daemon взаимодействует с containerd через API, основанное на **gRPC**.

```text
dockerd
   │
   │ gRPC
   ▼
containerd
```

Важно понимать:

**Docker-сети высокого уровня**, такие как:

```text
bridge
host
overlay
```

являются прежде всего частью Docker Engine и его сетевого стека.

Поэтому выражение:

> containerd сам полностью создает Docker-сеть

слишком упрощенное.

---

# runc

**runc** — низкоуровневый OCI-compatible runtime.

Именно он непосредственно занимается созданием контейнера на уровне Linux.

`runc` получает описание контейнера и выполняет необходимые операции с ядром:

- создает namespaces;
- применяет cgroups;
- настраивает mounts;
- применяет capabilities;
- настраивает root filesystem;
- запускает основной процесс контейнера.

Упрощенно:

```text
runc
 ↓
Linux syscalls
 ↓
Namespaces + Cgroups + Mounts + Security
 ↓
Container process
```

---

# OCI

**OCI — Open Container Initiative** — организация и набор стандартов контейнерной экосистемы.

Основные спецификации OCI:

```text
OCI Image Specification
OCI Runtime Specification
OCI Distribution Specification
```

`runc` является одной из наиболее известных реализаций **OCI Runtime Specification**.

Это означает, что структура контейнера и правила его запуска стандартизированы и не являются исключительно внутренним форматом Docker.

---

# containerd-shim

Между `containerd` и реальным процессом контейнера существует специальный процесс:

```text
containerd-shim
```

Современная схема выглядит примерно так:

```text
dockerd
   ↓
containerd
   ↓
containerd-shim
   ↓
container process
```

`runc` в основном нужен именно в момент создания или выполнения операций над контейнером.

Упрощенно:

```text
containerd
    ↓
shim
    ↓
runc creates container
    ↓
container process starts
    ↓
runc exits
    ↓
shim remains alive
```

---

## Зачем нужен shim

Shim позволяет процессу контейнера не зависеть непосредственно от постоянной работы `runc` и самого `containerd`.

Он:

- сохраняет stdin/stdout контейнера;
- отслеживает код завершения процесса;
- служит родительской/промежуточной прослойкой для контейнерного процесса;
- позволяет `runc` завершиться после запуска контейнера;
- помогает отделить жизненный цикл контейнера от управляющих демонов.

Благодаря этому архитектура становится более устойчивой.

---

# Почему runc не работает постоянно

Можно представить, что `runc` — это инструмент, который **создает окружение контейнера и запускает процесс**, после чего его постоянное присутствие больше не требуется.

Например:

```text
containerd
   ↓
runc
   ↓
create namespaces
create cgroups
mount filesystem
start process
   ↓
runc exits
```

Но основной процесс приложения продолжает работать:

```text
nginx
python
postgres
java
...
```

---

# Что на самом деле является контейнером

Контейнер — это **не виртуальная машина и не отдельная ОС**.

С точки зрения Linux это обычный процесс или группа процессов, к которым применены механизмы изоляции.

Например:

```text
Host processes

PID 1    systemd
PID 812  sshd
PID 941  dockerd
PID 1050 containerd
PID 2100 nginx
```

Процесс `nginx` может быть процессом внутри Docker-контейнера.

Но ядро Linux по-прежнему видит его как обычный процесс.

Docker просто запускает его с:

```text
PID namespace
Network namespace
Mount namespace
User namespace
Cgroups
Capabilities
Seccomp
...
```

В результате процессу кажется, что у него есть отдельная среда.

---

# Namespaces

**Namespaces** отвечают за изоляцию.

Они позволяют разным группам процессов видеть разные представления одной системы.

Основные namespaces:

| Namespace | Что изолирует |
|---|---|
| PID | процессы |
| NET | сетевые интерфейсы, маршруты, порты |
| MNT | точки монтирования |
| UTS | hostname и domain name |
| IPC | shared memory, message queues |
| USER | пользователей и UID/GID |
| CGROUP | представление cgroups |

Например, PID namespace позволяет процессу внутри контейнера видеть:

```text
PID 1
PID 7
PID 12
```

хотя на самом хосте эти же процессы могут иметь PID:

```text
PID 5231
PID 5250
PID 5278
```

---

# Cgroups

**Control Groups — cgroups** отвечают прежде всего за учет и ограничение ресурсов.

Через них можно ограничивать:

```text
CPU
RAM
I/O
number of processes
```

Например:

```bash
docker run \
  --memory=512m \
  --cpus=1 \
  nginx
```

Docker настроит соответствующие ограничения через cgroups.

---

# Полный путь docker run

Рассмотрим:

```bash
docker run nginx
```

## Шаг 1. Docker CLI

Пользователь выполняет:

```bash
docker run nginx
```

Docker Client формирует API-запрос.

```text
User
 ↓
docker CLI
 ↓
Docker API request
```

---

## Шаг 2. Docker Daemon

Запрос получает:

```text
dockerd
```

Если нужного образа нет локально, Docker Engine инициирует получение образа из registry.

Например:

```text
Docker Hub
```

---

## Шаг 3. Подготовка Docker-объектов

Docker Engine подготавливает высокоуровневую конфигурацию:

- container metadata;
- volumes;
- Docker networking;
- port mappings;
- environment variables;
- filesystem configuration.

После этого задача запуска контейнера передается `containerd`.

---

## Шаг 4. containerd

`containerd` подготавливает низкоуровневую контейнерную среду:

```text
image
 ↓
snapshot
 ↓
container metadata
 ↓
task
```

Для запуска создается shim-процесс.

---

## Шаг 5. containerd-shim

Shim управляет связью с контейнерным процессом и инициирует запуск OCI runtime.

```text
containerd
    ↓
containerd-shim
    ↓
runc
```

---

## Шаг 6. runc

`runc` создает необходимые Linux namespaces и применяет ограничения.

Примерно:

```text
create PID namespace
create NET namespace
create MNT namespace
apply cgroups
mount root filesystem
apply security settings
start process
```

После этого запускается команда из образа.

Например:

```text
nginx
```

---

## Шаг 7. runc завершает работу

После успешного запуска приложения постоянная работа `runc` больше не требуется.

Остаются:

```text
dockerd
containerd
containerd-shim
nginx
```

Схема:

```text
docker CLI
    ↓
dockerd
    ↓
containerd
    ↓
containerd-shim
    ↓
nginx
```

---

# Полная архитектурная схема

```text
┌─────────────────────────┐
│        Docker CLI       │
│                        │
│ docker run             │
│ docker ps              │
│ docker pull            │
└────────────┬────────────┘
             │
             │ Docker Engine API
             │ HTTP / Unix Socket
             ▼
┌─────────────────────────┐
│         dockerd         │
│                        │
│ containers             │
│ images                 │
│ networks               │
│ volumes                │
│ API                    │
└────────────┬────────────┘
             │
             │ gRPC
             ▼
┌─────────────────────────┐
│       containerd        │
│                        │
│ image lifecycle        │
│ snapshots              │
│ container lifecycle    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   containerd-shim       │
└────────────┬────────────┘
             │
             │ invokes
             ▼
┌─────────────────────────┐
│          runc           │
│                        │
│ OCI Runtime            │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│       Linux Kernel      │
│                        │
│ namespaces             │
│ cgroups                │
│ capabilities           │
│ seccomp                │
│ mounts                 │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Application Process   │
│                        │
│ nginx / python / java  │
└─────────────────────────┘
```

---

# Что происходит с образом

Перед запуском контейнера Docker работает с **image**.

Образ — неизменяемый шаблон файловой системы и конфигурации приложения.

Например:

```text
nginx image

Layer 4
Layer 3
Layer 2
Layer 1
```

При создании контейнера поверх read-only слоев образа добавляется writable layer:

```text
Container writable layer
────────────────────────
Image layer 4
Image layer 3
Image layer 2
Image layer 1
```

Таким образом:

```text
Image = шаблон

Container = запущенный экземпляр image
```

---

# Docker Registry

Образы Docker обычно хранятся в registry.

Например:

```text
Docker Hub
GitHub Container Registry
GitLab Container Registry
Amazon ECR
Google Artifact Registry
Harbor
```

При выполнении:

```bash
docker pull nginx
```

происходит примерно следующее:

```text
Docker CLI
 ↓
dockerd
 ↓
registry
 ↓
download image layers
 ↓
local image storage
```

После этого образ можно использовать для создания контейнера.

---

# Локальное взаимодействие клиента и демона

Обычно:

```text
Docker CLI
 ↓
Unix socket
 ↓
dockerd
```

Socket:

```text
/var/run/docker.sock
```

То есть здесь TCP вообще не нужен.

---

# Удаленное управление Docker

Docker Client и Docker Daemon могут находиться на разных машинах.

Например:

```text
Laptop
  │
  │ network
  ▼
Server
  │
  └── dockerd
```

Docker Daemon может слушать TCP socket.

Исторически часто встречаются:

```text
2375 — Docker API без TLS
2376 — Docker API с TLS
```

Однако открывать Docker API без защиты опасно.

Например:

```text
tcp://0.0.0.0:2375
```

без аутентификации фактически позволяет удаленному клиенту полностью управлять Docker-хостом.

Поэтому такой Docker API нельзя просто публиковать в интернет.

---

# TLS

Для удаленного управления Docker можно использовать TLS.

Схема:

```text
Docker Client
    │
    │ HTTPS / TLS
    ▼
Docker Daemon
```

При использовании mutual TLS:

```text
Client Certificate
Server Certificate
CA
```

сервер проверяет клиента, а клиент проверяет сервер.

Для production-инфраструктуры часто вместо прямого публичного Docker API используются:

- SSH;
- Kubernetes API;
- CI/CD agents;
- cloud management APIs;
- защищенные internal networks.

---

# Что будет при перезапуске dockerd

Современная архитектура Docker отделяет контейнерные процессы от самого `dockerd`.

Запущенные контейнеры связаны с `containerd` и `containerd-shim`, а не являются обычными дочерними процессами `dockerd`.

Это позволяет сделать архитектуру гораздо устойчивее.

Однако фраза:

> Docker Daemon всегда можно перезапустить, и контейнеры гарантированно продолжат работать

слишком сильная.

Поведение зависит от:

- конфигурации Docker;
- способа перезапуска;
- настроек `live-restore`;
- состояния `containerd`;
- версии Docker.

Docker имеет специальный механизм:

```text
live-restore
```

который предназначен для сохранения работающих контейнеров при недоступности Docker Daemon.

Пример настройки:

```json
{
  "live-restore": true
}
```

---

# Docker Engine и containerd — зачем два демона

На первый взгляд может показаться, что:

```text
dockerd
containerd
```

делают одно и то же.

Но уровни ответственности разные.

### dockerd

Docker-specific высокоуровневая логика:

```text
Docker API
Docker networks
Docker volumes
Docker images
Docker build
Docker UX
```

### containerd

Более универсальное управление контейнерным runtime:

```text
image management
snapshots
container lifecycle
tasks
OCI runtime integration
```

`containerd` может использоваться и **без Docker**.

Например, Kubernetes может работать с containerd напрямую через CRI.

Схема:

```text
Docker
   ↓
containerd
   ↓
runc
```

или:

```text
Kubernetes
   ↓
containerd
   ↓
runc
```

---

# Docker и Kubernetes

Docker не является обязательной частью Kubernetes.

Современный Kubernetes обычно работает через CRI-compatible runtime.

Например:

```text
Kubernetes
    ↓
CRI
    ↓
containerd
    ↓
runc
```

То есть Docker и Kubernetes могут использовать одни и те же нижние уровни контейнерного стека.

---

# Главное, что нужно запомнить

Docker можно представить как несколько уровней:

```text
docker CLI
    ↓
dockerd
    ↓
containerd
    ↓
containerd-shim
    ↓
runc
    ↓
Linux Kernel
    ↓
Application process
```

Где:

| Компонент | Роль |
|---|---|
| `docker` | интерфейс пользователя |
| `dockerd` | высокоуровневое управление Docker |
| `containerd` | жизненный цикл контейнеров |
| `containerd-shim` | отделяет процесс контейнера от runtime-демона |
| `runc` | непосредственно создает Linux-контейнер |
| Linux kernel | обеспечивает namespaces, cgroups и другие механизмы |
| container process | обычный Linux-процесс в изолированном окружении |

Самая важная мысль:

> **Docker-контейнер — это не маленькая виртуальная машина. Это обычный процесс Linux, который ядро изолировало при помощи namespaces, cgroups и других механизмов.**

Docker предоставляет удобную систему, которая автоматизирует создание и управление такими изолированными процессами.

---

# Короткая схема запуска

```bash
docker run nginx
```

```text
docker CLI
    ↓
Docker API
    ↓
dockerd
    ↓
containerd
    ↓
containerd-shim
    ↓
runc
    ↓
Linux namespaces + cgroups
    ↓
nginx process
```

После запуска:

```text
runc exits

containerd-shim
      ↓
nginx
```

А сам контейнер продолжает работать.
