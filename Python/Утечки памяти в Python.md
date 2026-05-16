## 1. Почему в Python возможны утечки памяти

В Python объект удаляется, когда на него больше нет ссылок. Обычная ссылка называется **сильной ссылкой**.

```python
obj = SomeObject()
```

Пока существует переменная `obj`, объект живёт.

Утечка памяти возникает, когда объект уже не нужен, но на него всё ещё остаётся ссылка. Один из частых случаев — **циклические ссылки**.

---

## 2. Циклическая ссылка

Пример:

```text
Parent → Child
Child  → Parent
```

То есть два объекта ссылаются друг на друга.

```python
import gc


class Parent:
    def __init__(self, name):
        self.name = name
        self.child = None

    def __del__(self):
        print(f"Parent {self.name} deleted")


class Child:
    def __init__(self, name):
        self.name = name
        self.parent = None

    def __del__(self):
        print(f"Child {self.name} deleted")


parent = Parent("P1")
child = Child("C1")

parent.child = child
child.parent = parent

del parent
del child

gc.collect()
```

Здесь внешние ссылки удалены, но объекты всё ещё держат друг друга:

```text
Parent держит Child
Child держит Parent
```

Современный Python обычно умеет собирать такие циклы сборщиком мусора, но в реальных программах циклы могут долго жить или создавать проблемы в сложных структурах: GUI, callbacks, observers, графы объектов, замыкания.

---

## 3. Что такое `weakref`

`weakref` создаёт **слабую ссылку**.

Слабая ссылка позволяет обратиться к объекту, если он ещё существует, но не мешает Python удалить этот объект.

```python
import weakref

class User:
    pass


user = User()
weak_user = weakref.ref(user)

print(weak_user())  # объект User

del user

print(weak_user())  # None
```

После удаления `user` объект исчезает, потому что `weak_user` не удерживает его в памяти.

---

## 4. Исправление циклической ссылки через `weakref`

Обычно родитель владеет ребёнком, а ребёнок только знает родителя.

Поэтому связь лучше сделать так:

```text
Parent → Child
Child  --weakref--> Parent
```

Код:

```python
import weakref
import gc


class Parent:
    def __init__(self, name):
        self.name = name
        self.child = None

    def __del__(self):
        print(f"Parent {self.name} deleted")


class Child:
    def __init__(self, name, parent):
        self.name = name
        self.parent = weakref.ref(parent)

    def get_parent(self):
        return self.parent()

    def __del__(self):
        print(f"Child {self.name} deleted")


parent = Parent("P1")
child = Child("C1", parent)

parent.child = child

print(child.get_parent())  # объект Parent

del parent
gc.collect()

print(child.get_parent())  # None

del child
gc.collect()
```

Теперь `Child` хранит слабую ссылку на `Parent`. Он может получить родителя через:

```python
self.parent()
```

Но если родитель уже удалён, вернётся:

```python
None
```

---

## 5. Где полезен `weakref`

`weakref` применяют, когда объект нужно “знать”, но не нужно им владеть:

```text
связь child → parent
observer pattern
event listeners
callbacks
графы объектов
кэши
реестры объектов
```

Главная идея:

```text
владелец объекта → strong reference
обратная ссылка → weak reference
```

---

## 6. Ограничения

Не все объекты поддерживают слабые ссылки.

Обычно поддерживают:

```text
экземпляры пользовательских классов
функции
методы
```

Не поддерживают напрямую:

```text
int
str
list
dict
tuple
```

Если в классе используется `__slots__`, нужно добавить:

```python
class User:
    __slots__ = ("name", "__weakref__")
```

---

## 7. Короткий вывод

Циклическая ссылка:

```text
A → B → A
```

может привести к тому, что объекты живут дольше, чем нужно.

`weakref` позволяет разорвать цикл:

```text
A → B
B --weakref--> A
```

То есть объект может ссылаться на другой объект, но не удерживать его в памяти.