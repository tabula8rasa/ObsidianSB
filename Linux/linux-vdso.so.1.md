# `linux-vdso.so.1` — vDSO в Linux

## Что это такое

`linux-vdso.so.1` — это **vDSO (virtual Dynamic Shared Object)**: небольшая ELF-библиотека, которую **ядро Linux само отображает в виртуальное адресное пространство процесса**.

Главная цель vDSO — ускорить некоторые часто вызываемые операции, для которых не всегда нужен полноценный переход:

```text
user mode
   ↓
kernel mode
   ↓
user mode
```

Вместо обычного системного вызова программа в подходящих случаях может вызвать функцию из vDSO и получить результат, оставаясь в user space.

Упрощённо:

```text
Обычный syscall

process
   │
   ▼
syscall instruction
   │
   ▼
Linux kernel
   │
   ▼
return to user space
```

С vDSO:

```text
process
   │
   ▼
glibc
   │
   ▼
vDSO function
   │
   ▼
результат в user space
```

---

## Почему она называется `linux-vdso.so.1`

Имя выглядит как имя обычной shared library.

Например:

```bash
ldd /bin/ls
```

может показать:

```text
linux-vdso.so.1 (0x00007ffd...)
libc.so.6 => /usr/lib/libc.so.6 (...)
...
```

Но есть принципиальная разница.

`libc.so.6` обычно существует как реальный файл на файловой системе.

`linux-vdso.so.1` обычно **не существует как файл в `/usr/lib`, `/lib` или другой директории**. Её предоставляет сам Linux kernel.

Поэтому:

```bash
find / -name 'linux-vdso.so.1'
```

не обязана ничего найти.

---

## Где находится vDSO

Правильнее говорить не «где лежит файл», а:

> где vDSO отображена в виртуальном адресном пространстве конкретного процесса.

Посмотреть можно так:

```bash
grep -E '\[vdso\]|\[vvar\]' /proc/$$/maps
```

Пример:

```text
7ffd6c1d9000-7ffd6c1dd000 r--p ... [vvar]
7ffd6c1dd000-7ffd6c1df000 r-xp ... [vdso]
```

`[vdso]` — отображённый код vDSO.

Адрес относится к виртуальному адресному пространству конкретного процесса, поэтому у другого процесса он может отличаться.

---

## vDSO создаёт ядро

Когда Linux запускает ELF-процесс через `execve()`, ядро подготавливает его virtual address space.

Помимо самой программы, стека и других mappings, kernel отображает туда vDSO.

Упрощённо:

```text
execve("/usr/bin/program")
        │
        ▼
Linux kernel
        │
        ├── создаёт address space
        ├── отображает ELF executable
        ├── подготавливает stack
        ├── передаёт auxiliary vector
        ├── отображает vDSO
        └── запускает программу
```

В результате address space может выглядеть примерно так:

```text
Virtual address space процесса

high addresses
┌─────────────────────────────┐
│ stack                       │
├─────────────────────────────┤
│ [vdso]                      │
├─────────────────────────────┤
│ [vvar]                      │
├─────────────────────────────┤
│ shared libraries            │
│ libc.so.6                   │
│ ld-linux-x86-64.so.2        │
├─────────────────────────────┤
│ heap                        │
├─────────────────────────────┤
│ executable                  │
└─────────────────────────────┘
low addresses
```

Конкретный порядок и адреса могут отличаться.

---

## vDSO — настоящий ELF-объект

Хотя `linux-vdso.so.1` обычно не существует как обычный файл на диске, `[vdso]` оформлен как ELF shared object.

То есть в памяти присутствуют привычные ELF-структуры:

```text
ELF header
program headers
dynamic section
symbol table
...
```

Благодаря этому userspace может находить экспортируемые функции обычными ELF-механизмами.

---

## Как программа узнаёт адрес vDSO

При запуске ELF-программы kernel передаёт ей **auxiliary vector — auxv**.

Это набор пар:

```text
тип → значение
```

Для vDSO особенно важен:

```text
AT_SYSINFO_EHDR
```

Он содержит адрес ELF header vDSO в памяти процесса.

Схема:

```text
Linux kernel
     │
     │ execve()
     ▼
auxiliary vector
     │
     ├── AT_PAGESZ
     ├── AT_UID
     ├── ...
     └── AT_SYSINFO_EHDR
             │
             ▼
         адрес vDSO
```

Пример на C:

```c
#include <stdio.h>
#include <sys/auxv.h>

int main(void)
{
    unsigned long vdso = getauxval(AT_SYSINFO_EHDR);

    printf("vDSO: 0x%lx\n", vdso);

    return 0;
}
```

