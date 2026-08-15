# Вопрос и стартовая точка
смтори, я сделал prune системы. У меня все директории были пусты от слоев и прочего. Затем я сделал docker pull nginx\:latest и всё. вот такой вывод получил

```
docker pull nginx
Using default tag: latest
latest: Pulling from library/nginx
26c307b5e35a: Pull complete
b8b80b9bc028: Pull complete
d84ae7b21412: Pull complete
f5de6e85ac74: Pull complete
5a4222b844e8: Pull complete
3c55dc422a81: Pull complete
c0df8d325117: Pull complete
92fcf0fc2ef2: Download complete
0f03cb4db0ef: Download complete
mDigest: sha256:8541484afbc9c8a5a8a99b379568ebbc957f658583ec9448fc43104229c03cf8
Status: Downloaded newer image for nginx\:latest
docker.io/library/nginx\:latest
```

Я понял, что mDigest указывает на то что показывает docker image inspect nginx\:latest. И этот файл лежит в /var/lib/containerd/.../blobs/sha256 под таких же именем. Это мне понято. Дальше я могу найти соответствие каждому файлу из этого лога у которого стоит pull complete или download complete в /var/lib/containerd/.../blobs/sha256. Значит это какие то исходиники данного образа - еще не слои, необходимые для сборки rootfs а лишь исходники, которые containerd еще должен раскрыть в снепшоты. Я даже преполагаю, что те объекты у которых стоит pull complete это исходники будущих слоев, судя по совпадению их количетсва с количество папок в /var/lib/containerd/.../snapshots. после этого момента возникают вопросы

1\)Почему объектов в  /var/lib/containerd/.../blobs/sha256 больше чем было скачана судя по логам команды docker pull. Других образов нет, поэтому вариант что они от других образов не подходит. Они появились ровно момент с остальными, которые отображены в docker pull nginx.

2\)Где объекты слоев указанные в image nginx

**"RootFS":{"Type":**"layers"**,"Layers":[** 7 хэшей]

их количество совпадает с количеством строк со статусом pull complete. Но их хэши не совпадают

3\)Что показывает команда docker manifest inspect nginx

4\)откуда взялись эти самые манифесты. Их всего 16 и только 2 из них совпадают с двуми лежащими в /var/lib/containerd/.../blobs/sha256 Остальных нигде нет.

по итогу в /var/lib/containerd/.../blobs/sha256 осталось два объекта появления которых я не могу объяснить. Поэтому сейчас по шагам пройти пусть что происходит после команды docker pull nginx, параллельно отвечая на мои вопросы. Именно на уровне папок и файлов которые появились у меня после команды, а именно директории /var/lib/containerd/.../blobs/sha256, docker image inspect и docker manifest inspect

# Шаги 
Да. Теперь у нас достаточно данных, чтобы собрать **всю цепочку `docker pull nginx` почти побайтово** и объяснить все 14 объектов. У тебя наблюдение правильное, но есть одна важная поправка:

> Файлы в `blobs/sha256` — не просто «исходники, из которых потом делаются слои».  
> Там вперемешку лежат **OCI index, manifests, config, сжатые filesystem layers и attestations**. Containerd хранит registry content практически в том же формате, в каком получил его из registry. ([GitHub](https://github.com/containerd/containerd/blob/main/docs/content-flow.md "containerd/docs/content-flow.md at main · containerd/containerd · GitHub"))

А уже **только filesystem layer blobs** распаковываются в:

```text
/var/lib/containerd/
└── io.containerd.snapshotter.v1.overlayfs/
    └── snapshots/
```

Containerd описывает именно такой flow: content сначала попадает в content store, затем filesystem layers применяются один за другим и превращаются в committed snapshots. ([GitHub](https://github.com/containerd/containerd/blob/main/docs/content-flow.md "containerd/docs/content-flow.md at main · containerd/containerd · GitHub"))

---

# 0. Что было до `docker pull`

После prune условно:

```text
/var/lib/containerd/
│
├── io.containerd.content.v1.content/
│   └── blobs/sha256/
│       └── пусто
│
└── io.containerd.snapshotter.v1.overlayfs/
    └── snapshots/
        └── пусто
```

Затем:

```bash
docker pull nginx
```

Docker обращается к Docker Hub за:

```text
docker.io/library/nginx:latest
```

---

# 1. Сначала `latest` разрешается в OCI Image Index

Тег:

```text
nginx:latest
```

сам по себе не содержит layers.

Registry отвечает:

```text
nginx:latest
      │
      ▼
OCI Image Index

sha256:8541484afbc9c8a5a8a99b379568ebbc...
```

Именно этот digest ты видишь здесь:

```text
Digest: sha256:8541484...
```

И здесь:

```json
"Descriptor": {
    "mediaType": "application/vnd.oci.image.index.v1+json",
    "digest": "sha256:8541484...",
    "size": 10229
}
```

OCI Image Index — это верхнеуровневый JSON, содержащий ссылки на manifests для разных платформ. ([GitHub](https://github.com/opencontainers/image-spec/blob/main/image-index.md "image-spec/image-index.md at main · opencontainers/image-spec · GitHub"))

Физически он появляется:

```text
/var/lib/containerd/
└── io.containerd.content.v1.content/
    └── blobs/sha256/
        └── 8541484afbc9c8a5...
```

Важно: весь вывод:

```bash
docker image inspect nginx
```

**не является содержимым этого файла**.

`docker image inspect` — представление Docker, собранное из нескольких OCI-объектов.

Только:

```text
Descriptor.digest
```

указывает непосредственно на этот OCI index.

Если сделать:

```bash
sudo ctr -n moby content get \
sha256:8541484afbc9c8a5a8a99b379568ebbc957f658583ec9448fc43104229c03cf8 \
| jq
```

ты должен увидеть JSON, очень похожий на:

```bash
docker manifest inspect nginx
```

---

# 2. Что именно показывает `docker manifest inspect nginx`

Вот здесь твой третий вопрос.

```bash
docker manifest inspect nginx
```

показывает **не слои nginx и не локальные snapshots**.

Он показывает верхнеуровневый:

```text
OCI Image Index
```

то есть:

```text
sha256:8541484...
```

В OCI index поле:

```json
"manifests": [...]
```

содержит descriptors дочерних manifests. OCI специально использует image index для выбора подходящего image manifest по `architecture + os`. ([GitHub](https://github.com/opencontainers/image-spec/blob/main/image-index.md "image-spec/image-index.md at main · opencontainers/image-spec · GitHub"))

У тебя там 16 записей.

Но посмотри внимательно на структуру:

```text
1  amd64
2  unknown/unknown

3  arm/v5
4  unknown/unknown

5  arm/v7
6  unknown/unknown

7  arm64/v8
8  unknown/unknown

9  386
10 unknown/unknown

11 ppc64le
12 unknown/unknown

13 riscv64
14 unknown/unknown

15 s390x
16 unknown/unknown
```

То есть на самом деле:

```text
8 обычных platform manifests
+
8 attestation manifests
=
16
```

---

# 3. Что за `unknown/unknown`

Это не странные процессоры.

Это **attestation manifests**.

Docker специально помечает manifest аттестаций:

```json
"platform": {
    "architecture": "unknown",
    "os": "unknown"
}
```

чтобы container runtime не попытался запустить их как обычный container image. Attestations могут содержать, например, SBOM и provenance. ([Docker Documentation](https://docs.docker.com/build/metadata/attestations/attestation-storage/ "Image attestation storage | Docker Docs"))

Поэтому твой index логически выглядит так:

```text
nginx index
sha256:8541484...
│
├── linux/amd64
│   └── sha256:963cfe6...
│
├── attestation для amd64
│   └── sha256:a2a0343...
│
├── linux/arm/v5
│   └── sha256:dd8c480...
│
├── attestation для arm/v5
│   └── sha256:dbb9ed6...
│
├── linux/arm/v7
│   └── ...
│
├── attestation
│
├── linux/arm64/v8
│   └── ...
│
└── ...
```

---

# 4. Почему из этих 16 manifests локально есть только 2

Вот теперь твой четвёртый вопрос становится понятен.

Ты работаешь на:

```text
linux/amd64
```

Docker не обязан скачивать filesystem image для:

```text
arm
arm64
386
ppc64le
riscv64
s390x
```

Containerd получает index, выбирает manifest, соответствующий нужной платформе, а затем скачивает содержимое именно выбранного manifest. Это прямо описано в его content flow. ([GitHub](https://github.com/containerd/containerd/blob/main/docs/content-flow.md "containerd/docs/content-flow.md at main · containerd/containerd · GitHub"))

Поэтому локально появляется:

```text
sha256:963cfe6...
```

то есть:

```text
linux/amd64 image manifest
```

И у тебя также сохранился соответствующий ему attestation manifest:

```text
sha256:a2a0343...
```

А остальные 14 записей:

```text
arm
arm/v7
arm64
...
```

просто **упомянуты внутри локального index JSON**:

```text
8541484...
```

но сами target objects тебе не потребовались.

То есть:

```text
8541484...                 ← локально
│
├── 963cfe6... amd64      ← локально
├── a2a0343... attestation← локально
│
├── dd8c480... arm/v5     ← НЕ скачан
├── dbb9ed6... attestation← НЕ скачан
│
├── ...
```

Это очень важное различие:

> **Наличие digest внутри index не означает, что объект с этим digest уже скачан.**

Index — просто JSON со ссылками.

---

# 5. Теперь Docker открывает AMD64 manifest

Вот этот объект:

```text
sha256:963cfe6e75d1c292...
```

уже является настоящим:

```text
OCI Image Manifest
```

OCI Image Manifest для одной конкретной платформы содержит две главные вещи:

```text
config
layers[]
```

OCI spec определяет manifest именно как описание config + набора layers конкретного image. ([GitHub](https://github.com/opencontainers/image-spec/blob/main/manifest.md "image-spec/manifest.md at main · opencontainers/image-spec · GitHub"))

Посмотри его непосредственно:

```bash
sudo ctr -n moby content get \
sha256:963cfe6e75d1c292f66589d7e190b137cf89310414c0c1c5b476dfc61a4fcd0d \
| jq
```

Там будет примерно:

```json
{
  "schemaVersion": 2,

  "config": {
    "digest": "sha256:XXXXXXXX"
  },

  "layers": [
    {
      "digest": "sha256:..."
    },
    {
      "digest": "sha256:..."
    }
  ]
}
```

И вот здесь начинается самое интересное.

---

# 6. Семь `Pull complete` — это действительно семь filesystem layer blobs

Твоя догадка правильная.

У тебя:

```text
26c307b5e35a: Pull complete
b8b80b9bc028: Pull complete
d84ae7b21412: Pull complete
f5de6e85ac74: Pull complete
5a4222b844e8: Pull complete
3c55dc422a81: Pull complete
c0df8d325117: Pull complete
```

ровно:

```text
7 объектов
```

И:

```bash
docker image inspect nginx
```

показывает:

```text
7 RootFS layers
```

И snapshotter создал:

```text
7 snapshots
```

Это не случайность.

В твоём конкретном image эти семь `Pull complete` соответствуют **семи сжатым filesystem layer blobs**, перечисленным в:

```text
963cfe6... manifest
        ↓
layers[]
```

Физически:

```text
blobs/sha256/
├── 26c307b5e35a...
├── b8b80b9bc028...
├── d84ae7b21412...
├── f5de6e85ac74...
├── 5a4222b844e8...
├── 3c55dc422a81...
└── c0df8d325117...
```

Это уже **слои**.

Тут стоит поправить твою формулировку:

> они не «исходники будущих слоёв».

Правильнее:

> это **слои image в транспортном OCI-формате**, обычно сжатые tar-архивы.

Но:

```text
tar.gz layer blob
```

ещё нельзя непосредственно использовать как rootfs.

Поэтому containerd делает:

```text
compressed layer blob
        ↓
decompress
        ↓
apply changes
        ↓
OverlayFS snapshot
```

Containerd прямо описывает: создаётся active snapshot, layer blob применяется к нему, затем snapshot commit'ится. По одному committed snapshot на filesystem layer. ([GitHub](https://github.com/containerd/containerd/blob/main/docs/content-flow.md "containerd/docs/content-flow.md at main · containerd/containerd · GitHub"))

Поэтому:

```text
7 filesystem blobs
        ↓
7 committed snapshots
```

---

# 7. Почему hashes в `RootFS.Layers` другие

Теперь твой второй вопрос.

У тебя в `docker image inspect`:

```json
"RootFS": {
    "Type": "layers",
    "Layers": [
        "sha256:6f943283...",
        "sha256:9df56c3b...",
        "sha256:4647e810...",
        ...
    ]
}
```

Это **не digests файлов в content store**.

Это:

```text
DiffID
```

OCI config называет это:

```json
rootfs.diff_ids
```

и определяет как hashes слоёв в несжатом виде. ([GitHub](https://github.com/opencontainers/image-spec/blob/main/config.md "image-spec/config.md at main · opencontainers/image-spec · GitHub"))

То есть один и тот же слой имеет:

```text
registry / content store

26c307b5e35a...
       │
       │ SHA256 от compressed blob
       ▼
layer.tar.gz


       gunzip
         │
         ▼

layer.tar
       │
       │ SHA256 от uncompressed tar
       ▼

6f9432833129...
       ↑
      DiffID
```

Поэтому:

```text
26c307... != 6f943...
```

хотя это один логический layer.

Containerd даже сохраняет связь между ними через label:

```text
containerd.io/uncompressed=sha256:<DiffID>
```

и официальная документация показывает, что можно взять compressed blob, распаковать gzip и получить этот uncompressed digest. ([GitHub](https://github.com/containerd/containerd/blob/main/docs/content-flow.md "containerd/docs/content-flow.md at main · containerd/containerd · GitHub"))

Проверь:

```bash
sudo ctr -n moby content ls
```

Для filesystem layer увидишь что-то вроде:

```text
sha256:26c307...  ...
containerd.io/uncompressed=sha256:6f943283...
```

То есть связь уже хранится containerd:

```text
compressed blob digest
       │
       │ containerd.io/uncompressed
       ▼
DiffID
```

---

# 8. Где физически лежат эти `RootFS.Layers`

Вот важный ответ:

```text
sha256:6f943283...
sha256:9df56c3b...
...
```

**не обязаны существовать как файлы с такими именами.**

Они прежде всего записаны внутри **image config JSON**.

AMD64 manifest:

```text
963cfe6...
```

содержит:

```json
"config": {
    "digest": "sha256:SOME_CONFIG_HASH"
}
```

Этот `SOME_CONFIG_HASH` — ещё один blob в:

```text
blobs/sha256/
```

которого ты не видел в `docker pull`.

Открой manifest:

```bash
MANIFEST=sha256:963cfe6e75d1c292f66589d7e190b137cf89310414c0c1c5b476dfc61a4fcd0d

sudo ctr -n moby content get "$MANIFEST" \
| jq '.config'
```

Получишь:

```json
{
  "mediaType": "application/vnd.oci.image.config.v1+json",
  "digest": "sha256:XXXXXXXX",
  "size": ...
}
```

Теперь:

```bash
sudo ctr -n moby content get sha256:XXXXXXXX \
| jq '.rootfs'
```

И там:

```json
{
  "type": "layers",
  "diff_ids": [
    "sha256:6f943283...",
    "sha256:9df56c3b...",
    ...
  ]
}
```

То есть:

```text
docker image inspect
    RootFS.Layers

        ║
        ║ фактически взято из
        ▼

OCI image config
    rootfs.diff_ids
```

OCI config специально содержит `rootfs.diff_ids` именно для этой цели. ([GitHub](https://github.com/opencontainers/image-spec/blob/main/config.md "image-spec/config.md at main · opencontainers/image-spec · GitHub"))

---

# 9. Теперь два `Download complete`

У тебя ещё были:

```text
92fcf0fc2ef2: Download complete
0f03cb4db0ef: Download complete
```

Вот почему они **не превратились в snapshots**.

С высокой уверенностью по структуре именно этого nginx index это **attestation blobs**, а не filesystem layers.

Docker attestations хранятся в OCI index через специальный attestation manifest, а сами данные attestation могут быть отдельными `application/vnd.in-toto+json` blobs. Один attestation manifest может содержать несколько таких blobs — например provenance и SBOM. ([Docker Documentation](https://docs.docker.com/build/metadata/attestations/attestation-storage/ "Image attestation storage | Docker Docs"))

Получается:

```text
a2a0343...        attestation manifest
       │
       ├── 92fcf0fc2ef2...
       │
       └── 0f03cb4db0ef...
```

Они были:

```text
Download complete
```

но не:

```text
Pull complete
```

в том смысле, что их не нужно распаковывать и применять как filesystem layer.

Поэтому:

```text
92fc...
0f03...
       ↓

content store     YES

snapshotter       NO
```

Чтобы доказать это именно на своей машине, открой attestation manifest:

```bash
sudo ctr -n moby content get \
sha256:a2a034340090fa5be6987a96c1c1e9cd5be56157bea6d918acf9c1bbd28073c8 \
| jq
```

И посмотри:

```text
.layers[].digest
```

Я ожидаю, что там окажутся полные digest'ы:

```text
92fcf0fc2ef2...
0f03cb4db0ef...
```

И можно посмотреть их:

```bash
sudo ctr -n moby content get sha256:<92fc-full-digest> | jq
```

и:

```bash
sudo ctr -n moby content get sha256:<0f03-full-digest> | jq
```

У attestation body будет структура вроде:

```json
{
    "_type": "...in-toto...",
    "predicateType": "...",
    "predicate": { ... }
}
```

По `predicateType` можно точно определить, какой из двух — provenance, а какой SBOM. Docker документирует именно такую структуру attestation blobs. ([Docker Documentation](https://docs.docker.com/build/metadata/attestations/attestation-storage/ "Image attestation storage | Docker Docs"))

---

# 10. И вот откуда берутся твои два необъяснённых blob

Теперь можно собрать всю арифметику.

По твоему описанию после чистого prune появилось примерно:

```text
14 blobs
```

Разложим их.

### 1. OCI Image Index

```text
8541484...
```

Количество:

```text
1
```

---

### 2. Выбранный AMD64 manifest

```text
963cfe6...
```

Количество:

```text
1
```

---

### 3. OCI Image Config

На него указывает:

```text
963cfe6...
        ↓
.config.digest
```

Количество:

```text
1
```

Это, скорее всего, **первый из твоих двух необъяснённых объектов**.

---

### 4. Семь filesystem layer blobs

```text
26c307...
b8b80b...
d84ae7...
f5de6e...
5a4222...
3c55dc...
c0df8d...
```

Количество:

```text
7
```

---

### 5. AMD64 attestation manifest

```text
a2a0343...
```

Количество:

```text
1
```

---

### 6. Два attestation blobs

```text
92fcf0fc...
0f03cb4d...
```

Количество:

```text
2
```

---

### 7. OCI empty config для attestation manifest

Современный OCI-artifact attestation manifest также содержит config descriptor. Для attestation это обычно специальный пустой JSON `{}`. Docker показывает в документации стандартный digest такого объекта:

```text
sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a
```

Docker attestation storage использует такой empty OCI config для artifact manifests. ([Docker Documentation](https://docs.docker.com/build/metadata/attestations/attestation-storage/ "Image attestation storage | Docker Docs"))

Если у тебя среди оставшихся blobs есть:

```text
44136fa355b3678a...
```

то это **второй необъяснённый объект**.

Проверить:

```bash
sudo cat \
/var/lib/containerd/io.containerd.content.v1.content/blobs/sha256/44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a
```

получишь:

```json
{}
```

---

# Итого ровно 14

Получается:

```text
1   OCI index
1   amd64 image manifest
1   image config
7   filesystem layer blobs
1   amd64 attestation manifest
2   attestation blobs
1   empty OCI config
────────────────────────────
14 blobs
```

Это очень хорошо совпадает с твоим экспериментом.

Физически:

```text
/var/lib/containerd/
└── io.containerd.content.v1.content/
    └── blobs/sha256/
        │
        ├── 8541484...     OCI INDEX
        │
        ├── 963cfe6...     AMD64 IMAGE MANIFEST
        │
        ├── XXXXXXXX...    IMAGE CONFIG
        │
        ├── 26c307...      FS LAYER
        ├── b8b80b...      FS LAYER
        ├── d84ae7...      FS LAYER
        ├── f5de6e...      FS LAYER
        ├── 5a4222...      FS LAYER
        ├── 3c55dc...      FS LAYER
        ├── c0df8d...      FS LAYER
        │
        ├── a2a0343...     ATTESTATION MANIFEST
        ├── 92fcf0...      ATTESTATION DATA
        ├── 0f03cb...      ATTESTATION DATA
        │
        └── 44136fa...     EMPTY OCI CONFIG
```

А snapshotter получает **только семь filesystem layers**:

```text
26c307...
b8b80b...
d84ae7...
f5de6e...
5a4222...
3c55dc...
c0df8d...
     │
     │ decompress + apply
     ▼

/var/lib/containerd/
└── io.containerd.snapshotter.v1.overlayfs/
    └── snapshots/
        ├── 1/fs
        ├── 2/fs
        ├── 3/fs
        ├── 4/fs
        ├── 5/fs
        ├── 6/fs
        └── 7/fs
```

По одному committed snapshot на каждый filesystem layer — именно такой unpack flow описывает containerd. ([GitHub](https://github.com/containerd/containerd/blob/main/docs/content-flow.md "containerd/docs/content-flow.md at main · containerd/containerd · GitHub"))

---

# Вся цепочка `docker pull nginx` целиком

Теперь можно собрать всё в одну архитектуру:

```text
docker pull nginx
       │
       ▼
Docker Hub
nginx:latest
       │
       ▼
resolve tag
       │
       ▼
OCI INDEX
8541484...
       │
       │
       ├──────────────────────────────────────────┐
       │                                          │
       ▼                                          ▼
linux/amd64 manifest                    amd64 attestation manifest
963cfe6...                              a2a0343...
       │                                          │
       │                                          ├── 92fc... attestation
       │                                          ├── 0f03... attestation
       │                                          └── 44136... empty config
       │
       ├── image config
       │      │
       │      ├── Entrypoint
       │      ├── Cmd
       │      ├── Env
       │      └── rootfs.diff_ids
       │             │
       │             ├── 6f943...
       │             ├── 9df56...
       │             └── ...
       │
       └── compressed filesystem blobs
              │
              ├── 26c307...
              ├── b8b80b...
              ├── d84ae7...
              ├── f5de6...
              ├── 5a4222...
              ├── 3c55d...
              └── c0df8...
                     │
                     │ unpack/apply
                     ▼
              overlayfs snapshotter
                     │
                     ├── snapshot 1
                     ├── snapshot 2
                     ├── snapshot 3
                     ├── snapshot 4
                     ├── snapshot 5
                     ├── snapshot 6
                     └── snapshot 7
```

И самое важное соответствие:

```text
docker manifest inspect nginx
        ↓
показывает OCI INDEX
        ↓
8541484...
```

```text
AMD64 OCI manifest
963cfe6...
        ↓
.layers[]
        ↓
7 compressed filesystem blob digests
        ↓
26c307..., ...
```

```text
AMD64 OCI manifest
963cfe6...
        ↓
.config.digest
        ↓
OCI IMAGE CONFIG
        ↓
.rootfs.diff_ids[]
        ↓
docker image inspect
RootFS.Layers
        ↓
6f943..., 9df56..., ...
```

И:

```text
compressed layer digest
26c307...
        │
        │ decompress
        ▼
DiffID
6f943...
        │
        │ apply
        ▼
snapshot
snapshots/N/fs
```

Это как раз три разных уровня, которые раньше смешивались:

```text
26c307...    ← digest скачанного compressed layer blob

6f943...     ← DiffID того же layer после распаковки

N/fs         ← физически применённый слой в snapshotter
```

Если сейчас выполнить три команды:

```bash
sudo ctr -n moby content get \
sha256:963cfe6e75d1c292f66589d7e190b137cf89310414c0c1c5b476dfc61a4fcd0 | jq
```

```bash
sudo ctr -n moby content get \
sha256:a2a034340090fa5be6987a96c1c1e9cd5be56157bea6d918acf9c1bbd28073c8 | jq
```

```bash
sudo ctr -n moby content ls
```

ты сможешь **для каждого из 14 файлов провести стрелку: кто на него ссылается, что внутри и почему он появился**.

# OCI Image Index
**OCI Image Index** — это верхнеуровневый JSON-документ, который говорит:

> «Для этого тега существует несколько вариантов образа. Вот их manifests и вот для каких платформ каждый предназначен».

По спецификации OCI это higher-level manifest, который ссылается на конкретные image manifests для одной или нескольких платформ. ([GitHub](https://github.com/opencontainers/image-spec/blob/main/image-index.md?utm_source=chatgpt.com "OCI Image Index Specification"))

В твоём случае:

```text
nginx:latest
    │
    ▼
OCI IMAGE INDEX
sha256:8541484...
```

Именно этот объект ты увидел через:

```bash
docker manifest inspect nginx
```

У него:

```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.index.v1+json",
  "manifests": [
    ...
  ]
}
```

Поле:

```text
mediaType = application/vnd.oci.image.index.v1+json
```

прямо говорит: **это OCI Image Index**. ([GitHub](https://github.com/opencontainers/image-spec/blob/main/image-index.md?plain=1&utm_source=chatgpt.com "image-spec/image-index.md at main"))

Сам index **не содержит rootfs, файлы nginx или filesystem layers напрямую**. Он содержит descriptors — ссылки на другие объекты по digest. Descriptor в OCI содержит, среди прочего, `mediaType`, `digest`, `size`, а для платформенных manifests может содержать `platform`. ([GitHub](https://github.com/opencontainers/image-spec/blob/main/descriptor.md?utm_source=chatgpt.com "OCI Content Descriptors - opencontainers/image-spec"))

Например твоя запись:

```json
{
    "mediaType": "application/vnd.oci.image.manifest.v1+json",
    "size": 2290,
    "digest": "sha256:963cfe6e...",
    "platform": {
        "architecture": "amd64",
        "os": "linux"
    }
}
```

означает:

```text
если клиенту нужен:

OS           = linux
architecture = amd64

то смотри объект:

sha256:963cfe6e...
```

То есть можно воспринимать index как таблицу маршрутизации:

```text
nginx:latest
    │
    ▼
OCI IMAGE INDEX
    │
    ├── linux/amd64
    │      └── manifest sha256:963c...
    │
    ├── linux/arm/v5
    │      └── manifest sha256:dd8c...
    │
    ├── linux/arm/v7
    │      └── manifest sha256:74a6...
    │
    ├── linux/arm64/v8
    │      └── manifest sha256:8725...
    │
    ├── linux/386
    │      └── manifest sha256:b6be...
    │
    └── ...
```

### Зачем он вообще нужен

Представь, что ты выполняешь:

```bash
docker pull nginx:latest
```

на обычном x86-64 компьютере.

Docker/containerd определяет:

```text
OS   = linux
ARCH = amd64
```

Смотрит в OCI Index:

```text
linux/amd64
       │
       ▼
sha256:963cfe6...
```

и дальше работает уже с **этим конкретным Image Manifest**.

На ARM-компьютере тот же самый:

```bash
docker pull nginx:latest
```

пройдёт:

```text
nginx:latest
    ↓
тот же OCI Index
    ↓
linux/arm64
    ↓
другой Image Manifest
```

Поэтому разработчику не нужно публиковать пользователю:

```text
nginx-amd64:latest
nginx-arm64:latest
nginx-armv7:latest
```

Достаточно:

```text
nginx:latest
```

а index выбирает нужную ветку.

---

## Index и Manifest — разные вещи

Это ключевое различие.

### OCI Image Index

Говорит:

```text
Какие варианты образа существуют?
```

Пример:

```text
OCI INDEX
│
├── amd64 → manifest A
├── arm64 → manifest B
└── arm   → manifest C
```

### OCI Image Manifest

Говорит уже:

```text
Из чего состоит КОНКРЕТНЫЙ вариант образа?
```

Например manifest для `linux/amd64`:

```text
Image Manifest
sha256:963c...
│
├── config
│      └── sha256:...
│
└── layers
       ├── sha256:...
       ├── sha256:...
       ├── sha256:...
       └── ...
```

OCI определяет Image Manifest как объект, содержащий configuration и набор layers конкретного container image. ([GitHub](https://github.com/opencontainers/image-spec/blob/master/manifest.md?utm_source=chatgpt.com "OCI Image Manifest Specification"))

Поэтому структура в целом:

```text
nginx:latest
     │
     ▼
OCI IMAGE INDEX
sha256:8541484...
     │
     │ выбираем linux/amd64
     ▼
OCI IMAGE MANIFEST
sha256:963cfe6...
     │
     ├── CONFIG
     │      └── Env
     │          Cmd
     │          Entrypoint
     │          DiffIDs
     │          ...
     │
     └── LAYERS
            ├── compressed layer 1
            ├── compressed layer 2
            ├── ...
            └── compressed layer 7
```

И уже эти семь layer blobs containerd распаковывает в snapshots.

---

## Что физически представляет собой OCI Index

Это просто JSON-файл.

У тебя он физически лежит как content blob:

```text
/var/lib/containerd/
└── io.containerd.content.v1.content/
    └── blobs/
        └── sha256/
            └── 8541484afbc9c8a5...
```

Название файла — SHA256 его содержимого.

То есть условно:

```bash
sha256sum 8541484afbc9c8a5...
```

даёт:

```text
8541484afbc9c8a5...
```

Именно поэтому OCI называется **content-addressable**: объект идентифицируется digest своего содержимого. OCI Image Format строится вокруг manifests, index, configuration и filesystem layers, связанных такими content descriptors. ([GitHub](https://github.com/opencontainers/image-spec/blob/main/spec.md?utm_source=chatgpt.com "image-spec/spec.md at main · opencontainers/image-spec"))

---

## Очень полезная модель

Не воспринимай:

```text
nginx:latest
```

как один огромный архив.

Это скорее граф объектов:

```text
                     nginx:latest
                          │
                          ▼
                   OCI IMAGE INDEX
                   sha256:854148...
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
       amd64            arm64           arm/v7
      manifest         manifest         manifest
      963c...          8725...          74a6...
          │
          ▼
      config + layers
```

И только выбранная ветка:

```text
index
  ↓
amd64 manifest
  ↓
config + 7 filesystem layer blobs
```

непосредственно нужна для создания твоего `linux/amd64` rootfs.

Поэтому твой:

```text
sha256:8541484...
```

можно читать буквально как:

> **«корневой каталог/индекс всего multi-platform набора nginx:latest»**

а:

```text
sha256:963cfe6...
```

как:

> **«описание конкретного nginx для linux/amd64».**