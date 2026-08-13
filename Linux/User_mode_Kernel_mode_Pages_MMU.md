## 1. Главная идея

Обычная программа **не обращается к ядру Linux при каждой инструкции**.

Когда процесс уже запущен, CPU напрямую исполняет его инструкции в **user mode**:

```text
ADD
MOV
CMP
JMP
MUL
...
```

Ядро не участвует в каждом сложении, сравнении или чтении памяти.

Упрощённо:

```text
Linux kernel
    │
    │ запускает процесс,
    │ настраивает память,
    │ выдаёт CPU time
    ▼

CPU
    │
    ├── instruction
    ├── instruction
    ├── instruction
    └── instruction
```

Переход в kernel mode нужен только тогда, когда процессу требуется действие, которое обычному userspace-коду выполнять напрямую нельзя.

---

# 2. User mode и Kernel mode

Современный CPU имеет уровни привилегий.

На x86 обычно упрощённо говорят:

```text
Ring 3 → user mode
Ring 0 → kernel mode
```

## User mode

В user mode работают обычные программы:

```text
Python
nginx
PostgreSQL
bash
браузер
...
```

В этом режиме процесс может:

```text
выполнять арифметику
работать с регистрами
читать свою память
писать в свою память
выполнять переходы
вызывать функции
использовать SIMD-инструкции
```

Например:

```c
int a = 10;
int b = 20;
int c = a + b;
```

может свестись к обычным инструкциям CPU:

```asm
mov ...
add ...
mov ...
```

и выполниться полностью в user mode.

---

## Kernel mode

В kernel mode выполняется ядро Linux.

Оно имеет доступ к привилегированным возможностям:

```text
управление page tables
управление процессами
работа с устройствами
сетевой стек
filesystem
scheduler
драйверы
permissions
mount
cgroups
namespaces
...
```

Обычный процесс не может напрямую выполнять эти действия.

---

# 3. Когда нужен переход в Kernel mode

Есть несколько основных причин.

## 3.1. System call

Процесс сам просит kernel выполнить привилегированную операцию.

Например:

```c
write(fd, "hello", 5);
```

Схема:

```text
application
    │
    ▼
libc
    │
    │ syscall
    ▼

====== privilege boundary ======

Linux kernel
    │
    ├── проверяет fd
    ├── проверяет права
    ├── находит объект
    ├── выполняет запись
    └── возвращает результат

====== privilege boundary ======

application
```

Типичные syscalls:

```text
open
read
write
mmap
brk
fork
clone
socket
connect
mount
...
```

---

## 3.2. Exception

CPU сам обнаруживает событие, которое требует обработки kernel.

Например:

```text
page fault
division by zero
invalid instruction
general protection fault
```

---

## 3.3. Hardware interrupt

Событие приходит от устройства.

Например:

```text
сетевой адаптер получил пакет
диск завершил операцию
таймер сработал
```

CPU временно переключается в kernel mode, чтобы обработать interrupt.

---

## 3.4. Scheduler / Timer interrupt

Процесс может просто долго считать:

```text
ADD
CMP
JMP
ADD
CMP
JMP
...
```

Но аппаратный timer периодически вызывает interrupt.

Kernel получает управление и может решить:

```text
этому процессу хватит CPU,
теперь запускаем другой
```

После чего происходит context switch.

---

# 4. Kernel не стоит между программой и CPU

Это один из самых важных моментов.

Когда программа уже выполняется, CPU напрямую исполняет её инструкции.

Например:

```text
RAX = 5
RBX = 10

ADD RAX, RBX
```

CPU получает:

```text
RAX = 15
```

Kernel здесь не нужен.

То же самое касается обычного чтения памяти:

```c
x = array[100];
```

Путь выглядит примерно так:

```text
process
   │
   ▼
CPU
   │
   ▼
MMU
   │
   ▼
RAM / CPU cache
```

Kernel не исполняет код при каждом таком обращении.

---

# 5. Что такое виртуальная память

Процесс обычно не работает с физическими адресами RAM напрямую.

Он работает с **виртуальными адресами**.

Например процесс считает, что у него есть:

```text
0x00000000
...
0x7fffffffffff
```

Это его собственное виртуальное адресное пространство.

Другой процесс может использовать такие же виртуальные адреса, но они будут отображаться на другие физические области RAM.

Например:

```text
Process A

virtual 0x1000
    ↓
physical page X
```

```text
Process B

virtual 0x1000
    ↓
physical page Y
```

То есть одинаковый virtual address у двух процессов может указывать на разные physical memory pages.

---

# 6. Что такое Page

