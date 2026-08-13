`libcontainer` — Linux-specific библиотечная часть проекта `runc`.

```text
runc CLI
   ↓
libcontainer
   ↓
Linux syscalls / kernel APIs
```

---

# Области работы

Концептуально:

```text
namespaces
mounts
root filesystem
UID/GID
capabilities
cgroups integration
seccomp integration
process setup
```

Именно здесь OCI/Linux configuration превращается в Linux-specific runtime work.

---

# Зачем знать

Для эксплуатации Docker глубоко разбирать libcontainer необязательно.

Но если изучать исходники `runc`, большая часть низкоуровневой container logic находится именно ниже CLI-уровня.

Связано: [[11 - runc]], [[16 - Linux kernel primitives]].
