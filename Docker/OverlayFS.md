# `lowerdir`, `upperdir`, `workdir` и `merged`

OverlayFS объединяет несколько директорий в одно виртуальное файловое дерево.

При этом файлы физически не копируются в одну общую директорию. OverlayFS создаёт mount, через который несколько слоёв выглядят как одна файловая система.

Упрощённо:

```text
lowerdir + upperdir
        │
   workdir помогает
        │
        ▼
    OverlayFS
        │
        ▼
      merged
```

---

## `lowerdir`

`lowerdir` — нижний слой OverlayFS.

Обычно он используется как **read-only источник файлов**.

Например:

```text
/lower/
├── etc/
│   └── nginx.conf
├── usr/
└── var/
```

OverlayFS может читать эти файлы, но изменения в `lowerdir` напрямую не записывает.

### Несколько `lowerdir`

OverlayFS может использовать сразу несколько нижних директорий:

```text
lowerdir=/layer3:/layer2:/layer1
```

Логически:

```text
layer3
────────
layer2
────────
layer1
```

Если один файл существует в нескольких слоях, будет видна версия из самого верхнего слоя.

Например:

```text
layer1/etc/config
layer2/etc/config
```

В итоговом файловом дереве будет видна:

```text
layer2/etc/config
```

При этом файл из `layer1` физически никуда не исчезает.

---

## `upperdir`

`upperdir` — **изменяемый слой OverlayFS**.

Все новые файлы и изменения записываются сюда.

Например:

```text
/upper/
```

Допустим в `lowerdir` находится:

```text
/lower/etc/nginx.conf
```

Процесс пытается выполнить:

```bash
echo "test" >> /etc/nginx.conf
```

OverlayFS не может изменить файл непосредственно в `lowerdir`.

Поэтому происходит механизм **copy-up**:

```text
/lower/etc/nginx.conf
        │
        │ copy-up
        ▼
/upper/etc/nginx.conf
```

После этого изменяется уже верхняя копия.

Получаем:

```text
lowerdir
└── etc/nginx.conf
        ↑
        оригинальная версия

upperdir
└── etc/nginx.conf
        ↑
        изменённая версия
```

В итоговом файловом дереве OverlayFS покажет версию из `upperdir`.

---

## Copy-on-write

OverlayFS использует принцип **copy-on-write**.

Пока файл только читается:

```text
process
   ↓
OverlayFS
   ↓
lowerdir
```

никакой копии не создаётся.

Если файл нужно изменить:

```text
process
   ↓
WRITE
   ↓
OverlayFS
   ↓
copy-up
   ↓
upperdir
   ↓
изменение файла
```

Таким образом исходный нижний слой остаётся неизменным.

---

## `workdir`

`workdir` — служебная директория OverlayFS.

Например:

```text
/work/
```

Она **не является файловым слоем**.

Неправильно представлять:

```text
upper
──────
work
──────
lower
```

`workdir` используется ядром для внутренних операций OverlayFS.

Например:

```text
lower
  │
  │ нужно изменить файл
  ▼
OverlayFS
  │
  ├── использует workdir
  │
  ▼
upper
```

Он может использоваться во время:

- `copy-up`;
    
- `rename`;
    
- атомарных файловых операций;
    
- других внутренних действий OverlayFS.
    

Пользователь обычно не должен напрямую работать с содержимым `workdir`.

`workdir` должен находиться на той же файловой системе, что и `upperdir`.

Например:

```text
/dev/sda1

/container/
├── upper/
└── work/
```

---

## `merged`

Кроме трёх директорий:

```text
lowerdir
upperdir
workdir
```

есть ещё mount point, который обычно условно называют:

```text
merged
```

Например:

```bash
mount -t overlay overlay \
    -o lowerdir=/lower,upperdir=/upper,workdir=/work \
    /merged
```

Здесь:

```text
/lower
/upper
/work
```

— реальные директории.

А:

```text
/merged
```

— mount point OverlayFS.

Именно через него пользователь или процесс видит итоговую файловую систему.

