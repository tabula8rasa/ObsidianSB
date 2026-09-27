---
tags: [mongodb, database, nosql]
created: 2026-09-27
---
# ObjectId в MongoDB

## Что это

`ObjectId` — уникальный идентификатор документа в MongoDB, используемый по умолчанию как значение поля `_id`. Если при вставке документа поле `_id` не указано явно, MongoDB сгенерирует его автоматически.

Тип данных: `ObjectId` (BSON-тип).

## Структура (12 байт)

ObjectId состоит из 12 байт (24 hex-символа в строковом представлении):

| Байты | Компонент | Описание |
|---|---|---|
| 0–3 | Timestamp | Unix-время создания (секунды), 4 байта |
| 4–8 | Random value | Случайное значение, уникальное для машины+процесса, 5 байт |
| 9–11 | Counter | Инкрементный счётчик, стартует со случайного значения, 3 байта |

> В старых версиях MongoDB (до 3.4) структура была другой: machine identifier (3 байта) + process id (2 байта) + counter (3 байта). Текущая схема (timestamp + random + counter) используется начиная с MongoDB 3.4+/драйверов новых версий.

### Пример

```
507f1f77bcf86cd799439011
└──────┘└────────┘└────┘
timestamp  random  counter
(4 байта) (5 байт) (3 байта)
```

## Ключевые свойства

- **Уникальность** — гарантируется без необходимости обращения к серверу для генерации (генерируется на клиенте/драйвере).
- **Сортируемость по времени** — так как первые 4 байта это timestamp, ObjectId монотонно возрастают примерно в порядке создания (с точностью до секунды).
- **Компактность** — 12 байт против, например, UUID (16 байт).
- **Не требует автоинкремента на сервере** — в отличие от SQL SERIAL/AUTO_INCREMENT, генерируется независимо, что удобно для распределённых систем.

## Извлечение timestamp из ObjectId

Так как первые 4 байта — это время создания, можно достать дату документа без отдельного поля `createdAt`:

**MongoDB Shell:**
```js
ObjectId("507f1f77bcf86cd799439011").getTimestamp()
// ISODate("2012-10-17T20:46:23Z")
```

**Node.js (driver):**
```js
const { ObjectId } = require('mongodb');
const id = new ObjectId("507f1f77bcf86cd799439011");
console.log(id.getTimestamp());
```

**Python (pymongo):**
```python
from bson import ObjectId
oid = ObjectId("507f1f77bcf86cd799439011")
print(oid.generation_time)
```

## Создание ObjectId

```js
// Автоматически (mongosh)
db.collection.insertOne({ name: "test" }) // _id создастся сам

// Явно
new ObjectId()
new ObjectId("507f1f77bcf86cd799439011") // из строки
```

## Запросы по ObjectId

```js
db.collection.find({ _id: ObjectId("507f1f77bcf86cd799439011") })
```

⚠️ Частая ошибка: искать по строке напрямую —
```js
db.collection.find({ _id: "507f1f77bcf86cd799439011" }) // НЕ сработает!
```
Строка и ObjectId — разные типы, сравнение не совпадёт. Нужно явно оборачивать в `ObjectId(...)`.

## Сортировка по дате создания через _id

Если нет отдельного поля с датой, можно сортировать по `_id`, так как он содержит timestamp:

```js
db.collection.find().sort({ _id: -1 }) // последние созданные первыми
```

## Использование в разных языках

| Драйвер | Класс/тип |
|---|---|
| Node.js | `ObjectId` из `mongodb` или `mongoose.Types.ObjectId` |
| Python | `bson.ObjectId` (pymongo) |
| Java | `org.bson.types.ObjectId` |
| C# | `MongoDB.Bson.ObjectId` |
| Go | `go.mongodb.org/mongo-driver/bson/primitive.ObjectId` |

## Валидация ObjectId (важно при приёме данных из API)

Перед конвертацией строки в ObjectId стоит проверять валидность, иначе будет exception:

```js
const { ObjectId } = require('mongodb');

if (ObjectId.isValid(someString)) {
  const id = new ObjectId(someString);
}
```

⚠️ Нюанс: `ObjectId.isValid()` в некоторых версиях драйвера возвращает `true` для любой 12-символьной строки (не только hex), так как она тоже может быть преобразована в байты. Для строгой проверки 24-символьного hex лучше дополнительно проверять регуляркой:

```js
/^[0-9a-fA-F]{24}$/.test(someString)
```

## ObjectId vs UUID

| | ObjectId | UUID (v4) |
|---|---|---|
| Размер | 12 байт | 16 байт |
| Содержит timestamp | Да (секунды) | Нет (v4), Да (v1, v7) |
| Специфичен для MongoDB | Да | Нет, универсален |
| Сортируемость по времени | Да | Зависит от версии |
| Генерация | На клиенте/драйвере | На клиенте |

## Частые вопросы / заметки

- ObjectId **не криптографически безопасен** — не использовать как токен доступа или secret.
- Точность timestamp — только до секунды, поэтому документы, созданные в одну секунду, различаются только random+counter частью, но порядок между ними не строго гарантирован по миллисекундам.
- Можно принудительно задать свой `_id` (например, строку или число) — MongoDB это разрешает, но тогда теряются приведённые выше преимущества (timestamp, сортировка).
- Индекс на `_id` создаётся автоматически и всегда уникален.

## Полезные ссылки

- [MongoDB Docs — ObjectId](https://www.mongodb.com/docs/manual/reference/method/ObjectId/)
- [BSON spec](https://bsonspec.org/spec.html)

---
#mongodb #nosql #database
