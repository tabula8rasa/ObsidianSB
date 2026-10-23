---
title: "S3 и RustFS — Урок 19. SSE-C"
aliases:
  - "S3: урок 19"
tags: [s3, rustfs, security, sse-c, encryption, course]
lesson: 19
module: 2
status: study
---

# Урок 19. SSE-C: ключ шифрования предоставляет клиент

> [!abstract] Цель урока
> Понять, как серверное шифрование SSE-C отличается от SSE-S3/SSE-KMS и проверить чтение с правильным, отсутствующим и неправильным ключом.

**Предварительные знания:** TLS, S3 API, AWS CLI.  
**Практическая среда:** локальный RustFS **с HTTPS из урока 16**, AWS CLI, `fish`, OpenSSL.  
**Критерий завершения:** запись с клиентским ключом успешна, чтение без ключа не работает, чтение с исходным ключом возвращает те же байты.  
**Время чтения:** до 5 минут; практика отдельно.

---

## 1. Принцип SSE-C

**SSE-C (Server-Side Encryption with Customer-Provided Keys)** — клиент генерирует **256-битный AES-ключ** и передаёт его RustFS **при каждой операции, которой нужен доступ к содержимому**.

- При **записи** RustFS получает ключ, шифрует объект и не сохраняет клиентский ключ в открытом виде.
- При **чтении** клиент повторно передаёт **тот же ключ**.
- Если ключ потерян, RustFS **не восстановит** данные.

Это **серверное**, а не client-side encryption: сервер на время операции видит ключ и открытые байты. KMS RustFS для SSE-C **не нужен**.

## 2. Три HTTP-заголовка

| Заголовок S3 | Значение |
|---|---|
| `x-amz-server-side-encryption-customer-algorithm` | `AES256` |
| `x-amz-server-side-encryption-customer-key` | Клиентский 32-байтовый ключ, представленный в Base64 |
| `x-amz-server-side-encryption-customer-key-MD5` | Контрольная сумма самого ключа, также в Base64 |

**MD5 здесь служит проверкой правильности передачи ключа**, а не защитой объекта от изменения и не заменой SigV4. AWS CLI формирует нужные заголовки при передаче двоичного ключа через `fileb://`.

## 3. Где это находится в RustFS Console

На присланной странице **SSE Configuration** настраивается **KMS/Vault**, а не SSE-C.

- Для SSE-C **нет постоянного ключа бакета**, который пользователь устанавливает в Console.
- Ключ приходит **в каждом соответствующем S3-запросе**.
- Обычная кнопка **Download** в Console не обязана уметь передавать пользовательский SSE-C-ключ; для проверки используем AWS CLI.

**Важно:** даже если объект виден в списке Console, это **не значит**, что его содержимое можно прочитать без клиентского ключа.

## 4. Лаборатория: подготовка ключа и HTTPS

Выполняй в каталоге лаборатории, где находится `tls/rustfs_cert.pem` из урока 16:

```fish
openssl rand -out sse-c.key 32
chmod 600 sse-c.key
printf 'SSE-C private object\n' > sse-c.txt
set EP https://127.0.0.1:9000
```

Создай бакет `lesson19` через Console. Убедись, что настроены credentials AWS CLI.

> [!warning] Не используй для SSE-C локальный `http://127.0.0.1:9000` и не передавай ключ через `curl -k` как замену проверке сертификата. Никогда не публикуй `sse-c.key`.

## 5. Запись и три варианта чтения

**Загрузка:**

```fish
aws --ca-bundle tls/rustfs_cert.pem --endpoint-url $EP \
  s3api put-object --bucket lesson19 --key protected.txt \
  --body sse-c.txt --sse-customer-algorithm AES256 \
  --sse-customer-key fileb://sse-c.key
```

**Чтение без ключа** (должно завершиться отказом):

```fish
aws --ca-bundle tls/rustfs_cert.pem --endpoint-url $EP \
  s3api get-object --bucket lesson19 --key protected.txt no-key.txt
```

**Чтение с исходным ключом:**

```fish
aws --ca-bundle tls/rustfs_cert.pem --endpoint-url $EP \
  s3api get-object --bucket lesson19 --key protected.txt \
  --sse-customer-algorithm AES256 \
  --sse-customer-key fileb://sse-c.key downloaded.txt
cmp sse-c.txt downloaded.txt
```

Проверь отрицательный сценарий: создай **другой** 32-байтовый ключ и повтори `GetObject` с ним. Чтение не должно возвращать исходные данные. При отличиях поведения зафиксируй HTTP-ошибку и версию RustFS.

## 6. Архитектурные последствия

- Приложению нужен безопасный **key management** и сопоставление объекта с его ключом.
- Права `s3:GetObject` **недостаточно** для чтения SSE-C-объекта без правильного ключа.
- SSE-C-ключ нельзя помещать в URL, логи, Git или метаданные объекта.
- Обычная presigned GET-ссылка сама по себе **не передаёт** требуемые SSE-C-заголовки: получателю нужен поддерживающий их клиент и сам ключ.
- Изменение default SSE-S3/SSE-KMS для бакета не удаляет требование старого SSE-C-ключа для уже записанного объекта.

## 7. Самостоятельные задания и результат

- [ ] Объясни, почему SSE-C — не client-side encryption.
- [ ] Сравни чтение без ключа, с неправильным ключом и с исходным ключом.
- [ ] Объясни разницу между S3 Access Key и клиентским AES-ключом SSE-C.
- [ ] Назови последствия потери `sse-c.key`.

> [!success] Результат
> В SSE-C ключ контролирует клиент, но шифрование выполняет RustFS. Ключ нужен **повторно при чтении**, поэтому утрата ключа равнозначна утрате доступа к данным.

## 8. Источники

- [RustFS — SSE-C](https://docs.rustfs.com/en/security-compliance/encryption/sse-c)
- [AWS CLI — Binary parameters via `fileb://`](https://docs.aws.amazon.com/cli/v1/userguide/cli-usage-parameters-file.html)
- [AWS S3 — SSE-C](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerSideEncryptionCustomerKeys.html)

**Следующий урок:** №20 — CORS.  
**Дата сверки документации:** 2026-10-23.
