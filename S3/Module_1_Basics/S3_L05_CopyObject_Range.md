---
title: "S3 и RustFS — Уроки 05. Копирование и частичное чтение"
aliases: "S3: урок 5"
tags: [s3, rustfs, http, object-storage, course]
lessons: 5
module: 1
status: study
---
# Урок 05. CopyObject, Range и Conditional Requests

**Цель:** освоить копирование, перемещение и пакетное удаление объектов, а также безопасное частичное чтение. Используй бакет `s3-course-lesson1` и функцию `s3` из урока 02.

## Операции и ограничения

- **`CopyObject`** создаёт самостоятельный объект из источника. При копировании внутри одной S3-системы клиенту не нужно скачивать тело на backend. В обычном AWS S3 единичная операция ограничена размером объекта до 5 ГиБ; для больших объектов применяют multipart copy.
- **`MetadataDirective=COPY`** сохраняет поддерживаемые метаданные; **`REPLACE`** задаёт новые. Результат для тегов, шифрования и доступа зависит от параметров копирования и настроек бакета назначения.
- **Переименование/перемещение в обычном S3:** `CopyObject(old → new)` → проверка → `DeleteObject(old)`. Единой транзакции нет: между операциями существуют оба объекта.
- **`DeleteObjects`** принимает до 1000 ключей/версий за один запрос в AWS S3. Успех HTTP не означает успех для всех элементов: проверяй `Errors` в ответе.
- **Versioning:** обычный DELETE создаёт `delete marker`; для удаления отдельной версии указывают `versionId`. Object Lock может запретить удаление. Результат API не гарантирует физическое стирание байтов.

## Архитектура безопасного перемещения

```text
1. Проверить источник → 2. CopyObject → 3. Проверить назначение
→ 4. DeleteObject(источник) → 5. Зафиксировать результат в БД
```

Сбой после копирования может оставить два объекта. Повторная попытка должна учитывать существующую копию и конкурентные изменения: нужны **идемпотентность** и **контроль состояния**. При неуспешном копировании нельзя удалять источник.

## Практика

```bash
printf 'Lesson 07\n' > lesson07.txt
s3 s3api put-object --bucket s3-course-lesson1 \
  --key lesson07/source.txt --body lesson07.txt
s3 s3api copy-object \
  --copy-source s3-course-lesson1/lesson07/source.txt \
  --bucket s3-course-lesson1 --key lesson07/archive.txt
s3 s3api head-object --bucket s3-course-lesson1 \
  --key lesson07/archive.txt
s3 s3api delete-object --bucket s3-course-lesson1 \
  --key lesson07/source.txt
```

Пакетное удаление двух тестовых ключей:

```bash
s3 s3api put-object --bucket s3-course-lesson1 \
  --key lesson07/temporary.txt --body lesson07.txt
s3 s3api delete-objects --bucket s3-course-lesson1 \
  --delete '{"Objects":[{"Key":"lesson07/archive.txt"},{"Key":"lesson07/temporary.txt"}],"Quiet":false}'
```

## Самостоятельно

1. Смоделируй сбой между `CopyObject` и `DeleteObject`; реализуй безопасный повтор.
2. Докажи, что удаление исходного объекта не меняет копию.
3. Проверь обработку частичного успеха `DeleteObjects` и поля `Errors`.

## Range: чтение диапазона

**Range request** — `GetObject` с заголовком `Range`, ограничивающим передаваемую часть тела.

- `bytes=10-15` — шесть байтов с индексами 10–15 включительно.
- `bytes=10-` — до конца, `bytes=-5` — последние пять байтов.
- `206 Partial Content` — диапазон возвращён. `Content-Range` описывает диапазон и полный размер, `Content-Length` — размер переданной части.
- `416 Range Not Satisfiable` — диапазон недопустим. Обычный AWS S3 поддерживает один диапазон за GET.

Range — **частичное чтение**, не изменение объекта. Multipart Upload — отдельный механизм записи частями.

## Условные запросы

| Условие | Когда выдаётся содержимое | При невыполнении |
|---|---|---|
| `If-Match: ETag` | ETag совпадает | `412 Precondition Failed` |
| `If-None-Match: ETag` | ETag отличается | GET: `304 Not Modified` |
| `If-Unmodified-Since` | Нет изменений после даты | `412` |
| `If-Modified-Since` | Есть изменения после даты | GET: `304` |

**ETag не равен гарантированной MD5-сумме и не заменяет `versionId`.** Для безопасного чтения частями: HEAD → получить размер и ETag → задать диапазоны → для каждого GET использовать `If-Match` → собрать в исходном порядке. Если ETag изменился, не объединять части разных состояний. При включённом versioning можно читать по конкретному `versionId`.

## Практика

```bash
printf '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\n' > lesson08.txt
s3 s3api put-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --body lesson08.txt
s3 s3api get-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --range bytes=10-15 part08.txt
printf ABCDEF > expected08.txt
cmp part08.txt expected08.txt
```

Условное чтение (синтаксис `fish`):

```bash
set etag (s3 s3api head-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --query ETag --output text)
s3 s3api get-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --range bytes=10-15 --if-match $etag matched08.txt
s3 s3api get-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --if-none-match $etag unchanged08.txt
```

**Проверка:** `cmp` не показывает различий, а последний GET возвращает `304` без тела (AWS CLI показывает ошибку вызова).

## Самостоятельно

1. Прочитай последние пять байтов через `bytes=-5`; проверь результат.
2. Перезапиши объект и повтори GET со старым `If-Match`; объясни `412`.
3. Реализуй скачивание двумя диапазонами с проверкой ETag; при его изменении отклоняй результат.
