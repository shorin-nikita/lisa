# L.I.S.A. 2.0

**Локальная Интеллектуальная Система Автоматизации**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-blue)](https://www.docker.com/)

AI-агент на своём сервере — с памятью, интеграциями и мозгом.

> Не набор инструментов, а работающий AI-сотрудник из коробки.

---

## Быстрый старт

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/shorin-nikita/lisa/main/install.sh)
```

Одна команда. 5 минут. Готово.

---

## Что устанавливается

| Компонент | Роль | Порт |
|-----------|------|------|
| **OpenClaw** | Оркестрация агентов, каналы, HITL, память | 18789 |
| **PostgreSQL** | БД + pgvector для RAG | 5433 |
| **Redis** | Кэш, очереди, сессии | 6379 |
| Squid Proxy | Прокси для AI API (опционально) | 3128 |
| Caddy | HTTPS с автосертификатами (опционально) | 443 |

---

## Архитектура

```
Lisa 2.0
│
├── Ядро (устанавливается всегда)
│   ├── OpenClaw         → мозг: агенты, skills, каналы, HITL
│   ├── PostgreSQL       → память: данные + pgvector (RAG)
│   └── Redis            → скорость: кэш, очереди
│
├── Модули (ставятся по выбору)
│   ├── trends           → анализ трендов (Google, YouTube, Yandex)
│   ├── tg-export        → экспорт и анализ Telegram-чатов
│   ├── n8n              → визуальная автоматизация (400+ коннекторов)
│   ├── ollama           → локальные LLM (без API ключей)
│   ├── langfuse         → мониторинг LLM-вызовов
│   ├── whisper          → голос → текст
│   └── caddy            → HTTPS
│
└── Шаблоны агентов
    ├── sales            → квалификация лидов, запись на встречу
    ├── support          → FAQ + RAG по базе знаний
    ├── content          → анализ трендов + контент-план
    └── assistant        → календарь, задачи, почта
```

---

## Модули

### Trends Analyzer

Анализ трендов по ключевому слову из трёх источников:

- **Google Trends** — растущие и топовые запросы
- **YouTube Data API** — видео, просмотры, паттерны заголовков
- **Yandex Suggest** — связанные поисковые запросы

```bash
lisa trends "нейросети"
```

### Telegram Export

Экспорт и анализ данных из Telegram через MTProto API:

- Экспорт сообщений (JSON / Markdown)
- Статистический анализ чатов и каналов
- Аналитика контента (просмотры, реакции, лучшие посты)
- Автоматический pipeline: экспорт → эмбеддинги → RAG

```bash
lisa tg-export @channel --analyze
```

### Другие модули

```bash
lisa module install n8n        # визуальная автоматизация
lisa module install ollama      # локальные LLM
lisa module install langfuse    # мониторинг
lisa module install whisper     # голос в текст
```

---

## Шаблоны агентов

```bash
lisa agent create --template sales      # бот-продажник
lisa agent create --template support    # бот-поддержка
lisa agent create --template content    # контент-менеджер
lisa agent create --template assistant  # личный ассистент
```

### Sales Agent

Квалификация входящих лидов, скоринг, маршрутизация:
- Уверен в ответе (>=0.85) → отвечает автоматически
- Не уверен → эскалирует на человека (HITL)
- Результат: запись на консультацию или редирект на продукт

### Support Agent

FAQ-бот с RAG по базе знаний:
- Загрузи документы → агент отвечает по ним
- Telegram Export → автоматическая база знаний из чата
- Fallback на человека, если ответа нет

---

## Отличия от конкурентов

| | Lisa 2.0 | Dify | Flowise | LobeChat |
|---|----------|------|---------|----------|
| Агент из коробки | ✅ | ❌ | ❌ | ❌ |
| Persistent memory | ✅ | ❌ | ❌ | ❌ |
| HITL (эскалация) | ✅ | ❌ | ❌ | ❌ |
| Dynamic context | ✅ | ❌ | ❌ | ❌ |
| Анализ трендов | ✅ | ❌ | ❌ | ❌ |
| Telegram Export + RAG | ✅ | ❌ | ❌ | ❌ |
| Модульная архитектура | ✅ | ❌ | ❌ | ❌ |

---

## Системные требования

| | Минимум | Рекомендуется |
|---|---------|--------------|
| CPU | 2 ядра | 4+ ядер |
| RAM | 2 GB | 4+ GB |
| Диск | 10 GB SSD | 20+ GB SSD |
| ОС | Ubuntu 20.04+ / macOS | Ubuntu 22.04+ |
| Docker | 20.10+ | Последняя |
| Node.js | 22+ | 22+ |

> Для модуля Ollama (локальные LLM): NVIDIA GPU с 6+ GB VRAM рекомендуется

---

## PRO: Клуб PrideAI

Базовая Lisa — бесплатно. В клубе — готовые решения и поддержка:

- Готовые шаблоны агентов под бизнес-задачи
- Интеграции с CRM (Bitrix24, AmoCRM)
- Еженедельные разборы и уроки
- Чат с поддержкой от автора

**Цена:** 5 000 ₽/мес

**[Вступить в PrideAI →](https://t.me/prideaibot)**

---

## Нужно внедрение под ключ?

Интегрируем AI-агентов в ваш бизнес:
- Bitrix24, AmoCRM, WhatsApp, Telegram
- Автоматизация обработки заявок 24/7
- RAG, голосовые ассистенты, мультиканальность

**[aibot.direct](https://aibot.direct)** | **[@SHORIN1618](https://t.me/SHORIN1618)**

---

## Лицензия

[Apache 2.0](LICENSE) — свободное использование, включая коммерческое.

---

<div align="center">

**[GitHub Issues](https://github.com/shorin-nikita/lisa/issues)** | **[@PrideAIBot](https://t.me/prideaibot)** | **[@SHORIN1618](https://t.me/SHORIN1618)**

</div>
