---
title: "S3 и RustFS — Уроки 04–06. Объекты, ключи и метаданные"
aliases: ["S3: уроки 4–6", "S3: урок 4", "S3: урок 5", "S3: урок 6"]
tags: [s3, rustfs, object-storage, course]
lessons: [4, 5, 6]
module: 1
status: study
---

# Уроки 04–06. Объекты, ключи, метаданные

**Цель:** освоить операции с объектами, организацию ключей, перечисление и управление атрибутами. В практике используется бакет `s3-course-lesson1` и функция `s3` из урока 02.

## 04. Objects: PUT, GET, HEAD, DELETE

### Контракт S3 API

| Операция | HTTP | Результат |
|---|---|---|
| `PutObject` | PUT | Записывает тело и метаданные под ключом |
| `GetObject` | GET | Возвращает байты и заголовки |
| `HeadObject` | HEAD | Возвращает метаданные без тела |
| `DeleteObject` | DELETE | Удаляет объект или создаёт `delete marker` при versioning |

**Object** состоит из тела (**body**, произвольные байты) и **metadata**. Клиент сам назначает ключ; он не обязан совпадать с именем исходного файла. S3 не обязан определять формат содержимого.

### Архитектура и семантика

```text
Клиент → S3 API → аутентификация и проверка прав
                 → поиск bucket + key → данные/метаданные → ответ
```

- **PUT:** без versioning заменяет объект по ключу, с versioning создаёт новую версию. Это запись всего содержимого, а не изменение байтов по смещению.
- **GET / HEAD:** чтение тела / только атрибутов объекта.
- **DELETE:** без versioning удаляет объект; с включённым versioning добавляет `delete marker`, сохраняя прежние версии. `versionId` позволяет адресовать конкретную версию.
- API не раскрывает физическое расположение данных или момент освобождения диска. Конкурентные записи по одному ключу требуют контроля со стороны приложения.

### Практика

```fish
printf 'Object storage lesson 04\n' > lesson04.txt
s3 s3api put-object --bucket s3-course-lesson1 \
  --key docs/lesson04.txt --body lesson04.txt --content-type text/plain
s3 s3api head-object --bucket s3-course-lesson1 --key docs/lesson04.txt
s3 s3api get-object --bucket s3-course-lesson1 \
  --key docs/lesson04.txt downloaded04.txt
cmp lesson04.txt downloaded04.txt
s3 s3api delete-object --bucket s3-course-lesson1 --key docs/lesson04.txt
```

**Проверка:** `cmp` без различий; после DELETE обычный GET по ключу не возвращает объект.

### Самостоятельно

1. Перезапиши ключ другим содержимым; сравни `ContentLength` до и после.
2. Сравни результаты HEAD до записи, после записи и после DELETE.
3. Предложи защиту от потери изменений при двух конкурентных PUT.
4. Объясни, почему DELETE не гарантирует удаления всех версий и физического стирания байтов.

## 05. Keys, Prefixes, Listing

### Модель ключей

У обычного S3-бакета **плоское пространство ключей**. `docs/a.txt` и `docs/b.txt` — независимые объекты; `/` не создаёт каталог. Ключи `docs` и `docs/a.txt` могут сосуществовать.

- **Prefix** — фильтр по началу строки ключа; `docs/` не требуется предварительно создавать.
- **Delimiter** — разделитель для группировки результатов. При `Prefix=lesson05/`, `Delimiter=/` объект `lesson05/root.txt` попадает в `Contents`, а `lesson05/docs/` — в `CommonPrefixes`.
- **CommonPrefixes** — логические группы, не физические папки. Console может представлять папку нулевым объектом-маркером с ключом, оканчивающимся на `/`.
- Префиксы не выдают прав доступа: авторизация определяется политиками.

### ListObjectsV2 и пагинация

`ListObjectsV2` перечисляет объекты бакета **без скачивания их содержимого**.

| Параметр / поле | Назначение |
|---|---|
| `Prefix`, `Delimiter` | Фильтрация и группировка |
| `Contents`, `CommonPrefixes` | Объекты и логические группы |
| `MaxKeys` | Лимит результатов; в AWS S3 — до 1000 |
| `IsTruncated` | Признак следующей страницы |
| `NextContinuationToken` | Непрозрачный токен продолжения |

