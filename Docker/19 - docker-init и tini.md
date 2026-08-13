# docker-init и tini

Container PID 1 имеет особое поведение в Linux.

Если приложение плохо обрабатывает signals/zombies/orphans, можно использовать маленький init process.

---

# Docker `--init`

```bash
docker run --init myimage
```

```text
container PID 1
    ↓
docker-init / tini
    ↓
application
```

---

# Роль

```text
reap zombies
forward signals
minimal PID 1 behavior
```

---

# Не обязателен

Без `--init` PID 1 внутри container может быть напрямую Python/Nginx/Bash.

Связано: [[14 - Linux Namespaces и unshare]].
