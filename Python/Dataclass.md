---
title: Python ataclass
created: 2026-07-11
tags:
  - python
  - oop
  - dataclass
  - typing
  - backend
---
6`dataclass` — это инструмент из стандартной библиотеки Python, который автоматически генерирует служебные методы для классов, которые в основном хранят данные.

Вместо ручного написания `__init__`, `__repr__`, `__eq__` и части другой boilerplate-логики можно описать только поля класса.

```python
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str


user = User(1, "Ivan", "ivan@example.com")
print(user)
```

Вывод:

```text
User(id=1, name='Ivan', email='ivan@example.com')
```

Главная идея:

```text
dataclass = обычный класс + автогенерация типового кода для хранения данных
```

---

# 1. Что генерирует `@dataclass`

По умолчанию:

```python
from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int
```

примерно похоже на:

```python
class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Point(x={self.x!r}, y={self.y!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented

        return self.x == other.x and self.y == other.y
```

Но фактически реализация внутри Python сложнее.

---

# 2. Важное ограничение

`dataclass` **не проверяет типы во время выполнения**.

```python
from dataclasses import dataclass


@dataclass
class User:
    id: int
    age: int


user = User(id="one", age="twenty")
print(user)
```

Это не вызовет ошибку само по себе.

Аннотации типов нужны для:

- читаемости;
- IDE;
- автодополнения;
- mypy / pyright;
- документации к классу;
- сторонних библиотек.

Если нужна runtime-валидация входных данных, лучше смотреть в сторону `pydantic`, `attrs`, `msgspec` или писать проверки в `__post_init__`.

---

# 3. Основные параметры `@dataclass`

Общий вид:

```python
from dataclasses import dataclass


@dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=False,
    match_args=True,
    kw_only=False,
    slots=False,
    weakref_slot=False,
)
class Example:
    ...
```

| Параметр | Что делает |
|---|---|
| `init=True` | создаёт `__init__` |
| `repr=True` | создаёт `__repr__` |
| `eq=True` | создаёт `__eq__` |
| `order=False` | создаёт `<`, `<=`, `>`, `>=` |
| `unsafe_hash=False` | принудительно создаёт `__hash__` |
| `frozen=False` | запрещает переназначать поля после создания |
| `match_args=True` | включает поддержку positional pattern matching |
| `kw_only=False` | делает поля keyword-only |
| `slots=False` | создаёт класс через `__slots__` |
| `weakref_slot=False` | добавляет поддержку `weakref` при `slots=True` |

---

# 4. `init`

`init=True` создаёт конструктор.

```python
from dataclasses import dataclass


@dataclass
class Product:
    title: str
    price: float


product = Product("Keyboard", 99.9)
print(product)
```

Если поставить `init=False`, `__init__` не будет сгенерирован.

```python
from dataclasses import dataclass


@dataclass(init=False)
class Product:
    title: str
    price: float


product = Product()
product.title = "Keyboard"
product.price = 99.9
```

Обычно `init=False` используют редко. Чаще всего он нужен, если ты хочешь полностью контролировать создание объекта.

---

# 5. `repr`

`repr=True` делает удобный вывод объекта.

```python
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str


print(User(1, "Ivan"))
```

Вывод:

```text
User(id=1, name='Ivan')
```

Если поле не надо показывать в `repr`, используй `field(repr=False)`.

```python
from dataclasses import dataclass, field


@dataclass
class User:
    username: str
    password: str = field(repr=False)


user = User("admin", "secret")
print(user)
```

Вывод:

```text
User(username='admin')
```

> [!warning]
> `repr=False` не защищает данные. Он просто не показывает поле при печати объекта.

---

# 6. `eq`

`eq=True` сравнивает объекты по полям.

```python
from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int


print(Point(1, 2) == Point(1, 2))
print(Point(1, 2) == Point(2, 2))
```

Вывод:

```text
True
False
```

Сравнение идёт по всем полям, у которых `compare=True`.

```python
from dataclasses import dataclass, field


@dataclass
class User:
    id: int
    name: str
    last_login: str = field(compare=False)


u1 = User(1, "Ivan", "2026-01-01")
u2 = User(1, "Ivan", "2026-07-10")

print(u1 == u2)
```