Сборка:

```bash
gcc vdso.c -o vdso
```

---

## Кто обычно вызывает vDSO

Обычная программа чаще всего не работает с vDSO напрямую.

Этим занимается libc, например glibc.

Программа вызывает:

```c
clock_gettime(...);
```

а дальше логика примерно такая:

```text
application
    │
    ▼
glibc
    │
    ├── есть подходящая vDSO function?
    │          │
    │         да
    │          ▼
    │        vDSO
    │
    └── иначе
             │
             ▼
           syscall
```

То есть source code приложения может вообще ничего не знать о существовании vDSO.

---

## Какие функции могут быть в vDSO

Точный набор зависит от:

- архитектуры CPU;
- версии и ABI kernel;
- конкретной платформы.

Типичные примеры на некоторых архитектурах:

```text
__vdso_clock_gettime
__vdso_gettimeofday
__vdso_time
__vdso_getcpu
```

Нельзя предполагать, что любой Linux экспортирует один и тот же набор символов.

---

## Зачем ускорять `clock_gettime()`

Без vDSO частый запрос времени выглядел бы так:

```text
userspace
   │
   │ syscall
   ▼
kernel
   │
   ▼
userspace
```

Переход между user mode и kernel mode имеет стоимость.

Для части операций kernel может безопасно предоставить userspace код и данные, необходимые для вычисления результата.

Тогда получается:

```text
userspace
   │
   ▼
vDSO
   │
   ▼
kernel-provided data
   │
   ▼
результат
```

без полноценного системного вызова.

---

## `[vvar]`

Рядом с `[vdso]` часто виден mapping:

```text
[vvar]
```

Например:

```bash
grep -E '\[vdso\]|\[vvar\]' /proc/self/maps
```

может показать:

```text
... r--p ... [vvar]
... r-xp ... [vdso]
```

Упрощённо:

```text
[vdso]
= исполняемый userspace-код, предоставленный kernel

[vvar]
= kernel-provided данные, которые этот код может использовать
```

Точная организация зависит от архитектуры.

---

## Почему vDSO быстрее syscall

Обычный syscall:

```text
Ring 3 / user mode
        │
        │ syscall
        ▼
Ring 0 / kernel mode
        │
        ▼
Ring 3 / user mode
```

vDSO-код уже находится в address space процесса:

```text
Ring 3
process
   │
   ▼
vDSO
   │
   ▼
return
```

Поэтому в подходящих случаях можно избежать полноценного перехода в kernel mode.

---

## vDSO не заменяет системные вызовы вообще

Большинство операций всё равно требует kernel mode.

Например:

```text
open()
read()
write()
fork()
mount()
```

обычно должны работать с защищённым состоянием kernel:

- filesystem;
- драйверами;
- page cache;
- scheduler;
- permissions;
- kernel memory.

vDSO подходит только для ограниченного набора операций.

---

## vDSO и syscall — не одно и то же

Полезно различать:

```text
syscall
```

— механизм перехода из userspace в kernel.

```text
vDSO
```

— kernel-provided ELF-код, выполняемый в userspace.

То есть vDSO function не обязательно является «скрытым syscall».

Некоторые операции могут быть выполнены полностью в userspace, а при невозможности libc или реализация может использовать fallback к обычному syscall.

---

## Почему `ldd` показывает `linux-vdso.so.1`

Например:

```bash
ldd /bin/bash
```

может вернуть:

```text
linux-vdso.so.1 (0x00007ffc...)
libc.so.6 => /usr/lib/libc.so.6 (...)
...
```

Это не означает:

```text
/bin/bash
   ↓
ищет linux-vdso.so.1 на диске
   ↓
dynamic linker загружает файл
```

Правильнее:

```text
execve()
   │
   ▼
kernel
   │
   ├── отображает executable
   ├── отображает vDSO
   └── передаёт AT_SYSINFO_EHDR
             │
             ▼
       dynamic linker / libc
             │
             ▼
        используют vDSO
```

---

## Имя зависит от архитектуры

`linux-vdso.so.1` — типичное имя для x86-64, но имя vDSO может отличаться между архитектурами и ABI.

Например исторически на i386 встречается:

```text
linux-gate.so.1
```

Поэтому программам не следует жёстко привязываться к строке:

```text
linux-vdso.so.1
```

---

## ASLR и адрес vDSO

Адрес vDSO нельзя считать постоянным.

Например:

