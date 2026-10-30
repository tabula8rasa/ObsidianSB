---
title: "S3 и RustFS — Урок 18. SSE-KMS и Vault"
aliases:
  - "S3: урок 18"
tags: [s3, rustfs, security, kms, vault, sse-kms, course]
lesson: 18
module: 2
status: study
---
# Урок 18. SSE-KMS: ключи, Vault и экран SSE Configuration

> [!abstract] Цель урока
> Разобраться в работе KMS, отличать SSE-KMS от SSE-S3, прочитать все основные поля экранa RustFS SSE Configuration и проверить связь с Vault Transit.

**Предварительные знания:** SSE-S3, TLS, Docker Compose.  
**Практическая среда:** RustFS Console, Docker Compose; для полной лаборатории — HashiCorp Vault.  
**Критерий завершения:** понятны поля KMS Console; создан ключ тестового Vault; проверены статус KMS и зашифрованная запись.  
**Время чтения:** до 5 минут; настройка Vault отдельно.

---

## 1. Чем SSE-KMS отличается от SSE-S3

Оба режима шифруют данные **на стороне RustFS** и используют ключ данных **DEK** для объекта. Различается способ выбора и управления защищающим ключом:

| Режим S3 | Кто выбирает ключ защиты DEK |
|---|---|
| **SSE-S3** (`AES256`) | RustFS использует настроенный ключ по умолчанию |
| **SSE-KMS** (`aws:kms`) | Клиент или правило бакета может указать **KMS key ID** |

В RustFS название `aws:kms` — стандартное значение **S3 API**, а не обещание интеграции с облачной службой **AWS KMS**. Бэкенды RustFS: `local`, `vault-kv2`, `vault-transit`.

## 2. Архитектура: данные отделены от мастер-ключа

```text
Клиент --> RustFS --> шифрованный объект на диске
              |
              +--> KMS --> ключ, защищающий DEK
```

При `PutObject` RustFS получает или создаёт DEK, шифрует им объект и сохраняет **завёрнутый (wrapped) DEK** вместе с метаданными. Для `GetObject` требуется возможность восстановить DEK.

**Доступность KMS — часть доступности объектов.** Ротация мастер-ключа не означает автоматического перешифрования всех старых байтов; старые версии ключей должны оставаться пригодными для чтения зависимых объектов.

## 3. Разбор присланного экрана SSE Configuration

| Поле | Что означает |
|---|---|
| **KMS Status Overview** | Сводка текущего состояния KMS |
| **Backend Type / Status / Health** | Выбранный бэкенд, состояние настройки и проверка его работоспособности |
| **Default SSE Key** | ID ключа KMS по умолчанию, **не само секретное значение ключа** |
| **KMS Backend** | Реализация хранилища ключей; на скриншоте выбран **HashiCorp Vault Transit Engine** |
| **Vault Server Address** | Адрес Vault **из контейнера RustFS**, не адрес в браузере |
| **Vault Token** | Секрет аутентификации RustFS в Vault; не S3 Access Key |
| **Vault Namespace** | Пространство имён Vault, если используется; иначе пусто |
| **Transit Mount Path** | Путь, на котором в Vault смонтирован Transit engine, например `transit` |
| **Skip TLS Verification** | Отключение проверки сертификата **Vault**; для рабочего сервера не включать |
| **Advanced TLS / Advanced Settings** | Доверенный CA и mTLS к Vault; устойчивость и настройки KMS-кеша |

`NOT CONFIGURED` и `Default SSE Key: Not set` на скриншоте означают: **KMS ещё не настроен**. Нажатие **Refresh** обновляет статус, но не создаёт ключ.

## 4. Что можно изменить через Console, а что — вне её

Экран даёт поля подключения к **Vault Transit** и кнопку **Save Configuration**. Реально работоспособное подключение требует **уже запущенного Vault и существующего Transit-ключа**.

В документации RustFS также поддерживаются настройки запуска сервера `RUSTFS_KMS_ENABLE`, `RUSTFS_KMS_BACKEND`, `RUSTFS_KMS_DEFAULT_KEY_ID`. Для **Local** и **Vault KV2** ориентируйся на конфигурацию сервера; не считай, что показанный UI поддерживает настройку всех типов бэкендов.

Проверяй **статус после сохранения и реальную запись**: состояние кнопки Save не является доказательством готовности шифрования.

## 5. Лаборатория: временный Vault Transit

