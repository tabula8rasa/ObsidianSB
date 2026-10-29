---
title: "S3 и RustFS — Урок 06. Метаданные и теги"
aliases: ["S3: урок 6"]
tags: [s3, rustfs, object-storage, course]
lesson: 6
module: 1
status: study
---
# Урок 06. Метаданные объектов и теги

**Цель:** отличать атрибуты объекта от его содержимого и от данных бизнес-модели.

## Три группы атрибутов

- **Системные метаданные:** `Content-Type` (MIME-тип), `Content-Length` (размер тела), `Last-Modified` (время изменения), `ETag` (идентификатор состояния представления). **ETag не всегда MD5 содержимого.**
- **Пользовательские метаданные:** пары имя/значение, записываемые с объектом; в HTTP представлены заголовками `x-amz-meta-*`. Изменение требует перезаписи либо `CopyObject` с `MetadataDirective=REPLACE`.
- **Object tags:** отдельный набор пар `Key/Value`. В обычном AWS S3 максимум 10 тегов. Управляются `PutObjectTagging`, `GetObjectTagging`, `DeleteObjectTagging` **без повторной загрузки тела**.

`HeadObject` возвращает метаданные без содержимого; полный набор тегов читается через `GetObjectTagging`. `ListObjectsV2` не фильтрует по произвольным пользовательским метаданным.

## Архитектурное разделение

```text
PostgreSQL: file_id, owner_id, original_filename, bucket, key, status
S3:         bytes, Content-Type, metadata, tags
```

База приложения хранит принадлежность файла пользователю, отображаемое имя, связи и поисковые атрибуты. S3 отвечает за хранение байтов и S3-атрибутов. Изменение имени файла в пользовательском интерфейсе не требует смены ключа в S3.

**`Content-Type`** подсказывает клиенту способ интерпретации тела, но не меняет его байты; объявленный тип не является проверкой формата файла.

## Практика

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

Для замены user metadata без передачи локального файла:

```fish
s3 s3api copy-object \
  --copy-source s3-course-lesson1/lesson06/document.txt \
  --bucket s3-course-lesson1 --key lesson06/document.txt \
  --metadata-directive REPLACE --content-type text/plain \
  --metadata source=course,stage=reviewed
```

После копирования повторно проверь `HeadObject` и теги; поведение отдельных атрибутов зависит от параметров копирования.

## Самостоятельно

1. Измени только тег `stage` на `approved`; докажи, что пользовательские метаданные не изменились.
2. Замени пользовательский атрибут `source`, не меняя байты объекта; проверь результат через HEAD и GET.
3. Раздели `owner_id`, `original_filename`, `content_type`, `storage_key` между PostgreSQL и S3 и объясни решение.
