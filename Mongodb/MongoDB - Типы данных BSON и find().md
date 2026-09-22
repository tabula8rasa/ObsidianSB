---
tags: [mongodb, nosql, bson, datatypes, find, databases]
created: 2026-09-22
---

# MongoDB: типы данных BSON, сценарии вложенности, продвинутый find()

Связанные заметки: [[MongoDB - Архитектура и CRUD]] · [[MongoDB - Практика Шардирование и Репликация]]

Цель заметки — референс по всем BSON-типам, типовым паттернам вложенности документов и малоизвестным (но полезным) возможностям `find()` и связанных курсорных методов.

---

## 1. Эталонный документ со всеми типами и сценариями вложенности

```js
{
  "_id": ObjectId("64a1b2c3d4e5f6a7b8c9d0e1"),

  "types": {
    "stringField": "Строковое значение (UTF-8)",
    "int32Field": 42,
    "int64Field": NumberLong("9223372036854775807"),
    "doubleField": 3.14159,
    "decimalField": NumberDecimal("199.99"),
    "booleanField": true,
    "nullField": null,
    "dateField": ISODate("2026-06-06T12:00:00.000Z"),
    "timestampField": Timestamp(1717675200, 1),
    "regexField": /^mongodb/i,
    "binaryField": BinData(0, "SGVsbG8gV29ybGQ="),
    "uuidField": BinData(4, "c7GJ8f3qQdWz2u6zvOwzdQ=="),
    "objectIdField": ObjectId("64a1b2c3d4e5f6a7b8c9d0e2"),
    "codeField": function() { return this.int32Field * 2; },
    "codeWithScopeField": {
      "$code": "function() { return multiplier * this.int32Field; }",
      "$scope": { "multiplier": 10 }
    },
    "symbolField": Symbol("legacySymbol"),
    "dbPointerField": DBPointer("otherCollection", ObjectId("64a1b2c3d4e5f6a7b8c9d0e3")),
    "minKeyField": MinKey(),
    "maxKeyField": MaxKey(),
    "undefinedField": undefined
  },

  "arrays": {
    "homogeneousArray": ["apple", "banana", "orange"],
    "heterogeneousArray": [42, "text", true, null, { "key": "value" }],
    "arrayOfDocuments": [
      { "tagId": 1, "name": "backend" },
      { "tagId": 2, "name": "database" }
    ],
    "nestedArrays": [
      [1, 2],
      [3, 4]
    ],
    "setLikeArray": ["read", "write", "delete"],
    "arrayOfObjectIds": [
      ObjectId("64a1b2c3d4e5f6a7b8c9d0e4"),
      ObjectId("64a1b2c3d4e5f6a7b8c9d0e5")
    ],
    "mixedNestedArrayOfDocs": [
      [ { "step": 1, "status": "done" } ],
      [ { "step": 2, "status": "pending" }, { "step": 3, "status": "blocked" } ]
    ]
  },

  "nesting": {
    "level1": {
      "name": "Первый уровень вложенности",
      "level2": {
        "name": "Второй уровень вложенности",
        "level3": {
          "name": "Глубокая вложенность (до 100 уровней)",
          "metadata": {
            "createdBy": "admin",
            "version": 1.1
          }
        }
      }
    }
  },

  "dynamicDictionary": {
    "en": "Hello",
    "ru": "Привет",
    "de": "Hallo"
  },

  "polymorphicItems": [
    { "kind": "text", "content": "Заметка" },
    { "kind": "image", "url": "https://example.com/a.png", "width": 800, "height": 600 },
    { "kind": "link", "url": "https://example.com", "title": "Пример" }
  ],

  "selfReference": {
    "parentId": ObjectId("64a1b2c3d4e5f6a7b8c9d0e6")
  },

  "geo": {
    "location": {
      "type": "Point",
      "coordinates": [37.6176, 55.7558]
    },
    "area": {
      "type": "Polygon",
      "coordinates": [[
        [37.60, 55.75], [37.63, 55.75], [37.63, 55.77], [37.60, 55.77], [37.60, 55.75]
      ]]
    }
  }
}
```

---

## 2. Описание типов данных