Вывод:

```text
True
```

`last_login` не участвует в сравнении.

---

# 7. `order`

`order=True` добавляет методы сравнения:

- `__lt__`;
- `__le__`;
- `__gt__`;
- `__ge__`.

```python
from dataclasses import dataclass


@dataclass(order=True)
class User:
    age: int
    name: str


users = [
    User(25, "Ivan"),
    User(19, "Anna"),
    User(25, "Boris"),
]

print(sorted(users))
```

Вывод:

```text
[User(age=19, name='Anna'), User(age=25, name='Boris'), User(age=25, name='Ivan')]
```

Сравнение идёт по порядку объявления полей:

```text
age → name
```

> [!warning]
> `order=True` требует `eq=True`. Если поставить `order=True, eq=False`, будет ошибка.

Можно исключить поле из сортировки:

```python
from dataclasses import dataclass, field


@dataclass(order=True)
class Task:
    priority: int
    title: str = field(compare=False)


print(sorted([
    Task(3, "Low"),
    Task(1, "High"),
    Task(2, "Medium"),
]))
```

---

# 8. `frozen`

`frozen=True` делает объект условно неизменяемым.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: int
    y: int


point = Point(1, 2)
point.x = 10
```

Будет ошибка:

```text
dataclasses.FrozenInstanceError: cannot assign to field 'x'
```

Хорошо подходит для:

- value object;
- DTO;
- конфигов;
- координат;
- денег;
- ключей словаря;
- элементов множества.

Пример:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CurrencyPair:
    base: str
    quote: str


rates = {
    CurrencyPair("USD", "EUR"): 0.92,
}

print(rates[CurrencyPair("USD", "EUR")])
```

---

# 9. Нюанс `frozen=True`

`frozen=True` не делает глубокую неизменяемость.

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Basket:
    items: list[str] = field(default_factory=list)


basket = Basket()
basket.items.append("apple")

print(basket.items)
```

Это сработает:

```text
['apple']
```

Почему? Потому что нельзя заменить поле `items`, но можно изменить сам список, который лежит внутри.

Лучше для настоящей неизменяемости использовать неизменяемые типы:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Basket:
    items: tuple[str, ...] = ()
```

---

# 10. `unsafe_hash`

`unsafe_hash=True` принудительно генерирует `__hash__`.

```python
from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class User:
    id: int
    name: str
```

Использовать осторожно.

Опасный пример:

```python
from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class User:
    id: int
    name: str


user = User(1, "Ivan")
users = {user}

user.id = 2

print(user in users)
```

Проблема: объект изменился после попадания в `set`. Для словарей и множеств это плохая идея.

Чаще лучше так:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    name: str
```

---

# 11. Правила `hash` в dataclass

Упрощённо:

| Ситуация | Что с `__hash__` |
|---|---|
| `eq=True`, `frozen=True` | обычно генерируется безопасный hash |
| `eq=True`, `frozen=False` | объект обычно становится unhashable |
| `eq=False` | hash берётся как у обычного объекта |
| `unsafe_hash=True` | hash создаётся принудительно |

Главная мысль:

```text
Изменяемые объекты лучше не делать хешируемыми.
```

---

# 12. `slots`

`slots=True` создаёт класс через `__slots__`.

```python
from dataclasses import dataclass


@dataclass(slots=True)
class User:
    id: int
    name: str


user = User(1, "Ivan")
user.age = 30
```

Будет ошибка, потому что `age` не объявлен как поле.

Плюсы:

- меньше расход памяти;
- нельзя случайно добавить новый атрибут;
- иногда быстрее доступ к полям.

Минусы:

- может быть сложнее с наследованием;
- может быть несовместимо с частью библиотек;
- нельзя свободно добавлять атрибуты объекту.

Практический пример:

```python
from dataclasses import dataclass


@dataclass(slots=True)
class LogEvent:
    timestamp: float
    level: str
    message: str
```

---

# 13. `weakref_slot`

Если используется `slots=True`, объект может не поддерживать weak references. Для этого есть `weakref_slot=True`.

```python
from dataclasses import dataclass


