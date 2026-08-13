## Что такое системный вызов

`chroot()`, `execve()`, `read()`, `write()`, `mmap()` и похожие функции относятся к системным вызовам Linux либо к функциям libc, которые в конечном итоге используют системный вызов.

Обычная программа работает в **user mode** и не может напрямую менять привилегированное состояние системы:

```text
процессы
mount tree
page tables
network stack
credentials
namespaces
устройства
filesystem state
```

Когда программе нужна такая операция, она обращается к ядру:

```text
user program
    │
    │ syscall
    ▼
Linux kernel
    │
    │ выполняет привилегированную операцию
    ▼
user program
```

Отсюда и название:

```text
system call
=
вызов операционной системы / ядра
```

Обычный вызов функции:

```c
foo();
```

может полностью остаться в user mode:

```text
user code
   ↓
foo()
   ↓
user code
```

А системный вызов приводит к переходу:

```text
user mode
    │
    │ syscall
    ▼
kernel mode
    │
    │ kernel выполняет операцию
    ▼
user mode
```

---

## Важное различие: C-функция и настоящий syscall

В C запись:

```c
write(fd, buf, size);
```

выглядит как обычный вызов функции.

Часто это действительно вызов wrapper-функции из libc:

```text
application
    ↓
glibc write()
    ↓
syscall instruction
    ↓
Linux syscall
    ↓
kernel implementation
```

Поэтому полезно различать:

```text
C API
   ↓
libc wrapper
   ↓
Linux syscall
   ↓
kernel
```

Не каждая функция libc вызывает ядро.

Например:

```c
strlen("hello");
```

может полностью выполниться в user mode.

А `write()` должен обратиться к kernel, потому что объект, связанный с file descriptor, управляется ядром.

---

## `chroot()`

Название:

```text
ch + root
change root
```

Пример:

```c
chroot("/home/user/dump");
```

Меняет root directory **текущего процесса**.

Было:

```text
process.root → /
```

Стало:

```text
process.root → /home/user/dump
```

PID процесса не меняется.

После этого абсолютный путь:

```text
/etc/passwd
```

для процесса разрешается относительно нового root:

```text
/home/user/dump/etc/passwd
```

`chroot()` требует участия kernel, потому что root directory является частью состояния процесса, которым управляет ядро.

---

## `chdir()`

Название:

```text
ch + dir
change directory
```

Пример:

```c
chdir("/tmp");
```

Меняет current working directory процесса:

```text
process.cwd
```

Было:

```text
cwd → /home/user
```

Стало:

```text
cwd → /tmp
```

---

## `fchdir()`

Название можно понимать как:

```text
file-descriptor chdir
```

Вместо строки пути используется уже открытый file descriptor директории:

```c
int fd = open("/tmp", O_RDONLY);

fchdir(fd);
```

Схема:

```text
fd
 │
 ▼
directory /tmp
 │
 ▼
cwd процесса
```

Это позволяет сохранить ссылку на директорию и позже сделать её текущей рабочей директорией.

---

## `execve()`

Название исторически раскладывается так:

```text
exec = execute
v    = vector
e    = environment
```

Пример:

```c
execve(
    "/bin/bash",
    argv,
    envp
);
```

`execve()` говорит kernel:

> заменить исполняемую программу текущего процесса новой программой.

Например:

```text
PID 5000
exploit
```

после:

```c
execve("/bin/bash", ...);
```

становится:

```text
PID 5000
bash
```

PID остаётся тем же.

Kernel заменяет старый executable, mappings программы и stack на состояние нового executable.

---

## `open()` и `openat()`

`open` означает:

```text
open file
```

Пример:

```c
open("/etc/passwd", O_RDONLY);
```

Kernel:

1. разрешает путь;
2. проверяет права;
3. открывает объект;
4. создаёт запись в таблице file descriptors процесса;
5. возвращает номер descriptor.

Например:

```text
0 → stdin
1 → stdout
2 → stderr
3 → /etc/passwd
```

`openat()` позволяет разрешать относительный путь относительно directory file descriptor.

Пример:

```c
openat(dirfd, "config.txt", O_RDONLY);
```

Если:

```text
dirfd → /etc/myapp
```

то путь:

```text
config.txt
```

будет разрешён как:

```text
/etc/myapp/config.txt
```

У многих filesystem API существуют варианты `*at()`:

```text
openat()
mkdirat()
unlinkat()
renameat()
fchmodat()
```

---

## `read()`

Название буквально:

```text
read
= прочитать
```

Пример:

```c
read(fd, buffer, 100);
```

Просит kernel прочитать до 100 байт из объекта, связанного с file descriptor.

Этот объект может быть:

```text
обычный файл
socket
pipe
terminal
device
```

---

## `write()`

Название:

```text
write
= записать
```

Пример:

```c
write(1, "hello\n", 6);
```

File descriptor `1` обычно является stdout.

Схема:

```text
process
   │
   │ write(1, ...)
   ▼
kernel
   │
   ▼
stdout object
   │
   ▼
terminal / pipe / file
```

---

## `close()`

Название:

```text
close
= закрыть
```

Пример:

```c
close(fd);
```

