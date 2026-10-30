---
title: "S3 и RustFS — Урок 02. HTTP, endpoint, region и AWS CLI"
aliases: ["S3: урок 2"]
tags: [s3, rustfs, http, aws-cli, course]
lesson: 2
module: 1
status: study
---
# Урок 02. S3 API: HTTP, endpoint, region и AWS CLI

**Цель:** понять, как вызов S3 API превращается в подписанный HTTP-запрос, и настроить AWS CLI.

## Определения и адресация

- **API** — контракт между программами. **REST** — стиль взаимодействия с ресурсами через URI и методы HTTP. В S3 операция определяется сочетанием метода, пути, заголовков и query-параметров.
- **Endpoint** — адрес конкретного сервиса: `http://127.0.0.1:9000` для S3 API RustFS. Console работает отдельно на `:9001`.
- **Region** — регион AWS, влияющий на размещение бакета и область действия подписи. В локальном RustFS `us-east-1` служит настройкой совместимости/подписи, а не географическим размещением в AWS.
- **Path-style:** `http://127.0.0.1:9000/bucket/key`. **Virtual-hosted-style:** `https://bucket.s3.us-east-1.amazonaws.com/key`. В лаборатории используется path-style.
- **Query string** выбирает параметры или операцию: `GET /bucket?list-type=2&prefix=docs%2F` — список ключей; `GET /bucket/docs/a.txt` — содержимое объекта.

## Как обрабатывается запрос

```text
AWS CLI → метод + URL + заголовки + подпись SigV4
        → RustFS: проверка подписи и полномочий
        → HTTP-статус + S3-ответ (часто XML)
        → AWS CLI разбирает ответ и выводит JSON/текст
```

**SigV4** — механизм подписи запроса с использованием Secret Access Key, даты, региона и параметров запроса. Сам секрет не передаётся в HTTP-заголовке как открытый ключ. Подлинность подписи и разрешение на операцию — две отдельные проверки.

**`aws s3`** — высокоуровневые действия (`ls`, `cp`, `sync`), которые могут вызывать несколько API-операций. **`aws s3api`** — прямые вызовы операций (`list-buckets`, `head-bucket`, `put-object`). `--query` в CLI фильтрует уже полученный результат локально; это не серверный поиск S3.

## Настройка AWS CLI (fish)

Установи AWS CLI v2, если он отсутствует, и создай профиль из реквизитов `.env` урока 01:

```bash
aws --version
aws configure --profile rustfs-lab
aws configure set s3.addressing_style path --profile rustfs-lab
```

Для `aws configure` укажи access key, secret key, region `us-east-1`, формат `json`. Настройки хранятся в `~/.aws/config` и `~/.aws/credentials`; не публикуй их.

Чтобы в следующих уроках не повторять длинный набор флагов, создай функцию `fish`:

```bash
function s3
    aws --profile rustfs-lab --endpoint-url http://127.0.0.1:9000 $argv
end
funcsave s3
```

```bash
s3 s3api list-buckets
s3 s3api list-buckets --query 'Buckets[].Name' --output text
s3 s3 ls
curl -i http://127.0.0.1:9000/
```

Первый запрос соответствует `GET /` с SigV4. Последний — запрос без подписи: зафиксируй ответ сервера. **Не отправляй команды без локального endpoint при работе с учебными ключами.**

## Самостоятельно

1. Сравни результаты `s3 s3api list-buckets` и `s3 s3 ls`. Укажи, что возвращает API, а что форматирует клиент.
2. Выполни `s3 --debug s3api list-buckets` и найди метод, URL, статус ответа. Не публикуй журнал целиком: он содержит служебные сведения.
3. Сравни path-style и virtual-hosted-style; объясни, почему изменение `region` не переносит данные локального RustFS на другой сервер.
4. Объясни разницу между ошибкой подписи и отказом в полномочиях.

**Результат:** один и тот же RustFS доступен из Console, AWS CLI и клиентского кода по S3 API.
