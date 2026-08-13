# Linux kernel primitives

Docker не реализует собственное ядро.

Все контейнерные гарантии в итоге предоставляет Linux kernel.

---

# Process

Контейнерное приложение — обычный Linux process.

---

# Namespaces

Изолируют представление ресурсов:

```text
PID
network
mounts
hostname
IPC
users
```

См. [[14 - Linux Namespaces и unshare]].

---

# cgroups

Управляют:

```text
CPU
RAM
PIDs
I/O
```

См. [[15 - cgroups]].

---

# Mount/VFS

Для Docker rootfs:

```text
open("/usr/bin/python")
   ↓
VFS
   ↓
OverlayFS
   ↓
upper/lower snapshots
   ↓
real inode
```

---

# OverlayFS

Kernel filesystem объединяет lowerdirs + upperdir + workdir в один view.

---

# `execve`

Финальный запуск:

```text
runtime setup
   ↓
execve(application)
```

---

# ELF dynamic linker

Как видно на `chroot`, динамический ELF может требовать interpreter и shared libraries внутри rootfs.

---

# Capabilities

Linux root privileges разбиты на отдельные capabilities:

```text
CAP_NET_ADMIN
CAP_SYS_ADMIN
CAP_CHOWN
CAP_SETUID
...
```

Container root не обязан получать все host-root capabilities.

---

# seccomp

Seccomp фильтрует syscalls процесса.

---

# Networking

veth, bridge, routing, network namespaces также предоставляются Linux kernel.

См. [[17 - Docker Networking]].
