## 1. Что делает `open()`

`open()` открывает файл и возвращает **файловый объект (I/O stream)**.

```python
f = open("data.txt", "r", encoding="utf-8")
```

`f` — не содержимое файла, а объект, через который можно читать, писать, перемещаться по файлу и закрывать поток.

```python
print(type(f))
# <class '_io.TextIOWrapper'>
```

Для большинства задач лучше использовать `with`:

```python
with open("data.txt", "r", encoding="utf-8") as f:
    text = f.read()
```

После выхода из `with` файл закрывается автоматически.

---

## 2. Сигнатура

```python
open(
    file,
    mode="r",
    buffering=-1,
    encoding=None,
    errors=None,
    newline=None,
    closefd=True,
    opener=None,
)
```

### Параметры

| Параметр | Назначение |
|---|---|
| `file` | путь к файлу или файловый дескриптор |
| `mode` | режим открытия |
| `buffering` | настройка буферизации |
| `encoding` | кодировка текста |
| `errors` | обработка ошибок кодировки |
| `newline` | обработка переносов строк |
| `closefd` | закрывать ли файловый дескриптор вместе с объектом |
| `opener` | пользовательская функция низкоуровневого открытия |

---

## 3. Режимы `mode`

Базовые символы режима:

| Символ | Значение |
|---|---|
| `r` | чтение; файл должен существовать |
| `w` | запись; файл создаётся или очищается |
| `a` | добавление в конец; файл создаётся при отсутствии |
| `x` | создать новый файл; ошибка, если он уже существует |
| `b` | бинарный режим (`bytes`) |
| `t` | текстовый режим (`str`), используется по умолчанию |
| `+` | чтение и запись |

### Основные варианты

```text
r
rb
rt
r+
rb+
r+b
rt+
r+t

w
wb
wt
w+
wb+
w+b
wt+
w+t

a
ab
at
a+
ab+
a+b
at+
a+t

x
xb
xt
x+
xb+
x+b
xt+
x+t
```

Некоторые записи эквивалентны:

```python
"rb+" == "r+b"
"wb+" == "w+b"
"ab+" == "a+b"
```

### Краткое сравнение

| Режим | Читать | Писать | Создаёт файл | Очищает существующий | Запись в конец |
|---|---:|---:|---:|---:|---:|
| `r` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `w` | ❌ | ✅ | ✅ | ✅ | ❌ |
| `a` | ❌ | ✅ | ✅ | ❌ | ✅ |
| `x` | ❌ | ✅ | ✅ | ❌ | ❌ |
| `r+` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `w+` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `a+` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `x+` | ✅ | ✅ | ✅ | ❌ | ❌ |

`b` меняет тип данных с `str` на `bytes`.

```python
with open("data.txt", "r", encoding="utf-8") as f:
    print(type(f.read()))
    # str
```

```python
with open("data.bin", "rb") as f:
    print(type(f.read()))
    # bytes
```

---

## 4. Основные I/O-классы

`open()` возвращает разные классы в зависимости от режима и буферизации.

Упрощённая иерархия:

```text
IOBase
│
├── RawIOBase
│   └── FileIO
│
├── BufferedIOBase
│   ├── BufferedReader
│   ├── BufferedWriter
│   └── BufferedRandom
│
└── TextIOBase
    └── TextIOWrapper
```

Типичная архитектура текстового файла:

```text
TextIOWrapper
      ↓
BufferedReader / BufferedWriter / BufferedRandom
      ↓
FileIO
      ↓
file descriptor
      ↓
операционная система
```

### `TextIOWrapper`

Верхний текстовый слой.

Ответственность:

- работает с `str`;
- кодирует `str → bytes` при записи;
- декодирует `bytes → str` при чтении;
- учитывает `encoding`, `errors`, `newline`.

Пример:

```python
f = open("data.txt", "r", encoding="utf-8")

print(type(f))
# TextIOWrapper
```

### `BufferedReader`

Буферизированное чтение байтов.

Ответственность:

- читает `bytes`;
- хранит часть данных в памятиж;
- уменьшает количество обращений к низкоуровневому I/O.

Обычно встречается при:

```python
open("data.bin", "rb")
```

### `BufferedWriter`

Буферизированная запись байтов.

Ответственность:

- принимает `bytes`;
- накапливает данные в буфере;
- передаёт их нижнему слою крупными блоками;
- поддерживает `flush()`.

Обычно встречается при:

```python
open("data.bin", "wb")
```

### `BufferedRandom`

Буферизированный поток для чтения и записи.

Название `Random` означает **random access**, а не случайные числа.

Ответственность:

- читать;
- писать;
- использовать `seek()`;
- работать с файлом в обоих направлениях.

Обычно встречается при бинарных режимах с `+`:

```python
open("data.bin", "rb+")
```

### `FileIO`

Низкоуровневый слой Python I/O.

Ответственность:

- работает с `bytes`;
- связан с файловым дескриптором ОС;
- выполняет низкоуровневые операции чтения, записи и позиционирования.

Пример без буферизации:

```python
f = open("data.bin", "rb", buffering=0)

print(type(f))
# FileIO
```

---

## 5. Связь слоёв

Для текстового чтения:

```text
Python str
    ↑
TextIOWrapper
    ↑
BufferedReader
    ↑
FileIO
    ↑
OS
```

Для текстовой записи:

```text
Python str
    ↓
TextIOWrapper
    ↓
BufferedWriter
    ↓
FileIO
    ↓
OS
```

Для бинарного чтения `TextIOWrapper` отсутствует:

```text
Python bytes
    ↑
BufferedReader
    ↑
FileIO
    ↑
OS
```