@dataclass(slots=True, weakref_slot=True)
class User:
    id: int
    name: str
```

Обычно это нужно редко. Может понадобиться для:

- `weakref`;
- `WeakValueDictionary`;
- кэшей;
- некоторых фреймворков.

> [!note]
> `weakref_slot=True` имеет смысл только вместе с `slots=True`.

---

# 14. `kw_only`

`kw_only=True` делает поля доступными только как keyword arguments.

```python
from dataclasses import dataclass


@dataclass(kw_only=True)
class User:
    id: int
    name: str
    email: str


user = User(id=1, name="Ivan", email="ivan@example.com")
```

Так нельзя:

```python
User(1, "Ivan", "ivan@example.com")
```

Зачем это нужно:

- меньше риск перепутать аргументы;
- лучше читаемость;
- удобно для конфигов;
- удобно для DTO;
- удобно, когда у класса много полей.

Плохой вариант:

```python
User(1, "ivan@example.com", "Ivan")
```

Хороший вариант:

```python
User(id=1, name="Ivan", email="ivan@example.com")
```

---

# 15. `field(kw_only=True)`

Можно сделать keyword-only не весь класс, а отдельное поле.

```python
from dataclasses import dataclass, field


@dataclass
class RequestConfig:
    url: str
    timeout: float = field(default=3.0, kw_only=True)
    retries: int = field(default=3, kw_only=True)


config = RequestConfig(
    "https://example.com",
    timeout=10.0,
    retries=5,
)
```

Первое поле можно передать позиционно, а настройки только по имени.

---

# 16. `KW_ONLY`

`KW_ONLY` — специальный маркер. Все поля после него становятся keyword-only.

```python
from dataclasses import KW_ONLY, dataclass


@dataclass
class User:
    id: int
    name: str

    _: KW_ONLY

    email: str
    is_active: bool = True


user = User(1, "Ivan", email="ivan@example.com")
```

Поле `_` не становится обычным полем объекта. Это просто маркер.

Так нельзя:

```python
User(1, "Ivan", "ivan@example.com")
```

Так можно:

```python
User(1, "Ivan", email="ivan@example.com")
```

`KW_ONLY` удобен, если основные поля можно передавать позиционно, а дополнительные лучше заставить передавать по имени.

---

# 17. `match_args`

`match_args=True` включает поддержку positional pattern matching.

```python
from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int


point = Point(10, 20)

match point:
    case Point(10, y):
        print(f"x = 10, y = {y}")
    case Point(x, y):
        print(x, y)
```

Dataclass создаёт примерно такое:

```python
__match_args__ = ("x", "y")
```

Если поставить:

```python
@dataclass(match_args=False)
class Point:
    x: int
    y: int
```

позиционное сопоставление по полям не будет автоматически настроено.

Нюанс: keyword-only поля обычно не попадают в `__match_args__`.

```python
from dataclasses import dataclass, field


@dataclass
class User:
    id: int
    name: str
    email: str = field(kw_only=True)


print(User.__match_args__)
```

Вывод:

```text
('id', 'name')
```

---

# 18. `field`

`field()` позволяет настроить конкретное поле.

```python
from dataclasses import field


name: str = field(
    default="Unknown",
    default_factory=None,
    init=True,
    repr=True,
    hash=None,
    compare=True,
    metadata={},
    kw_only=False,
)
```

| Параметр | Что делает |
|---|---|
| `default` | значение по умолчанию |
| `default_factory` | функция, создающая значение по умолчанию |
| `init` | добавлять ли поле в `__init__` |
| `repr` | показывать ли поле в `repr` |
| `compare` | участвует ли поле в `eq` и `order` |
| `hash` | участвует ли поле в `hash` |
| `metadata` | дополнительные данные для библиотек |
| `kw_only` | поле можно передавать только по имени |

---

# 19. `default`

```python
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str = "Unknown"


print(User(1))
```

Вывод:

```text
User(id=1, name='Unknown')
```

Правило: поля без default должны идти до полей с default.

Нельзя:

```python
from dataclasses import dataclass


@dataclass
class User:
    name: str = "Unknown"
    id: int
