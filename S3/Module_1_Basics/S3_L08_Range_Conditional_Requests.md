---
title: "S3 и RustFS — Урок 08. Range и условные запросы"
aliases: ["S3: урок 8"]
tags: [s3, rustfs, http, object-storage, course]
lesson: 8
module: 1
status: study
---
# Урок 08. Range и Conditional Requests

**Цель:** читать части больших объектов и не смешивать данные разных состояний при параллельном скачивании.

## Range: чтение диапазона

**Range request** — `GetObject` с заголовком `Range`, ограничивающим возвращаемые байты.

- `bytes=10-15` — байты с индексами 10–15 **включительно**, всего шесть.
- `bytes=10-` — начиная с десятого до конца; `bytes=-5` — последние пять байтов.
- `206 Partial Content` — диапазон успешно возвращён; `Content-Range` обозначает диапазон и полный размер, `Content-Length` — длину возвращённой части.
- `416 Range Not Satisfiable` — указанный диапазон не может быть возвращён. Обычный AWS S3 поддерживает один диапазон в одном GET.

Частичный GET **не меняет объект**. Это не Multipart Upload: Range управляет чтением, multipart — записью по частям.

## Условные запросы

| Условие | Когда передаются данные | Если условие не выполнено |
|---|---|---|
| `If-Match: ETag` | ETag совпал | `412 Precondition Failed` |
| `If-None-Match: ETag` | ETag отличается | Для GET: `304 Not Modified` |
| `If-Unmodified-Since` | Объект не изменён после даты | `412` |
| `If-Modified-Since` | Объект изменён после даты | Для GET: `304` |

**ETag не универсальная MD5-сумма и не заменяет `versionId`.** Для скачивания большого объекта: HEAD → получить размер и ETag → разбить на диапазоны → GET каждого диапазона с `If-Match` → собрать в исходном порядке. Если объект изменился, не склеивай диапазоны разных состояний. При versioning можно адресовать конкретную версию.

## Практика

```fish
printf '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\n' > lesson08.txt
s3 s3api put-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --body lesson08.txt
s3 s3api get-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --range bytes=10-15 part08.txt
printf ABCDEF > expected08.txt
cmp part08.txt expected08.txt
```

Получение ETag и условный GET в `fish`:

```fish
set etag (s3 s3api head-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --query ETag --output text)
s3 s3api get-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --range bytes=10-15 --if-match $etag matched08.txt
s3 s3api get-object --bucket s3-course-lesson1 \
  --key lesson08/data.txt --if-none-match $etag unchanged08.txt
```

Последняя команда должна получить `304` без скачивания тела; AWS CLI показывает его как ошибку вызова.

## Самостоятельно

1. Прочитай последние пять байтов с помощью `bytes=-5`; проверь ответ через `cmp`.
2. Замени содержимое объекта и повтори GET со **старым** `If-Match`. Объясни `412`.
3. Реализуй алгоритм чтения объекта двумя диапазонами. При изменении ETag между запросами отклони результат, не склеивая части.
