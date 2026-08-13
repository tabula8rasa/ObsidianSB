# docker-proxy

`docker-proxy` — опциональная вспомогательная программа Docker networking.

Она может участвовать в userland proxy для опубликованных портов.

Пример:

```bash
docker run -p 8080:80 nginx
```

Проверить:

```bash
ps -ef | grep '[d]ocker-proxy'
```

---

# Не центральный runtime component

Основная цепочка:

```text
dockerd
  ↓
containerd
  ↓
shim
  ↓
runc
```

`docker-proxy` относится только к networking/port publication и может отсутствовать в конкретной конфигурации.

Связано: [[17 - Docker Networking]].