```

Будет ошибка, потому что обязательное поле `id` идёт после поля со значением по умолчанию.

---

# 20. `default_factory`

Для изменяемых значений по умолчанию используй `default_factory`.

Плохо:

```python
from dataclasses import dataclass


@dataclass
class Basket:
    items: list[str] = []
```

Правильно:

```python
from dataclasses import dataclass, field


@dataclass
class Basket:
    items: list[str] = field(default_factory=list)


basket_1 = Basket()
basket_2 = Basket()

basket_1.items.append("apple")

print(basket_1.items)
print(basket_2.items)
```

Вывод:

```text
['apple']
[]
```

Можно использовать свою функцию:

```python
from dataclasses import dataclass, field
from uuid import uuid4


def generate_id() -> str:
    return str(uuid4())


@dataclass
class User:
    id: str = field(default_factory=generate_id)
    name: str = "Unknown"
```

---

# 21. `field(init=False)`

Поле не будет параметром конструктора.

```python
from dataclasses import dataclass, field


@dataclass
class User:
    first_name: str
    last_name: str
    full_name: str = field(init=False)

    def __post_init__(self) -> None:
        self.full_name = f"{self.first_name} {self.last_name}"


user = User("Ivan", "Petrov")
print(user.full_name)
```

Вывод:

```text
Ivan Petrov
```

---

# 22. `metadata`

`metadata` — словарь дополнительных данных для поля. Сам `dataclass` почти ничего с ним не делает.

```python
from dataclasses import dataclass, field, fields


@dataclass
class User:
    id: int = field(metadata={"db_column": "user_id"})
    email: str = field(metadata={"db_column": "email"})


for item in fields(User):
    print(item.name, item.metadata)
```

Вывод:

```text
id {'db_column': 'user_id'}
email {'db_column': 'email'}
```

`metadata` может быть полезен для:

- сериализации;
- валидации;
- ORM-маппинга;
- генерации схем;
- документации;
- внутренних инструментов.

---

# 23. `__post_init__`

`__post_init__` вызывается после автоматически созданного `__init__`.

Используется для:

- валидации;
- нормализации;
- вычисляемых полей;
- дополнительной инициализации.

```python
from dataclasses import dataclass


@dataclass
class User:
    name: str
    age: int

    def __post_init__(self) -> None:
        if self.age < 0:
            raise ValueError("Возраст не может быть отрицательным")

        self.name = self.name.strip().title()


user = User("  ivan  ", 20)
print(user)
```

Вывод:

```text
User(name='Ivan', age=20)
```

---

# 24. `__post_init__` в `frozen=True`

В `frozen=True` нельзя просто присваивать поля даже внутри `__post_init__`.

Нужно использовать `object.__setattr__`.

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    first_name: str
    last_name: str
    full_name: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "full_name",
            f"{self.first_name} {self.last_name}",
        )


user = User("Ivan", "Petrov")
print(user.full_name)
```

Это нормальный способ заполнить вычисляемое поле у frozen dataclass.

---

# 25. `InitVar`

`InitVar` — параметр, который передаётся в `__init__` и `__post_init__`, но не сохраняется как поле объекта.

```python
from dataclasses import InitVar, dataclass


@dataclass
class User:
    username: str
    raw_password: InitVar[str]
    password_hash: str = ""

    def __post_init__(self, raw_password: str) -> None:
        self.password_hash = f"hashed-{raw_password}"


user = User("admin", "12345")

print(user)
print(user.password_hash)
print(hasattr(user, "raw_password"))
```

Вывод:

```text
User(username='admin', password_hash='hashed-12345')
hashed-12345
False
```

`raw_password` нужен только при создании объекта.

Подходит для:

- сырого пароля;
- временного флага;
- настроек инициализации;
- подключения к базе;
- внешнего контекста.

---

# 26. `ClassVar`

`ClassVar` показывает, что переменная относится к классу, а не к объекту.

```python
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class User:
    id: int
    name: str

    table_name: ClassVar[str] = "users"


user = User(1, "Ivan")

print(user)
print(User.table_name)
```

Вывод:

```text
User(id=1, name='Ivan')
users
```

`table_name`:

- не попадает в `__init__`;
- не попадает в `repr`;
- не считается полем dataclass.