> [!warning] Только изолированная локальная лаборатория. Vault в dev mode хранит ключи непостоянно и выдаёт root token. **После потери его состояния зашифрованные объекты могут стать нечитаемыми.** Не используй эту конфигурацию для настоящих данных.

Добавь **в существующий Compose-проект** второй сервис:

```yaml
services:
  vault:
    image: hashicorp/vault:1.19
    command: ["server", "-dev", "-dev-listen-address=0.0.0.0:8200"]
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: "lab-only-token"
      VAULT_TOKEN: "lab-only-token"
      VAULT_ADDR: "http://127.0.0.1:8200"
    ports:
      - "127.0.0.1:8200:8200"
```

Здесь показан фрагмент, который нужно **объединить с уже существующим `services.rustfs`**, не заменяя его. Выполни:

```bash
docker compose up -d vault
docker compose exec vault vault status
docker compose exec vault vault secrets enable transit
docker compose exec vault vault write -f transit/keys/rustfs-default-key
```

Затем открой **SSE Configuration** и заполни:

| Поле | Лабораторное значение |
|---|---|
| KMS Backend | `HashiCorp Vault Transit Engine` |
| Default SSE Key | `rustfs-default-key` |
| Vault Server Address | `http://vault:8200` |
| Vault Token | `lab-only-token` |
| Vault Namespace | пусто |
| Transit Mount Path | `transit` |
| Skip TLS Verification | выключено |

`127.0.0.1` внутри **контейнера RustFS** указывает на сам RustFS, поэтому адрес `http://127.0.0.1:8200` **не годится** для связи с соседним контейнером Vault.

Нажми **Save Configuration**, затем **Refresh**. Если KMS остаётся `NOT CONFIGURED`, попробуй предусмотренную документацией настройку запуска. Добавь в **существующий `environment` RustFS**:

```yaml
RUSTFS_KMS_ENABLE: "true"
RUSTFS_KMS_BACKEND: "vault-transit"
RUSTFS_KMS_VAULT_ADDRESS: "http://vault:8200"
RUSTFS_KMS_VAULT_TOKEN: "lab-only-token"
RUSTFS_KMS_VAULT_MOUNT_PATH: "transit"
RUSTFS_KMS_DEFAULT_KEY_ID: "rustfs-default-key"
RUSTFS_KMS_ALLOW_INSECURE_DEV_DEFAULTS: "true"
```

Примени `docker compose up -d` и проверь статус. **Небезопасные dev defaults разрешены только для этого локального теста.** Для рабочего Vault требуются HTTPS и секреты вне Compose.

## 6. Проверяем SSE-KMS через S3 API

После состояния KMS **healthy** создай бакет `lesson18` и загрузи файл:

```bash
printf 'KMS test\n' > kms.txt
set EP http://127.0.0.1:9000
aws --endpoint-url $EP s3api put-object \
  --bucket lesson18 --key kms.txt --body kms.txt \
  --server-side-encryption aws:kms \
  --ssekms-key-id rustfs-default-key
aws --endpoint-url $EP s3api head-object \
  --bucket lesson18 --key kms.txt
```

Если активировал TLS в уроке 16, используй `https://...` и `--ca-bundle tls/rustfs_cert.pem`. Проверь возвращаемый режим `aws:kms`, ID ключа и возможность `GetObject`. **При ошибке не приписывай её автоматически Vault:** выясни ответ API и состояние KMS.

## 7. Самостоятельные задания и результат

- [ ] Объясни разницу `DEK` и `KMS key ID`.
- [ ] Найди все поля скриншота и объясни, какие из них секретные.
- [ ] Добейся изменения `NOT CONFIGURED` только после реальной настройки Vault/KMS.
- [ ] Объясни, почему удаление ключа в Vault опаснее удаления правила SSE бакета.

> [!success] Результат
> SSE-KMS позволяет выбирать KMS-ключ и отделяет защиту данных от управления ключами. Экран RustFS настраивает **доступ к Vault**, а не шифрует объекты сам по себе.

## 8. Источники

- [RustFS — SSE-KMS / KMS backends](https://docs.rustfs.com/en/security-compliance/encryption/kms)
- [RustFS — Environment Variables: KMS](https://docs.rustfs.com/en/reference/environment-variables)
- [RustFS — SSE-S3](https://docs.rustfs.com/en/security-compliance/encryption/sse-s)

**Следующий урок:** №19 — SSE-C.  
**Дата сверки документации:** 2026-10-23.
