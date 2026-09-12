## 1. Что это и зачем

**Unit of Work (UoW)** — паттерн из книги Мартина Фаулера *"Patterns of Enterprise Application Architecture"*. Определение оттуда:

> Поддерживает список объектов, затронутых бизнес-транзакцией, и координирует запись изменений и решение проблем параллельного доступа.

Проще: UoW — это объект, который **собирает все изменения**, сделанные за одну логическую операцию (например, обработку одного HTTP-запроса или одной команды), и в конце **атомарно** применяет их все разом (commit) или откатывает все разом (rollback), если что-то пошло не так.

### Проблема, которую он решает

Без UoW бизнес-логика вынуждена сама заботиться о транзакциях и знать детали хранилища:

```python
def transfer_money(from_id, to_id, amount, session):
    from_acc = session.query(Account).get(from_id)
    to_acc = session.query(Account).get(to_id)
    from_acc.balance -= amount
    to_acc.balance += amount
    session.add(from_acc)
    session.add(to_acc)
    session.commit()   # логика транзакции размазана по бизнес-коду
```

Проблемы такого подхода:

- Бизнес-логика смешана с управлением транзакцией — тестировать сложнее, переиспользовать в другом контексте (например, объединить с другой операцией в одну транзакцию) — тоже.
- Если операция состоит из нескольких шагов, использующих разные репозитории/таблицы, гарантировать атомарность ("всё или ничего") приходится вручную в каждом месте.
- Утечка деталей персистентности (`session`, SQL) в слой, который должен думать только о домене.

### Что даёт UoW

```python
def transfer_money(uow, from_id, to_id, amount):
    with uow:
        from_acc = uow.accounts.get(from_id)
        to_acc = uow.accounts.get(to_id)
        from_acc.withdraw(amount)
        to_acc.deposit(amount)
        uow.commit()
```

Бизнес-логика работает с доменными объектами через репозитории, ничего не знает про SQL/сессии, а атомарность и откат при ошибке гарантирует сам `uow` — это тот же принцип гарантированного управления ресурсом, что мы обсуждали в контекстных менеджерах: **ресурс (транзакция) открывается, используется и гарантированно закрывается (commit/rollback), независимо от того, что случится внутри блока**.

---

## 2. UoW — это context manager

На практике в Python UoW почти всегда реализуется именно как контекстный менеджер — это идеальное совпадение семантики: "открыть транзакцию → сделать работу → закрыть транзакцию (commit или rollback при исключении)" — ровно то, для чего создан протокол `__enter__`/`__exit__`.

### Синхронная версия (абстракция + реализация на SQLAlchemy)

```python
from __future__ import annotations
import abc
from sqlalchemy.orm import Session, sessionmaker


class AbstractUnitOfWork(abc.ABC):
    def __enter__(self) -> "AbstractUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.rollback()
        # если исключения не было, но пользователь забыл вызвать commit() —
        # это осознанное решение: по умолчанию откатываем (см. раздел 4)
        else:
            self.rollback()

    @abc.abstractmethod
    def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: sessionmaker = sessionmaker()):
        self.session_factory = session_factory

    def __enter__(self):
        self.session: Session = self.session_factory()
        self.accounts = AccountRepository(self.session)  # репозиторий на этой же сессии
        return super().__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
```

Использование:

```python
def transfer_money(uow: AbstractUnitOfWork, from_id, to_id, amount):
    with uow:
        from_acc = uow.accounts.get(from_id)
        to_acc = uow.accounts.get(to_id)
        from_acc.withdraw(amount)
        to_acc.deposit(amount)
        uow.commit()
```

Если внутри блока `with uow` произойдёт исключение (например, `from_acc.withdraw()` бросит `InsufficientFundsError`), `__exit__` вызовет `rollback()` до того, как исключение улетит дальше — база данных не окажется в промежуточном, противоречивом состоянии.

### Асинхронная версия

Ровно та же идея, но через `__aenter__`/`__aexit__`, как мы разбирали в гайде про асинхронные контекстные менеджеры — потому что `commit()`/`rollback()` в асинхронной БД сами требуют сетевого round-trip и должны быть `await`-able:

