`cgroups` (**control groups**) — механизм Linux kernel для объединения процессов в группы, учёта их ресурсов и установки ограничений на использование этих ресурсов.

Если [[Linux_Namespaces_unshare]] отвечают на вопрос:

> **Что процесс видит?**

то `cgroups` отвечают на вопрос:

> **Сколько ресурсов процесс может использовать?**

---

## Основная идея

Допустим, на машине работают:

```text
python
nginx
postgres
```

Их можно объединить в одну cgroup:

```text
/my-container
├── python
├── nginx
└── postgres
```

После этого Linux может установить ограничения сразу для всей группы:

```text
RAM максимум 1 GB
CPU максимум 50%
не больше 100 процессов
ограничение дискового I/O
```

Контроль выполняет само ядро Linux.

---

# Зачем cgroups нужны контейнерам

Одних namespaces недостаточно.

Например, контейнеру можно дать отдельные:

```text
PID namespace
NET namespace
MNT namespace
UTS namespace
```

Но процесс всё ещё может попытаться использовать:

```text
всю RAM
100% всех CPU
огромное количество процессов
весь доступный I/O
```

Namespaces это не ограничивают.

Для ограничения ресурсов используются `cgroups`.

---

# Связь с Docker

Например:

```bash
docker run --memory=512m nginx
```

Docker не реализует собственный механизм ограничения памяти.

Упрощённо он создаёт/настраивает cgroup контейнера:

```text
cgroup container-123
│
├── nginx
│
└── memory.max = 512 MB
```

Когда процесс пытается получить память:

```text
nginx
   │
   │ malloc()
   ▼
Linux kernel
   │
   │ проверяет cgroup
   ▼
memory.max
```

Лимит контролируется ядром.

---

# cgroup v2

В современных Linux обычно используется **cgroup v2**.

Проверить:

```bash
mount | grep cgroup
```

Обычно будет:

```text
cgroup2 on /sys/fs/cgroup type cgroup2
```

Основной интерфейс находится здесь:

```text
/sys/fs/cgroup
```

Посмотреть:

```bash
ls /sys/fs/cgroup
```

Можно увидеть файлы:

```text
cgroup.procs

cpu.max
cpu.stat

memory.max
memory.current
memory.stat

pids.max
pids.current

io.max
...
```

Это не обычные файлы на диске.

`/sys/fs/cgroup` — виртуальная файловая система, через которую userspace взаимодействует с механизмом cgroups в ядре.

---

# Процессы внутри cgroup

В каждой cgroup есть файл:

```text
cgroup.procs
```

Он содержит PID процессов, принадлежащих группе.

Например:

```text
18342
18351
18377
```

означает:

```text
PID 18342 ─┐
PID 18351 ─┼── cgroup
PID 18377 ─┘
```

Условная структура:

```text
/sys/fs/cgroup/my-container/
├── cgroup.procs
├── memory.max
├── memory.current
├── cpu.max
└── pids.max
```

---

# Основные контроллеры

## Memory

Ограничивает и учитывает использование RAM.

```text
memory.max
```

Максимально разрешённая память.

```text
memory.current
```

Текущее использование памяти.

```text
memory.stat
```

Подробная статистика.

---

## CPU

Управляет использованием процессорного времени.

```text
cpu.max
```

Позволяет ограничить доступное CPU-время.

```text
cpu.stat
```

Статистика использования CPU.

---

## PIDs

Ограничивает количество процессов.

```text
pids.max
```

Максимально допустимое число процессов.

```text
pids.current
```

Текущее число процессов.

Это защищает систему, например, от fork bomb.

---

## I/O

Управляет использованием блочных устройств.

```text
io.max
```

Позволяет ограничивать дисковый ввод-вывод.

---

# cgroup namespace — не то же самое, что cgroups

Нужно различать:

```text
cgroups
```

и:

```text
cgroup namespace
```

**cgroups** реально ограничивают и учитывают ресурсы:

```text
CPU
RAM
I/O
PIDs
```

**cgroup namespace** изолирует представление cgroup-иерархии для процесса.

Сам по себе cgroup namespace не создаёт лимиты ресурсов.

---

# Итоговая модель контейнера

После изучения `chroot`, namespaces и cgroups контейнер можно представить так:

```text
Linux process
     │
     ├── rootfs / chroot
     │      └── какие файлы процесс считает своей системой
     │
     ├── namespaces
     │      └── что процесс видит
     │
     │          PID
     │          network
     │          mounts
     │          hostname
     │          IPC
     │          users
     │
     └── cgroups
            └── сколько ресурсов процесс может использовать

                CPU
                RAM
                I/O
                количество процессов
```

К этому контейнерные runtime дополнительно добавляют:

```text
capabilities
seccomp
rootfs
mounts
network configuration
и другие ограничения
```

Коротко:

> **Namespaces изолируют представление системы, а cgroups ограничивают ресурсы процессов.**
