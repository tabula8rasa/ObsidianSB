## Где Docker держит примонтированный rootfs контейнера

На моей системе готовый rootfs каждого контейнера примонтирован в:

```text
/var/lib/docker/rootfs/overlayfs/<container-id>/
```

Например:

```text
/var/lib/docker/rootfs/overlayfs/
├── 06d2c5a7d2e616f8fb43e6b3b3f76194421ec93841852540c5088c4b3614cee8/
└── ce5cdcd23cfd6fa39b96477a90411cce722e590e441a355fe565b9ee133480d3/
```

Внутри видна уже обычная полноценная Linux root filesystem:

```text
/var/lib/docker/rootfs/overlayfs/<container-id>/
├── bin -> usr/bin
├── boot
├── dev
├── docker-entrypoint.d
├── docker-entrypoint.sh
├── etc
├── home
├── lib -> usr/lib
├── lib64 -> usr/lib64
├── media
├── mnt
├── opt
├── proc
├── root
├── run
├── sbin -> usr/sbin
├── srv
├── sys
├── tmp
├── usr
└── var
```

Важно: эта директория — **не отдельная физическая копия всех файлов контейнера**.

Это **mount point OverlayFS**, в который Docker монтирует объединённое представление файловых слоёв image и writable-слоя конкретного контейнера.

То есть:

```text
/var/lib/docker/rootfs/overlayfs/<container-id>
                    │
                    │ mount
                    ▼
                 OverlayFS
                    │
        ┌───────────┴───────────┐
        │                       │
   image snapshots       writable snapshot
     lowerdir                upperdir
```

---

# Где физически лежат snapshots

На моей системе backing storage OverlayFS находится в containerd:

```text
/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/
```

Например:

```text
/var/lib/containerd/
└── io.containerd.snapshotter.v1.overlayfs/
    └── snapshots/
        ├── 42/
        │   ├── fs/
        │   └── work/
        ├── 43/
        │   └── fs/
        ├── 44/
        │   └── fs/
        ├── ...
        ├── 51/
        │   └── fs/
        └── 52/
            ├── fs/
            └── work/
```

`fs/` содержит файловые данные snapshot.

Для writable snapshot также используется `work/`, который нужен самому OverlayFS для внутренних операций.

---

# Как увидеть rootfs конкретного контейнера

Сначала можно получить ID контейнера:

```bash
docker ps -a
```

Например:

```text
ce5cdcd23cfd6fa39b96477a90411cce722e590e441a355fe565b9ee133480d3
```

Сохраним его:

```bash
ID=ce5cdcd23cfd6fa39b96477a90411cce722e590e441a355fe565b9ee133480d3
```

Теперь rootfs контейнера доступен здесь:

```bash
ls /var/lib/docker/rootfs/overlayfs/$ID
```

или:

```bash
eza --tree --level 2 /var/lib/docker/rootfs/overlayfs/$ID
```

---

# Как доказать, что это OverlayFS mount

Команда:

```bash
findmnt -T /var/lib/docker/rootfs/overlayfs/$ID
```

показывает mount, которому принадлежит этот путь.

Но обычный вывод может обрезать длинную колонку `OPTIONS`.

Поэтому удобнее использовать:

```bash
findmnt -u -T /var/lib/docker/rootfs/overlayfs/$ID
```

или вывести только mount options без обрезания:

```bash
findmnt -u -n -o OPTIONS -T /var/lib/docker/rootfs/overlayfs/$ID
```

На моей системе я получил:

```text
rw,relatime,lowerdir=/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/51/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/48/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/47/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/46/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/45/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/44/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/43/fs:/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/42/fs,upperdir=/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/52/fs,workdir=/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/52/work,index=off
```

Это прямое доказательство того, из каких директорий OverlayFS собирает rootfs этого контейнера.

---

# Разбор найденного mount

В моём случае:

```text
lowerdir=
    snapshots/51/fs
    snapshots/48/fs
    snapshots/47/fs
    snapshots/46/fs
    snapshots/45/fs
    snapshots/44/fs
    snapshots/43/fs
    snapshots/42/fs
```

Это read-only слои image.

Далее:

```text
upperdir=
    snapshots/52/fs
```

Это writable слой именно этого контейнера.

