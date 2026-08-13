# Docker под капотом — набор заметок

Этот набор заметок собран вокруг практической модели Docker Engine на Linux:

```text
Docker CLI
   ↓
dockerd
   ↓
containerd
   ↓
containerd-shim-runc-v2
   ↓
runc
   ↓
Linux kernel
   ↓
обычный Linux-процесс
```

Отдельно разобраны build-путь, OCI, слои image, `rootfs`, containerd content store, snapshotter, OverlayFS, `chroot`, namespaces, cgroups и сетевой слой.

## Рекомендуемый порядок чтения
1. [[13 - chroot]]
2. [[14 - Linux Namespaces и unshare]]
3. [[15 - cgroups]]
4. [[16 - Linux kernel primitives]]
5. [[06 - Filesystem layers и rootfs]]
6. [[09 - Snapshotter и OverlayFS]]
7. [[05 - OCI]]
8. [[12 - libcontainer]]
9. [[11 - runc]]
10. [[10 - containerd-shim-runc-v2]]
11. [[08 - containerd Content Store]]
12. [[07 - containerd]]
13. [[21 - Каталоги Docker на хосте]]
14. [[17 - Docker Networking]]
15. [[18 - docker-proxy]]
16. [[19 - docker-init и tini]]
17. [[02 - dockerd]]
18. [[01 - Docker CLI]]
19. [[04 - BuildKit]]
20. [[03 - Docker Buildx]]
21. [[22 - Жизненный цикл build pull run]]
22. [[20 - Docker Compose]]
23. [[00 - Архитектура Docker целиком]]
24. [[README]]
