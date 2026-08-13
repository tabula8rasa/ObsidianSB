```
						 ПОЛЬЗОВАТЕЛЬ
                              │
                              ▼
                        docker CLI
                        /usr/bin/docker
                              │
                         Docker API
                              │
                              ▼
                           dockerd
                     /usr/bin/dockerd
                              │
              ┌───────────────┼────────────────┐
              │               │                │
              ▼               ▼                ▼
           BuildKit        networking        volumes
          docker build     bridge/veth       bind mounts
              │
              │
              └──── создание OCI image
                              │
                              ▼
                          containerd
                    /usr/bin/containerd
                              │
               ┌──────────────┼───────────────┐
               │              │               │
               ▼              ▼               ▼
         content store    snapshotter     task/runtime
        blobs/images       overlayfs
                              │
                              ▼
                    containerd-shim-runc-v2
                              │
                              ▼
                            runc
                              │
                              ▼
                         Linux kernel
                              │
            ┌─────────────────┼──────────────────┐
            ▼                 ▼                  ▼
       namespaces          cgroups          mounts/rootfs
            │
            └─────────────────┬──────────────────┘
                              ▼
                     container process
                   python/nginx/bash/...
```

