`cgroups` — control groups.

Механизм Linux kernel для группировки процессов, учёта ресурсов и ограничения их использования.

Если namespaces отвечают:

> что process видит?

то cgroups:

> сколько ресурсов process/group может использовать?

---

# Основные контроллеры

```text
CPU
memory
PIDs
I/O
```

---

# cgroup v2

Проверить:

```bash
mount | grep cgroup
```

Основной интерфейс:

```text
/sys/fs/cgroup
```

Это виртуальная filesystem.

---

# Важные файлы

```text
cgroup.procs
memory.max
memory.current
memory.stat
cpu.max
cpu.stat
pids.max
pids.current
io.max
```

---

# Docker example

```bash
docker run --memory=512m nginx
```

```text
Docker option
    ↓
OCI resources
    ↓
runc
    ↓
cgroup
    ↓
Linux kernel enforces limit
```

---

# Почему namespaces недостаточно

Даже с отдельными PID/NET/MNT/UTS namespaces без cgroups process потенциально может использовать все RAM/CPU или создать слишком много processes.

---

# cgroup namespace ≠ cgroups

`cgroups` реально учитывают и ограничивают ресурсы.

`cgroup namespace` изолирует представление cgroup hierarchy.

Связано: [[11 - runc]], [[16 - Linux kernel primitives]].
