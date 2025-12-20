# Л.И.С.А. — Локальная Интеллектуальная Система Автоматизации

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-blue)](https://www.docker.com/)

**Self-hosted AI платформа** — готовый Docker-шаблон для развёртывания локальной среды автоматизации с ИИ.

---

## Что если твоя CRM сама:

- Принимает заявки из **WhatsApp, Telegram, Instagram, VK, Avito**
- Понимает **текст, голос и фото**
- Отвечает клиенту **первой**
- Дожимает автоматически через **2/24 часа**
- Выводит менеджеру только **«готовых к сделке»**

**Это n8n + Bitrix24 + Supabase**, где RAG, мультиагенты и автодожимы работают как единый организм.

---

## Видео-инструкция

[![Видео-инструкция по установке](https://img.youtube.com/vi/vEwYIoZAFOY/maxresdefault.jpg)](https://youtu.be/vEwYIoZAFOY)

**[Смотреть установку на YouTube](https://youtu.be/vEwYIoZAFOY)** | **[Текстовая инструкция со скриншотами](https://aibot.direct/blog/lisa-install)**

---

## Что входит в Л.И.С.А.

| Компонент | Что делает |
|-----------|------------|
| **[N8N](https://n8n.io/)** | Автоматизация с 400+ интеграциями |
| **[Supabase](https://supabase.com/)** | PostgreSQL + векторный поиск для RAG |
| **[Ollama](https://ollama.com/)** | Локальные LLM (Llama, Mistral, Gemma) |
| **[Open WebUI](https://openwebui.com/)** | ChatGPT-подобный интерфейс |
| **[Whisper](https://github.com/fedirz/faster-whisper-server)** | Распознавание речи |
| **[Qdrant](https://qdrant.tech/)** | Векторное хранилище |
| **[Caddy](https://caddyserver.com/)** | Автоматический HTTPS |
| **FFmpeg** | Обработка аудио/видео |

---

## Быстрый старт

### 1. Арендуй VPS

Минимум **2 CPU / 8 GB RAM / 50 GB SSD** — этого хватит для старта.

Рекомендую **[Beget](https://beget.com/p2329622)** — стабильные серверы, быстрая поддержка.

### 2. Установи Л.И.С.А.

```bash
git clone https://github.com/shorin-nikita/lisa.git
cd lisa
python3 CTAPT.py
```

Скрипт сам определит GPU, сгенерирует ключи, настроит firewall и запустит контейнеры.

## Обновление

```bash
cd lisa
python3 O6HOBA.py
```

---

## Готовые шаблоны

При установке автоматически импортируются рабочие workflows:

| Шаблон | Описание |
|--------|----------|
| **Telegram Bot** | Бот с голосом, фото, памятью, аналитикой |
| **RAG L.I.S.A.** | RAG-агент с векторным поиском |
| **WebM → OGG + Транскрибация** | Конвертация видео + расшифровка речи |
| **HTTP Handle** | Настройка webhooks для Telegram/Wazzup |

---

## Продвинутые шаблоны — в PrideAIBot

Внутри сообщества **PrideAIBot** ты получишь:

- **Флагманскую CRM-систему** — полный разбор Bitrix24 + Wazzup + RAG + автодожимы
- Еженедельные уроки по N8N и промптингу
- Готовые workflows под реальные бизнес-задачи
- Поддержку и разборы кейсов

**[Telegram-канал: @prideaibot](https://t.me/prideaibot)**

---

## Системные требования

| | Минимум | Рекомендуется |
|---|---------|---------------|
| **CPU** | 2 ядра | 4+ ядер |
| **RAM** | 8 ГБ | 12 ГБ |
| **Диск** | 50 ГБ | 50 ГБ |
| **ОС** | Ubuntu 20.04+, macOS, Windows (WSL2) |

---

## Нужно внедрение под ключ?

Мы интегрируем ИИ-агентов в твой бизнес:
- Bitrix24, AmoCRM, WhatsApp, Telegram
- Автоматизация обработки заявок 24/7
- RAG, голосовые ассистенты, дожимы

**[aibot.direct](https://aibot.direct)** | **[@shorin_nikita](https://t.me/shorin_nikita)**

---

## Лицензия

Apache 2.0 — см. `LICENSE`

---

<div align="center">

**Сделано для русскоязычного AI-сообщества**

**[GitHub Issues](https://github.com/shorin-nikita/lisa/issues)** | **[@prideaibot](https://t.me/prideaibot)** | **[@shorin_nikita](https://t.me/shorin_nikita)**

</div>
