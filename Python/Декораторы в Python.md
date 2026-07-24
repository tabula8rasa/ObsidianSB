
Декоратор `wraps` сохраняет doc_string исходной функции

## Декоратор с параметром для функции с аргументами

```python
from typing import Callable
import time
from functools import wraps

def deco(param: int):
    def wrapper(func: Callable):
        @wraps(func)
        def inner(*args, **kwargs):
        
            "Логика декоратора с параметром до вызова функции"

            res = func(*args, **kwargs)
            
            "Логика декоратора с параметром после вызова функции"
            
            return res
        return inner
    return wrapper
```

Чтобы применить декоратор к функции есть два варианта: **явный** и через **@**

```python
# 1 вариант

def my_func(*args, **kwargs):
	...
	
my_func = deco(5)(my_func)

# 2 вариант

@deco(5)
def my_func(*args, **kwargs):
	...

```

## Декоратор для асинхронной функции

```python
from typing import Coroutine
import asyncio

def deco(coroutine: Coroutine):
    async def wrapper(*args, **kwargs):
        res = await coroutine(*args, **kwargs)
        return res
    return wrapper

@deco
async def my_async_func():
    await asyncio.sleep(0.5)
    return 1

await my_async_func()

# my_async_func = deco(my_async_func)
``` 

## Примеры декораторов

### Декоратор для кэширования результата работы функции
```python
from functools import lru_cache

@lru_cache
def my_long_calc():
    time.sleep(3)
    return 42
```

### Декоратор для создания контекстного менеджера
```python
from contextlib import contextmanager

@contextmanager
def ctx_manager():
    print("hello") # Открытие соединения с базой данных
    yield
    print("end")   # Закрытие соединения базой данных

with ctx_manager() as man:
    print("123")

"""  
Вывод:
 hello
 123
 end
"""
```