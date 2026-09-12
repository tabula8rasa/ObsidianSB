## 1. Что такое `with`

`with` — конструкция Python для управления **контекстом**: ресурсом или временным состоянием, которое нужно корректно подготовить перед блоком кода и гарантированно завершить после него.

Базовая идея:

```text
подготовить контекст
    ↓
выполнить блок
    ↓
гарантированно завершить контекст
```

Классический пример:

```python
with open("data.txt", "r", encoding="utf-8") as f:
    text = f.read()
```

После выхода из блока файл будет закрыт автоматически, в том числе если внутри блока возникнет исключение.

---

## 2. Чем является `with`

`with` — это **синтаксис языка**, работающий с объектами, реализующими протокол контекстного менеджера.

Синхронный контекстный менеджер должен иметь два метода:

```python
__enter__()
__exit__()
```

Минимальная реализация:

```python
class MyContextManager:
    def __enter__(self):
        print("ENTER")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("EXIT")
        return False
```

Использование:

```python
with MyContextManager() as manager:
    print("BODY")
```

Результат:

```text
ENTER
BODY
EXIT
```

---

## 3. Общий синтаксис

```python
with expression as variable:
    block
```

Например:

```python
with Manager() as resource:
    use(resource)
```

Сначала вычисляется:

```python
Manager()
```

затем вызывается:

```python
__enter__()
```

Результат `__enter__()` присваивается переменной после `as`.

То есть:

```python
with manager as value:
    ...
```

концептуально содержит:

```python
value = manager.__enter__()
```

`as` необязателен:

```python
with lock:
    ...
```

Он нужен только тогда, когда значение, возвращённое `__enter__()`, потребуется внутри блока.

---

## 4. Как `with` работает внутри

Код:

```python
with Manager() as value:
    do_something()
```

можно представить так:

```python
manager = Manager()
value = manager.__enter__()

try:
    do_something()
except BaseException as error:
    suppress = manager.__exit__(
        type(error),
        error,
        error.__traceback__,
    )

    if not suppress:
        raise
else:
    manager.__exit__(None, None, None)
```

Это **концептуальная модель**, а не буквальный исходный код интерпретатора Python.

Главная схема:

```text
__enter__()
    ↓
тело with
    ↓
__exit__()
```

---

## 5. `__enter__()`

Типичная сигнатура:

```python
def __enter__(self):
    ...
```

Его область ответственности:

- получить ресурс;
- захватить блокировку;
- начать транзакцию;
- изменить временное состояние;
- подготовить окружение;
- вернуть объект для использования внутри `with`.

### Возврат `self`

```python
class Manager:
    def __enter__(self):
        return self
```

Тогда:

```python
with Manager() as manager:
    manager.some_method()
```

`manager` будет экземпляром `Manager`.

### Возврат отдельного ресурса

```python
class FileManager:
    def __init__(self, path):
        self.path = path
        self.file = None

    def __enter__(self):
        self.file = open(self.path, "r", encoding="utf-8")
        return self.file

    def __exit__(self, exc_type, exc_value, traceback):
        self.file.close()
```

Теперь:

```python
with FileManager("data.txt") as f:
    print(type(f))
```

`f` — файловый объект, а не `FileManager`.

Важно:

```text
объект до `as`
≠
объект после `as`
```

Переменная после `as` получает **результат `__enter__()`**.

---

## 6. `__exit__()`

Сигнатура:

```python
def __exit__(
    self,
    exc_type,
    exc_value,
    traceback,
):
    ...
```

Аргументы:

| Параметр | Что содержит |
|---|---|
| `exc_type` | класс исключения |
| `exc_value` | объект исключения |
| `traceback` | traceback исключения |

Если блок завершился успешно:

```python
exc_type is None
exc_value is None
traceback is None
```

Если внутри произошло:

```python
10 / 0
```

то `__exit__()` получит данные о `ZeroDivisionError`.

---

## 7. Возвращаемое значение `__exit__()`

Это важнейшая часть протокола.

### `False` или `None`

Исключение **не подавляется** и продолжает распространяться.

```python
def __exit__(self, exc_type, exc_value, traceback):
    cleanup()
    return False
```

или просто:

```python
def __exit__(self, exc_type, exc_value, traceback):
    cleanup()
```

Поскольку без `return` Python возвращает `None`.

### `True`

Исключение считается обработанным и наружу не выходит.

```python
class IgnoreErrors:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return True
```

```python
with IgnoreErrors():
    10 / 0

print("Программа продолжается")
```

Такое поведение нужно использовать осторожно.

### Подавление конкретного исключения

```python
class IgnoreZeroDivision:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is ZeroDivisionError:
            return True

        return False
```

---

