# Сценарий 1: приложение ещё не поднято, есть только БД, Alembic не инициализирован

## Шаг 0 — стартовая ситуация

```
myproject/
├── app/
│   ├── models.py        ← модели уже написаны, но БД про них ничего не знает
│   └── core/config.py
└── (alembic вообще отсутствует)
```

БД поднята (например, пустой PostgreSQL в Docker), но в ней нет ни одной таблицы, ни `alembic_version`, ничего.

## Шаг 1 — установка и инициализация

```bash
pip install alembic
alembic init alembic
```

**Что физически создаётся:**

```
myproject/
├── alembic/
│   ├── versions/          ← пустая папка, миграций пока нет
│   ├── env.py              ← шаблонный, ещё не связан с твоими моделями
│   ├── script.py.mako
│   └── README
├── alembic.ini
```

В БД **пока ничего не меняется** — эта команда только генерирует файлы на диске, к базе она не подключается.

## Шаг 2 — связываем `env.py` с моделями и настройками

Редактируешь `alembic/env.py` вручную (это единственный ручной шаг конфигурации за всю жизнь проекта, дальше он не трогается):

```python
from app.models import Base
from app.core.config import get_settings

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata   # вот ключевая строка
```

Здесь важно: `Base` должен реально "видеть" все модели — то есть в `app/models.py` (или там, куда указывает импорт) должны быть импортированы все классы-модели, иначе Alembic просто не узнает об их существовании при сравнении.

**Физически меняется** только сам файл `env.py` — ни БД, ни `versions/` ещё не затронуты.

## Шаг 3 — первая миграция: "привести БД в соответствие"

Так как БД пустая, а моделей уже несколько, генерируешь одну (первую) миграцию через автогенерацию:

```bash
alembic revision --autogenerate -m "initial schema"
```

**Что происходит внутри этой команды:**

1. Alembic подключается к БД (используя строку из `env.py`), смотрит, какие таблицы там реально есть — сейчас ни одной.
2. Смотрит на `target_metadata` (`Base.metadata`) — там уже расписаны все твои модели.
3. Строит diff: "в коде есть таблицы `users`, `orders`, `accounts` — в БД их нет" → генерирует `op.create_table(...)` для каждой.
4. Пишет результат в новый файл.

**Физически создаётся:**

```
alembic/versions/
└── ae1027a6acf_initial_schema.py
```

```python
revision = "ae1027a6acf"
down_revision = None        # это первая миграция — ей не на что ссылаться назад

def upgrade():
    op.create_table("users", ...)
    op.create_table("orders", ...)
    op.create_table("accounts", ...)

def downgrade():
    op.drop_table("accounts")
    op.drop_table("orders")
    op.drop_table("users")
```

**В БД пока по-прежнему ничего не изменилось** — файл миграции сгенерирован, но не выполнен. Это чистый "черновик", который стоит открыть глазами и проверить, что автогенерация не упустила ничего (индексы, constraints иногда требуют ручной доводки).

## Шаг 4 — применяем миграцию к БД

```bash
alembic upgrade head
```

**Что происходит:**

1. Alembic смотрит в БД — таблицы `alembic_version` там ещё нет, значит текущая версия "с самого начала" (`None`).
2. Строит граф миграций, видит: от `None` до head'а (`ae1027a6acf`) нужно применить ровно один шаг.
3. Выполняет `upgrade()` из этого файла — реально шлёт `CREATE TABLE` в БД.
4. **Создаёт служебную таблицу `alembic_version`** и записывает туда `ae1027a6acf`.

**Физически в БД теперь:**

```
users, orders, accounts   ← реальные таблицы приложения
alembic_version            ← служебная, version_num = ae1027a6acf
```

Файлы в проекте на этом шаге уже не меняются — меняется только состояние БД.

## Итоговый порядок операций (сценарий 1)

```
pip install alembic
  → alembic init alembic          (создаёт alembic/, alembic.ini)
  → правишь env.py вручную        (связь с моделями и настройками — один раз)
  → alembic revision --autogenerate -m "initial schema"
                                    (создаёт файл миграции, БД не трогает)
  → alembic upgrade head          (применяет миграцию, создаёт таблицы + alembic_version)
```

Этот же файл `initial schema` дальше коммитится в Git — любой другой разработчик, подняв пустую БД и выполнив `alembic upgrade head`, получит идентичную схему.

---

# Сценарий 2: приложение уже работает, ты поменял модель SQLAlchemy