---

# 27. `asdict`

`asdict()` превращает dataclass в словарь.

```python
from dataclasses import asdict, dataclass


@dataclass
class Address:
    city: str
    street: str


@dataclass
class User:
    id: int
    name: str
    address: Address


user = User(
    id=1,
    name="Ivan",
    address=Address("Tbilisi", "Rustaveli"),
)

print(asdict(user))
```

Вывод:

```python
{
    'id': 1,
    'name': 'Ivan',
    'address': {
        'city': 'Tbilisi',
        'street': 'Rustaveli',
    },
}
```

> [!warning]
> `asdict()` рекурсивно обходит вложенные dataclass-объекты. Для больших объектов это может быть не самым дешёвым действием.

---

# 28. `astuple`

`astuple()` превращает dataclass в кортеж.

```python
from dataclasses import astuple, dataclass


@dataclass
class Point:
    x: int
    y: int


point = Point(10, 20)
print(astuple(point))
```

Вывод:

```text
(10, 20)
```

Порядок значений соответствует порядку объявления полей.

---

# 29. `replace`

`replace()` создаёт копию объекта с изменёнными полями.

Особенно удобно для `frozen=True`.

```python
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class User:
    id: int
    name: str
    email: str


user_1 = User(1, "Ivan", "old@example.com")
user_2 = replace(user_1, email="new@example.com")

print(user_1)
print(user_2)
```

Вывод:

```text
User(id=1, name='Ivan', email='old@example.com')
User(id=1, name='Ivan', email='new@example.com')
```

---

# 30. `fields`

`fields()` возвращает информацию о полях.

```python
from dataclasses import dataclass, fields


@dataclass
class User:
    id: int
    name: str
    email: str


for item in fields(User):
    print(item.name, item.type)
```

Вывод:

```text
id <class 'int'>
name <class 'str'>
email <class 'str'>
```

Можно использовать для:

- сериализации;
- валидации;
- генерации SQL;
- генерации форм;
- документации;
- динамического анализа класса.

---

# 31. `is_dataclass`

```python
from dataclasses import dataclass, is_dataclass


@dataclass
class User:
    id: int
    name: str


print(is_dataclass(User))
print(is_dataclass(User(1, "Ivan")))
print(is_dataclass(dict))
```

Вывод:

```text
True
True
False
```

---

# 32. `make_dataclass`

`make_dataclass()` позволяет создать dataclass динамически.

```python
from dataclasses import make_dataclass


User = make_dataclass(
    "User",
    [
        ("id", int),
        ("name", str),
        ("email", str, "unknown@example.com"),
    ],
)

user = User(1, "Ivan")
print(user)
```

Вывод:

```text
User(id=1, name='Ivan', email='unknown@example.com')
```

В обычном коде используется редко. Может пригодиться для генераторов моделей и metaprogramming.

---

# 33. Наследование dataclass

```python
from dataclasses import dataclass


@dataclass
class Person:
    name: str
    age: int


@dataclass
class Employee(Person):
    company: str
    salary: float


employee = Employee("Ivan", 25, "Google", 5000)
print(employee)
```

Вывод:

```text
Employee(name='Ivan', age=25, company='Google', salary=5000)
```

Поля родителя идут раньше полей потомка.

## Нюанс с default-полями

Если в родителе есть поле со значением по умолчанию, а в потомке обязательное поле, может быть ошибка.

```python
from dataclasses import dataclass


@dataclass
class Person:
    name: str = "Unknown"


@dataclass
class Employee(Person):
    company: str
```

Проблема: обязательное поле `company` идёт после поля `name` со значением по умолчанию.

Вариант решения через `kw_only=True`:

```python
from dataclasses import dataclass


@dataclass
class Person:
    name: str = "Unknown"


@dataclass(kw_only=True)
class Employee(Person):
    company: str


employee = Employee(company="Google")
```

---

# 34. `__post_init__` и наследование

Если у родителя есть `__post_init__`, а у наследника тоже, то родительский метод нужно вызвать вручную.