## 8. `__init__`, `__enter__`, `__exit__`

Хорошее разделение ответственности:

```text
__init__
→ сохранить конфигурацию

__enter__
→ получить ресурс / изменить состояние

__exit__
→ освободить ресурс / восстановить состояние
```

Пример:

```python
class ResourceManager:
    def __init__(self, config):
        self.config = config
        self.resource = None

    def __enter__(self):
        self.resource = acquire_resource(self.config)
        return self.resource

    def __exit__(self, exc_type, exc_value, traceback):
        if self.resource is not None:
            release_resource(self.resource)

        return False
```

Часто не стоит открывать ресурс прямо в `__init__()`, потому что тогда:

```python
manager = ResourceManager(...)
```

уже захватит ресурс, хотя `with` ещё не начался.

---

## 9. Почему `with` удобнее `try/finally`

Без контекстного менеджера:

```python
resource = acquire_resource()

try:
    use(resource)
finally:
    release_resource(resource)
```

С ним:

```python
with ResourceManager() as resource:
    use(resource)
```

Главный плюс — логика получения и освобождения ресурса находится внутри самого менеджера, а пользователь пишет только рабочий код.

---

# Где используется `with`

## 10. Файлы

```python
with open("data.txt", "r", encoding="utf-8") as f:
    text = f.read()
```

`open()` возвращает объект, поддерживающий контекстный протокол.

После выхода вызывается закрытие файла.

---

## 11. Блокировки `threading.Lock`

```python
from threading import Lock

lock = Lock()

with lock:
    print("Критическая секция")
```

По смыслу:

```python
lock.acquire()

try:
    print("Критическая секция")
finally:
    lock.release()
```

То есть:

```text
__enter__ → acquire
__exit__  → release
```

---

## 12. Временная директория

```python
from tempfile import TemporaryDirectory

with TemporaryDirectory() as path:
    print(path)
```

Внутри блока директория существует.

После выхода она удаляется автоматически.

---

## 13. Архивы

```python
from zipfile import ZipFile

with ZipFile("archive.zip", "r") as archive:
    print(archive.namelist())
```

Архив будет закрыт после блока.

---

## 14. Временные настройки `decimal`

`with` может управлять не ресурсом, а состоянием.

```python
from decimal import Decimal, localcontext

with localcontext() as ctx:
    ctx.prec = 5
    result = Decimal("1") / Decimal("7")
    print(result)
```

После выхода прежний decimal-context восстанавливается.

---

## 15. Перенаправление `stdout`

```python
from contextlib import redirect_stdout

with open("output.txt", "w", encoding="utf-8") as f:
    with redirect_stdout(f):
        print("Этот текст попадёт в файл")
```

`redirect_stdout` временно заменяет `sys.stdout`, а затем восстанавливает прежнее значение.

---

# Собственные реализации

## 16. Простой менеджер для демонстрации порядка вызовов

```python
class DebugManager:
    def __init__(self):
        print("1. __init__")

    def __enter__(self):
        print("2. __enter__")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("4. __exit__")
        return False


with DebugManager() as manager:
    print("3. body")

print("5. after with")
```

Результат:

```text
1. __init__
2. __enter__
3. body
4. __exit__
5. after with
```

---

## 17. Таймер

```python
import time


class Timer:
    def __enter__(self):
        self.started_at = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.finished_at = time.perf_counter()
        self.elapsed = self.finished_at - self.started_at

        print(f"Время: {self.elapsed:.6f} секунд")

        return False
```

Использование:

```python
with Timer() as timer:
    total = sum(range(1_000_000))

print(timer.elapsed)
```

Даже если внутри блока произойдёт исключение, `__exit__()` будет вызван и время будет рассчитано.

---

## 18. Временная смена рабочей директории

```python
import os


class ChangeDirectory:
    def __init__(self, new_directory):
        self.new_directory = new_directory
        self.old_directory = None

    def __enter__(self):
        self.old_directory = os.getcwd()
        os.chdir(self.new_directory)

        return self.new_directory

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.old_directory)
        return False
```

Использование:

```python
with ChangeDirectory("/tmp"):
    print(os.getcwd())
```

После блока исходная директория будет восстановлена.

---

## 19. Менеджер блокировки

```python
class ManagedLock:
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        self.lock.acquire()
        return self.lock

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()
        return False
```

```python
from threading import Lock

lock = Lock()

with ManagedLock(lock):
    print("Защищённая секция")
```

---

## 20. Транзакционный менеджер

Классический паттерн:

```text
ENTER
↓
BEGIN

BODY
↓
операции

если успех
→ COMMIT

если ошибка
→ ROLLBACK
```

Реализация:

```python
class Transaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.connection.begin()
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()

        return False
```