**Пагинация:** запросить страницу → обработать ответ → при `IsTruncated=true` передать `NextContinuationToken` как `ContinuationToken` → повторить. AWS CLI автоматически обходит страницы, если не передан `--no-paginate`. Первый ответ не равен гарантированно полному списку.

`ListObjectsV2` не ищет по пользовательским метаданным или бизнес-полям: для этого нужен индекс в базе приложения.

### Практика

```fish
printf 'lesson 05\n' > lesson05.txt
for key in lesson05/root.txt lesson05/docs/a.txt lesson05/docs/b.txt lesson05/photos/a.txt
    s3 s3api put-object --bucket s3-course-lesson1 --key $key \
      --body lesson05.txt > /dev/null
end
s3 s3api list-objects-v2 --bucket s3-course-lesson1 \
  --prefix lesson05/ --delimiter /
s3 s3api list-objects-v2 --bucket s3-course-lesson1 \
  --prefix lesson05/ --max-keys 2 --no-paginate
```

**Проверка:** первый ответ содержит один элемент `Contents` и две группы `CommonPrefixes`; во втором есть токен следующей страницы.

### Самостоятельно

1. Получи объекты `lesson05/docs/` с `Delimiter=/` и без него; сравни ответы.
2. Вручную пройди страницы с `MaxKeys=2`, собери четыре ключа без пропусков.
3. Спроектируй поиск файлов по `owner_id` и отображаемому имени в PostgreSQL без полного листинга S3.

## 06. Метаданные объектов и теги

### Три группы атрибутов

- **Системные:** `Content-Type` (заявленный MIME-тип), `Content-Length` (размер тела), `Last-Modified` (время изменения), `ETag` (идентификатор состояния представления). **ETag не всегда равен MD5.** `Content-Type` не подтверждает действительный формат байтов.
- **Пользовательские:** пары `имя=значение`, передаваемые как HTTP-заголовки `x-amz-meta-*`. Изменение требует записи или `CopyObject` с `MetadataDirective=REPLACE`.
- **Object tags:** отдельные пары `Key/Value` (до 10 тегов в обычном AWS S3); изменяются через `PutObjectTagging`, читаются через `GetObjectTagging`, удаляются через `DeleteObjectTagging` без повторной передачи тела.

`HeadObject` возвращает метаданные, но не полный набор тегов. `ListObjectsV2` не фильтрует по произвольным пользовательским метаданным.

### Архитектурное разделение

```text
PostgreSQL: file_id, owner_id, original_filename, bucket, key, status
S3:         bytes, Content-Type, metadata, tags
```

БД отвечает за владельца, отображаемое имя и поиск; S3 — за байты и атрибуты хранения. Переименование файла в интерфейсе не требует изменения S3-ключа.

### Практика

```fish
printf 'Metadata lesson 06\n' > lesson06.txt
s3 s3api put-object --bucket s3-course-lesson1 \
  --key lesson06/document.txt --body lesson06.txt \
  --content-type text/plain --metadata source=course,stage=draft
s3 s3api head-object --bucket s3-course-lesson1 \
  --key lesson06/document.txt
s3 s3api put-object-tagging --bucket s3-course-lesson1 \
  --key lesson06/document.txt \
  --tagging '{"TagSet":[{"Key":"stage","Value":"reviewed"}]}'
s3 s3api get-object-tagging --bucket s3-course-lesson1 \
  --key lesson06/document.txt
```

Изменение пользовательских метаданных без повторной загрузки локального файла:

```fish
s3 s3api copy-object \
  --copy-source s3-course-lesson1/lesson06/document.txt \
  --bucket s3-course-lesson1 --key lesson06/document.txt \
  --metadata-directive REPLACE --content-type text/plain \
  --metadata source=course,stage=reviewed
```

**Проверка:** повторно прочитай HEAD и теги; результат копирования атрибутов зависит от параметров операции.

### Самостоятельно

1. Измени только тег `stage` на `approved`; проверь, что user metadata не изменились.
2. Измени метаданные `source`, сохранив исходные байты; проверь через HEAD и GET.
3. Распредели `owner_id`, `original_filename`, `content_type`, `storage_key` между PostgreSQL и S3 и обоснуй.