Kernel удаляет соответствующий descriptor из таблицы процесса.

---

## `mmap()`

Название:

```text
m + map
memory map
```

`mmap()` создаёт mapping в виртуальном адресном пространстве процесса.

Backing может быть:

```text
anonymous memory
file
shared memory
```

Например shared library может быть отображена так:

```text
libc.so.6
    │
    ▼
mmap()
    │
    ▼
virtual address space процесса
```

Kernel нужен потому, что операция изменяет memory mappings процесса и связанные структуры виртуальной памяти.

---

## `munmap()`

Название:

```text
m + unmap
memory unmap
```

Пример:

```c
munmap(addr, size);
```

Удаляет mapping из виртуального адресного пространства.

---

## `brk()`

`brk()` связан с понятием **program break** — границей heap.

Упрощённо:

```text
heap
┌─────────────────────┐
│ allocated           │
│ allocated           │
│ free                │
└─────────────────────┘
                     ▲
                     │
               program break
```

`brk()` может перемещать эту границу.

Современные allocators используют и `brk()`, и `mmap()`.

---

## `mprotect()`

Название:

```text
memory protect
```

Меняет права доступа к диапазону виртуальной памяти:

```text
read
write
execute
```

Kernel обновляет соответствующие permissions в memory mappings/page tables.

---

## `fork()`

Название:

```text
fork
= разветвление
```

Пример:

```c
pid_t pid = fork();
```

После вызова выполнение продолжают два процесса:

```text
             process
                │
               fork
             /      \
            /        \
       parent        child
```

`fork()` создаёт новый процесс.

На Linux libc может реализовывать это через более низкоуровневые механизмы вроде `clone()`.

---

## `clone()` / `clone3()`

Название:

```text
clone
= создать копию
```

Это более низкоуровневый Linux-механизм создания execution context.

В зависимости от flags можно создать сущность, которая:

```text
разделяет память
разделяет file descriptors
разделяет filesystem state
разделяет signal handlers
имеет отдельные namespaces
```

Поэтому через `clone()` можно реализовывать как процессы, так и threads.

---

## `wait4()` / `waitid()`

`wait` означает:

```text
ждать
```

Parent process может ждать изменения состояния child:

```text
parent
   │
   │ wait
   ▼
kernel
   │
   │ child завершился
   ▼
parent продолжает работу
```

---

## `exit()` и `_exit()`

Название:

```text
exit
= выйти
```

Kernel должен:

```text
освободить process state
закрыть descriptors
освободить mappings
уведомить parent
сохранить exit status
```

`exit()` из libc перед окончательным завершением может также выполнить userspace cleanup:

```text
flush buffers
atexit handlers
```

---

## `getpid()`

Название:

```text
get + PID
```

Возвращает Process ID текущего процесса.

---

## `kill()`

Название немного обманчиво.

```c
kill(pid, signal);
```

не обязательно убивает процесс.

Фактически операция означает:

> отправить signal процессу.

Например:

```text
SIGTERM
SIGKILL
SIGSTOP
SIGCONT
SIGHUP
SIGUSR1
```

---

## `socket()`

Создаёт kernel networking object.

Например:

```c
socket(AF_INET, SOCK_STREAM, 0);
```

создаёт IPv4 TCP socket.

Kernel возвращает file descriptor:

```text
fd 4
 │
 ▼
kernel TCP socket
```

---

## `connect()`

Название:

```text
connect
= подключиться
```

Для TCP kernel начинает установление соединения:

```text
application
    │
    │ connect()
    ▼
kernel TCP stack
    │
    ├── SYN
    ├── SYN-ACK
    └── ACK
```

---

## `bind()`

Название:

```text
bind
= привязать
```

Привязывает socket к локальному адресу и порту.

Например:

```text
socket
  │
  ▼
0.0.0.0:80
```

---

## `listen()`

Название:

```text
listen
= слушать
```

Переводит TCP socket в listening state:

```text
socket
   ↓
bind :80
   ↓
listen
   ↓
ожидание входящих соединений
```

---

## `accept()`

Название:

```text
accept
= принять
```

Server принимает входящее TCP connection.

Например:

```text
fd 3 → listening socket :80

accept()

fd 4 → connection Client A
```

---

## `sendto()` и `recvfrom()`

Используются для отправки и получения сетевых данных.

```text
sendto
= отправить данные адресу

recvfrom
= получить данные и узнать отправителя
```

---

## `pipe()`

Название:

```text
pipe
= труба
```

Создаёт kernel buffer и два descriptor:

```text
fd[0] → read end
fd[1] → write end
```

Схема:

```text
Process A
   │
   │ write
   ▼
┌──────── kernel pipe ────────┐
└─────────────────────────────┘
                 │
                 │ read
                 ▼
             Process B
```

Shell pipeline:

```bash
cat file | grep hello
```

использует эту идею.

---

## `dup()` / `dup2()`

Название:

```text
dup
= duplicate
```

Дублирует file descriptor.

Например:

```text
fd 3 ──┐
       ├──► один open file description
fd 7 ──┘
```

Это важно для shell redirection.

---

## `ioctl()`

Название:

```text
I/O control
```

`ioctl()` — универсальный интерфейс для специальных команд устройствам и kernel objects.

Схема:

```text
userspace
   │
   │ ioctl()
   ▼
kernel
   │
   ▼
driver / kernel subsystem
```

---

## `mount()`

Название:

```text
mount
= смонтировать
```

Пример:

```c
mount(
    "proc",
    "/proc",
    "proc",
    0,
    NULL
);
```

Kernel добавляет filesystem в mount tree:

```text
/
├── etc
├── usr
└── proc       ← mount point
      │
      ▼
    procfs
```

---

## `umount2()`

Удаляет mount из дерева.

Исторически системный вызов называется `umount`, а не `unmount`.

---

## `unshare()`

Название:

```text
un + share
```

То есть:

> перестать разделять некоторый kernel context с текущим окружением.

Очень важный syscall для контейнеров.

Например:

```c
unshare(CLONE_NEWNS);
```

создаёт отдельный mount namespace.

Типы namespace:

```text
CLONE_NEWNS
CLONE_NEWPID
CLONE_NEWNET
CLONE_NEWUTS
CLONE_NEWIPC
CLONE_NEWUSER
CLONE_NEWCGROUP
```

---

## `setns()`

Название:

```text
set namespace
```

Позволяет процессу присоединиться к уже существующему namespace:

```text
process
   │
   │ setns(fd)
   ▼
existing namespace
```

Утилита `nsenter` использует эту идею.

---

## `pivot_root()`

Название:

```text
pivot root
```

Меняет root filesystem mount namespace более фундаментально, чем `chroot()`.

Упрощённо:

```text
old root
   ↓
pivot_root()
   ↓
new root
```

Этот механизм особенно важен для контейнерных runtime.

---

## `setuid()`

Название:

```text
set + UID
```

Пример:

```c
setuid(1000);
```

Kernel хранит credentials процесса:

```text
UID
GID
capabilities
...
```

Поэтому процесс не может просто изменить число UID в userspace-памяти и стать root.

---

## `setgid()`

Название:

```text
set + GID
```

Меняет group identity процесса при наличии необходимых прав.

---

## `capset()`

Связан с Linux capabilities.

Позволяет изменять capability sets процесса при соблюдении правил kernel.

---

## `prctl()`

Название:

```text
process control
```

Используется для управления различными свойствами процесса.

---

## Классификация системных вызовов

### Filesystem

```text
openat()
read()
write()
close()
mkdir()
unlink()
rename()
chdir()
chroot()
mount()
umount2()
```

### Processes

```text
clone()
fork()
execve()
exit()
wait()
kill()
getpid()
```

### Memory

```text
mmap()
munmap()
mprotect()
brk()
```

### Networking

```text
socket()
bind()
listen()
accept()
connect()
sendto()
recvfrom()
```

### Security / identity

```text
setuid()
setgid()
capset()
prctl()
```

### Namespaces / containers

```text
clone()
unshare()
setns()
mount()
pivot_root()
chroot()
```

---

## Связь с Docker и `runc`

Когда говорят:

> `runc` создаёт контейнер

это не означает, что у Linux существует один syscall:

```text
create_container()
```

Такого системного вызова нет.

`runc` — userspace-программа, которая использует множество обычных Linux primitives.

Упрощённо:

```text
runc
  │
  ├── clone / clone3
  │      └── создать process/namespaces
  │
  ├── unshare
  │      └── отделить namespace
  │
  ├── setns
  │      └── войти в существующий namespace
  │
  ├── mount
  │      └── подготовить filesystem tree
  │
  ├── pivot_root
  │      └── сделать rootfs контейнера новым root
  │
  ├── setuid / setgid
  │      └── настроить credentials
  │
  ├── prctl / capabilities / seccomp
  │      └── ограничить процесс
  │
  └── execve
         └── запустить программу контейнера
```

То есть контейнер строится из обычных primitives Linux kernel:

```text
Docker / containerd / runc
            │
            ▼
        Linux syscalls
            │
            ▼
        Linux kernel
            │
      ┌─────┼───────────┐
      ▼     ▼           ▼
namespaces mounts     cgroups
      │     │           │
      └─────┼───────────┘
            ▼
      container process
```

---

## Главное

Системный вызов — это способ программы попросить kernel выполнить операцию, которую userspace не может или не должен выполнять самостоятельно.

Примеры:

```text
chroot()
→ изменить root процесса

execve()
→ заменить программу текущего процесса

openat()
→ открыть filesystem object

read()
→ прочитать данные через fd

write()
→ записать данные через fd

mmap()
→ создать virtual memory mapping

clone()
→ создать новый task/process/thread context

socket()
→ создать сетевой socket

mount()
→ изменить mount tree

unshare()
→ создать отдельный namespace context

setns()
→ войти в namespace

setuid()
→ изменить credentials

kill()
→ отправить signal
```

Ментальная модель:

```text
обычное вычисление
→ CPU выполняет напрямую в user mode

нужно изменить/использовать защищённое состояние ОС
→ syscall
→ kernel mode
→ kernel выполняет операцию
→ возврат в user mode
```