Использование:

```python
with Transaction(connection) as conn:
    conn.execute(...)
    conn.execute(...)
```

`return False` нужен, чтобы после `rollback()` исходная ошибка не исчезла.

---

## 21. Безопасная запись файла

Если нужно изменить файл только при успешном завершении блока, нельзя писать прямо в оригинал через `"w"`, потому что он очищается сразу при открытии.

Нужен временный файл:

```python
import os
import tempfile
from pathlib import Path


class AtomicFileWriter:
    def __init__(self, filename, encoding="utf-8"):
        self.filename = Path(filename)
        self.encoding = encoding
        self.temp_file = None
        self.temp_path = None

    def __enter__(self):
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding=self.encoding,
            delete=False,
            dir=self.filename.parent,
        )

        self.temp_path = Path(self.temp_file.name)

        return self.temp_file

    def __exit__(self, exc_type, exc_value, traceback):
        self.temp_file.close()

        if exc_type is None:
            os.replace(
                self.temp_path,
                self.filename,
            )
        else:
            self.temp_path.unlink(missing_ok=True)

        return False
```

Использование:

```python
with AtomicFileWriter("data.txt") as f:
    f.write("Новая версия")
```

Логика:

```text
успех
→ временный файл заменяет оригинал

ошибка
→ временный файл удаляется
→ оригинал остаётся прежним
```

---

# `contextlib`

## 22. `@contextmanager`

Для короткого менеджера необязательно создавать класс.

```python
from contextlib import contextmanager


@contextmanager
def my_manager():
    print("ENTER")

    yield

    print("EXIT")
```

```python
with my_manager():
    print("BODY")
```

Структура:

```python
@contextmanager
def manager():
    # аналог __enter__

    yield value

    # аналог __exit__
```

То, что передано через `yield`, попадёт после `as`.

---

## 23. Правильный шаблон `@contextmanager`

Cleanup лучше помещать в `finally`:

```python
from contextlib import contextmanager


@contextmanager
def managed_resource():
    resource = acquire_resource()

    try:
        yield resource
    finally:
        release_resource(resource)
```

Так освобождение ресурса произойдёт и при ошибке.

---

## 24. Таймер через `@contextmanager`

```python
import time
from contextlib import contextmanager


@contextmanager
def timer():
    started_at = time.perf_counter()

    try:
        yield
    finally:
        elapsed = time.perf_counter() - started_at
        print(f"{elapsed:.6f} sec")
```

```python
with timer():
    sum(range(1_000_000))
```

---

## 25. Класс или `@contextmanager`

### Класс удобнее, когда:

- у менеджера много состояния;
- есть дополнительные методы;
- нужен полноценный объект;
- логика входа/выхода сложная;
- объект должен иметь отдельный API.

### `@contextmanager` удобнее, когда:

- логика короткая;
- паттерн простой: `setup → yield → cleanup`;
- отдельный класс добавляет лишний код.

---

## 26. `contextlib.suppress`

Готовый контекстный менеджер для подавления конкретных исключений.

Вместо:

```python
try:
    os.remove("file.txt")
except FileNotFoundError:
    pass
```

можно:

```python
import os
from contextlib import suppress

with suppress(FileNotFoundError):
    os.remove("file.txt")
```

---

## 27. `contextlib.closing`

Если объект имеет `.close()`, но не поддерживает `with`:

```python
from contextlib import closing

with closing(resource) as r:
    r.do_something()
```

После выхода будет вызван:

```python
r.close()
```

---

## 28. `contextlib.nullcontext`

Менеджер, который ничего не делает.

Полезен для условного контекста:

```python
from contextlib import nullcontext

manager = (
    open("data.txt")
    if should_open
    else nullcontext(existing_object)
)

with manager as resource:
    ...
```

---

## 29. `contextlib.ExitStack`

Используется, когда количество ресурсов определяется во время выполнения.

```python
from contextlib import ExitStack

paths = [
    "a.txt",
    "b.txt",
    "c.txt",
]

with ExitStack() as stack:
    files = [
        stack.enter_context(open(path))
        for path in paths
    ]

    for f in files:
        print(f.read())
```

`ExitStack` закроет все зарегистрированные контексты в обратном порядке.

---

# Несколько менеджеров одновременно

## 30. Несколько контекстов в одном `with`

```python
with (
    open("input.txt", "r", encoding="utf-8") as src,
    open("output.txt", "w", encoding="utf-8") as dst,
):
    dst.write(src.read())
```

Вход выполняется слева направо:

```text
src.__enter__()
↓
dst.__enter__()
```

Выход — в обратном порядке:

```text
dst.__exit__()
↓
src.__exit__()
```

