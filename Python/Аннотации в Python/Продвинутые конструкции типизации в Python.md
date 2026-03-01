
Папка **«c»** (`c/new_types.py`) посвящена **продвинутым возможностям типизации** в Python. В ней рассматриваются инструменты, которые позволяют делать код более строгим, самодокументируемым и защищённым от логических ошибок.

Здесь используются:

- `Literal` — для ограничения допустимых значений
- `NewType` — для создания новых семантических типов
- алиасы типов — для удобных обозначений
- `TypedDict` — для описания структуры словарей
- `Protocol` — для структурной типизации
- `NotRequired` — для необязательных ключей в `TypedDict`
- `Optional` — для значений, которые могут быть `None`

---

## 1. Ограничение значений с помощью `Literal`

Тип `Literal` нужен, когда переменная должна принимать не просто значение определённого типа, а **одно из конкретно разрешённых значений**.

### Пример
```python
from typing import Literal

OrderStatus = Literal[
    "pending",
    "confirmed",
    "shipped",
    "delivered",
    "canceled",
]

PaymentMethod = Literal["card", "cash", "crypto", "bank_transfer"]
````

### Что это даёт

- IDE подсказывает допустимые варианты
- статический анализатор ловит опечатки
- код становится понятнее по смыслу

Например, если функция ждёт `OrderStatus`, то строка `"unknown"` уже будет считаться ошибкой.

---

## 2. Алиасы типов и `NewType`

В Python есть два похожих, но разных подхода: **алиасы типов** и **создание нового типа через `NewType`**.

---

### 2.1. Алиасы типов

Алиас — это просто новое имя для уже существующего типа.

```python
Price = int
type Quantity = int  # Python 3.12+
```

### Смысл

- `Price` и `int` для анализатора типов — одно и то же
- это не новый тип, а просто более понятное имя

Например:

- `Price` — цена в копейках
- `Quantity` — количество товара

Это удобно, когда хочется добавить **семантику**, не меняя сам тип.

---

### 2.2. `NewType`

`NewType` создаёт **новый тип** на базе существующего.

```python
from typing import NewType

OrderId = NewType("OrderId", str)
```

Теперь `OrderId` — это уже не просто строка по смыслу, а отдельный тип для идентификатора заказа.

### Пример

```python
def example_function(
    order_id: OrderId,
    quantity: Quantity,
    price: Price,
) -> None:
    print(f"Order ID: {order_id}, Quantity: {quantity}")

example_function(OrderId("12345"), 2, 1000)
```

### Зачем это нужно

Это помогает не путать разные сущности одинакового базового типа.

Например:

- `OrderId`
- `CustomerId`
- `ProductId`

Все они могут быть строками, но логически это разные вещи.

---

## 3. Типизированные словари `TypedDict`

Обычный `dict[str, Any]` не говорит, какие именно ключи там должны быть.  
`TypedDict` позволяет описать **структуру словаря**.

### Пример

```python
from typing import TypedDict, NotRequired

class OrderItem(TypedDict):
    product_id: str
    name: str | None
    quantity: Quantity
    price: Price


class CustomerInfo(TypedDict):
    customer_id: str
    email: str
    shipping_address: str
    phone: str | None
    missing_field: NotRequired[str]
```

---

### Что здесь важно

#### `OrderItem`

Описывает словарь товара заказа:

- `product_id` — строка
- `name` — строка или `None`
- `quantity` — количество
- `price` — цена

#### `CustomerInfo`

Описывает словарь с данными клиента:

- обязательные ключи: `customer_id`, `email`, `shipping_address`
- `phone` может быть `str | None`
- `missing_field` — необязательный ключ благодаря `NotRequired`    

---

### Важное замечание

В рантайме это всё ещё обычный словарь.

То есть:

```python
{"product_id": "p1", "quantity": 2, "price": 1000}
```

не становится специальным объектом — это просто `dict`, но статический анализатор понимает его структуру.

---

## 4. `Optional`

`Optional[T]` означает:

> значение может быть типа `T` или `None`

### Пример

```python
from typing import Optional

payment_processor: Optional[PaymentProcessor] = None
```

Это то же самое, что:

```python
payment_processor: PaymentProcessor | None = None
```

---

## 5. Структурная типизация через `Protocol`

`Protocol` позволяет описывать тип **по поведению**, а не по наследованию.

### Пример

```python
from typing import Protocol

class PaymentProcessor(Protocol):
    def process(self, amount: Price, method: PaymentMethod) -> bool:
        ...
```

Это значит:

> любой объект, у которого есть метод  
> `process(self, amount: Price, method: PaymentMethod) -> bool`  
> считается совместимым с `PaymentProcessor`

---

### Почему это удобно

Не нужно заставлять классы явно наследоваться от базового класса.

Если объект **подходит по структуре**, он уже совместим.

Это и есть статический duck typing:

> “если выглядит как утка и крякает как утка — значит, это утка”

---

## 6. Практический пример: обработка заказа

Ниже используется сразу несколько продвинутых инструментов типизации.

```python
def process_order(
    order_id: OrderId,
    status: OrderStatus,
    payment_method: PaymentMethod,
    items: list[OrderItem],
    customer_info: CustomerInfo,
    payment_processor: Optional[PaymentProcessor] = None
) -> dict[str, object]:
    # Обработка заказа
    if status == "confirmed":
        pass
    elif status == "shipped":
        pass

    # Обработка оплаты
    if payment_processor and payment_method in ["card", "crypto"]:
        total_amount = sum(item["price"] * item["quantity"] for item in items)
        payment_processor.process(total_amount, payment_method)

    print(customer_info)

    return {"order_id": order_id, "status": status, "processed": True}