---

## 6. Основные методы файлового объекта

### Чтение

```python
f.read()
f.read(size)
f.readline()
f.readlines()
```

Пример:

```python
with open("data.txt", "r", encoding="utf-8") as f:
    text = f.read()
```

Итерация по строкам:

```python
with open("data.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line)
```

Для больших файлов это удобнее, чем загружать весь файл через `readlines()`.

### Запись

```python
f.write(data)
f.writelines(lines)
```

```python
with open("data.txt", "w", encoding="utf-8") as f:
    f.write("Hello\n")
    f.write("Python\n")
```

`write()` сам не добавляет `\n`.

`writelines()` также не добавляет переносы строк автоматически.

### Позиция

```python
f.tell()
f.seek(offset)
```

```python
with open("data.txt", "r", encoding="utf-8") as f:
    print(f.tell())

    f.read(5)

    print(f.tell())

    f.seek(0)
```

### Состояние и возможности

```python
f.readable()
f.writable()
f.seekable()

f.closed
f.name
f.mode
```

### Низкоуровневые операции

```python
f.fileno()
f.flush()
f.truncate()
f.close()
```

`fileno()` возвращает файловый дескриптор ОС.

```python
with open("data.txt", "r") as f:
    print(f.fileno())
```

---

## 7. `with` и context manager

Файловые объекты поддерживают:

```python
__enter__()
__exit__()
```

Поэтому можно писать:

```python
with open("data.txt", "r") as f:
    data = f.read()
```

По смыслу это близко к:

```python
f = open("data.txt", "r")

try:
    data = f.read()
finally:
    f.close()
```

`with` гарантирует закрытие файла даже при исключении.

---

## 8. `encoding`

Используется только в текстовом режиме.

```python
with open(
    "data.txt",
    "r",
    encoding="utf-8",
) as f:
    text = f.read()
```

`TextIOWrapper` преобразует:

```text
bytes → decode → str
str   → encode → bytes
```

Для текстовых файлов лучше указывать кодировку явно:

```python
encoding="utf-8"
```

---

## 9. `errors`

Определяет поведение при ошибках кодирования/декодирования.

### `strict`

По умолчанию:

```python
errors="strict"
```

При ошибке возникает исключение.

### `ignore`

```python
errors="ignore"
```

Проблемные данные пропускаются.

### `replace`

```python
errors="replace"
```

Проблемные символы заменяются.

Пример:

```python
with open(
    "data.txt",
    "r",
    encoding="utf-8",
    errors="replace",
) as f:
    text = f.read()
```

---

## 10. `newline`

Управляет обработкой переносов строк.

Основные варианты:

```python
newline=None
newline=""
newline="\n"
newline="\r"
newline="\r\n"
```

При обычной работе параметр можно не указывать.

```python
with open(
    "data.txt",
    "r",
    encoding="utf-8",
) as f:
    ...
```

`TextIOWrapper` сам обрабатывает переводы строк.

---

## 11. `buffering`

Управляет буферизацией.

По умолчанию:

```python
buffering=-1
```

Python выбирает подходящий режим автоматически.

В бинарном режиме буферизацию можно отключить:

```python
f = open(
    "data.bin",
    "rb",
    buffering=0,
)
```

Тогда `open()` возвращает `FileIO` напрямую.

```text
обычно:

BufferedReader
    ↓
FileIO

buffering=0:

FileIO
```

Полностью отключать буферизацию в текстовом режиме нельзя.

---

## 12. `closefd`

Связан с файловыми дескрипторами.

По умолчанию:

```python
closefd=True
```

Если `open()` получил существующий файловый дескриптор, то при `f.close()` этот дескриптор также будет закрыт.

```python
import os

fd = os.open("data.txt", os.O_RDONLY)

f = open(
    fd,
    "r",
    closefd=False,
)

f.close()

# fd всё ещё открыт
os.close(fd)
```

При обычной работе с путями этот параметр почти не используется.

---

## 13. `opener`

Позволяет передать собственную функцию низкоуровневого открытия.

```python
import os


def my_opener(path, flags):
    return os.open(path, flags)


with open(
    "data.txt",
    "r",
    opener=my_opener,
) as f:
    print(f.read())
```

Используется редко — когда нужен дополнительный контроль над открытием файла.

---

## 14. Полезная ментальная модель

```python
with open(
    "data.txt",
    "r",
    encoding="utf-8",
) as f:
    text = f.read()
```

можно представлять так:

```text
файл на диске
    ↓
операционная система
    ↓
file descriptor
    ↓
FileIO
    ↓
BufferedReader
    ↓
TextIOWrapper
    ↓
f
    ↓
f.read()
    ↓
str
```

Главное:

```text
FileIO
= низкоуровневая связь с ОС

Buffered*
= буферизация и уменьшение количества I/O-операций

TextIOWrapper
= работа с текстом и преобразование bytes ↔ str
```

---

## 15. Минимальный набор, который стоит помнить

```python
# Чтение текста
with open("data.txt", "r", encoding="utf-8") as f:
    text = f.read()


# Запись текста
with open("data.txt", "w", encoding="utf-8") as f:
    f.write("Hello")


# Добавление в конец
with open("data.txt", "a", encoding="utf-8") as f:
    f.write("New line\n")


# Бинарное чтение
with open("image.png", "rb") as f:
    data = f.read()


# Бинарная запись
with open("copy.bin", "wb") as f:
    f.write(data)
```

И основная формула:

```text
open()
    ↓
возвращает I/O-объект

text mode
    ↓
str

binary mode
    ↓
bytes

with
    ↓
автоматический close()
```