То есть логика LIFO:

```text
Last In, First Out
```

Это эквивалентно вложенным `with`.

---

# Важные тонкости

## 31. Если ошибка произошла в `__enter__()`

```python
class Manager:
    def __enter__(self):
        raise RuntimeError("Ошибка")

    def __exit__(self, exc_type, exc_value, traceback):
        print("EXIT")
```

`__exit__()` не будет вызван.

Причина:

```text
__enter__ не завершился успешно
↓
контекст не считается захваченным
↓
тело with не начинается
↓
__exit__ не вызывается
```

Если `__enter__()` успел получить ресурс, а потом возникла ошибка, нужно освободить его внутри самого `__enter__()`:

```python
class Manager:
    def __enter__(self):
        self.resource = acquire_resource()

        try:
            configure_resource(self.resource)
        except Exception:
            self.resource.close()
            raise

        return self.resource
```

---

## 32. Если ошибка произошла в `__exit__()`

Если cleanup сам выбрасывает исключение:

```python
def __exit__(self, exc_type, exc_value, traceback):
    raise RuntimeError("Ошибка cleanup")
```

наружу выйдет новое исключение.

Оно может усложнить диагностику исходной ошибки, поэтому cleanup должен быть максимально надёжным.

---

## 33. Метод существует ≠ операция разрешена

Это актуально для файлов и других ресурсов.

Объект может иметь метод класса, но конкретное состояние объекта может запрещать операцию.

Например файловый объект может иметь `.read()`, но быть открыт в режиме только для записи.

Поэтому наличие метода и разрешённое состояние — разные вещи.

---

## 34. Не подавляй исключения без причины

Опасный вариант:

```python
def __exit__(self, exc_type, exc_value, traceback):
    cleanup()
    return True
```

Он подавит практически любое исключение из блока.

Для обычного менеджера ресурсов обычно нужно:

```python
return False
```

или:

```python
return None
```

---

## 35. Cleanup должен выполняться и при ошибке

Плохой вариант:

```python
def __exit__(self, exc_type, exc_value, traceback):
    if exc_type is None:
        resource.close()
```

При исключении ресурс останется открытым.

Для обычного ресурса:

```python
def __exit__(self, exc_type, exc_value, traceback):
    resource.close()
    return False
```

---

## 36. Контекстный менеджер не обязан быть многоразовым

Такой код:

```python
manager = Manager()

with manager:
    ...

with manager:
    ...
```

работает только если конкретная реализация это поддерживает.

Менеджер может быть одноразовым.

---

## 37. Reentrant context manager

Reentrant-менеджер позволяет использовать один и тот же объект вложенно:

```python
with manager:
    with manager:
        ...
```

Это отдельное свойство реализации.

Сам факт наличия `__enter__()` и `__exit__()` не гарантирует reentrancy.

---

# Типизация

## 38. Типизированный менеджер

Если `__enter__()` возвращает `self`:

```python
from typing import Self


class Manager:
    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> bool:
        return False
```

Если возвращается другой объект, указывается его тип.

Также существуют:

```python
typing.ContextManager
contextlib.AbstractContextManager
```

Пример базового класса:

```python
from contextlib import AbstractContextManager


class Manager(AbstractContextManager):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False
```

---

# Асинхронный вариант

## 39. `async with`

Для асинхронных ресурсов существует отдельный протокол:

```python
__aenter__()
__aexit__()
```

Пример формы:

```python
class AsyncManager:
    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False
```

Использование:

```python
async with AsyncManager() as resource:
    ...
```

Используется для:

- async HTTP-сессий;
- async DB connections;
- async locks;
- других асинхронных ресурсов.

`with` и `async with` — разные протоколы.

---

# Итоговая модель

## 40. Универсальный шаблон

```python
class ResourceManager:
    def __init__(self, config):
        self.config = config
        self.resource = None

    def __enter__(self):
        self.resource = acquire_resource(self.config)
        return self.resource

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        if self.resource is not None:
            release_resource(self.resource)

        return False
```

Ментальная модель:

```text
__init__
→ сохранить параметры

__enter__
→ получить ресурс

return из __enter__
→ значение после `as`

тело with
→ работа

__exit__
→ cleanup

return False / None
→ не скрывать исключение

return True
→ подавить исключение
```

Главное назначение `with`:

```text
setup
↓
работа
↓
гарантированный cleanup
```

Но контекстный менеджер может управлять не только ресурсами, а любым временным состоянием программы:

```text
файлы
блокировки
транзакции
таймеры
временные директории
настройки
stdout/stderr
обработку исключений
несколько динамических ресурсов
```

Поэтому `with` — универсальный механизм управления **временем жизни ресурса или временным состоянием программы**.
