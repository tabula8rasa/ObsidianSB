---
title: Airflow Params — ручной запуск DAG с параметрами
created: 2026-07-11
tags:
  - airflow
  - data-engineering
  - dag
  - backfill
  - params
  - etl
---
**Airflow Params** — это способ задать параметры для DAG и дать пользователю возможность передать их при ручном запуске.

Практический смысл: DAG может работать по расписанию, но при необходимости его можно вручную запустить с нужными датами, режимом загрузки или другими настройками.

Пример:

```text
Обычный daily run → грузим данные за ds
Ручной run → грузим данные за 2026-01-10 — 2026-04-02
```

Это удобно для:

- ретро-загрузок;
- пересчёта витрин;
- восстановления данных после сбоя;
- исправления периода, где источник отдал некорректные данные;
- ручного запуска пайплайна без изменения кода;
- передачи параметров аналитиком через Airflow UI.

---

# 1. Идея на простом примере

Без параметров DAG обычно работает так:

```python
from datetime import datetime

from airflow import DAG


dag = DAG(
    dag_id="daily_sales_pipeline",
    schedule_interval="0 10 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
)
```

Такой DAG запускается по расписанию.

Если добавить `params`, при ручном запуске можно будет передать значения:

```python
from datetime import datetime

from airflow import DAG
from airflow.models.param import Param


dag = DAG(
    dag_id="daily_sales_pipeline",
    schedule_interval="0 10 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    params={
        "start_date": Param(
            "",
            type="string",
            pattern=r"^$|^\d{4}-\d{2}-\d{2}$",
            description="Начальная дата ретро-загрузки в формате YYYY-MM-DD. Пусто = ds.",
        ),
        "end_date": Param(
            "",
            type="string",
            pattern=r"^$|^\d{4}-\d{2}-\d{2}$",
            description="Конечная дата ретро-загрузки в формате YYYY-MM-DD. Пусто = start_date.",
        ),
    },
)
```

Теперь пользователь может открыть DAG в Airflow UI, нажать запуск и ввести:

```text
start_date = 2026-01-10
end_date   = 2026-04-02
```

---

# 2. Что такое `params`

`params` — это словарь параметров DAG.

Их можно использовать:

- в Python-задачах;
- в TaskFlow API;
- в Jinja-шаблонах;
- в BashOperator;
- в SQL-запросах;
- в кастомных операторах.

Пример:

```python
params={
    "start_date": "2026-01-10",
    "end_date": "2026-04-02",
    "mode": "retro",
}
```

Важный плюс `params`: при ручном запуске Airflow может показать удобную форму, а не просто пустое поле для JSON.

---

# 3. Зачем нужен `Param`

Можно написать просто:

```python
params={
    "start_date": "",
    "end_date": "",
}
```

Но лучше использовать `Param`:

```python
from airflow.models.param import Param


params={
    "start_date": Param(
        "",
        type="string",
        pattern=r"^$|^\d{4}-\d{2}-\d{2}$",
        description="Дата начала в формате YYYY-MM-DD. Пусто = ds.",
    ),
}
```

`Param` позволяет указать:

| Возможность | Зачем нужна |
|---|---|
| `type` | тип значения: string, integer, boolean, array и т.д. |
| `description` | описание поля в Airflow UI |
| `pattern` | проверка строки регулярным выражением |
| `enum` | список допустимых значений |
| `minimum` / `maximum` | ограничения для чисел |
| default value | значение по умолчанию |

`Param` использует идеи JSON Schema, поэтому можно задавать валидацию прямо в описании параметра.

---

# 4. Пример DAG для ретро-загрузки

```python
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.decorators import task
from airflow.models.param import Param


default_args = {
    "owner": "data-engineering",
    "retries": 1,
}


with DAG(
    dag_id="DEMO__retro_load_pipeline",
    default_args=default_args,
    schedule_interval="0 10 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    params={
        "start_date": Param(
            "",
            type="string",
            pattern=r"^$|^\d{4}-\d{2}-\d{2}$",
            description="Начальная дата ретро-загрузки в формате YYYY-MM-DD. Пусто = ds.",
        ),
        "end_date": Param(
            "",
            type="string",
            pattern=r"^$|^\d{4}-\d{2}-\d{2}$",
            description="Конечная дата ретро-загрузки в формате YYYY-MM-DD. Пусто = start_date.",
        ),
    },
    description="Пример DAG с ручной ретро-загрузкой через params",
    tags=["demo", "retro", "params"],
) as dag:

    @task
    def resolve_period(**context) -> dict[str, str]:
        params = context["params"]
        ds = context["ds"]

        start_date = params.get("start_date") or ds
        end_date = params.get("end_date") or start_date

        if end_date < start_date:
            raise ValueError("end_date не может быть меньше start_date")

        return {
            "start_date": start_date,
            "end_date": end_date,
        }

    @task
    def load_data(period: dict[str, str]) -> None:
        print(f"Грузим данные с {period['start_date']} по {period['end_date']}")

        # Здесь может быть:
        # - запрос к API
        # - чтение из Postgres
        # - Spark job
        # - загрузка в S3
        # - запись в ClickHouse
        # - пересчёт витрины

    period = resolve_period()
    load_data(period)
```