Физическая и виртуальная память разбивается на блоки фиксированного размера — **pages**.

На x86-64 типичный размер обычной page:

```text
4 KiB
```

Также существуют large / huge pages, например:

```text
2 MiB
1 GiB
```

Но базовая модель обычно строится вокруг 4 KiB pages.

---

## Виртуальные pages

Виртуальное адресное пространство процесса делится:

```text
Virtual Address Space

┌───────────────┐
│ virtual page 0│
├───────────────┤
│ virtual page 1│
├───────────────┤
│ virtual page 2│
├───────────────┤
│ virtual page 3│
├───────────────┤
│ ...           │
└───────────────┘
```

---

## Physical frames

RAM тоже логически разбивается на блоки такого же размера.

Их часто называют:

```text
physical pages
```

или:

```text
page frames
```

Например:

```text
Physical RAM

┌──────────────┐
│ frame 0      │
├──────────────┤
│ frame 1      │
├──────────────┤
│ frame 2      │
├──────────────┤
│ frame 3      │
├──────────────┤
│ ...          │
└──────────────┘
```

---

# 7. Page Table

Kernel хранит для процесса структуру, которая описывает соответствие:

```text
virtual page
    ↓
physical frame
```

Эта структура называется:

```text
page table
```

Например:

```text
Process A page table

Virtual Page      Physical Frame
------------      --------------
0x1000         →  frame 120
0x2000         →  frame 901
0x3000         →  frame 77
0x4000         →  not mapped
```

Кроме физического адреса, page table entry содержит flags.

Например:

```text
present
readable
writable
executable
user accessible
dirty
accessed
...
```

То есть page table определяет не только:

> куда отображается виртуальная страница

но и:

> что процессу разрешено с ней делать.

---

# 8. Что такое MMU

**MMU — Memory Management Unit**.

Это аппаратный блок процессора, который занимается переводом:

```text
virtual address
    ↓
physical address
```

и проверкой прав доступа.

Важно:

> перевод virtual → physical обычно делает не kernel-код, а аппаратный MMU.

Kernel лишь заранее создаёт и настраивает page tables.

---

# 9. Как MMU работает при обычном доступе к памяти

Допустим программа выполняет:

```c
x = *(0x7f1234567000);
```

CPU получает virtual address:

```text
0x7f1234567000
```

Дальше:

```text
process
   │
   ▼
virtual address
   │
   ▼
MMU
   │
   ▼
page table
   │
   ▼
physical frame
   │
   ▼
RAM / cache
```

Если mapping существует и доступ разрешён:

```text
никакого перехода в kernel mode не происходит
```

CPU просто получает нужные данные.

---

# 10. Почему kernel не нужен при каждом обращении к RAM

Потому что kernel заранее настроил page tables.

После этого MMU применяет эти правила аппаратно.

Можно думать так:

```text
Kernel:
"для Process A virtual page X
 отображается на physical frame Y"
```

После этого:

```text
CPU + MMU
```

могут выполнять тысячи и миллионы memory accesses без вызова kernel.

---

# 11. TLB

Если бы MMU при каждом memory access полностью обходил page tables в RAM, это было бы дорого.

Поэтому CPU использует специальный cache:

```text
TLB
```

— Translation Lookaside Buffer.

Он хранит недавно использованные соответствия:

```text
virtual page
    ↓
physical frame
```

Схема:

```text
virtual address
     │
     ▼
    TLB
   /   \
 hit   miss
  │      │
  │      ▼
  │   page table walk
  │      │
  └──────┘
     │
     ▼
physical address
```

## TLB hit

Если перевод уже есть в TLB:

```text
virtual → physical
```

получается очень быстро.

## TLB miss

Если записи нет:

```text
MMU / CPU
    ↓
обходит page tables
    ↓
получает mapping
    ↓
кладёт его в TLB
```

Это ещё не обязательно требует перехода в kernel mode.

---

# 12. Page Fault

Page fault происходит, когда CPU обращается к virtual page, для которой текущий mapping требует участия kernel.

Например:

```text
page отсутствует
page не present
нарушены permissions
copy-on-write
страница ещё не загружена
```

Схема:

```text
user mode
    │
    │ memory access
    ▼
MMU
    │
    │ mapping не подходит
    ▼
CPU exception
    │
    ▼

====== kernel mode ======

page fault handler
    │
    ├── проверяет адрес
    ├── проверяет mapping
    ├── при необходимости выделяет page
    ├── обновляет page tables
    └── возвращает управление

====== user mode ======
```

---

# 13. Не каждый Page Fault является ошибкой