```python
from dataclasses import dataclass


@dataclass
class Person:
    name: str

    def __post_init__(self) -> None:
        self.name = self.name.strip()


@dataclass
class Employee(Person):
    company: str

    def __post_init__(self) -> None:
        super().__post_init__()
        self.company = self.company.strip()


employee = Employee(" Ivan ", " Google ")
print(employee)
```

Вывод:

```text
Employee(name='Ivan', company='Google')
```

---

# 35. Свой `__init__`

Можно написать `__init__` вручную.

```python
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str

    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name.strip().title()


user = User(1, " ivan ")
print(user)
```

Но если ты пишешь `__init__` сам, dataclass уже не генерирует его автоматически. Часто лучше оставить автогенерацию и использовать `__post_init__`.

---

# 36. `@property` и вычисляемые поля

Если значение должно всегда пересчитываться, используй `@property`.

```python
from dataclasses import dataclass


@dataclass
class Rectangle:
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height


rectangle = Rectangle(10, 5)
print(rectangle.area)
```

Вывод:

```text
50
```

Если значение нужно вычислить один раз при создании, используй `field(init=False)` и `__post_init__`.

---

# 37. Пример DTO

DTO — Data Transfer Object. Объект для передачи данных между слоями приложения.

```python
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class CreateUserDTO:
    username: str
    email: str
    password: str


dto = CreateUserDTO(
    username="admin",
    email="admin@example.com",
    password="12345",
)
```

Почему тут хорошо:

- `frozen=True` — объект не меняется после создания;
- `kw_only=True` — нельзя перепутать аргументы;
- класс явно описывает структуру данных.

---

# 38. Пример конфига

```python
from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True, slots=True)
class DatabaseConfig:
    host: str
    user: str
    password: str = field(repr=False)
    database: str
    port: int = 5432
    pool_size: int = 10
    timeout: float = 5.0


config = DatabaseConfig(
    host="localhost",
    user="postgres",
    password="secret",
    database="app",
)

print(config)
```

`kw_only=True` полезен, потому что у конфигурации много полей. Передавать их позиционно опасно.

`repr=False` скрывает пароль из вывода.

---

# 39. Пример value object `Money`

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("amount не может быть отрицательным")

        if len(self.currency) != 3:
            raise ValueError("currency должен быть ISO-кодом из 3 букв")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Нельзя складывать деньги в разных валютах")

        return Money(
            amount=self.amount + other.amount,
            currency=self.currency,
        )


wallet = Money(Decimal("100.00"), "USD")
income = Money(Decimal("50.00"), "USD")

print(wallet + income)
```

Вывод:

```text
Money(amount=Decimal('150.00'), currency='USD')
```

---

# 40. Пример runtime-состояния

```python
from dataclasses import dataclass, field
from time import time


@dataclass
class Session:
    user_id: int
    token: str = field(repr=False)
    created_at: float = field(default_factory=time, init=False)
    request_count: int = field(default=0, compare=False)

    def register_request(self) -> None:
        self.request_count += 1


session = Session(user_id=1, token="secret-token")
session.register_request()

print(session)
```

Особенности:

- `token` скрыт из `repr`;
- `created_at` создаётся автоматически;
- `request_count` не участвует в сравнении.

---

# 41. Пример с `slots`, `frozen`, `kw_only`

```python
from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class UserView:
    id: int
    username: str
    email: str


user = UserView(
    id=1,
    username="admin",
    email="admin@example.com",
)
```

Это хороший шаблон для read-only объекта:

- нельзя менять поля;
- нельзя добавить лишний атрибут;
- меньше расход памяти;
- аргументы только именованные.

---

# 42. Частые ошибки

## Ошибка 1. Ждать автоматическую проверку типов

```python
@dataclass
class User:
    age: int


User(age="twenty")
```

Dataclass не запрещает это автоматически.

## Ошибка 2. Использовать изменяемый default

Плохо:

```python
@dataclass
class Basket:
    items: list[str] = []
```

Правильно:

```python
@dataclass
class Basket:
    items: list[str] = field(default_factory=list)
```

## Ошибка 3. Хранить секреты в `repr`

Плохо:

```python
@dataclass
class User:
    login: str
    password: str
```

Лучше:

```python
@dataclass
class User:
    login: str
    password: str = field(repr=False)
