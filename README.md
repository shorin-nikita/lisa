# 🚀 Л.И.С.А. — Локальная Интеллектуальная Система Автоматизации

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green)](https://www.python.org/)

**Self-hosted AI Platform** — полностью готовый Docker Compose шаблон для быстрого развертывания локальной AI и Low Code среды разработки.

> 🎯 **Готово к работе "из коробки"** — все исправления и оптимизации уже внесены!

---

## 📋 Что включено

### 🖥️ **Основные компоненты**

✅ **[N8N](https://n8n.io/)** — Платформа автоматизации с 400+ интеграциями и AI компонентами  
✅ **[Supabase](https://supabase.com/)** — PostgreSQL БД с векторным поиском и аутентификацией  
✅ **[Ollama](https://ollama.com/)** — Платформа для локальных LLM (Llama, Mistral, etc.)  
✅ **[Open WebUI](https://openwebui.com/)** — ChatGPT-подобный интерфейс для общения с моделями  
✅ **[Whisper](https://github.com/openai/whisper)** — Распознавание речи OpenAI (Speech-to-Text)  
✅ **[FFmpeg](https://ffmpeg.org/)** — Обработка медиа-файлов (конвертация аудио/видео)

### 🎨 **Дополнительные сервисы**

✅ **[Flowise](https://flowiseai.com/)** — Визуальный конструктор AI-агентов  
✅ **[Qdrant](https://qdrant.tech/)** — Высокопроизводительное векторное хранилище  
✅ **[Neo4j](https://neo4j.com/)** — Граф-база знаний для GraphRAG  
✅ **[SearXNG](https://github.com/searxng/searxng)** — Приватный метапоисковик  
✅ **[Langfuse](https://langfuse.com/)** — Мониторинг и трейсинг LLM-операций  
✅ **[Caddy](https://caddyserver.com/)** — Автоматический HTTPS/SSL прокси

---

## 🎯 Ключевые возможности

- 🤖 **Автоматизация** — создавайте сложные workflows с помощью N8N
- 🎤 **Распознавание речи** — Whisper API для транскрибации аудио
- 🎬 **Медиа-обработка** — FFmpeg встроен в N8N для работы с видео/аудио
- 💾 **Векторный поиск** — RAG через Supabase и Qdrant
- 🌐 **Автоматический SSL** — Let's Encrypt сертификаты через Caddy
- 🔒 **Безопасность** — все данные остаются на вашем сервере

---

## ⚡ Быстрый старт

### Системные требования

- **ОС:** Linux (Ubuntu 20.04+), macOS, Windows (WSL2)
- **RAM:** Минимум 8 ГБ, рекомендуется 16+ ГБ
- **Диск:** Минимум 20 ГБ свободного места
- **Зависимости:** Docker 20.10+, Docker Compose, Python 3.8+

### Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/shorin-nikita/lisa.git
cd lisa

# 2. Запустить установщик
python3 CTAPT.py
```

Установщик автоматически:
- 🔍 Определит доступность GPU (NVIDIA/AMD)
- 🔐 Сгенерирует все необходимые секретные ключи
- ⚙️ Создаст файл `.env` с вашими параметрами
- 🐳 Соберёт и запустит все Docker контейнеры
- 📁 Создаст shared директорию с правильными правами

### Первый запуск

После установки откройте браузер:

```
🌐 Локальный доступ:
├─ N8N:        http://localhost:8001
├─ Open WebUI: http://localhost:8002
├─ Flowise:    http://localhost:8003
├─ Supabase:   http://localhost:8005
├─ Langfuse:   http://localhost:8007
└─ Neo4j:      http://localhost:8008

🔒 HTTPS (если настроен домен):
└─ https://ваш-домен.com
```

> 💡 **При первом запуске** создайте аккаунты в N8N и Open WebUI

---

## 🎤 Использование Whisper API

### В N8N workflows

Whisper доступен по адресу `http://whisper:8000` внутри Docker сети.

#### HTTP Request нода:

```
Method: POST
URL: http://whisper:8000/v1/audio/transcriptions

Body (multipart/form-data):
├─ file: [бинарный файл аудио]
└─ model: base (или tiny/small)
```

#### Пример curl:

```bash
curl -X POST http://whisper:8000/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=base"
```

### Рекомендации по моделям:

| Модель | Размер | Скорость | Точность | CPU |
|--------|--------|----------|----------|-----|
| `tiny` | 39 MB | ⚡⚡⚡ | ⭐⭐ | ✅ |
| `base` | 74 MB | ⚡⚡ | ⭐⭐⭐ | ✅ Рекомендуется |
| `small` | 244 MB | ⚡ | ⭐⭐⭐⭐ | ⚠️ Медленно |
| `medium` | 769 MB | 🐢 | ⭐⭐⭐⭐⭐ | ❌ Падает |

---

## 🎬 Обработка медиа-файлов

FFmpeg встроен в N8N для обработки видео и аудио.

### Конвертация видео → аудио

Используйте ноду **Execute Command** в N8N:

```bash
ffmpeg -i /data/shared/video.mp4 \
  -q:a 0 -map a \
  /data/shared/audio.wav
```

### Полный workflow: Видео → Транскрипция

1. **Загрузка видео** → сохранение в `/data/shared/`
2. **Execute Command** → извлечение аудио через FFmpeg
3. **HTTP Request** → транскрибация через Whisper API
4. **Сохранение текста** → в БД или файл

### Shared директория

Все медиа-файлы доступны в `/data/shared/` внутри контейнера N8N:

```
shared/
├── video.mp4      # Входные файлы
├── audio.wav      # Обработанные файлы
└── transcript.txt # Результаты
```

---

## 🔧 Управление системой

### Команды Docker Compose

   ```bash
# Просмотр статуса
docker ps

# Логи всех сервисов
docker compose -p localai logs -f

# Логи конкретного сервиса
docker logs n8n -f
docker logs whisper -f

# Остановка системы
docker compose -p localai down

# Перезапуск
python3 start_services.py
```

### Мониторинг ресурсов

```bash
# Использование CPU/RAM контейнерами
docker stats

# Использование диска
docker system df
```

---

## 🛠️ Конфигурация

### Файл `.env`

После первой установки создаётся файл `.env` с параметрами:

```bash
# Домены (для HTTPS)
N8N_HOSTNAME=n8n.yourdomain.com
WEBUI_HOSTNAME=webui.yourdomain.com

# Email для Let's Encrypt (ВАЖНО: используйте настоящий!)
LETSENCRYPT_EMAIL=your@email.com

# JWT секреты (генерируются автоматически)
JWT_SECRET=...
ANON_KEY=...
SERVICE_ROLE_KEY=...
```

> ⚠️ **Важно:** Для HTTPS используйте **настоящий email** — Let's Encrypt не принимает фейковые (test@test.test)

### Изменение настроек

Если нужно изменить параметры:

```bash
# 1. Остановить систему
docker compose -p localai down

# 2. Отредактировать .env
nano .env

# 3. Перезапустить
python3 start_services.py
```

---

## 🔒 Безопасность

- ✅ **Автоматический SSL** — Let's Encrypt сертификаты через Caddy
- ✅ **Генерация ключей** — все секреты создаются автоматически
- ✅ **Firewall** — автонастройка UFW (порты 80, 443, 22)
- ✅ **Изолированная сеть** — все контейнеры в отдельной Docker сети
- ✅ **Локальные данные** — ничего не отправляется на сторонние серверы

---

## 📊 Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                         Caddy (HTTPS/SSL)                   │
│                    ports: 80, 443, 8001-8008                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    localai_default network                  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   N8N    │  │  Whisper │  │ Supabase │  │  Ollama  │  │
│  │ +FFmpeg  │  │  :8000   │  │  :8000   │  │ :11434   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ OpenWebUI│  │ Flowise  │  │  Qdrant  │  │  Neo4j   │  │
│  │  :8080   │  │  :3001   │  │  :6333   │  │  :7474   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🐛 Решение проблем

### HTTPS не работает

**Проблема:** `ERR_SSL_PROTOCOL_ERROR` или `ERR_CONNECTION_TIMED_OUT`

**Решение:**
1. Проверьте email в `.env` — должен быть настоящим
2. Проверьте DNS — A-записи должны указывать на ваш сервер
3. Проверьте логи Caddy: `docker logs caddy -f`
4. Очистите DNS кэш на клиенте:
```bash
   # Mac
   sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
   
   # Linux
   sudo systemd-resolve --flush-caches
   
   # Windows
   ipconfig /flushdns
   ```

### Whisper падает с ошибкой

**Проблема:** `socket hang up` или `ECONNRESET`

**Решение:**
- Используйте модель `base` вместо `medium` или `large` для CPU
- Проверьте логи: `docker logs whisper -f`
- Перезапустите: `docker restart whisper`

### FFmpeg не найден в N8N

**Проблема:** `ffmpeg: not found` или `ffprobe: not found`

**Решение:**
- Убедитесь, что N8N собран из custom Dockerfile:
  ```bash
  docker inspect n8n | grep n8n-ffmpeg
  ```
- Пересоберите образ:
  ```bash
  docker compose -p localai build n8n
  docker compose -p localai up -d n8n
  ```

### Permission denied при записи в shared/

**Проблема:** `Permission denied` при сохранении файлов

**Решение:**
```bash
chmod 777 shared/
```

Это будет исправлено автоматически при следующем запуске `start_services.py`.

### PostgreSQL не запускается

**Проблема:** `container localai-postgres-1 is unhealthy`

**Решение:**
1. Проверьте логи: `docker logs localai-postgres-1`
2. Убедитесь, что используется PostgreSQL 16: `grep POSTGRES_VERSION .env`
3. Очистите тома и перезапустите:
   ```bash
   docker compose -p localai down -v
   python3 CTAPT.py
   ```

### ClickHouse ошибки аутентификации

**Проблема:** `Authentication failed: password is incorrect`

**Решение:**
- Пароль не должен содержать символы `$` и `@`
- Пересоздайте `.env` через `python3 CTAPT.py`
- Или вручную замените пароль в `.env` на пароль без спецсимволов

---

## 🎓 Примеры использования

### 1. Транскрибация голосовых сообщений

**Workflow:**
1. Webhook получает аудио файл
2. FFmpeg конвертирует в WAV (если нужно)
3. Whisper распознаёт текст
4. Текст сохраняется в Supabase

### 2. Автоматическая обработка видео

**Workflow:**
1. N8N загружает видео из облака
2. FFmpeg извлекает аудио
3. Whisper создаёт субтитры
4. Суббтитры загружаются обратно в облако

### 3. RAG с голосовым интерфейсом

**Workflow:**
1. Пользователь отправляет голосовой вопрос
2. Whisper преобразует в текст
3. Qdrant находит релевантные документы
4. Ollama генерирует ответ
5. Ответ отправляется пользователю

---

## 📚 Полезные ссылки

- 📖 [N8N документация](https://docs.n8n.io/)
- 🎤 [Whisper API](https://github.com/fedirz/faster-whisper-server)
- 🎬 [FFmpeg гайды](https://ffmpeg.org/documentation.html)
- 🗄️ [Supabase документация](https://supabase.com/docs)
- 🦙 [Ollama модели](https://ollama.com/library)

---

## 🤝 Вклад в проект

Мы приветствуем ваш вклад! 

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## 📝 Лицензия

Распространяется под лицензией Apache 2.0. См. `LICENSE` для дополнительной информации.

---

## 💬 Поддержка

**GitHub Issues:** [https://github.com/shorin-nikita/lisa/issues](https://github.com/shorin-nikita/lisa/issues)

---

## 👤 Автор

**Никита Шорин (shorin-nikita)**
- GitHub: [@shorin-nikita](https://github.com/shorin-nikita)
- Проект: Л.И.С.А. — Локальная Интеллектуальная Система Автоматизации

---

## ⭐ Благодарности

Проект основан на:
- [N8N Self-hosted AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit)
- [Cole's Enhanced Template](https://github.com/coleam00/ottomator-agents)

Спасибо всем контрибьюторам! 🎉

---

<div align="center">

**Сделано с ❤️ для русскоязычного AI-коммьюнити**

[⬆ Наверх](#-лиса--локальная-интеллектуальная-система-автоматизации)

</div>
