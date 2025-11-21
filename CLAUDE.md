# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Л.И.С.А. — Локальная Интеллектуальная Система Автоматизации

Проект представляет собой полностью готовый Docker Compose шаблон для развертывания локальной AI и Low Code среды разработки. Включает N8N, Supabase, Ollama, Open WebUI, Whisper, FFmpeg и другие сервисы.

## Архитектура проекта

### Единая конфигурация

Система работает с единой конфигурацией, включающей все основные сервисы:

**Системные требования:**

*Минимальные:*
- CPU: 2 ядра
- RAM: 8GB
- Диск: 50GB

*Рекомендуемые:*
- CPU: 4+ ядер
- RAM: 8-12GB
- Диск: 50GB

> **Примечание:** Минимальная конфигурация (2 CPU / 8GB RAM) подходит для работы с небольшими моделями Ollama (llama3.2:1b, phi3.5:mini). Для комфортной работы с более крупными моделями рекомендуется 4+ CPU и 12GB RAM.

**Включенные сервисы:**
- N8N + FFmpeg — автоматизация и медиа-обработка
- Ollama — локальные LLM (Llama3, Mistral)
- Open WebUI — ChatGPT-подобный интерфейс
- Supabase — PostgreSQL БД с векторным поиском (pgvector)
- Caddy — автоматический SSL/TLS
- Redis (Valkey) — кеш и очереди
- Qdrant — векторное хранилище
- Whisper — распознавание речи (Speech-to-Text)
- PostgreSQL — отдельная БД для N8N

### Структура Docker Compose

Проект использует модульную архитектуру Docker Compose:

- `docker-compose.yml` — основной файл с определениями всех сервисов
- `supabase/docker/docker-compose.yml` — включен через `include:`, содержит полный стек Supabase (PostgreSQL, Kong, GoTrue, PostgREST, Storage, etc.)
- `docker-compose.override.public.yml` — оверрайды для публичного доступа (с доменами)
- `docker-compose.override.private.yml` — оверрайды для локального доступа

Все контейнеры работают в единой Docker сети `localai_default` и используют общий project name `localai`.

### Профили Docker Compose

Ollama запускается через профили в зависимости от доступного GPU:
- `cpu` — CPU-only версия Ollama
- `gpu-nvidia` — версия с поддержкой NVIDIA GPU
- `gpu-amd` — версия с поддержкой AMD ROCm GPU

### Кастомный образ N8N

N8N использует кастомный Docker образ, собираемый из `n8n-ffmpeg/Dockerfile`:
- Базовый образ: `n8nio/n8n:latest`
- Добавлен FFmpeg для обработки медиа-файлов внутри workflows
- Образ собирается автоматически при первом запуске

## Команды управления системой

### Первая установка

```bash
# Запустить интерактивный установщик
python3 CTAPT.py
```

Установщик автоматически:
- Определяет доступный GPU (NVIDIA/AMD/CPU)
- Генерирует все секретные ключи
- Создаёт файл `.env` с конфигурацией
- Настраивает firewall (порты 80, 443, 22)
- Создаёт директорию `shared/` с правильными правами
- Клонирует репозиторий Supabase через sparse checkout
- Запускает все сервисы

### Обновление системы

```bash
# Обновить Л.И.С.А. до последней версии
python3 O6HOBA.py
```

Скрипт обновления:
- Определяет текущий профиль GPU и окружение
- Создаёт резервную копию (`.env`, `n8n/backup`, `neo4j/data`, `shared/`)
- Останавливает сервисы
- Получает обновления из Git
- Обновляет Docker образы
- Пересобирает n8n-ffmpeg образ
- Настраивает лимиты ресурсов в `.env` на основе доступных CPU/RAM
- Перезапускает систему

### Запуск сервисов вручную

```bash
# Запустить сервисы с указанием профиля
python3 start_services.py --profile cpu --environment public

# Параметры:
# --profile: cpu | gpu-nvidia | gpu-amd | none
# --environment: private | public
```

Скрипт `start_services.py`:
1. Валидирует `.env` файл (проверяет обязательные переменные)
2. Клонирует репозиторий Supabase (если отсутствует)
3. Создаёт директорию `shared/` с правами 777
4. Копирует `.env` в `supabase/docker/.env`
5. Останавливает существующие контейнеры
6. Запускает Supabase стек
7. Ожидает 30 секунд инициализации Supabase
8. Запускает AI стек
9. Ожидает готовности PostgreSQL контейнера (healthcheck)

