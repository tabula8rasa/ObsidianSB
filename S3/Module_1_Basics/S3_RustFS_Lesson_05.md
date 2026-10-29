---
title: "S3 и RustFS — Урок 05. Ключи, префиксы, перечисление"
aliases: ["S3: урок 5"]
tags: [s3, rustfs, object-storage, course]
lesson: 5
module: 1
status: study
---

# Урок 05. Keys, Prefixes, Listing

**Цель:** организовать объекты по ключам и получать полный список без предположений о папках.

## Модель ключей

Обычный S3-бакет имеет **плоское пространство ключей**. Строки `docs/a.txt`, `docs/b.txt`, `photos/a.txt` — три самостоятельных ключа. `/` не создаёт каталог. Объекты `docs` и `docs/a.txt` могут существовать одновременно.

- **Prefix** — начальная строка для фильтрации ключей. `Prefix=docs/` выбирает ключи, начинающиеся с `docs/`; заранее создавать такую «папку» не нужно.
- **Delimiter** — разделитель для группировки результатов. При `Prefix=lesson05/`, `Delimiter=/` ключ `lesson05/root.txt` попадает в `Contents`, а `lesson05/docs/` — в `CommonPrefixes`. Последние **не являются физическими каталогами**.
- Console может создавать **нулевые объекты-маркеры** с ключом, завершающимся `/`. Это соглашение интерфейса, не требование S3.
- Префикс **не предоставляет права доступа**. Доступ задаётся политиками, а не названиями «папок».

## ListObjectsV2 и пагинация

**`ListObjectsV2`** перечисляет объекты в указанном бакете без скачивания их содержимого. Основные поля:

| Поле | Значение |
|---|---|
| `Prefix`, `Delimiter` | Фильтр и группировка |
| `Contents`, `CommonPrefixes` | Объекты и логические группы |
| `MaxKeys` | Предел элементов ответа (в AWS S3 до 1000) |
| `IsTruncated` | Есть следующая страница |
| `NextContinuationToken` | Непрозрачный токен продолжения |

Алгоритм: запросить страницу → обработать результат → если `IsTruncated=true`, передать `NextContinuationToken` как `ContinuationToken` → повторять до завершения. AWS CLI обычно автоматически выполняет пагинацию; `--no-paginate` отключает её на стороне CLI. **Первый ответ не обязательно полный список.**

Перечисление не заменяет поиск по бизнес-атрибутам. Имена файлов, владельцев и связи `file_id → bucket/key` следует хранить в базе приложения.

## Практика

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

**Проверка:** в первом листинге одна запись `Contents` и две группы `CommonPrefixes`; во втором нужен токен следующей страницы.

## Самостоятельно

1. Получи только объекты `lesson05/docs/`; сравни выборки с `Delimiter=/` и без него.
2. Пройди страницы `MaxKeys=2` вручную и собери четыре ключа без пропусков.
3. Продумай таблицу PostgreSQL для поиска файла по `owner_id` и отображаемому имени без полного `ListObjectsV2`.
