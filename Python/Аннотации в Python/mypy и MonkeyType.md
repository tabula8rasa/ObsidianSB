Да — этот конспект уже хороший, но его полезно **чуть расширить в практическую сторону**: что именно дают инструменты, где их ограничения и как их лучше использовать вместе. Ниже — более полный и “рабочий” вариант. ([mypy.readthedocs.io](https://mypy.readthedocs.io/en/stable/config_file.html?utm_source=chatgpt.com "The mypy configuration file - mypy 1.19.1 documentation"))

# Проверка и автогенерация аннотаций типов: `mypy` и `MonkeyType`

После изучения синтаксиса аннотаций типов следующий шаг — освоить инструменты, которые помогают:

- **проверять** корректность аннотаций,
- **внедрять** аннотации в существующий код,
- **поддерживать** типизацию в проекте на постоянной основе. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))

Для этого чаще всего используют два инструмента:

- **mypy** — статический анализатор типов,
- **MonkeyType** — генератор аннотаций на основе реального выполнения программы. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))

---

## 1. `mypy`: статическая проверка типов

**mypy** — это статический type checker для Python. Он анализирует код **без запуска программы** и проверяет, согласуются ли аннотации типов с реальным использованием переменных, функций, методов и модулей. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))

### Что делает `mypy`

Если функция ожидает `int`, а ей передают `str`, `mypy` сообщит об ошибке ещё до выполнения кода. Это особенно полезно для:

- крупных проектов,
- библиотек,
- рефакторинга,    
- CI/CD-проверок перед merge. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))

### Базовый запуск

```bash
mypy your_file.py
mypy your_package/
```

`mypy` умеет проверять как отдельные файлы, так и целые директории и модули. Полный набор флагов смотрится через `mypy --help`, а документация отдельно подчёркивает, что CLI-флаги могут меняться между релизами. ([mypy.readthedocs.io](https://mypy.readthedocs.io/en/latest/command_line.html?utm_source=chatgpt.com "The mypy command line - MyPy Documentation - Read the Docs"))

### Почему `mypy` важен

Его главная ценность в том, что он ищет ошибки **до запуска**:

- несовместимые аргументы,
- неправильные возвращаемые значения,
- ошибки в наследовании,
- нарушения контрактов протоколов и overload-сигнатур. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))

---

## 2. Конфигурация `mypy`

В современных проектах настройки обычно кладут в `pyproject.toml` в секцию `[tool.mypy]`. Документация `mypy` также поддерживает отдельные конфиги и описывает порядок их поиска. ([mypy.readthedocs.io](https://mypy.readthedocs.io/en/stable/config_file.html?utm_source=chatgpt.com "The mypy configuration file - mypy 1.19.1 documentation"))

### Полезный минимальный конфиг

```toml
[tool.mypy]
python_version = "3.12"
disallow_untyped_defs = true
check_untyped_defs = true
```

### Что означают эти настройки

- `python_version` — сообщает `mypy`, под какую версию Python проверять синтаксис и правила типизации. Это особенно важно, если используются конструкции Python 3.12+, например новый синтаксис дженериков. ([mypy.readthedocs.io](https://mypy.readthedocs.io/en/stable/config_file.html?utm_source=chatgpt.com "The mypy configuration file - mypy 1.19.1 documentation"))
    
- `disallow_untyped_defs = true` — запрещает оставлять функции без аннотаций. Это хороший способ постепенно дисциплинировать проект. ([mypy.readthedocs.io](https://mypy.readthedocs.io/en/stable/config_file.html?utm_source=chatgpt.com "The mypy configuration file - mypy 1.19.1 documentation"))
    
- `check_untyped_defs = true` — заставляет `mypy` проверять даже тела неаннотированных функций, что позволяет находить часть ошибок даже в ещё не полностью типизированном коде. В релизных заметках отдельно упоминается поведение `--check-untyped-defs`. ([mypy.readthedocs.io](https://mypy.readthedocs.io/en/stable/config_file.html?utm_source=chatgpt.com "The mypy configuration file - mypy 1.19.1 documentation"))
    

### Практический совет

Для нового проекта часто разумно начать с:

- включить `check_untyped_defs = true`,
- потом добавить `disallow_untyped_defs = true`,
- и уже после этого постепенно ужесточать правила.

Такой путь обычно проще, чем сразу включать максимально строгий режим на старом коде.

---

## 3. Где `mypy` особенно полезен

`mypy` лучше всего работает там, где аннотации уже есть или внедряются системно:

- в новых проектах,
- в публичных API,
- в коде с дженериками, `Protocol`, `TypedDict`, `overload`,
- в CI/CD. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))

### Практика для CI

Хорошая практика — запускать `mypy` в CI на каждый pull request. Тогда в основную ветку попадает код, который хотя бы базово проходит проверку типов.

### Дополнительно

У `mypy` есть и сопутствующие инструменты и режимы, например документация отдельно упоминает:

- daemon / mypy server,
- automatic stub generation (`stubgen`),
- automatic stub testing (`stubtest`). ([mypy.readthedocs.io](https://mypy.readthedocs.io/en/latest/faq.html?utm_source=chatgpt.com "Frequently Asked Questions - mypy 1.20.0+dev ..."))

Это уже следующий уровень, но полезно знать, что экосистема у `mypy` шире, чем просто команда `mypy file.py`.

---

## 4. `MonkeyType`: динамическая генерация аннотаций

**MonkeyType** работает иначе: он не пытается логически доказать корректность типов, а **наблюдает за реальным выполнением программы** и запоминает, какие типы аргументов и результатов действительно встречались. По умолчанию он складывает call traces в SQLite-базу `monkeytype.sqlite3` в текущей директории. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))

### Установка и требования

На PyPI указано, что MonkeyType требует Python 3.7+ и библиотеку `libcst` для применения stub’ов к исходным файлам. Он генерирует именно Python type annotations, а не type comments. ([PyPI](https://pypi.org/project/MonkeyType/?utm_source=chatgpt.com "MonkeyType"))

### Базовый сценарий работы

1. **Запуск под MonkeyType**
    
    ```bash
    monkeytype run main.py
    ```
    
    Это запускает программу и записывает наблюдённые типы. По умолчанию трассы попадут в `monkeytype.sqlite3`. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))
    
2. **Просмотр предложенных аннотаций**
    
    ```bash
    monkeytype stub some.module
    ```
    
    Команда выводит stub-предложения на основе накопленных вызовов. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))
    
3. **Применение аннотаций к коду**
    
    ```bash
    monkeytype apply some.module
    ```
    
    Эта команда модифицирует исходный `.py` файл, подставляя найденные аннотации. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))
    

---

## 5. Где `MonkeyType` особенно полезен

MonkeyType особенно полезен для **legacy-кода**, где:

- функций много,
- аннотаций почти нет,
- вручную типизировать всё долго,
- но есть рабочие тесты или сценарии запуска. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))