### Управление Docker Compose

```bash
# Просмотр статуса всех контейнеров
docker ps

# Логи всех сервисов проекта
docker compose -p localai logs -f

# Логи конкретного сервиса
docker logs n8n -f
docker logs whisper -f
docker logs ollama -f

# Остановка всех сервисов
docker compose -p localai down

# Остановка с удалением volumes (УДАЛИТ ВСЕ ДАННЫЕ!)
docker compose -p localai down -v

# Пересборка конкретного образа
docker compose -p localai build n8n
docker compose -p localai up -d n8n

# Мониторинг ресурсов
docker stats
```

## Важные детали реализации

### Файл .env

Генерируется автоматически через `CTAPT.py`. Содержит:
- Секретные ключи N8N (`N8N_ENCRYPTION_KEY`, `N8N_USER_MANAGEMENT_JWT_SECRET`)
- Секретные ключи Supabase (`JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`)
- Пароли для PostgreSQL
- Домены для сервисов (`N8N_HOSTNAME`, `WEBUI_HOSTNAME`, `SUPABASE_HOSTNAME`)
- Email для Let's Encrypt (`LETSENCRYPT_EMAIL`)
- Лимиты ресурсов (`OLLAMA_CPU_LIMIT`, `POSTGRES_MEM_LIMIT`, etc.)

**ВАЖНО**: Используйте настоящий email для `LETSENCRYPT_EMAIL` — Let's Encrypt не принимает фейковые адреса.

### Supabase Integration

Supabase клонируется как подмодуль через sparse checkout:
```bash
git clone --filter=blob:none --no-checkout https://github.com/supabase/supabase.git
cd supabase
git sparse-checkout init --cone
git sparse-checkout set docker
git checkout master
```

Это позволяет получить только директорию `docker/` из огромного репозитория Supabase (~200MB вместо 2GB).

Основной `docker-compose.yml` включает Supabase через:
```yaml
include:
  - ./supabase/docker/docker-compose.yml
```

### Shared директория

Директория `shared/` используется для обмена файлами между контейнерами:
- N8N монтирует её как `/data/shared`
- Используется для временных файлов при обработке медиа через FFmpeg
- Должна иметь права 777 для записи из всех контейнеров

Создаётся автоматически скриптами `CTAPT.py` и `start_services.py`.

### N8N Workflows автоимпорт

При первом запуске контейнер `n8n-import` автоматически импортирует все workflows и credentials из `n8n/backup/`:

```yaml
n8n-import:
  container_name: n8n-import
  entrypoint: /bin/sh
  command:
    - "-c"
    - "n8n import:credentials --separate --input=/backup/credentials && n8n import:workflow --separate --input=/backup/workflows"
  volumes:
    - ./n8n/backup:/backup
```

Основной контейнер `n8n` зависит от успешного завершения импорта:
```yaml
depends_on:
  n8n-import:
    condition: service_completed_successfully
```

### Whisper API

Whisper предоставляет OpenAI-совместимый API для распознавания речи:
- Внутренний URL: `http://whisper:8000`
- Endpoint: `POST /v1/audio/transcriptions`
- Модели: `tiny`, `base` (по умолчанию), `small`
- Формат: multipart/form-data с полями `file` и `model`

Рекомендуется использовать модель `base` для CPU — оптимальный баланс скорости и точности.

### Caddy и SSL

Caddy автоматически получает Let's Encrypt сертификаты для доменов:
- Использует email из переменной `LETSENCRYPT_EMAIL`
- Поддерживает одновременный доступ по домену (HTTPS) и localhost:порт (HTTP)
- Переменные окружения могут содержать либо домен (`n8n.site.ru`), либо порт (`:8001`)

Пример из Caddyfile:
```
{$N8N_HOSTNAME}, :8001 {
    reverse_proxy n8n:5678
}
```

Если `N8N_HOSTNAME=n8n.site.ru`, Caddy настроит HTTPS с автоматическим сертификатом.
Если `N8N_HOSTNAME=:8001`, Caddy настроит HTTP на порту 8001.

### Firewall настройка

`CTAPT.py` автоматически настраивает UFW:
1. **СНАЧАЛА** добавляет правила для портов (22, 80, 443)
2. **ТОЛЬКО ПОТОМ** включает firewall
3. Проверяет успешность добавления SSH правила перед включением