Это очень важно.

Page fault — нормальная часть работы виртуальной памяти.

Например процесс делает:

```c
p = malloc(100 * 1024 * 1024);
```

Allocator может получить виртуальный диапазон:

```text
100 MB virtual address space
```

Но kernel не обязан сразу выделять 100 MB физической RAM.

Процесс впервые пишет:

```text
p[0] = 1;
```

MMU обнаруживает, что physical page ещё нет.

Возникает:

```text
page fault
```

Kernel выделяет physical frame:

```text
virtual page
    ↓
new physical frame
```

обновляет page table и возвращает процессу управление.

Это называется demand paging.

---

# 14. Minor и Major Page Fault

Упрощённо:

## Minor page fault

Kernel может обработать fault без чтения данных с диска.

Например:

```text
выделить новую zero-filled page
copy-on-write
уже имеющаяся страница page cache
```

## Major page fault

Для обработки требуется I/O.

Например страница executable или memory-mapped файла ещё не находится в RAM:

```text
page fault
    ↓
kernel
    ↓
disk / storage read
    ↓
RAM
```

Major page fault намного дороже.

---

# 15. Memory allocation и Kernel mode

Не каждый:

```text
malloc()
```

или создание Python object приводит к syscall.

Например Python allocator уже имеет свободную память:

```text
heap

┌───────────────┐
│ used          │
│ used          │
│ free          │
│ free          │
│ free          │
└───────────────┘
```

Python создаёт объект:

```python
x = [1, 2, 3]
```

и просто использует свободный кусок.

---

## Когда allocator идёт в kernel

Когда нужно расширить доступное виртуальное пространство:

```text
allocator
    │
    ▼
mmap()
или brk()
    │
    ▼
syscall
    │
    ▼
kernel
```

Kernel создаёт новый virtual memory mapping.

Но даже после этого physical pages могут назначаться лениво — через page faults при первом обращении.

---

# 16. Полный путь выделения памяти

Например:

```python
data = bytearray(100_000_000)
```

Упрощённая цепочка может выглядеть так:

```text
Python
   │
   ▼
Python allocator
   │
   ▼
libc allocator
   │
   │ нужно больше памяти
   ▼
mmap()
   │
   ▼
syscall
   │
   ▼
Linux kernel
   │
   ├── создаёт virtual mapping
   └── возвращает virtual addresses
   │
   ▼
Python
```

После этого первая запись:

```text
write to page
   │
   ▼
MMU
   │
   ▼
page not present
   │
   ▼
page fault
   │
   ▼
kernel
   │
   ├── выделяет physical page
   ├── обновляет page table
   └── return
```

После этого дальнейшие обращения:

```text
CPU
 ↓
MMU
 ↓
TLB/page table
 ↓
RAM
```

идут без kernel transition.

---

# 17. Permissions на уровне Pages

Page table может задавать разные права.

Например:

```text
code:
read + execute

data:
read + write

stack:
read + write

read-only data:
read only
```

Если процесс пытается писать в read-only page:

```text
WRITE
  ↓
MMU
  ↓
permission violation
  ↓
page fault
  ↓
kernel
```

Kernel анализирует ситуацию.

Если доступ незаконный, процесс может получить:

```text
SIGSEGV
```

---

# 18. Copy-on-Write и Pages

Copy-on-write используется не только OverlayFS.

Он также широко применяется в виртуальной памяти.

После `fork()` parent и child могут временно использовать одни и те же physical pages:

```text
Parent virtual page ─┐
                     ├──> Physical frame X
Child virtual page  ─┘
```

Обе mapping помечаются read-only/COW.

Если child пытается записать:

```text
write
 ↓
page fault
 ↓
kernel
 ↓
создаёт копию physical page
```

Получаем:

```text
Parent
   │
   └── Physical frame X

Child
   │
   └── Physical frame Y
```

То есть копирование происходит только при первой записи.

---

# 19. Почему процесс не может читать память другого процесса

У каждого процесса свои page tables.

Например:

```text
Process A:

0x1000 → frame 10
```

```text
Process B:

0x1000 → frame 900
```

Когда scheduler переключает CPU с процесса A на процесс B, активный memory context меняется.

Поэтому MMU начинает использовать page tables процесса B.

Это одна из основ изоляции процессов.

---

# 20. Context Switch и память

При переключении:

```text
Process A
   ↓
Kernel scheduler
   ↓
Process B
```

kernel меняет:

```text
register state
instruction pointer
stack pointer
memory context / page tables
и другие CPU state
```

После этого те же virtual addresses могут означать совершенно другие physical pages.

