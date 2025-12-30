# Л.И.С.А. — Локальная Интеллектуальная Система Автоматизации

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-blue)](https://www.docker.com/)

**Бесплатная self-hosted AI платформа** — разверни локальный ИИ на своём сервере за 5 минут.

---

## Зачем это нужно

- **Без подписок** — никаких ежемесячных платежей за API
- **Данные у тебя** — ничего не уходит на сторонние серверы
- **Всё в одном** — N8N, Ollama, Whisper, Supabase, векторный поиск
- **Готово к работе** — установил и пользуйся, без танцев с бубном

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
| **[Whisper](https://github.com/fedirz/faster-whisper-server)** | Распознавание речи |
| **[Qdrant](https://qdrant.tech/)** | Векторное хранилище |
| **[Caddy](https://caddyserver.com/)** | Автоматический HTTPS |
| **[FFmpeg](https://ffmpeg.org/)** | Обработка аудио/видео |

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

| Шаблон | Описание | Уровень |
|--------|----------|---------|
| **Telegram Bot** | Бот с голосом, фото, памятью | Бесплатно |
| **RAG L.I.S.A.** | RAG-агент с векторным поиском | Бесплатно |
| **WebM → OGG + Транскрибация** | Конвертация видео + расшифровка | Бесплатно |
| **HTTP Handle** | Webhooks для Telegram/Wazzup | Бесплатно |

---

## PRO: Bitrix24 + RAG Agent — флагманская система

Базовая Л.И.С.А. — бесплатно. В клубе — готовая CRM-система на стероидах.

**Что если твоя CRM сама:**
- принимает заявки из WhatsApp, Telegram, Instagram, VK, Avito
- понимает текст, голос и фото
- отвечает клиенту первой
- дожимает автоматически через 2/24 часа
- и выводит менеджеру только «готовых к сделке»?

**Я собрал такую систему.** Это n8n + Bitrix24 + Supabase, где RAG, мультиагенты и автодожимы работают как единый организм.

**Что внутри:**
- Bitrix24: воронки, статусы, вебхуки
- Подключение WhatsApp и Telegram через Wazzup
- Supabase: база знаний для агента
- Оркестратор + RAG в n8n
- Follow-up и дожимы
- Автоматическое создание сделок и задач

**Что ещё в клубе:**
- 20+ готовых n8n workflows
- Еженедельные разборы и уроки
- Чат с поддержкой

**Цена:** 5 000 ₽/мес

**[Вступить в PrideAIBot →](https://t.me/prideaibot)**

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