Это критически важно для удалённых серверов — предотвращает блокировку SSH доступа.

### PostgreSQL healthcheck

Многие сервисы (N8N) зависят от PostgreSQL. Скрипт `start_services.py` ожидает готовности:

```python
def wait_for_postgres_healthy(timeout=120):
    # Проверяет статус healthcheck контейнера
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", "localai-postgres-1"],
        capture_output=True, text=True
    )
    status = result.stdout.strip()
    return status == "healthy"
```

Это предотвращает ошибки подключения при параллельном запуске сервисов.

### Resource Limits

Docker Compose использует resource limits для предотвращения захвата всех ресурсов:
- Ollama: 40% CPU и RAM (минимум 2 CPU, 4GB RAM)
- PostgreSQL: 20% CPU и RAM
- N8N: 15% CPU и RAM
- Qdrant: 10% CPU и RAM

Лимиты автоматически рассчитываются в `O6HOBA.py` на основе доступных ресурсов системы.

## Готовые N8N workflows

Все workflows находятся в `n8n/backup/workflows/`:

- **Telegram Bot.json** — полнофункциональный Telegram бот с транскрибацией голосовых, анализом изображений, аналитическими командами
- **HTTP Handle.json** — вспомогательный workflow для настройки webhooks
- **Конвертация WebM → OGG + Транскрибация.json** — автоматическая конвертация видео в аудио с экстремальным сжатием
- **V1_Local_RAG_AI_Agent.json** — базовый RAG с Ollama
- **V2_Local_Supabase_RAG_AI_Agent.json** — RAG с векторной БД Supabase
- **V3_Local_Agentic_RAG_AI_Agent.json** — продвинутый агентный RAG

Импортируются автоматически при первом запуске через контейнер `n8n-import`.

## Решение типичных проблем

### FFmpeg не найден в N8N

Проблема: `ffmpeg: not found` при выполнении команды в N8N

Решение:
```bash
# Проверить, что используется кастомный образ
docker inspect n8n | grep n8n-ffmpeg

# Пересобрать образ
docker compose -p localai build n8n
docker compose -p localai up -d n8n
```

### PostgreSQL не запускается

Проблема: `container localai-postgres-1 is unhealthy`

Решение:
```bash
# Проверить логи
docker logs localai-postgres-1

# Убедиться в правильной версии PostgreSQL
grep POSTGRES_VERSION .env

# Очистить volumes и переустановить
docker compose -p localai down -v
python3 CTAPT.py
```

### Permission denied в shared/

Проблема: N8N не может записать файлы в `/data/shared`

Решение:
```bash
chmod 777 shared/
```

Это исправляется автоматически при запуске `start_services.py`.

### HTTPS не работает

Проблема: `ERR_SSL_PROTOCOL_ERROR` при доступе к домену

Проверить:
1. Email в `.env` должен быть настоящим (не `test@test.test`)
2. DNS A-записи должны указывать на IP сервера
3. Порты 80 и 443 должны быть открыты в firewall
4. Логи Caddy: `docker logs caddy -f`

### Whisper падает на больших файлах

Проблема: `socket hang up` или `ECONNRESET` при транскрибации

Решение:
- Используйте модель `base` вместо `medium`/`large` на CPU
- Разбивайте большие файлы на части (до 25MB)
- Убедитесь, что у контейнера достаточно памяти

## Порты сервисов

### Локальный доступ (HTTP)

- N8N: http://localhost:8001
- Open WebUI: http://localhost:8002
- Supabase: http://localhost:8005

### Внутренние порты (Docker сеть)

- N8N: n8n:5678
- Ollama: ollama:11434
- Open WebUI: open-webui:8080
- Whisper: whisper:8000
- Qdrant: qdrant:6333
- PostgreSQL (Supabase): db:5432
- PostgreSQL (N8N): postgres:5432
- Redis: redis:6379
- Kong (Supabase API): kong:8000

## Полезные ссылки

- [N8N документация](https://docs.n8n.io/)
- [Supabase self-hosting](https://supabase.com/docs/guides/self-hosting/docker)
- [Whisper faster-whisper-server](https://github.com/fedirz/faster-whisper-server)
- [Ollama модели](https://ollama.com/library)
- [FFmpeg документация](https://ffmpeg.org/documentation.html)