| Поле | BSON-тип | Код `$type` | Описание |
|---|---|---|---|
| `stringField` | String | `"string"` / 2 | UTF-8 строка |
| `int32Field` | Int32 | `"int"` / 16 | 32-битное целое |
| `int64Field` | Int64 (`NumberLong`) | `"long"` / 18 | 64-битное целое, нужен для больших счётчиков |
| `doubleField` | Double | `"double"` / 1 | 64-битное число с плавающей точкой (неточная арифметика) |
| `decimalField` | Decimal128 (`NumberDecimal`) | `"decimal"` / 19 | Точная десятичная арифметика, для денег |
| `booleanField` | Boolean | `"bool"` / 8 | true/false |
| `nullField` | Null | `"null"` / 10 | Явное отсутствие значения (отличается от отсутствия поля) |
| `dateField` | Date (`ISODate`) | `"date"` / 9 | Миллисекунды с эпохи Unix |
| `timestampField` | Timestamp | `"timestamp"` / 17 | Внутренний служебный тип (используется в oplog), НЕ для бизнес-дат |
| `regexField` | Regular Expression | `"regex"` / 11 | Хранимое регулярное выражение |
| `binaryField` | BinData subtype 0 | `"binData"` / 5 | Произвольные бинарные данные |
| `uuidField` | BinData subtype 4 | `"binData"` / 5 | UUID в бинарном виде |
| `objectIdField` | ObjectId | `"objectId"` / 7 | 12-байтовый уникальный идентификатор (timestamp+machine+counter) |
| `codeField` | JavaScript | `"javascript"` / 13 | Код без области видимости (используется редко, устаревающий паттерн) |
| `codeWithScopeField` | JavaScript with scope | `"javascriptWithScope"` / 15 | Код + захваченные переменные (deprecated с MongoDB 4.4) |
| `symbolField` | Symbol | `"symbol"` / 14 | Устаревший тип, наследие драйверов других языков |
| `dbPointerField` | DBPointer | `"dbPointer"` / 12 | Устаревшая ссылка на документ другой коллекции, замена — ручное поле-ссылка |
| `minKeyField` | MinKey | `"minKey"` / -1 | Служебное значение, всегда меньше любого другого при сравнении |
| `maxKeyField` | MaxKey | `"maxKey"` / 127 | Служебное значение, всегда больше любого другого |
| `undefinedField` | Undefined | `"undefined"` / 6 | Устаревший тип, использовать `null` вместо него |
| `homogeneousArray` | Array | `"array"` / 4 | Массив одного типа значений |
| `heterogeneousArray` | Array | `"array"` / 4 | Массив разнотипных значений — допустимо в BSON |
| `arrayOfDocuments` | Array of Object | — | Классический паттерн "один-ко-многим" через embedding |
| `dynamicDictionary` | Object (как map) | `"object"` / 3 | Документ, используемый как словарь с непредсказуемыми ключами |
| `polymorphicItems` | Array of Object с discriminator | — | Паттерн полиморфной коллекции: поле `kind` определяет остальную форму документа |
| `geo.location` / `geo.area` | GeoJSON Point / Polygon | — | Требует индекс `2dsphere` для гео-запросов |

---

## 3. Сценарии вложенности — сводка паттернов

- **Простая вложенность (embedding)** — `nesting.level1.level2.level3` — глубина вплоть до 100 уровней, доступ через dot notation.
- **Массив документов** — `arrays.arrayOfDocuments` — связь "один-ко-многим" без отдельной коллекции.
- **Массив массивов** — `arrays.nestedArrays`, `arrays.mixedNestedArrayOfDocs` — матрицы/группировки шагов.
- **Словарь с динамическими ключами** — `dynamicDictionary` — ключи не известны заранее (локали, feature-флаги), требует `$objectToArray` для запросов по значениям, а не по конкретному ключу.
- **Полиморфный массив (discriminator pattern)** — `polymorphicItems` — элементы с разной формой, различаются по полю `kind`.
- **Самоссылка** — `selfReference.parentId` — паттерн для деревьев/иерархий (категории, комментарии).
- **GeoJSON** — `geo.location`, `geo.area` — точки и полигоны для геозапросов.

---

## 4. Продвинутые find-запросы к этому документу