```

## Ошибка 4. Делать изменяемый объект хешируемым

Плохо:

```python
@dataclass(unsafe_hash=True)
class User:
    id: int
    name: str
```

Лучше:

```python
@dataclass(frozen=True)
class User:
    id: int
    name: str
```

## Ошибка 5. Слишком сложная бизнес-логика внутри dataclass

Dataclass хорош для данных. Если класс начинает ходить в базу, делать сетевые запросы и управлять сложным бизнес-процессом, возможно, это уже не просто dataclass-модель.

---

# 43. Когда использовать dataclass

Используй `dataclass`, если класс:

- в основном хранит данные;
- имеет понятный набор полей;
- часто сравнивается с другими объектами;
- должен красиво печататься;
- используется как DTO;
- используется как value object;
- используется как конфиг;
- используется как внутренняя модель.

Хорошие примеры:

```text
UserDTO
Point
Money
Config
TokenPayload
SearchFilter
Pagination
RequestContext
```

---

# 44. Когда dataclass не лучший выбор

Dataclass может быть не лучшим вариантом, если:

- нужна строгая runtime-валидация входных данных;
- нужно парсить JSON с приведением типов;
- объект является ORM-моделью;
- класс содержит сложное поведение;
- нужно много кастомной магии;
- данные приходят из недоверенного внешнего источника.

Альтернативы:

| Задача | Что рассмотреть |
|---|---|
| Runtime-валидация API | Pydantic |
| ORM | SQLAlchemy models |
| Много гибких настроек класса | attrs |
| Простая структура словаря | TypedDict |
| Неизменяемая tuple-like структура | NamedTuple |
| Максимальная производительность сериализации | msgspec |

---

# 45. Краткая шпаргалка

## Базовый dataclass

```python
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
```

## Read-only объект

```python
@dataclass(frozen=True)
class Point:
    x: int
    y: int
```

## Только именованные аргументы

```python
@dataclass(kw_only=True)
class Config:
    host: str
    port: int
```

## Экономия памяти

```python
@dataclass(slots=True)
class Event:
    id: int
    message: str
```

## Скрыть поле из `repr`

```python
password: str = field(repr=False)
```

## Список по умолчанию

```python
items: list[str] = field(default_factory=list)
```

## Поле не в `__init__`

```python
created_at: datetime = field(default_factory=datetime.now, init=False)
```

## Поле не участвует в сравнении

```python
cache: dict = field(default_factory=dict, compare=False)
```

## Валидация после создания

```python
def __post_init__(self) -> None:
    if self.age < 0:
        raise ValueError("age не может быть отрицательным")
```

---

# 46. Мой практический шаблон

Для DTO, конфигов и read-only объектов:

```python
from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True, slots=True)
class UserDTO:
    id: int
    username: str
    email: str
    password_hash: str = field(repr=False)
```

Почему так:

- `frozen=True` — объект нельзя случайно изменить;
- `kw_only=True` — нельзя перепутать аргументы;
- `slots=True` — меньше памяти и нельзя добавить лишний атрибут;
- `repr=False` — чувствительное поле не печатается.

Для изменяемой внутренней модели:

```python
from dataclasses import dataclass, field


@dataclass(slots=True)
class Basket:
    user_id: int
    items: list[str] = field(default_factory=list)

    def add_item(self, item: str) -> None:
        self.items.append(item)
```

---

# 47. Главное запомнить

`dataclass` — это не замена всем классам и не валидатор данных.

Это удобный способ быстро и аккуратно описывать классы, которые в основном хранят данные.

Самые важные фишки:

- `field(default_factory=...)` — для списков, словарей и set;
- `__post_init__` — для валидации и вычислений;
- `frozen=True` — для условно неизменяемых объектов;
- `kw_only=True` — для безопасного создания объектов;
- `slots=True` — для экономии памяти и запрета лишних атрибутов;
- `repr=False` — для секретных или больших полей;
- `compare=False` — для полей, которые не должны влиять на сравнение;
- `InitVar` — для временных параметров инициализации;
- `ClassVar` — для переменных класса;
- `asdict`, `replace`, `fields` — для работы с объектами.
