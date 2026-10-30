---
title: "S3 и RustFS — Уроки 04. Объекты, ключи и метаданные"
aliases:  "S3: урок 4"
tags: [s3, rustfs, object-storage, course]
lessons: 4
module: 1
status: study
---
# Урок 04. Объекты, ключи, метаданные

Цель: освоить операции с объектами S3, организацию ключей, перечисление с пагинацией и управление атрибутами на бакете `s3-course-lesson1` (функция `s3` из урока 02).

## Объект и базовые операции

Объект S3 состоит из **тела** (произвольные байты) и **метаданных**. Четыре базовые операции:


| `PutObject`    | PUT    | Записывает тело и метаданные под ключом                   |
| -------------- | ------ | --------------------------------------------------------- |
| `GetObject`    | GET    | Возвращает байты и заголовки                              |
| `HeadObject`   | HEAD   | Возвращает метаданные без тела                            |
| `DeleteObject` | DELETE | Удаляет объект или при versioning создаёт `delete marker` |

**Практика:** записать, прочитать метаданные, скачать, сравнить, удалить.

```bash
printf 'Object storage lesson 04\n' > lesson04.txt
s3 s3api put-object --bucket s3-course-lesson1 \
  --key docs/lesson04.txt --body lesson04.txt --content-type text/plain
s3 s3api head-object --bucket s3-course-lesson1 --key docs/lesson04.txt
s3 s3api get-object --bucket s3-course-lesson1 \
  --key docs/lesson04.txt downloaded04.txt
cmp lesson04.txt downloaded04.txt
s3 s3api delete-object --bucket s3-course-lesson1 --key docs/lesson04.txt
```

**Проверка:** `cmp` не показывает различий; после DELETE обычный GET по ключу не возвращает объект.

**Самостоятельно:**

1. Перезапиши ключ другим содержимым; сравни `ContentLength` до и после.
2. Сравни результаты HEAD до записи, после записи и после DELETE.
3. Предложи защиту от потери изменений при двух конкурентных PUT.
4. Объясни, почему DELETE не гарантирует удаления всех версий и физического стирания байтов.

## Ключи и перечисление объектов

У обычного бакета **плоское пространство ключей**: `docs/a.txt` и `docs/b.txt` — независимые объекты, а `/` не создаёт каталог. Ключи `docs` и `docs/a.txt` могут существовать одновременно.

- **Prefix** — фильтр по началу ключа. Префикс `docs/` заранее создавать не нужно.
- **Delimiter** — разделитель для группировки. При `Prefix=lesson05/` и `Delimiter=/` объект `lesson05/root.txt` попадает в `Contents`, а `lesson05/docs/` — в `CommonPrefixes`.
- **CommonPrefixes** — логические группы, а не физические папки. Console может показывать «папку» как пустой объект-маркер с ключом, оканчивающимся на `/`.
- Префиксы не дают прав доступа: авторизацию определяют политики.

### ListObjectsV2

Перечисляет объекты бакета **без скачивания содержимого**.

| Параметр / поле              | Назначение                            |
| ---------------------------- | ------------------------------------- |
| `Prefix`, `Delimiter`        | Фильтрация и группировка              |
| `Contents`, `CommonPrefixes` | Объекты и логические группы           |
| `MaxKeys`                    | Лимит результатов; в AWS S3 — до 1000 |
| `IsTruncated`                | Есть следующая страница               |
| `NextContinuationToken`      | Непрозрачный токен продолжения        |

**Пагинация** — цикл из трёх шагов:

1. Запросить страницу и обработать ответ.
2. Если `IsTruncated=true`, передать `NextContinuationToken` как `ContinuationToken`.
3. Повторять, пока `IsTruncated` не станет `false`.

AWS CLI обходит страницы сам, если не указан `--no-paginate`. Первый ответ не обязательно содержит полный список. Поиска по пользовательским метаданным или бизнес-полям у `ListObjectsV2` нет: для этого нужен индекс в базе приложения.

**Практика:** создать четыре ключа и посмотреть листинг с группировкой и с ограничением страницы.

```bash
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

Цикл `for ... end` записан в синтаксисе fish; в bash его нужно переписать на `for ...; do ...; done`.

**Проверка:** первый ответ содержит один элемент `Contents` и две группы `CommonPrefixes`; во втором есть токен следующей страницы.

**Самостоятельно:**

1. Получи объекты `lesson05/docs/` с `Delimiter=/` и без него; сравни ответы.
2. Вручную пройди страницы с `MaxKeys=2` и собери все четыре ключа без пропусков.
3. Спроектируй поиск файлов по `owner_id` и отображаемому имени в PostgreSQL без полного листинга S3.

## Метаданные и теги

У объекта три группы атрибутов, и менять их нужно по-разному.


| Группа             | Что входит                                                                                                                                              | Как менять                                                              | Как читать         |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------ |
| Системные          | `Content-Type` (заявленный MIME-тип), `Content-Length` (размер тела), `Last-Modified` (время изменения), `ETag` (идентификатор состояния представления) | Задаются при записи, например `--content-type`                          | `HeadObject`       |
| Пользовательские   | Пары `имя=значение` в заголовках `x-amz-meta-*`                                                                                                         | Только новой записью или `CopyObject` с `MetadataDirective=REPLACE`     | `HeadObject`       |
| Теги (object tags) | Пары `Key/Value`, до 10 штук в обычном AWS S3                                                                                                           | `PutObjectTagging`, `DeleteObjectTagging` — без повторной передачи тела | `GetObjectTagging` |

`HeadObject` не возвращает полный набор тегов, а `ListObjectsV2` не фильтрует по пользовательским метаданным.

**Практика:** записать объект с метаданными, повесить тег, прочитать всё обратно.

```bash
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

Изменить пользовательские метаданные без повторной загрузки файла:

```bash
s3 s3api copy-object \
  --copy-source s3-course-lesson1/lesson06/document.txt \
  --bucket s3-course-lesson1 --key lesson06/document.txt \
  --metadata-directive REPLACE --content-type text/plain \
  --metadata source=course,stage=reviewed
```

**Проверка:** повторно прочитай HEAD и теги. Что именно сохранится при копировании, зависит от параметров операции.

**Самостоятельно:**

1. Измени только тег `stage` на `approved` и проверь, что пользовательские метаданные не изменились.
2. Измени метаданные `source`, сохранив исходные байты; проверь через HEAD и GET.
3. Распредели `owner_id`, `original_filename`, `content_type`, `storage_key` между PostgreSQL и S3 и обоснуй выбор.

