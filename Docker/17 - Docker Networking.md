# Docker Networking

Docker networking — отдельная подсистема поверх Linux networking primitives.

---

# Базовая bridge-модель

```text
container NET namespace
        │
       eth0
        │
      veth pair
        │
host-side veth
        │
   Linux bridge
        │
    host network
        │
     Internet
```

---

# Network namespace

Отдельные:

```text
interfaces
IP addresses
routes
sockets
network stack
```

Сам пустой NET namespace ещё не имеет нормальной связи с host.

---

# veth

Пара виртуальных Ethernet interfaces:

```text
veth-host ↔ eth0-in-container
```

---

# Bridge

Host Linux bridge соединяет veth interfaces нескольких containers.

---

# Port publishing

```bash
docker run -p 8080:80 nginx
```

Это Docker/network layer, а не просто поле OCI runtime config.

---

# NAT/firewall

Docker использует host networking/firewall mechanisms для outbound NAT, published ports и forwarding.

---

# Что делает runc

Runc может создать/join network namespace, но полное подключение veth/bridge/IP/routes/NAT создаётся более высоким networking layer Docker.

---

# Проверка

```bash
docker network ls
docker network inspect bridge
ip link
ip addr
ip route
```

Связано: [[14 - Linux Namespaces и unshare]], [[18 - docker-proxy]].
