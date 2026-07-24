
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

