---
title: "S3 и RustFS — Урок 09. Multipart Upload"
aliases:
  - "S3: урок 9"
tags:
  - s3
  - rustfs
  - multipart
  - course
lesson: 9
module: 2
status: study
---
# Урок 09. Multipart Upload

**Цель:** загрузить объект частями, завершить и отменить загрузку; понять отличие multipart от механизмов отказоустойчивости.

## 1. Принцип и архитектура

**Multipart Upload** — загрузка одного объекта несколькими независимыми запросами. Позволяет повторно отправлять только неудачные части и загружать части параллельно.

- Загрузка имеет собственное состояние: `UploadId`, номера частей и их `ETag`. Для продолжения после перезапуска клиент должен сохранить эти данные.
- Части не доступны через обычный `GetObject` до успешного завершения. Существующий объект не становится «частично обновлённым».
- Повторный `UploadPart` с тем же номером заменяет эту часть. Итоговая сборка идёт **по номерам**, а не по времени отправки.
- **Multipart ≠ erasure coding / replication.** Это способ передачи данных, а не распределения их по дискам.

## 2. Жизненный цикл

| Операция | Результат |
|---|---|
| `CreateMultipartUpload` | Создаёт сессию, возвращает `UploadId`; здесь задают метаданные объекта |
| `UploadPart` | Передаёт часть по её номеру; возвращает `ETag` |
| `CompleteMultipartUpload` | Принимает пары `PartNumber + ETag` и публикует собранный объект |
| `AbortMultipartUpload` | Отменяет незавершённую загрузку и освобождает связанные ресурсы |

**Ограничения AWS S3:** до 10 000 частей; размер части — от 5 MiB до 5 GiB, последняя может быть меньше. Совместимость RustFS с основными операциями не гарантирует совпадение всех ограничений AWS.

## 3. Практика: загрузка 12 MiB

**1. Подготовь файл и начни сессию** (`fish`; AWS CLI уже настроен):

```fish
dd if=/dev/urandom of=source.bin bs=1M count=12 status=none
split -b 6M source.bin part-
set EP http://127.0.0.1:9000
set B s3-course-lesson1
set K lesson09/complete.bin
set U (aws --endpoint-url $EP s3api create-multipart-upload --bucket $B --key $K --query UploadId --output text)
```

**2. Загрузи части, сохрани `ETag`:**

```fish
aws --endpoint-url $EP s3api upload-part --bucket $B --key $K --upload-id $U --part-number 1 --body part-aa > response1.json
aws --endpoint-url $EP s3api upload-part --bucket $B --key $K --upload-id $U --part-number 2 --body part-ab > response2.json
```

**3. Создай `parts.json`**, подставив `ETag` из ответов **вместе с кавычками**:

```json
{"Parts":[{"PartNumber":1,"ETag":"\"ETAG_1\""},{"PartNumber":2,"ETag":"\"ETAG_2\""}]}
```

**4. Заверши загрузку и сравни содержимое:**

```fish
aws --endpoint-url $EP s3api complete-multipart-upload --bucket $B --key $K --upload-id $U --multipart-upload file://parts.json
aws --endpoint-url $EP s3api get-object --bucket $B --key $K downloaded.bin
cmp source.bin downloaded.bin
```

`cmp` без вывода означает совпадение байтов.

## 4. Самостоятельная реализация

1. **Отмена:** начни новую загрузку под ключом `lesson09/aborted.bin`, отправь одну часть, выполни `abort-multipart-upload` с её `UploadId`. Проверь результат через `list-multipart-uploads`.
2. **Порядок:** повтори полную загрузку, отправив часть №2 раньше №1. Убедись, что итоговый объект совпадает с исходным.
3. **Восстановление:** определи, какие данные необходимо сохранять для продолжения загрузки после перезапуска клиента.

**Важно:** незавершённые части занимают место до завершения или отмены; обычный список объектов их не показывает. Перед отменой останови параллельную отправку частей.

**Далее:** урок 10 — контроль целостности (`ETag`, MD5, SHA-256, checksums).

**Источники:** [AWS Multipart Upload](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html) · [RustFS Compatibility](https://docs.rustfs.com/en/reference/s3-compatibility)
