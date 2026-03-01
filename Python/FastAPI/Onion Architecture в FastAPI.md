Видео-источник:  https://www.youtube.com/watch?v=8Im74b55vFc

Ниже — расширенный конспект с практическими примерами, типичными ошибками и схемой потока запроса. Я опираюсь на твой текст и дополняю его общими принципами Onion Architecture и официальными возможностями FastAPI: зависимости, разбиение на модули и подмена зависимостей в тестах. FastAPI действительно поощряет DI через `Depends`, модульную структуру для “bigger applications”, а в тестах позволяет переопределять зависимости через `app.dependency_overrides`. Onion Architecture и Repository pattern как раз строятся вокруг dependency inversion: внутренние слои не должны знать о внешней инфраструктуре. ([fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/dependencies/?utm_source=chatgpt.com "Dependencies"))

# Слоистая архитектура в FastAPI: расширенный конспект

## 1. Главная идея

Смысл подхода не в том, чтобы “размазать код по папкам”, а в том, чтобы **разделить причины изменений**:

- если меняется HTTP-контракт — трогаем роутеры;
- если меняется бизнес-правило — трогаем сервис;    
- если меняется база/ORM — трогаем репозиторий.


Это и есть главный практический выигрыш: код становится локализованным по ответственности, проще тестируется и легче переживает замену инфраструктуры. В терминах Onion Architecture внутренние слои должны быть независимы от внешних, а зависимости направлены “снаружи внутрь” через абстракции. ([Programming with Palermo](https://jeffreypalermo.com/2008/07/the-onion-architecture-part-1/?utm_source=chatgpt.com "The Onion Architecture : part 1 | Programming with Palermo"))

---

## 2. Как выглядит поток запроса

Удобно запомнить такую цепочку:

```text
HTTP request
-> Router / Endpoint
-> Service
-> Repository
-> Database

и обратно:

Database
-> Repository
-> Service
-> Router
-> HTTP response
```

### Распределение ролей

**Router**

- принимает запрос;
- валидирует вход через Pydantic-схемы;
- вызывает сервис;
- возвращает response.

**Service**

- реализует бизнес-логику;
- координирует несколько операций;
- знает, _что_ нужно сделать, но не знает деталей SQL/ORM.

**Repository**

- знает, _как_ получить и сохранить данные;    
- изолирует SQLAlchemy, SQL, Mongo и любую другую инфраструктуру.

---

## 3. Типичная структура проекта

FastAPI официально рекомендует выносить крупное приложение в несколько файлов и модулей, используя `APIRouter` и отдельные зависимости. На практике под Onion/Service/Repository это часто выглядит так: ([fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/bigger-applications/?utm_source=chatgpt.com "Bigger Applications - Multiple Files"))

```text
app/
├── main.py
├── api/
│   └── tasks.py
├── schemas/
│   └── task.py
├── services/
│   └── task_service.py
├── repositories/
│   ├── abstract.py
│   └── task_sqlalchemy.py
├── models/
│   └── task.py
├── db/
│   └── session.py
└── dependencies.py
```

Это не “единственно правильная” структура, но она хорошо ложится на идею разделения слоёв.

---

## 4. Антипаттерн: “толстый” эндпоинт

Вот типичный плохой пример:

```python
@router.post("/tasks")
async def add_task(
    task: TaskSchemaAdd,
    session: AsyncSession = Depends(get_async_session),
):
    task_dict = task.model_dump()

    stmt = insert(TaskOrm).values(**task_dict).returning(TaskOrm.id)
    result = await session.execute(stmt)
    await session.commit()
    task_id = result.scalar_one()

    # ещё и письмо отправим
    await send_email("Task created")

    # и лог напишем
    logger.info("Task created")

    return {"task_id": task_id}
```

### Что тут плохо

- эндпоинт знает про БД;
- эндпоинт знает про бизнес-процесс;
- эндпоинт знает про уведомления;
- это трудно переиспользовать;
- это трудно тестировать отдельно.

Если SQLAlchemy API поменяется, или ты захочешь перейти на другой способ хранения, менять придётся роутеры, хотя они вообще не должны об этом думать.

---

## 5. Хороший вариант: тонкий роутер

```python
@router.post("/tasks")
async def add_task(
    task: TaskSchemaAdd,
    task_service: TaskService = Depends(get_task_service),
):
    task_id = await task_service.add_task(task)
    return {"task_id": task_id}
```

### Почему это хорошо

Роутер здесь:

- принимает HTTP;
- передаёт DTO/схему в сервис;
- возвращает ответ.

Больше он ничего не делает.

Это хорошо согласуется и с DI-механизмом FastAPI, где зависимости передаются через `Depends`. ([fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/dependencies/?utm_source=chatgpt.com "Dependencies"))

---

## 6. Репозиторий: не “слой ради слоя”, а изоляция инфраструктуры

Твой пример с абстрактным репозиторием правильный по сути. Его можно чуть расширить.

### Абстракция

```python
from abc import ABC, abstractmethod

class AbstractTaskRepository(ABC):
    @abstractmethod
    async def add_one(self, data: dict) -> int:
        raise NotImplementedError

    @abstractmethod
    async def find_all(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, task_id: int) -> dict | None:
        raise NotImplementedError
```

### Реализация на SQLAlchemy

```python
class SQLAlchemyTaskRepository(AbstractTaskRepository):
    model = TaskOrm

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_one(self, data: dict) -> int:
        stmt = insert(self.model).values(**data).returning(self.model.id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    async def find_all(self) -> list[dict]:
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            {"id": row.id, "name": row.name, "description": row.description}
            for row in rows
        ]

    async def find_by_id(self, task_id: int) -> dict | None:
        stmt = select(self.model).where(self.model.id == task_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {"id": row.id, "name": row.name, "description": row.description}
```

### Практический смысл

Сервис не знает:

- `insert` это или ORM `.add()`,
- PostgreSQL это или SQLite,
- синхронная БД или асинхронная.

Он знает только контракт репозитория.

Это и есть dependency inversion в прикладном виде. ([cosmicpython.com](https://www.cosmicpython.com/book/chapter_02_repository.html?utm_source=chatgpt.com "Repository Pattern"))

---

## 7. Сервис: место для бизнес-логики

Сервис нужен не просто как “прокладка”. Его задача — держать **правила приложения**.

### Пример

```python
class TaskService:
    def __init__(self, tasks_repo: AbstractTaskRepository):
        self.tasks_repo = tasks_repo

    async def add_task(self, task: TaskSchemaAdd) -> int:
        tasks_dict = task.model_dump()

        # пример бизнес-правила
        if len(tasks_dict["name"]) < 3:
            raise ValueError("Task name is too short")

        task_id = await self.tasks_repo.add_one(tasks_dict)
        return task_id

    async def get_task(self, task_id: int) -> dict:
        task = await self.tasks_repo.find_by_id(task_id)
        if task is None:
            raise LookupError("Task not found")
        return task
```

### Что тут важно

Именно сервис решает:

- можно ли создавать сущность;
- как валидировать бизнес-ограничения;
- что делать, если объект не найден;
- в каком порядке вызывать несколько зависимостей.

Если в будущем кроме записи в БД надо:

- отправить письмо,
- записать аудит,
- создать событие в брокере,

это уже естественное место для сервиса, а не для роутера.

---

## 8. Dependency Injection в FastAPI

FastAPI официально предоставляет встроенную dependency injection систему, а зависимости можно организовывать как функции или классы. Это хорошо сочетается со слоистой архитектурой: роутер получает уже готовый сервис, а сервис — уже готовый репозиторий. ([fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/dependencies/?utm_source=chatgpt.com "Dependencies"))

### Пример провайдеров зависимостей

```python
def get_task_repository(
    session: AsyncSession = Depends(get_async_session),
) -> AbstractTaskRepository:
    return SQLAlchemyTaskRepository(session)


def get_task_service(
    repo: AbstractTaskRepository = Depends(get_task_repository),
) -> TaskService:
    return TaskService(repo)
```

### Почему это удобно

Меняется только wiring, а не код бизнес-логики.

Например, на тестах ты можешь подменить `get_task_service` или `get_task_repository` на фейк.

---

## 9. Как тестировать такую архитектуру

Вот здесь слоистость реально окупается.

### 9.1. Unit-тест сервиса без FastAPI и без БД

```python
class FakeTaskRepository(AbstractTaskRepository):
    def __init__(self):
        self.storage = []
        self.seq = 1

    async def add_one(self, data: dict) -> int:
        task_id = self.seq
        self.seq += 1
        self.storage.append({"id": task_id, **data})
        return task_id

    async def find_all(self) -> list[dict]:
        return self.storage

    async def find_by_id(self, task_id: int) -> dict | None:
        for item in self.storage:
            if item["id"] == task_id:
                return item
        return None
```

```python
async def test_add_task():
    repo = FakeTaskRepository()
    service = TaskService(repo)

    task_id = await service.add_task(TaskSchemaAdd(name="Test", description="Demo"))

    assert task_id == 1
```

### Почему это сильно

- нет БД;
- нет SQLAlchemy;
- нет FastAPI;
- тест быстрый и изолированный.

Это одна из главных причин, почему Repository pattern ценят в прикладной архитектуре. ([cosmicpython.com](https://www.cosmicpython.com/book/chapter_02_repository.html?utm_source=chatgpt.com "Repository Pattern"))

---

### 9.2. Тест эндпоинта с подменой зависимости

FastAPI официально поддерживает `app.dependency_overrides`: можно заменить исходную зависимость на тестовую. ([fastapi.tiangolo.com](https://fastapi.tiangolo.com/advanced/testing-dependencies/?utm_source=chatgpt.com "Testing Dependencies with Overrides"))

```python
app.dependency_overrides[get_task_service] = lambda: TaskService(FakeTaskRepository())
```

После этого запросы в тесте будут идти через фейковый сервис/репозиторий, а не через настоящую базу.

### Практический вывод

- сервис тестируем отдельно как unit;
- роутер тестируем отдельно как integration/API layer;
- БД можно проверять в отдельных repository-тестах.

---

## 10. Где должна жить валидация

Тут часто путаются.

### В роутере / Pydantic-схемах

Должна жить:

- проверка формата входных данных;
- обязательные поля;
- типы;
- базовые ограничения вроде `min_length`, `EmailStr` и т.д.

### В сервисе

Должна жить:

- бизнес-валидация;
- правила предметной области;
- межсущностные проверки.

### Пример

- “email должен быть валидным” — схема;
- “пользователь с таким email уже существует” — сервис;
- “как именно искать пользователя по email в PostgreSQL” — репозиторий.

Такое разделение обычно делает систему намного понятнее.

---

## 11. Частая ошибка: сервис как “пустая прослойка”

Иногда делают так:

```python
class TaskService:
    def __init__(self, repo):
        self.repo = repo

    async def add_task(self, task):
        return await self.repo.add_one(task.model_dump())
```

Формально слой есть, но смысла почти нет.

### Когда сервис оправдан

Когда в нём есть хотя бы одно из:

- бизнес-правила;
- orchestration;
- преобразование DTO/моделей;
- работа с несколькими репозиториями;
- транзакционные сценарии;
- вызовы внешних сервисов.

Если сервис — только переадресация 1 в 1, это сигнал, что либо бизнес-логика ещё не выделена, либо архитектура пока преждевременно усложнена.

---

## 12. Когда Repository pattern может быть избыточен

Тоже важный момент.

Для очень маленького CRUD-сервиса из 2–3 ручек иногда отдельный репозиторий действительно может выглядеть тяжеловесно.

### Разумный ориентир

Выделение репозиториев почти всегда окупается, если:

- сущностей несколько;
- бизнес-логика растёт;
- нужны тесты без БД;
- проект будет жить долго;
- команда больше одного человека.

Если проект совсем маленький и временный, можно начать проще — но важно не закапывать SQLAlchemy прямо в роутеры, если есть шанс роста.

---

## 13. Пример “полного” хорошего сценария

### Схема

```python
class TaskSchemaAdd(BaseModel):
    name: str
    description: str
```

### Роутер

```python
@router.post("/tasks")
async def add_task(
    task: TaskSchemaAdd,
    task_service: TaskService = Depends(get_task_service),
):
    task_id = await task_service.add_task(task)
    return {"task_id": task_id}
```

### Сервис

```python
class TaskService:
    def __init__(self, tasks_repo: AbstractTaskRepository):
        self.tasks_repo = tasks_repo

    async def add_task(self, task: TaskSchemaAdd) -> int:
        data = task.model_dump()

        if len(data["name"]) < 3:
            raise ValueError("Too short")

        return await self.tasks_repo.add_one(data)
```

### Репозиторий

```python
class SQLAlchemyTaskRepository(AbstractTaskRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_one(self, data: dict) -> int:
        stmt = insert(TaskOrm).values(**data).returning(TaskOrm.id)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.scalar_one()
```

Такой код:

- прозрачен по ролям,
- расширяем,
- тестируем по слоям,
- не завязывает бизнес-логику на FastAPI и ORM.

---

## 14. Итоговый вывод

Твой исходный конспект правильный по сути. Я бы усилил его такими формулировками:

### Что даёт слоистая архитектура на практике

- уменьшает связность между HTTP, бизнес-логикой и БД;
- позволяет менять инфраструктуру без переписывания доменной логики;
- упрощает unit-тесты;
- делает код предсказуемым для команды. ([fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/dependencies/?utm_source=chatgpt.com "Dependencies"))

### Самая полезная мысль

**Роутер не должен “думать”, сервис не должен “знать SQL”, репозиторий не должен “решать бизнес-задачи”.**

Если хочешь, следующим сообщением я могу собрать это в ещё более удобный вид:

- **в формате короткого конспекта для сдачи**,  
    или
- **в формате готового markdown-файла с код-блоками и заголовками**.