---

# 5. Как это выглядит в Airflow UI

Сценарий:

1. Открыть нужный DAG.
2. Нажать кнопку ручного запуска.
3. Airflow покажет форму параметров.
4. Ввести `start_date` и `end_date`.
5. Запустить DAG.

Пример значений:

```text
start_date: 2026-01-10
end_date: 2026-04-02
```

Если оставить поля пустыми:

```text
start_date:
end_date:
```

DAG может использовать стандартную дату запуска `ds`.

---

# 6. `ds`, `logical_date` и параметры

В Airflow часто используется переменная `ds`.

`ds` — это дата логического запуска DAG в формате:

```text
YYYY-MM-DD
```

Например:

```text
2026-07-11
```

Обычный daily-DAG может работать так:

```text
DAG запущен за 2026-07-11 → грузим данные за 2026-07-11
```

Но с параметрами можно сделать универсальную логику:

```python
start_date = params.get("start_date") or context["ds"]
end_date = params.get("end_date") or start_date
```

Тогда:

| Сценарий | Что произойдёт |
|---|---|
| scheduled run, параметры пустые | загрузится `ds` |
| manual run, указан `start_date` | загрузится выбранная дата |
| manual run, указан диапазон | загрузится период `start_date` — `end_date` |

---

# 7. Пример с режимом загрузки

Можно добавить параметр режима:

```python
params={
    "mode": Param(
        "incremental",
        type="string",
        enum=["incremental", "retro", "full"],
        description="Режим загрузки",
    ),
}
```

В UI можно будет выбрать один из вариантов:

```text
incremental
retro
full
```

Использование:

```python
@task
def run_pipeline(**context) -> None:
    mode = context["params"]["mode"]

    match mode:
        case "incremental":
            print("Обычная инкрементальная загрузка")
        case "retro":
            print("Ретро-загрузка за выбранный период")
        case "full":
            print("Полная перезагрузка")
        case _:
            raise ValueError(f"Неизвестный mode: {mode}")
```

---

# 8. Пример с флагом `force_reload`

```python
params={
    "force_reload": Param(
        False,
        type="boolean",
        description="Принудительно перезаписать данные за период",
    ),
}
```

Использование:

```python
@task
def load_data(**context) -> None:
    force_reload = context["params"]["force_reload"]

    if force_reload:
        print("Сначала удаляем старые данные за период")
    else:
        print("Обычная загрузка без удаления")
```

---

# 9. Пример с ограничением количества дней

Если не хочется, чтобы пользователь случайно запустил пересчёт за 5 лет, можно добавить ограничение.

```python
from datetime import date


MAX_DAYS = 31


@task
def validate_period(**context) -> dict[str, str]:
    params = context["params"]
    ds = context["ds"]

    start = date.fromisoformat(params.get("start_date") or ds)
    end = date.fromisoformat(params.get("end_date") or start.isoformat())

    days_count = (end - start).days + 1

    if days_count > MAX_DAYS:
        raise ValueError(
            f"Период слишком большой: {days_count} дней. Максимум: {MAX_DAYS}"
        )

    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
```

Такой guard полезен на production.

---

# 10. Доступ к `params` в разных местах

## Через context в Python-задаче

```python
@task
def my_task(**context):
    start_date = context["params"]["start_date"]
```

## Через `get_current_context`

```python
from airflow.decorators import get_current_context, task


@task
def my_task():
    context = get_current_context()
    start_date = context["params"]["start_date"]
```

## Через Jinja template

```python
bash_command = "echo {{ params.start_date }}"
```

## В SQL

```sql
DELETE FROM mart.sales
WHERE dt BETWEEN '{{ params.start_date }}' AND '{{ params.end_date }}';
```

---

# 11. `params` и `dag_run.conf`