### В чём его сила

Он быстро даёт “черновик” аннотаций. Это удобно, если надо:

- стартовать типизацию существующего проекта,
- типизировать внутренние сервисы,
- быстро получить основу для последующей ручной доработки.

### Главное ограничение

MonkeyType видит **только те типы, которые реально прошли через код во время запуска**. Если какая-то ветка не была выполнена, он её не узнает. Это прямо следует из его принципа работы: инструмент пишет call traces на основе наблюдаемых вызовов runtime. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))

Из этого следует важный вывод:

> качество аннотаций MonkeyType зависит от качества покрытия тестами или сценариями запуска.

Если запуск был узким, аннотации могут получиться слишком оптимистичными или неполными.

---

## 6. `mypy` и `MonkeyType` — не конкуренты, а связка

Их лучше воспринимать как инструменты для **разных этапов**:

### `MonkeyType`

Нужен, чтобы **быстро сгенерировать стартовые аннотации** в старом проекте. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))

### `mypy`

Нужен, чтобы **проверить и поддерживать корректность типов дальше**. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))

Идеальный рабочий цикл часто выглядит так:

1. Прогоняешь тесты/скрипты через `monkeytype run`.
2. Смотришь `monkeytype stub`.
3. При необходимости применяешь `monkeytype apply`.
4. После этого запускаешь `mypy` и исправляешь неточности.

Это хороший компромисс между скоростью внедрения и качеством результата.

---

## 7. Сравнение инструментов

### `mypy`

- анализирует код **без выполнения**,
- ищет логические ошибки типов,
- подходит для ежедневной проверки и CI,
- лучше для новых и уже типизированных проектов. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))

### `MonkeyType`

- работает **во время выполнения**,
- собирает наблюдённые типы,
- помогает быстро добавить аннотации в старый код,
- зависит от того, какие ветки реально были запущены. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))

---

## 8. Практический совет по внедрению

Если проект **новый**:

- сразу пиши аннотации,
- подключай `mypy`,
- включай проверку в CI. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))

Если проект **старый**:

- сначала собери типы через MonkeyType,
- потом руками отшлифуй спорные места,
- и закрепи результат через `mypy`. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))

Если проект **большой**:

- типизируй постепенно,
- начинай с публичных API, utility-модулей и критичных сервисов,
- не пытайся “сделать всё идеально за один проход”.

---

## 9. Финальный вывод

`mypy` и `MonkeyType` решают разные, но очень хорошо сочетающиеся задачи:

- **mypy** делает типизацию рабочим механизмом контроля качества кода, а не просто набором подсказок. ([mypy.readthedocs.io](https://mypy.readthedocs.io/?utm_source=chatgpt.com "mypy 1.19.1 documentation"))
- **MonkeyType** помогает быстро войти в типизацию там, где её раньше не было. ([monkeytype.readthedocs.io](https://monkeytype.readthedocs.io/?utm_source=chatgpt.com "MonkeyType — MonkeyType 23.3.0 documentation"))

Лучший подход обычно такой:

> **генерировать аннотации можно автоматически,  
> но доверять им окончательно стоит только после проверки `mypy`.**

Если хочешь, я могу следующим сообщением сделать тебе ещё и **короткую шпаргалку-команды** по `mypy` и `MonkeyType` в формате “установить → настроить → проверить”.