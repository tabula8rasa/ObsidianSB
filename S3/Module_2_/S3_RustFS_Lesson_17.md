---
title: "S3 и RustFS — Урок 17. Уведомления о событиях"
aliases:
  - "S3: урок 17"
tags:
  - s3
  - rustfs
  - events
  - course
lesson: 17
module: 2
status: study
---

# Урок 17. Event Notifications: от загрузки объекта к обработчику

> [!abstract] Цель урока
> Получить уведомление о создании объекта и понять, почему надёжному обработчику нужны очередь, повторы и защита от повторной обработки.

**Предварительные знания:** PUT/DELETE, версионирование, политики доступа, Docker Compose.  
**Практическая среда:** локальный RustFS, AWS CLI с настроенными реквизитами, терминал `fish`.  
**Критерий завершения:** после загрузки файла получен JSON с именем события, бакетом и ключом.  
**Время чтения:** до 5 минут; практика выполняется отдельно.

---

## 1. Зачем отделять загрузку от обработки

После загрузки фотографии нужно создать миниатюру. Если делать это внутри запроса пользователя, длительность загрузки начинает зависеть от обработки изображения. **Event Notification** сообщает потребителю об изменении объекта, позволяя выполнить работу отдельно.

Уведомление содержит описание события, а не содержимое файла. Обработчик при необходимости читает объект через S3 API со своими правами. Успешный PUT подтверждает сохранение объекта, но не готовность миниатюры. 

## 2. Правило, получатель и обработчик

Уведомления имеют две независимые настройки: адрес получателя и правило бакета. Правило выбирает события, например `s3:ObjectCreated:*`, и при необходимости ограничивает ключи префиксом `incoming/`.

В AWS получателями служат SQS, SNS, Lambda и EventBridge. Произвольный HTTP webhook не является прямым получателем обычной конфигурации S3 Notifications: нужен промежуточный сервис. В RustFS официально описаны webhook-цели и правила через `QueueConfigurations`. Queue в JSON не означает AWS SQS.

Очередь позволяет пережить временную недоступность обработчика и распределить работу между исполнителями. Webhook — способ отправить HTTP-запрос получателю; наличие HTTP само по себе не гарантирует сохранение недоставленного сообщения.

## 3. Гарантии и опасные предположения

AWS проектирует доставку по принципу **как минимум один раз**: возможны дубликаты и задержки. Порядок поступления событий не гарантируется. Поэтому обработчик должен быть **идемпотентным**: повтор события не создаёт вторую миниатюру или повторное начисление.

Для AWS поле `sequencer` помогает сравнивать события одного ключа, но не устанавливает общий порядок между разными объектами. Ключ в сообщении URL-кодирован; декодируй его до обращения к API. Если есть `versionId`, чтение конкретной версии защищает от случайной обработки более новой перезаписи.

> [!warning] Не запускай бесконечный цикл
> Если обработчик пишет результат в тот же отслеживаемый префикс, результат снова вызывает обработчик. Разделяй `incoming/` и `processed/` либо используй разные бакеты.

## 4. Практика: получаем локальный webhook

Используй отдельный учебный бакет `s3-course-events`, созданный через Console. Сначала проверь документацию установленной версии: приведённая конфигурация соответствует текущему руководству RustFS. 

Создай `receiver.py`:

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
class Receiver(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200); self.end_headers()
    def do_POST(self):
        print(self.rfile.read(int(self.headers['Content-Length'])).decode(), flush=True)
        self.send_response(204); self.end_headers()
HTTPServer(('0.0.0.0', 8080), Receiver).serve_forever()
```

Добавь сервис в существующий раздел `services`:

```yaml
  receiver:
    image: python:3.12-alpine
    command: python /receiver.py
    volumes:
      - ./receiver.py:/receiver.py:ro
```

В `environment` сервиса `rustfs` добавь:

```yaml
      RUSTFS_NOTIFY_ENABLE: "true"
      RUSTFS_NOTIFY_WEBHOOK_ENABLE_PRIMARY: "on"
      RUSTFS_NOTIFY_WEBHOOK_ENDPOINT_PRIMARY: http://receiver:8080/events
      RUSTFS_OUTBOUND_ALLOW_ORIGINS: http://receiver:8080
```

Адрес доступен внутри сети Compose; `localhost` внутри RustFS означал бы сам контейнер. Приёмник отвечает на проверочный HEAD и печатает POST. 

Запусти получателя, затем пересоздай RustFS без удаления томов:

```fish
docker compose up -d receiver
docker compose up -d rustfs
```

Создай `notification.json`:

```json
{"QueueConfigurations":[{"Id":"lesson17","QueueArn":"arn:rustfs:sqs:us-east-1:primary:webhook","Events":["s3:ObjectCreated:*"]}]}
```

Примени правило и загрузи небольшой файл:

```fish
aws --endpoint-url http://127.0.0.1:9000 --region us-east-1 s3api put-bucket-notification-configuration --bucket s3-course-events --notification-configuration file://notification.json
printf 'event test\n' > event.txt
aws --endpoint-url http://127.0.0.1:9000 --region us-east-1 s3 cp event.txt s3://s3-course-events/incoming/event.txt
docker compose logs --tail=20 receiver
```

Найди событие создания, бакет и ключ. Сохранённое правило без фактической доставки не доказывает работоспособность. При отсутствии сообщения проверь логи RustFS, доступность получателя и соответствие ARN версии сервера.

## 5. Что показал эксперимент

Ты настроил маршрут события отдельно от операции записи. Получатель подтвердил HTTP-доставку, но эксперимент не проверил восстановление очереди после сбоя или выполнение прикладной работы. Гарантии RustFS проверяются отдельно.

> [!important] Изменение конфигурации
> `PutBucketNotificationConfiguration` заменяет всю конфигурацию бакета. Сохраняй существующие правила, если меняешь настройки общего бакета.

## 6. Самостоятельные задания

1. Повторно передай сохранённое сообщение мысленно: какие данные помогут не выполнить работу дважды?
2. Добавь событие `s3:ObjectRemoved:*`, удали учебный объект и сравни сообщение с созданием. При versioning различай удаление версии и появление delete marker.
3. Объясни, почему подтверждение webhook до надёжного сохранения задания может привести к потере работы.

## 7. Чеклист результата

- [ ] Я получил уведомление после загрузки.
- [ ] Я различаю правило бакета, получателя и обработчик.
- [ ] Я учитываю дубликаты и возможную перезапись объекта.
- [ ] Я исключил цикл обработки результатов.

**Следующий урок:** №18 — AWS SDK и boto3: клиент, endpoint, реквизиты, Client и Resource API.

## 8. Источники

- [AWS — Event Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html)
- [AWS — Структура сообщения](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html)
- [RustFS — Event Notifications](https://docs.rustfs.com/en/operations/event-notifications)

**Дата сверки:** 2026-10-20. Поддержку и формат уведомлений проверяй на установленной версии RustFS.