```text
process A:
[vdso] → 0x7ffd12340000
```

```text
process B:
[vdso] → 0x7ffe98760000
```

Адрес может рандомизироваться вместе с другими частями virtual address space.

Поэтому программа получает реальный адрес через механизм запуска процесса, а не угадывает его.

---

## Как посмотреть vDSO текущего shell

```bash
grep '\[vdso\]' /proc/$$/maps
```

Пример:

```text
7ffca10a4000-7ffca10a6000 r-xp 00000000 00:00 0 [vdso]
```

Здесь:

```text
7ffca10a4000
```

— начало mapping.

```text
7ffca10a6000
```

— конец mapping.

```text
r-xp
```

означает, что mapping читаемый и исполняемый.

---

## Сравнение с обычной `.so`

Обычная shared library:

```text
/usr/lib/libc.so.6
        │
        │ файл на filesystem
        ▼
dynamic loader
        │
        │ mmap()
        ▼
address space процесса
```

vDSO:

```text
Linux kernel
        │
        │ execve()
        ▼
создаёт / отображает vDSO
        │
        ▼
address space процесса
```

Источник различается:

```text
libc.so.6
→ filesystem

linux-vdso.so.1
→ Linux kernel
```

---

## vDSO и Docker / контейнеры

Для контейнеров это особенно важно.

Если внутри контейнера выполнить:

```bash
ldd /bin/sh
```

можно увидеть:

```text
linux-vdso.so.1
```

Но искать её в Docker image:

```text
snapshot/fs/usr/lib/
snapshot/fs/lib/
```

бессмысленно.

Она **не является слоем image и не хранится в rootfs контейнера как обычная библиотека**.

Контейнер использует kernel хоста.

Схема:

```text
Docker image
    │
    ├── /bin
    ├── /usr
    ├── libc.so
    └── ...
          │
          ▼
      container process
          │
          │ запускается Linux kernel хоста
          ▼
kernel отображает [vdso]
          │
          ▼
virtual address space процесса
```

То есть rootfs предоставляет userspace-файлы, а `linux-vdso.so.1` предоставляет kernel хоста.

Это ещё один пример разделения:

```text
Container userspace
────────────────────
rootfs из image
glibc
nginx
/bin/sh
...

Host Linux kernel
────────────────────
namespaces
cgroups
syscalls
vDSO
...
```

---

## Полезные команды

Посмотреть vDSO текущего shell:

```bash
grep '\[vdso\]' /proc/$$/maps
```

Посмотреть vDSO и vvar:

```bash
grep -E '\[vdso\]|\[vvar\]' /proc/$$/maps
```

Посмотреть все mappings процесса:

```bash
cat /proc/$$/maps
```

Посмотреть строку vDSO через `ldd`:

```bash
ldd /bin/bash
```

или:

```bash
ldd /bin/ls
```

Посмотреть auxiliary vector процесса:

```bash
cat /proc/$$/auxv
```

`/proc/<pid>/auxv` имеет бинарный формат, поэтому для удобного получения конкретного значения обычно используют `getauxval()`.

---

## Полная схема

```text
                    Linux kernel
                         │
                         │ execve()
                         ▼
              создаётся новый процесс
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
       ELF program                  vDSO
            │                         │
            │                    [vdso] mapping
            │                         │
            └────────────┬────────────┘
                         │
                         ▼
                virtual address space
                         │
                         ▼
                      glibc
                         │
             ┌───────────┴───────────┐
             │                       │
             ▼                       ▼
      подходящая vDSO          обычный syscall
         function                 fallback
```

---

## Главное

`linux-vdso.so.1` — это **не обычная библиотека на диске**.

Это небольшой ELF shared object, который Linux kernel отображает в virtual address space процесса.

Он позволяет libc и приложениям выполнять некоторые часто используемые операции быстрее, иногда без полноценного перехода:

```text
userspace → kernel → userspace
```

Ключевая модель:

```text
Linux kernel
     │
     │ создаёт mapping
     ▼
   [vdso]
     │
     │ ELF shared object
     ▼
virtual address space процесса
     │
     ▼
glibc
     │
     ▼
application
```

В Docker-контейнере `linux-vdso.so.1` также не приходит из image:

```text
Docker image/rootfs
    ≠
linux-vdso.so.1
```

Её предоставляет общий Linux kernel хоста каждому запускаемому процессу.

---

## Источники

- Linux `vdso(7)` manual page.
- Linux Kernel documentation по vDSO ABI.
- Linux Kernel documentation по `/proc` и mappings процессов.