Исторически для ручных запусков часто использовали `dag_run.conf`.

Пример JSON при ручном запуске:

```json
{
  "start_date": "2026-01-10",
  "end_date": "2026-04-02"
}
```

И внутри задачи:

```python
conf = context["dag_run"].conf or {}
start_date = conf.get("start_date")
```

Но `params` удобнее для пользователей:

- появляется UI-форма;
- можно добавить типы;
- можно добавить описание;
- можно добавить валидацию;
- меньше риска ошибиться в JSON.

На практике для ручного запуска бизнес-параметров лучше использовать `params`.

---

# 12. Пример полного пайплайна с перезаписью периода

```python
from __future__ import annotations

from datetime import date, datetime

from airflow import DAG
from airflow.decorators import task
from airflow.models.param import Param


MAX_DAYS = 31


with DAG(
    dag_id="DEMO__sales_retro_reload",
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 10 * * *",
    catchup=False,
    params={
        "start_date": Param(
            "",
            type="string",
            pattern=r"^$|^\d{4}-\d{2}-\d{2}$",
            description="Начальная дата. Пусто = ds.",
        ),
        "end_date": Param(
            "",
            type="string",
            pattern=r"^$|^\d{4}-\d{2}-\d{2}$",
            description="Конечная дата. Пусто = start_date.",
        ),
        "force_reload": Param(
            False,
            type="boolean",
            description="Удалить старые данные за период перед загрузкой",
        ),
    },
    tags=["demo", "sales", "retro"],
) as dag:

    @task
    def resolve_and_validate_period(**context) -> dict[str, str | bool]:
        params = context["params"]
        ds = context["ds"]

        start = date.fromisoformat(params.get("start_date") or ds)
        end = date.fromisoformat(params.get("end_date") or start.isoformat())

        if end < start:
            raise ValueError("end_date не может быть меньше start_date")

        days_count = (end - start).days + 1

        if days_count > MAX_DAYS:
            raise ValueError(f"Период слишком большой: {days_count} дней")

        return {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "force_reload": params["force_reload"],
        }

    @task
    def clear_target_period(period: dict[str, str | bool]) -> None:
        if not period["force_reload"]:
            print("force_reload=False, очистка периода пропущена")
            return

        print(
            "Удаляем старые данные за период: "
            f"{period['start_date']} — {period['end_date']}"
        )

        # DELETE FROM target_table
        # WHERE business_date BETWEEN start_date AND end_date

    @task
    def load_target_period(period: dict[str, str | bool]) -> None:
        print(
            "Загружаем данные за период: "
            f"{period['start_date']} — {period['end_date']}"
        )

        # INSERT INTO target_table
        # SELECT ...
        # WHERE business_date BETWEEN start_date AND end_date

    period = resolve_and_validate_period()
    clear_target_period(period)
    load_target_period(period)
```

---

# 13. Production-чеклист

Перед тем как давать аналитикам ручной запуск с параметрами:

- [ ] есть валидация формата дат;
- [ ] есть проверка `end_date >= start_date`;
- [ ] есть ограничение максимального периода;
- [ ] загрузка идемпотентная;
- [ ] нет дублей при повторном запуске;
- [ ] есть логи параметров запуска;
- [ ] есть понятное описание параметров в UI;
- [ ] есть права доступа на запуск DAG;
- [ ] опасные режимы защищены флагом или отдельным DAG;
- [ ] при ошибке понятно, что именно пошло не так.

---

# 14. Мини-шпаргалка

## Импорт

```python
from airflow.models.param import Param
```

## Параметр-строка с датой

```python
"start_date": Param(
    "",
    type="string",
    pattern=r"^$|^\d{4}-\d{2}-\d{2}$",
    description="Дата начала в формате YYYY-MM-DD. Пусто = ds.",
)
```

## Параметр-boolean

```python
"force_reload": Param(
    False,
    type="boolean",
    description="Перезаписать данные за период",
)
```

## Параметр с выбором

```python
"mode": Param(
    "incremental",
    type="string",
    enum=["incremental", "retro", "full"],
    description="Режим загрузки",
)
```

## Получить параметры в задаче

```python
@task
def my_task(**context):
    params = context["params"]
    start_date = params["start_date"]
```

## Получить параметры через `get_current_context`

```python
from airflow.decorators import get_current_context


context = get_current_context()
params = context["params"]
```

## Использовать дефолт `ds`

```python
start_date = params.get("start_date") or context["ds"]
end_date = params.get("end_date") or start_date
```