И:

```text
workdir=
    snapshots/52/work
```

Это служебная директория OverlayFS.

Полная схема:

```text
snapshot 51/fs ─────┐
snapshot 48/fs ─────┤
snapshot 47/fs ─────┤
snapshot 46/fs ─────┤
snapshot 45/fs ─────┤
snapshot 44/fs ─────┤
snapshot 43/fs ─────┤
snapshot 42/fs ─────┤
                    │
snapshot 52/fs ─────┼── OverlayFS
   upperdir         │
                    │
snapshot 52/work ───┘
   workdir
                    │
                    ▼
/var/lib/docker/rootfs/overlayfs/<container-id>
                    │
                    ▼
                    /
          ┌─────────┼─────────┐
          ▼         ▼         ▼
         etc       usr       var
```

---

# Что такое `lowerdir`

`lowerdir` — это исходные read-only слои.

В моём случае:

```text
51:48:47:46:45:44:43:42
```

Они соответствуют snapshot-слоям, из которых состоит image.

Их физические данные находятся в:

```text
/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/<id>/fs
```

Например:

```text
/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/42/fs
```

Важно: номера snapshot вроде `42`, `43`, `44`, `48`, `51` — внутренние ID containerd. Они не обязаны идти подряд, потому что между ними containerd мог создавать другие snapshots.

---

# Что такое `upperdir`

Для каждого запущенного контейнера создаётся свой writable snapshot.

В моём примере:

```text
upperdir=/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/52/fs
```

Все изменения файловой системы конкретного контейнера попадают сюда.

Например, если внутри контейнера выполнить:

```bash
touch /opadpa.txt
```

то логически файл виден как:

```text
/opadpa.txt
```

через:

```text
/var/lib/docker/rootfs/overlayfs/<container-id>/opadpa.txt
```

а физически изменение относится к writable snapshot контейнера:

```text
/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/52/fs/
```

---

# Copy-on-write

Если контейнер просто читает файл из image:

```text
/usr/bin/bash
```

OverlayFS может читать его непосредственно из одного из `lowerdir`.

Копирование не происходит.

```text
container
    │
    │ read
    ▼
OverlayFS
    │
    ▼
lowerdir
```

Если контейнер пытается изменить файл из lower layer, OverlayFS выполняет `copy-up`.

Например:

```text
lowerdir/etc/nginx/nginx.conf
              │
              │ copy-up
              ▼
upperdir/etc/nginx/nginx.conf
              │
              ▼
          изменение
```

После этого конкретный контейнер видит свою версию файла из `upperdir`, а исходный image layer остаётся неизменным.

---

# Где именно происходит экономия места

Это один из главных выводов из найденного mount.

Если из одного image запустить несколько контейнеров:

```bash
docker run nginx
docker run nginx
docker run nginx
```

не создаются три полные копии nginx rootfs.

Все контейнеры могут использовать одни и те же read-only `lowerdir` snapshots:

```text
                 image snapshots
                  42 ... 51
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
    container A container B container C
```

При этом для каждого контейнера создаётся только собственный writable слой:

```text
container A
upperdir = snapshot 52/fs

container B
upperdir = snapshot 53/fs

container C
upperdir = snapshot 54/fs
```

Получается:

```text
                    shared lowerdirs
                   snapshots 42...51
                          │
           ┌──────────────┼──────────────┐
           │              │              │
           ▼              ▼              ▼
     container A    container B    container C
           │              │              │
      upperdir 52     upperdir 53     upperdir 54
```

Именно здесь происходит существенная экономия дискового пространства:

- image layers хранятся один раз;
- один и тот же `lowerdir` может использоваться несколькими контейнерами;
- контейнер хранит отдельно только собственные изменения;
- файл из lower layer копируется в upper только тогда, когда контейнер действительно пытается его изменить.

Это и есть практическое проявление `copy-on-write`.

---

# Почему rootfs виден в `/var/lib/docker`, а snapshots лежат в `/var/lib/containerd`

Здесь участвуют два разных уровня.

Containerd хранит backing snapshots:

```text
/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/
```

Docker создаёт mount point для готового rootfs контейнера:

```text
/var/lib/docker/rootfs/overlayfs/<container-id>/
```

То есть:

```text
/var/lib/containerd/
        │
        │ physical snapshots
        ▼
   lowerdir + upperdir + workdir
        │
        ▼
     OverlayFS
        │
        │ mount
        ▼
/var/lib/docker/rootfs/overlayfs/<container-id>
```

Поэтому нельзя говорить, что все файлы rootfs физически скопированы в `/var/lib/docker/rootfs/...`.

Правильнее:

> `/var/lib/docker/rootfs/overlayfs/<container-id>` — mount point готового объединённого rootfs контейнера.

А реальные backing-файлы находятся в snapshot storage containerd.

---

# `/var/lib/docker/containers` и `/var/lib/docker/rootfs` — разные вещи

Для одного и того же container ID можно увидеть:

```text
/var/lib/docker/containers/<container-id>/
```

и:

```text
/var/lib/docker/rootfs/overlayfs/<container-id>/
```

Но их назначение разное.

## `/var/lib/docker/containers/<container-id>`

Содержит Docker-метаданные контейнера:

```text
/var/lib/docker/containers/<container-id>/
├── <container-id>-json.log
├── checkpoints/
├── config.v2.json
├── hostconfig.json
├── hostname
├── hosts
├── mounts/
├── resolv.conf
└── resolv.conf.hash
```

Здесь хранятся:

- конфигурация контейнера;
- host configuration;
- hostname;
- `/etc/hosts`;
- DNS-конфигурация;
- логи;
- сведения о mounts;
- другие служебные данные Docker.

## `/var/lib/docker/rootfs/overlayfs/<container-id>`

Это уже mount point готовой файловой системы контейнера:

```text
/
├── bin
├── etc
├── usr
├── var
└── ...
```

---

# Итоговая физическая архитектура

```text
Docker image
    │
    │ unpack
    ▼
containerd snapshotter

/var/lib/containerd/
└── io.containerd.snapshotter.v1.overlayfs/
    └── snapshots/
        ├── 42/fs
        ├── 43/fs
        ├── 44/fs
        ├── 45/fs
        ├── 46/fs
        ├── 47/fs
        ├── 48/fs
        ├── 51/fs
        │
        │   shared read-only lowerdirs
        │
        └── 52/
            ├── fs      ← upperdir конкретного контейнера
            └── work    ← workdir
                    │
                    ▼
                 OverlayFS
                    │
                    │ mount
                    ▼
/var/lib/docker/rootfs/overlayfs/<container-id>/
                    │
                    ▼
                    /
          ┌─────────┼─────────┐
          ▼         ▼         ▼
         etc       usr       var
```

---

# Основные команды для исследования

Получить контейнеры:

```bash
docker ps -a
```

Сохранить ID:

```bash
ID=<container-id>
```

Посмотреть готовый rootfs:

```bash
eza --tree --level 2 /var/lib/docker/rootfs/overlayfs/$ID
```

Узнать тип mount:

```bash
findmnt -T /var/lib/docker/rootfs/overlayfs/$ID
```

Показать полный вывод без обрезания:

```bash
findmnt -u -T /var/lib/docker/rootfs/overlayfs/$ID
```

Показать только параметры OverlayFS:

```bash
findmnt -u -n -o OPTIONS -T /var/lib/docker/rootfs/overlayfs/$ID
```

В этих параметрах нужно искать:

```text
lowerdir=
upperdir=
workdir=
```

Посмотреть сами snapshots:

```bash
eza --tree --level 2 \
/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/
```

---

# Главный вывод

Для каждого контейнера Docker предоставляет отдельный rootfs:

```text
/var/lib/docker/rootfs/overlayfs/<container-id>
```

Но этот rootfs не является отдельной полной копией image.

Он создаётся как OverlayFS mount:

```text
shared read-only image snapshots
            +
unique writable container snapshot
            +
workdir
            │
            ▼
         OverlayFS
            │
            ▼
     container rootfs
```

Поэтому несколько контейнеров одного image могут использовать одни и те же физические `lowerdir` snapshots.

Уникальными для каждого контейнера являются прежде всего его writable `upperdir` и соответствующий `workdir`.

Именно переиспользование общих read-only image layers плюс `copy-on-write` позволяет не создавать полную копию rootfs для каждого контейнера.