## Шаг 0 — стартовая ситуация

Всё из сценария 1 уже есть и применено. Ты добавляешь новое поле в модель:

```python
# app/models.py
class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(default="pending")
    cancellation_reason: Mapped[str | None] = mapped_column(nullable=True)   # ← новое
```

На этом этапе: **код изменён, БД — нет**. Приложение, если его сейчас запустить и обратиться к этому полю, получит ошибку — колонки в реальной таблице `orders` физически ещё не существует.

## Шаг 1 — генерируешь новую миграцию

```bash
alembic revision --autogenerate -m "add cancellation reason to orders"
```

**Что делает Alembic:**

1. Смотрит в БД (через таблицу `alembic_version`) — видит, что текущая версия БД `ae1027a6acf`.
2. Подключается к самой БД и читает **реальную** структуру таблицы `orders` (через рефлексию — буквально `SELECT` из системного каталога PostgreSQL, что за колонки там есть).
3. Сравнивает с `target_metadata` — видит, что в модели `Order` появилось поле, которого нет в реальной таблице.
4. Генерирует новый файл в `versions/`.

**Физически создаётся:**

```
alembic/versions/
├── ae1027a6acf_initial_schema.py
└── f7c88e2a001_add_cancellation_reason_to_orders.py   ← новый файл
```

```python
revision = "f7c88e2a001"
down_revision = "ae1027a6acf"    # ссылается на предыдущую — цепочка продолжается

def upgrade():
    op.add_column("orders", sa.Column("cancellation_reason", sa.String(), nullable=True))

def downgrade():
    op.drop_column("orders", "cancellation_reason")
```

**В БД на этом шаге всё ещё ничего не изменилось.** Это критично понимать: `--autogenerate` только **читает** БД для сравнения, но не пишет в неё.

## Шаг 2 — обязательно проверяешь файл глазами

Особенно если в модели было что-то тоньше, чем "просто добавил поле" — переименование, смена типа. В этом случае (простое добавление nullable-поля) автогенерация справляется полностью верно, править нечего.

## Шаг 3 — применяешь миграцию

```bash
alembic upgrade head
```

**Что происходит:**

1. Alembic видит: текущая версия БД — `ae1027a6acf`, head в файлах — `f7c88e2a001`. Между ними один шаг.
2. Выполняет `upgrade()` этого одного файла — реально шлёт `ALTER TABLE orders ADD COLUMN cancellation_reason VARCHAR` в БД.
3. Обновляет `alembic_version`: `version_num` меняется с `ae1027a6acf` на `f7c88e2a001`.

**Физически в БД:**

```
orders   ← у таблицы появилась новая колонка cancellation_reason
alembic_version   ← version_num теперь f7c88e2a001
```

## Шаг 4 — коммит

```bash
git add app/models.py alembic/versions/f7c88e2a001_add_cancellation_reason_to_orders.py
git commit -m "add cancellation reason to orders"
```

Модель и миграция коммитятся **вместе, одним PR** — иначе на чужой машине после `git pull` код будет ожидать поле, которого в его локальной БД ещё нет (пока он сам не выполнит `alembic upgrade head`).

## Итоговый порядок операций (сценарий 2)

```
меняешь app/models.py вручную
  → alembic revision --autogenerate -m "..."
                                    (создаёт новый файл в versions/, БД не трогает)
  → проверяешь сгенерированный файл глазами
  → alembic upgrade head          (применяет ALTER TABLE, обновляет alembic_version)
  → коммитишь модель + файл миграции вместе
```

## Сравнение двух сценариев рядом

||Сценарий 1 (с нуля)|Сценарий 2 (изменение)|
|---|---|---|
|`down_revision` новой миграции|`None`|ID предыдущей миграции|
|Что генерируется в `upgrade()`|`create_table(...)` на каждую модель|точечная операция (`add_column`, `alter_column` и т.п.)|
|Состояние `alembic_version` до|таблицы вообще нет|есть строка с текущей версией|
|Состояние `alembic_version` после|создаётся, записывается первая ревизия|обновляется на новую ревизию|
|Что меняется в файлах проекта|новая папка `alembic/`, `alembic.ini`, первый файл в `versions/`|только один новый файл в `versions/`|

Единственная операция, которая **реально касается БД**, — это `alembic upgrade head`. Всё, что до неё (`revision --autogenerate`), работает только с файлами на диске и лишь **читает** БД для сравнения, не изменяя её.