```js
// 1. Поиск по типу поля через $type (по строковому алиасу и числовому коду)
db.demo.find({ "types.decimalField": { $type: "decimal" } })
db.demo.find({ "types.int64Field": { $type: 18 } })

// 2. Проверка существования поля / явного null
db.demo.find({ "types.nullField": { $exists: true, $eq: null } })
db.demo.find({ "types.undefinedField": { $exists: false } })

// 3. Регулярное выражение по имени (без сохранённого regex-поля)
db.demo.find({ "types.stringField": { $regex: /^строков/i } })

// 4. $elemMatch — документ массива, удовлетворяющий нескольким условиям сразу
db.demo.find({
  "arrays.arrayOfDocuments": { $elemMatch: { tagId: { $gte: 1 }, name: "database" } }
})

// 5. $all — массив содержит все перечисленные элементы (в любом порядке)
db.demo.find({ "arrays.setLikeArray": { $all: ["read", "write"] } })

// 6. $size — точная длина массива
db.demo.find({ "arrays.homogeneousArray": { $size: 3 } })

// 7. $in / $nin по массиву ObjectId-ссылок
db.demo.find({
  "arrays.arrayOfObjectIds": { $in: [ObjectId("64a1b2c3d4e5f6a7b8c9d0e4")] }
})

// 8. Точечная нотация в глубокую вложенность + $gt по вложенному числовому полю
db.demo.find({ "nesting.level1.level2.level3.metadata.version": { $gt: 1.0 } })

// 9. $expr — сравнение двух полей одного документа между собой
db.demo.find({
  $expr: { $gt: ["$types.int32Field", { $toInt: "$nesting.level1.level2.level3.metadata.version" }] }
})

// 10. Полиморфный массив: документ, где ЕСТЬ элемент с kind="image" и width больше 500
db.demo.find({
  "polymorphicItems": { $elemMatch: { kind: "image", width: { $gt: 500 } } }
})

// 11. $geoWithin по полигону (нужен индекс 2dsphere на geo.location)
db.demo.find({
  "geo.location": {
    $geoWithin: { $geometry: { type: "Polygon", coordinates: [[[37.5,55.7],[37.7,55.7],[37.7,55.8],[37.5,55.8],[37.5,55.7]]] } }
  }
})

// 12. $near — ближайшие точки к заданным координатам в пределах радиуса (метры)
db.demo.find({
  "geo.location": { $near: { $geometry: { type: "Point", coordinates: [37.6176, 55.7558] }, $maxDistance: 5000 } }
})

// 13. Проекция: часть полей + позиционный оператор $ (первый совпавший элемент массива)
db.demo.find(
  { "arrays.arrayOfDocuments.tagId": 2 },
  { "arrays.arrayOfDocuments.$": 1, "types.stringField": 1 }
)

// 14. Проекция $slice — только последние 2 элемента массива
db.demo.find({}, { "arrays.mixedNestedArrayOfDocs": { $slice: -2 } })

// 15. $elemMatch в проекции — вернуть только подходящий элемент массива, а не весь массив
db.demo.find(
  {},
  { polymorphicItems: { $elemMatch: { kind: "link" } } }
)

// 16. Сортировка + skip + limit — постраничная выборка
db.demo.find({}).sort({ "types.dateField": -1 }).skip(10).limit(5)

// 17. hint — принудительное указание индекса для плана выполнения
db.demo.find({ "types.objectIdField": ObjectId("64a1b2c3d4e5f6a7b8c9d0e2") }).hint({ "types.objectIdField": 1 })

// 18. min/max — ограничение диапазона сканирования индекса (требует createIndex и hint на тот же индекс)
db.demo.find({}).min({ "types.dateField": ISODate("2026-01-01") })
              .max({ "types.dateField": ISODate("2026-12-31") })
              .hint({ "types.dateField": 1 })

// 19. collation — регистронезависимое/локале-зависимое сравнение строк
db.demo.find({ "types.stringField": "СТРОКОВОЕ ЗНАЧЕНИЕ (UTF-8)" })
       .collation({ locale: "ru", strength: 2 })

// 20. comment + maxTimeMS — маркировка запроса для профайлера и таймаут выполнения
db.demo.find({ "types.int32Field": { $gte: 0 } })
       .comment("dashboard: overview query")
       .maxTimeMS(2000)

// 21. Курсор вручную: batchSize + итерация без toArray()
const cursor = db.demo.find({}).batchSize(50)
while (cursor.hasNext()) {
  printjson(cursor.next())
}

// 22. MinKey/MaxKey в запросе — типовой паттерн проверки границ (например, в шардированных коллекциях)
db.demo.find({ "types.minKeyField": { $type: "minKey" } })

// 23. $mod — остаток от деления (например, чётные значения int32Field)
db.demo.find({ "types.int32Field": { $mod: [2, 0] } })

// 24. distinct — уникальные значения поля во всей коллекции
db.demo.distinct("polymorphicItems.kind")

// 25. countDocuments — количество документов под фильтр (с учётом limit/skip)
db.demo.countDocuments({ "arrays.arrayOfDocuments.name": "backend" }, { limit: 100 })

// 26. readConcern — уровень согласованности чтения прямо в запросе
db.demo.find({}).readConcern("majority")
```

---

## 5. Заметки по использованию редких типов

- `codeField`, `codeWithScopeField`, `symbolField`, `dbPointerField`, `undefinedField` — практически не используются в новых проектах, оставлены в BSON-спецификации для обратной совместимости. При проектировании новой схемы их стоит избегать.
- `Timestamp` — не путать с `Date`. `Timestamp` используется MongoDB внутренне (`oplog`, change streams); для бизнес-логики всегда `ISODate`.
- `MinKey`/`MaxKey` — полезны как искусственные "граничные" значения при построении диапазонных запросов или как sentinel-значения в шардированных коллекциях.
- `BinData(4, ...)` — стандартный способ хранить UUID компактно (16 байт вместо строки из 36 символов).

---

## См. также
- [[MongoDB - Архитектура и CRUD]]
- [[MongoDB - Практика Шардирование и Репликация]]