```python
import abc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class AbstractUnitOfWork(abc.ABC):
    async def __aenter__(self) -> "AbstractUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.rollback()

    @abc.abstractmethod
    async def commit(self): ...

    @abc.abstractmethod
    async def rollback(self): ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session: AsyncSession = self.session_factory()
        self.accounts = AsyncAccountRepository(self.session)
        return await super().__aenter__()

    async def __aexit__(self, exc_type, exc_value, traceback):
        await super().__aexit__(exc_type, exc_value, traceback)
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
```

```python
async def transfer_money(uow: AbstractUnitOfWork, from_id, to_id, amount):
    async with uow:
        from_acc = await uow.accounts.get(from_id)
        to_acc = await uow.accounts.get(to_id)
        from_acc.withdraw(amount)
        to_acc.deposit(amount)
        await uow.commit()
```

---

## 3. Связь с Repository и общая картина слоёв

UoW почти всегда идёт в паре с **паттерном Repository** (репозиторий — абстракция доступа к коллекции доменных объектов, скрывающая SQL):

```
┌─────────────────────────┐
│   Бизнес-логика/сервис   │  знает только про домен и uow.commit()
└───────────┬─────────────┘
            │ uow.accounts.get(id), uow.accounts.add(x)
┌───────────▼─────────────┐
│   Unit of Work            │  управляет транзакцией (commit/rollback)
│   ├─ accounts: Repository │
│   └─ orders:   Repository │
└───────────┬─────────────┘
            │ session.query(...), session.add(...)
┌───────────▼─────────────┐
│   ORM-сессия (SQLAlchemy) │
└───────────┬─────────────┘
            │ SQL
┌───────────▼─────────────┐
│   База данных              │
└─────────────────────────┘
```

Репозитории создаются **внутри** UoW и делят с ним одну и ту же сессию — поэтому все изменения через разные репозитории (например, `uow.accounts` и `uow.orders` в одной операции) попадают в одну транзакцию и коммитятся/откатываются вместе.

```python
class AccountRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, account_id) -> Account:
        return self.session.query(Account).filter_by(id=account_id).one()

    def add(self, account: Account):
        self.session.add(account)
```

---

## 4. Важные детали и грабли

**По умолчанию — rollback, а не commit.** Это осознанный выбор дизайна в примере выше: если код внутри `with uow` дошёл до конца, но забыл явно вызвать `uow.commit()`, транзакция откатится. Это заставляет **явно** фиксировать намерение сохранить изменения, а не полагаться на "если не было исключения — наверное, надо закоммитить". Уменьшает риск случайно закоммитить неполную/некорректную операцию.

**UoW не должен течь наружу за пределы одной операции.** Обычно UoW создаётся на входе в use case / обработчик запроса и живёт ровно до его завершения — аналогично тому, как `get_session` из FastAPI-примера создаёт сессию на время одного HTTP-запроса. UoW — это как раз более высокоуровневая обёртка над этим же принципом: не просто "сессия на запрос", а "транзакция на бизнес-операцию", с явным `commit()`.

**Тестируемость — одна из главных причин использовать UoW.** Так как бизнес-логика зависит от абстрактного `AbstractUnitOfWork`, а не от конкретной БД, для тестов легко подставить in-memory реализацию:

```python
class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.accounts = FakeAccountRepository()
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass
```

Это позволяет тестировать `transfer_money(uow, ...)` вообще без реальной БД — только проверяя состояние `FakeAccountRepository` и флаг `committed`.

**Вложенные/составные операции.** Если бизнес-операция должна объединить несколько шагов в одну транзакцию (например, "перевести деньги и создать запись в аудит-логе"), оба шага делаются внутри одного `with uow:` — это и есть весь смысл паттерна: границы UoW = границы атомарной бизнес-операции, а не границы отдельного запроса к БД.

---

## 5. Итог

| Вопрос | Ответ |
|---|---|
| Что такое UoW | Объект, собирающий изменения одной бизнес-операции и атомарно коммитящий/откатывающий их разом |
| Как реализуется в Python | Как контекстный менеджер (`with`/`async with`) — та же механика `__enter__`/`__exit__` (или `__aenter__`/`__aexit__`), что и везде |
| С чем используется в паре | С паттерном Repository — репозитории живут внутри UoW и делят одну сессию/транзакцию |
| Главный эффект | Бизнес-логика не знает про SQL/сессии; транзакционность гарантирована языковым механизмом, а не дисциплиной разработчика |
| Частый выбор по умолчанию | Rollback, если явно не вызван `commit()` — защита от "забытого" сохранения |