```

---

### Что здесь типизировано

- `order_id: OrderId` — специальный тип ID заказа
- `status: OrderStatus` — одно из разрешённых строковых значений
- `payment_method: PaymentMethod` — один из допустимых способов оплаты
- `items: list[OrderItem]` — список строго описанных словарей
- `customer_info: CustomerInfo` — словарь с определённой структурой
- `payment_processor: Optional[PaymentProcessor]` — объект с нужным методом или `None`
- возвращаемое значение: `dict[str, object]`

---

## 7. Пример вызова функции

```python
process_order(
    OrderId("12345"),
    "confirmed",
    "card",
    [
        OrderItem(**{"product_id": "p1", "name": "Product a", "quantity": 2, "price": 1000}),
        {"product_id": "p2", "name": "Product 2", "quantity": 1, "price": 2000}
    ],
    {
        "customer_id": "c1",
        "email": "123@gmail.com",
        "shipping_address": "123 Main St",
        "phone": "123 Main St",
        "missing_field": "123 Main St"
    },
)
```

Этот пример показывает, как разные типы работают вместе:

- `OrderId("12345")` создаёт значение нового типа
- статус `"confirmed"` проверяется через `Literal`
- список товаров подчиняется структуре `OrderItem`
- данные клиента соответствуют `CustomerInfo`

---

## 8. Передача самого класса: `type[C]`

Иногда нужно передать в функцию **не экземпляр класса**, а **сам класс**.

Пример идеи:

```python
class CustomType:
    pass

custom = CustomType
```

Если нужно явно типизировать, что переменная содержит именно класс, а не объект, можно использовать:

```python
type[CustomType]
```

Это означает:

- в переменной хранится объект-класс
- это должен быть `CustomType` или его подкласс

Такой подход часто используется:

- в фабриках
- при внедрении зависимостей
- в универсальных конструкторах объектов

---

## 9. Разница между этими инструментами

### `Literal`

Ограничивает **конкретные допустимые значения**

```python
PaymentMethod = Literal["card", "cash", "crypto"]
```

---

### Алиас типа

Просто даёт типу новое имя

```python
Price = int
```

---

### `NewType`

Создаёт **отдельный тип** на базе существующего

```python
OrderId = NewType("OrderId", str)
```

---

### `TypedDict`

Описывает структуру словаря

```python
class CustomerInfo(TypedDict):
    email: str
    phone: str | None
```

---

### `Protocol`

Описывает интерфейс по набору методов и атрибутов

```python
class PaymentProcessor(Protocol):
    def process(self, amount: Price, method: PaymentMethod) -> bool:
        ...
```

---

## 10. Итог

Папка **«c»** показывает, как перейти от базовой типизации к более выразительной и строгой модели данных.

Эти инструменты помогают:

- ограничивать допустимые значения
- разделять логически разные сущности одного базового типа
- описывать структуру словарей
- задавать интерфейсы без наследования
- делать код понятнее и безопаснее ещё до запуска

---

## Полный объединённый пример

```python
from typing import Literal, TypedDict, Protocol, NewType, Optional, NotRequired

class CustomType:
    pass

custom = CustomType

# Использование Literal для ограничения возможных значений
OrderStatus = Literal[
    "pending",
    "confirmed",
    "shipped",
    "delivered",
    "canceled",
]
PaymentMethod = Literal["card", "cash", "crypto", "bank_transfer"]

# Создание алиасов для встроенных типов, когда имеет смысл добавить семантику
OrderId = NewType("OrderId", str)  # OrderId - это не просто строка, а именно ID заказа
Price = int  # Цена в копейках (или другой валюте), без десятичных знаков
type Quantity = int  # python 3.12+

def example_function(
    order_id: OrderId,
    quantity: Quantity,
    price: Price,
) -> None:
    print(f"Order ID: {order_id}, Quantity: {quantity}")

example_function(OrderId("12345"), 2, 1000)

# Создание собственных типов с помощью TypedDict
class OrderItem(TypedDict):
    product_id: str
    name: str | None
    quantity: Quantity
    price: Price


class CustomerInfo(TypedDict):
    customer_id: str
    email: str
    shipping_address: str
    phone: str | None
    missing_field: NotRequired[str]

# Создание протоколов для структурной типизации
class PaymentProcessor(Protocol):
    def process(self, amount: Price, method: PaymentMethod) -> bool:
        ...


def process_order(
    order_id: OrderId,
    status: OrderStatus,
    payment_method: PaymentMethod,
    items: list[OrderItem],
    customer_info: CustomerInfo,
    payment_processor: Optional[PaymentProcessor] = None
) -> dict[str, object]:
    # Обработка заказа
    if status == "confirmed":
        pass
    elif status == "shipped":
        pass

    # Обработка оплаты
    if payment_processor and payment_method in ["card", "crypto"]:
        total_amount = sum(item["price"] * item["quantity"] for item in items)
        payment_processor.process(total_amount, payment_method)

    print(customer_info)

    return {"order_id": order_id, "status": status, "processed": True}


process_order(
    OrderId("12345"),
    "confirmed",
    "card",
    [
        OrderItem(**{"product_id": "p1", "name": "Product a", "quantity": 2, "price": 1000}),
        {"product_id": "p2", "name": "Product 2", "quantity": 1, "price": 2000}
    ],
    {
        "customer_id": "c1",
        "email": "123@gmail.com",
        "shipping_address": "123 Main St",
        "phone": "123 Main St",
        "missing_field": "123 Main St"
    },
)
```