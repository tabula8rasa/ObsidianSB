# containerd-shim-runc-v2

`containerd-shim-runc-v2` — runtime shim между `containerd` и `runc`/container process.

Проверить:

```bash
ps -ef | grep '[c]ontainerd-shim'
```

---

# Зачем shim нужен

```text
containerd
    ↓
shim
    ↓
runc
    ↓
container process
```

`runc` не является постоянным daemon для каждого container.

Shim остаётся для runtime lifecycle.

---

# Что делает shim

Концептуально участвует в:

```text
task lifecycle
stdio
exit status
exec processes
signals
runtime communication
runtime filesystem preparation
```

---

# Почему `runc` может исчезнуть из `ps`

После запуска:

```text
runc
   ↓
создал process
   ↓
завершился
```

Но остаются:

```text
containerd
shim
container process
```

---

# Runtime directories

Live state обычно связан с:

```text
/run/containerd/io.containerd.runtime.v2.task/
```

Для Docker namespace:

```text
moby
```

Там могут находиться runtime bundle/rootfs mount/state данные task.

Связано: [[07 - containerd]], [[11 - runc]].
