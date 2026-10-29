---
title: "S3 и RustFS — Урок 07. Копирование и массовое удаление"
aliases: ["S3: урок 7"]
tags: [s3, rustfs, object-storage, course]
lesson: 7
module: 1
status: study
---
# Урок 07. CopyObject, перемещение и DeleteObjects

**Цель:** различать копирование, перемещение и пакетное удаление объектов.

## Операции и ограничения

- **`CopyObject`** создаёт объект назначения на основе источника. В обычном AWS S3 одна операция копирования рассчитана на объект размером до 5 ГиБ; для большего объекта применяется multipart copy.
- Источник и назначение — **независимые объекты**. В пределах одной S3-системы клиенту не нужно скачивать байты на backend для копирования: достаточно команды API.
- `MetadataDirective=COPY` сохраняет поддерживаемые метаданные источника; `REPLACE` задаёт новые. Теги, шифрование и доступ назначения определяются собственными параметрами копирования и настройками бакета.
- В обычном S3 **переименование/перемещение = `CopyObject(old → new)` → проверка успеха → `DeleteObject(old)`**. Это две операции **без общей транзакции**. Между ними существуют оба объекта, а ошибка удаления оставляет копию и оригинал.
- **`DeleteObjects`** удаляет до **1000** указанных ключей/версий за запрос (обычный AWS S3). Возможен частичный успех: проверяй `Errors` в ответе, а не только HTTP-статус.

**Versioning:** обычный DELETE в versioned-бакете создаёт delete marker, не удаляя старые версии. Удаление конкретной версии требует `versionId`; Object Lock способен запретить его. API не гарантирует немедленное физическое стирание байтов.

## Архитектура безопасного перемещения

```text
1. Проверить источник → 2. CopyObject → 3. Проверить назначение
→ 4. DeleteObject(источник) → 5. Зафиксировать итог в БД
```

При сбое между шагами 3 и 4 не теряй источник; повторная попытка должна учитывать уже существующую копию и параллельные изменения исходного ключа. Для надёжной реализации нужны идемпотентность и контроль состояния объекта.

## Практика

```fish
printf 'Lesson 07\n' > lesson07.txt
s3 s3api put-object --bucket s3-course-lesson1 \
  --key lesson07/source.txt --body lesson07.txt
s3 s3api copy-object --copy-source s3-course-lesson1/lesson07/source.txt \
  --bucket s3-course-lesson1 --key lesson07/archive.txt
s3 s3api head-object --bucket s3-course-lesson1 \
  --key lesson07/archive.txt
s3 s3api delete-object --bucket s3-course-lesson1 \
  --key lesson07/source.txt
```

Создай `lesson07/temporary.txt` и удали оба оставшихся тестовых ключа одним запросом:

```fish
s3 s3api put-object --bucket s3-course-lesson1 \
  --key lesson07/temporary.txt --body lesson07.txt
s3 s3api delete-objects --bucket s3-course-lesson1 \
  --delete '{"Objects":[{"Key":"lesson07/archive.txt"},{"Key":"lesson07/temporary.txt"}],"Quiet":false}'
```

## Самостоятельно

1. Смоделируй сбой после успешного CopyObject, но до DeleteObject. Реализуй безопасную повторную попытку.
2. Проверь, что удаление источника не меняет копию.
3. Объясни, почему HTTP-успех `DeleteObjects` не означает успешного удаления каждого объекта, и как обработать `Errors`.
