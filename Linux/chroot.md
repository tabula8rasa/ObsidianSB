`chroot` (**change root**) — механизм Linux, который меняет корневой каталог `/` для текущего процесса и его дочерних процессов.

После `chroot` абсолютные пути разрешаются относительно нового корня.

Например, если выполнить:

```bash
chroot /tmp/rootfs /usr/bin/bash
```

то для запущенного Bash:

```text
/ = /tmp/rootfs
```

Поэтому путь:

```text
/usr/bin/bash
```

в реальной файловой системе хоста означает:

```text
/tmp/rootfs/usr/bin/bash
```

## Синтаксис

```bash
chroot NEW_ROOT [COMMAND [ARG]...]
```

Пример:

```bash
sudo chroot /tmp/rootfs /usr/bin/bash
```

Последовательность работы:

```text
chroot("/tmp/rootfs")
        ↓
новый / установлен
        ↓
запуск /usr/bin/bash
```

То есть переданная программа запускается **после изменения root**.

Если `COMMAND` не указана:

```bash
sudo chroot /tmp/rootfs
```

утилита пытается запустить shell (`$SHELL`, либо `/bin/sh`).

## Минимальный rootfs

Недостаточно просто положить программу:

```text
/tmp/rootfs/usr/bin/bash
```

Если программа динамически слинкована, внутри нового root должны находиться также:

- ELF interpreter / dynamic linker;
    
- shared libraries;
    
- другие необходимые файлы.
    

Проверить зависимости:

```bash
ldd /usr/bin/bash
```

Проверить ELF interpreter:

```bash
readelf -l /usr/bin/bash | grep interpreter
```

Например Bash может требовать:

```text
/lib64/ld-linux-x86-64.so.2
```

Тогда этот файл должен существовать именно как:

```text
/tmp/rootfs/lib64/ld-linux-x86-64.so.2
```

иначе запуск может закончиться ошибкой:

```text
No such file or directory
```

даже если сам `/usr/bin/bash` существует.

## `PATH` и запуск программы

Если передать абсолютный путь:

```bash
chroot /tmp/rootfs /usr/bin/bash
```

`PATH` для поиска Bash не нужен.

Если передать:

```bash
chroot /tmp/rootfs bash
```

программу нужно найти через `PATH`.

Сам `chroot` не обязан очищать переменные окружения. Например:

```text
PATH=/usr/bin:/bin
```

может сохраниться, но после `chroot` `/usr/bin` уже означает:

```text
/tmp/rootfs/usr/bin
```

Переменные окружения можно посмотреть:

```bash
env
```

или:

```bash
printenv
```

Все переменные самого Bash, включая неэкспортированные:

```bash
set
```

## Почему `echo` работает, а `ls` нет

`echo` в Bash является **shell builtin**:

```bash
type echo
```

```text
echo is a shell builtin
```

Его код уже находится внутри работающего процесса Bash, поэтому отдельный executable не требуется.

`ls` обычно является отдельной программой:

```text
/usr/bin/ls
```

Поэтому внутри chroot она работает только если файл существует в новом root:

```text
/tmp/rootfs/usr/bin/ls
```

То же относится к `cat`, `ps`, `curl`, `python` и другим внешним программам.

Builtin-команды вроде:

```text
echo
cd
pwd
export
unset
```

могут работать даже в очень минимальном rootfs.

## Что `chroot` изолирует

`chroot` меняет только представление процесса о корне файловой системы:

```text
до:

root → /

после:

root → /tmp/rootfs
```

Он **не создаёт полноценный контейнер** и сам по себе не изолирует:

- процессы;
    
- PID;
    
- сеть;
    
- hostname;
    
- IPC;
    
- пользователей;
    
- CPU;
    
- RAM;
    
- Linux kernel.
    

Для этого используются [[Linux Namespaces]], [[cgroups]], capabilities и другие механизмы.

## Граничные случаи

### `chroot` — не новая файловая система

Файлы не копируются автоматически. Новый root — обычный существующий каталог.

### `chroot` — не namespace

Процесс продолжает использовать namespaces хоста, если отдельно не созданы новые.

### `chroot` — не полноценная security sandbox

Его нельзя рассматривать как надёжную границу безопасности для привилегированного процесса.

### `/proc` не появляется автоматически

Если внутри rootfs нет смонтированного `/proc`, его содержимого там не будет.

Если примонтировать `/proc` хоста:

```bash
mount --bind /proc /tmp/rootfs/proc
```

процесс внутри `chroot` сможет увидеть процессы хоста, поскольку PID namespace не был изменён.

## Связь с Docker

`chroot` помогает понять одну часть контейнеризации — **rootfs**.

Упрощённо:

```text
Docker image
    ↓
root filesystem
    ↓
процесс получает собственное представление /
```

Но настоящий контейнер дополнительно использует namespaces, cgroups, capabilities и другие механизмы Linux.

Главная идея:

> `chroot` не создаёт отдельную ОС. Он заставляет обычный Linux-процесс разрешать абсолютные пути относительно другого каталога.