---

# 21. Связь с Docker

Контейнер не имеет отдельного kernel.

Процессы контейнера выполняются обычным Linux kernel хоста.

То есть процесс nginx внутри контейнера:

```text
nginx
  │
  ├── выполняет обычные CPU instructions в user mode
  ├── использует MMU
  ├── имеет virtual address space
  ├── использует pages
  ├── вызывает syscalls
  └── получает page faults
```

точно так же, как обычный host process.

Namespaces и cgroups изменяют изоляцию и ограничения, но модель:

```text
user mode
kernel mode
MMU
page tables
pages
syscalls
```

остаётся той же.

---

# 22. Связь с `linux-vdso.so.1`

Теперь понятно, зачем существует vDSO.

Например `clock_gettime()` мог бы каждый раз делать:

```text
application
    ↓
syscall
    ↓
kernel mode
    ↓
получить время
    ↓
user mode
```

Но переход:

```text
user → kernel → user
```

имеет стоимость.

Поэтому kernel отображает в process address space:

```text
[vdso] — условно инструкция / алгоритм / исполняемый код
[vvar] — актуальные данные от ядра, необходимые этому алгоритму
```

и libc иногда может получить результат без полноценного syscall:

```text
                  Linux kernel
                       │
          ┌────────────┴─────────────┐
          │                          │
          ▼                          ▼
       [vdso]                     [vvar]
   код вычисления             базовые параметры
          │                          │
          └────────────┬─────────────┘
                       ▼
                    process
                       │
                       ├── читает CPU counter
                       ├── читает [vvar]
                       ├── выполняет [vdso]
                       │
                       ▼
                получает время
```

Всё это может выполниться:

```text
user mode
```

---

# 23. Итоговая модель

```text
                     PROCESS
                        │
                        ▼

                USER MODE / Ring 3

        ┌─────────────────────────┐
        │ application             │
        │                         │
        │ ADD / MOV / CMP         │
        │ function calls          │
        │ normal memory access    │
        │ vDSO                    │
        └────────────┬────────────┘
                     │
                     │ syscall
                     │ exception
                     │ interrupt
                     ▼

============= privilege boundary =============

               KERNEL MODE / Ring 0

        ┌─────────────────────────┐
        │ Linux kernel            │
        │                         │
        │ scheduler               │
        │ filesystem              │
        │ networking              │
        │ memory management       │
        │ drivers                 │
        │ page fault handler      │
        │ process management      │
        └─────────────────────────┘
```

При обычном memory access:

```text
application
    │
    ▼
virtual address
    │
    ▼
MMU
    │
    ├── TLB hit
    │      │
    │      ▼
    │  physical address
    │
    └── TLB miss
           │
           ▼
      page table walk
           │
           ▼
      physical address
           │
           ▼
        RAM/cache
```

Если mapping отсутствует или нарушены права:

```text
MMU
 ↓
page fault
 ↓
kernel
 ↓
page fault handler
 ↓
обновление page tables / ошибка
 ↓
user process
```

---

# 24. Коротко

## User mode

Обычный режим работы приложений.

```text
вычисления
регистры
чтение своей памяти
запись в свою память
function calls
```

---

## Kernel mode

Привилегированный режим ядра.

```text
syscalls
devices
filesystem
networking
scheduler
page tables
process management
```

---

## Page

Фиксированный блок виртуальной или физической памяти.

Типично:

```text
4 KiB
```

---

## Page table

Структура, которая описывает:

```text
virtual page
    ↓
physical frame
```

и права доступа.

---

## MMU

Аппаратная часть CPU, которая:

```text
virtual address
    ↓
physical address
```

и проверяет page permissions.

---

## TLB

Cache переводов:

```text
virtual page
    ↓
physical frame
```

---

## Page fault

Exception, возникающий, когда MMU не может завершить доступ к странице без вмешательства kernel.

---

# Главное

Kernel **не является посредником при каждом вычислении или обращении к RAM**.

Правильная модель:

```text
Kernel
   │
   ├── создаёт процесс
   ├── создаёт page tables
   ├── задаёт permissions
   ├── выделяет virtual memory
   └── выдаёт CPU time
          │
          ▼
CPU выполняет user code напрямую
          │
          ▼
MMU аппаратно переводит addresses
          │
          ▼
RAM
```

Kernel снова получает управление только при событиях вроде:

```text
syscall
interrupt
exception
page fault
scheduler event
```

Именно благодаря этому программы могут выполнять огромное количество инструкций и обращений к памяти без постоянных переходов между user mode и kernel mode.
