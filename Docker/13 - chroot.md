# chroot

`chroot` меняет корневой каталог `/` для процесса и его потомков.

```bash
chroot NEW_ROOT COMMAND
```

Пример:

```bash
sudo chroot /tmp/rootfs /usr/bin/bash
```

После смены root:

```text
/usr/bin/bash
```

разрешается как:

```text
HOST:/tmp/rootfs/usr/bin/bash
```

---

# Порядок

```text
chroot("/tmp/rootfs")
        ↓
новый /
        ↓
exec /usr/bin/bash
```

Поэтому executable и runtime dependencies должны существовать внутри нового root.

---

# Dynamic linker

Проверить ELF interpreter:

```bash
readelf -l /usr/bin/bash | grep interpreter
```

Если Bash требует:

```text
/lib64/ld-linux-x86-64.so.2
```

то после chroot он ищется как:

```text
/tmp/rootfs/lib64/ld-linux-x86-64.so.2
```

---

# Shared libraries

```bash
ldd /usr/bin/bash
```

Необходимые libraries тоже должны существовать в новом root.

---

# Почему `echo` работает, а `ls` нет

`echo` обычно Bash builtin.

`ls` — отдельный executable.

```bash
type echo
type ls
```

---

# `PATH`

При абсолютном пути:

```bash
chroot /tmp/rootfs /usr/bin/bash
```

`PATH` для поиска Bash не нужен.

Сам `chroot` не обязан очищать environment.

Строка `PATH=/usr/bin:/bin` может остаться прежней, но смысл `/usr/bin` уже относится к новому `/`.

---

# Если COMMAND не указан

CLI `chroot` запускает shell по умолчанию.

---

# Что chroot НЕ изолирует

```text
PID
network
hostname
IPC
CPU
RAM
kernel
```

Это не полноценный container sandbox.

Связано: [[14 - Linux Namespaces и unshare]], [[11 - runc]].