---

## Пример объединения

Физически:

```text
lower/
├── a.txt
├── b.txt
└── etc/
    └── config
```

И:

```text
upper/
├── b.txt
└── c.txt
```

OverlayFS покажет:

```text
merged/
├── a.txt
├── b.txt
├── c.txt
└── etc/
    └── config
```

При этом:

```text
a.txt
```

берётся из:

```text
lower
```

`b.txt` существует в обоих слоях:

```text
lower/b.txt
upper/b.txt
```

но будет показан:

```text
upper/b.txt
```

`c.txt` существует только в:

```text
upper
```

---

## Роль директорий

```text
lowerdir
```

— откуда брать исходные файлы.

```text
upperdir
```

— куда записывать изменения.

```text
workdir
```

— служебная директория самого OverlayFS.

```text
merged
```

— итоговое виртуальное файловое дерево, которое видит процесс.

---

# OverlayFS в Docker / containerd

При работе Docker image containerd может иметь несколько snapshots:

```text
snapshot 35
snapshot 36
snapshot 37
snapshot 38
...
snapshot 41
```

Они представляют файловые изменения разных слоёв image.

При запуске контейнера создаётся ещё один writable snapshot:

```text
snapshot 42
```

Концептуально OverlayFS получает:

```text
lowerdir:
    snapshot41/fs
    snapshot40/fs
    snapshot39/fs
    ...
    snapshot35/fs
```

А writable snapshot используется как:

```text
upperdir:
    snapshot42/fs
```

Его служебная директория:

```text
workdir:
    snapshot42/work
```

Получается:

```text
snapshot41/fs ───────┐
snapshot40/fs ───────┤
snapshot39/fs ───────┤
...                   ├─────┐
snapshot35/fs ───────┘     │
                           │
snapshot42/fs ─ upperdir ──┼── OverlayFS
                           │
snapshot42/work ─ workdir ─┘
                           │
                           ▼
                       merged rootfs
                           │
                           ▼
                           /
                  ┌────────┼────────┐
                  ▼        ▼        ▼
                 etc      usr      var
```

Именно объединённое дерево затем используется как root filesystem контейнера.

---

# Что происходит при чтении

Допустим процесс внутри контейнера выполняет:

```bash
cat /usr/bin/bash
```

Если файл существует только в:

```text
snapshot35/fs/usr/bin/bash
```

OverlayFS просто направляет чтение туда:

```text
process
   │
   ▼
OverlayFS
   │
   ▼
snapshot35/fs/usr/bin/bash
```

Файл при этом не копируется.

---

# Что происходит при изменении

Допустим:

```text
snapshot36/fs/etc/nginx/nginx.conf
```

является частью image.

Контейнер выполняет:

```bash
echo "test" >> /etc/nginx/nginx.conf
```

OverlayFS делает:

```text
snapshot36/fs/etc/nginx/nginx.conf
                │
                │ copy-up
                ▼
snapshot42/fs/etc/nginx/nginx.conf
```

После этого изменение происходит только в:

```text
snapshot42
```

Image остаётся неизменным.

Логически:

```text
IMAGE

snapshot36
└── nginx.conf
        ↑
        read-only

CONTAINER

snapshot42
└── nginx.conf
        ↑
        writable
```

---

# Главное

OverlayFS не делает:

```text
snapshot35
snapshot36
snapshot37
       │
       ▼
COPY
       │
       ▼
final_rootfs/
```

Вместо этого:

```text
snapshot35 ─┐
snapshot36 ─┤
snapshot37 ─┤
...         ├── OverlayFS
snapshot41 ─┤
snapshot42 ─┘
             │
             ▼
        virtual merged rootfs
```

Файлы продолжают физически лежать в своих слоях.

OverlayFS только предоставляет единое представление этих слоёв через mount point.

Коротко:

```text
lowerdir
= исходные read-only файлы

upperdir
= изменения и новые файлы

workdir
= служебная директория OverlayFS

merged
= итоговое дерево, которое видит процесс
```