"""Утилиты: парсинг источников, имена файлов, имена сущностей."""

import re
from telethon.tl.types import User, Chat, Channel


def parse_source(source):
    """
    Распарсить идентификатор источника Telegram.

    Поддерживаемые форматы:
      - https://t.me/c/CHAT_ID (приватная группа/канал)
      - https://t.me/c/CHAT_ID/TOPIC_ID (топик форума)
      - https://t.me/username (публичный канал/группа/пользователь)
      - @username
      - +79001234567 (номер телефона)
      - 1234567890 (числовой ID)

    Returns:
        (identifier, source_type, topic_id)
    """
    source = source.strip()

    # Приватный чат/канал: https://t.me/c/CHAT_ID или https://t.me/c/CHAT_ID/TOPIC_ID
    private_match = re.match(r'https://t\.me/c/(\d+)(?:/(\d+))?', source)
    if private_match:
        chat_id = private_match.group(1)
        topic_id = private_match.group(2)
        return int(f"-100{chat_id}"), "private_chat", int(topic_id) if topic_id else None

    # Публичный канал/группа: https://t.me/username
    public_match = re.match(r'https://t\.me/([a-zA-Z0-9_]+)', source)
    if public_match:
        return public_match.group(1), "public", None

    # @username
    if source.startswith('@'):
        return source[1:], "username", None

    # Номер телефона
    if source.startswith('+') and source[1:].replace(' ', '').isdigit():
        return source, "phone", None

    # Числовой ID
    if source.lstrip('-').isdigit():
        num = int(source)
        if num < 0:
            return num, "chat_id", None
        return num, "user_id", None

    # По умолчанию — username
    return source, "username", None


def sanitize_filename(name):
    """Привести имя к безопасному имени файла."""
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    safe_name = safe_name.strip('. ')
    return safe_name[:200] if safe_name else "unknown"


def get_entity_name(entity):
    """Получить отображаемое имя для любого типа сущности Telegram."""
    if isinstance(entity, User):
        parts = [entity.first_name or '', entity.last_name or '']
        name = ' '.join(p for p in parts if p).strip()
        return name or entity.username or f"User_{entity.id}"
    elif isinstance(entity, (Chat, Channel)):
        return entity.title or f"Chat_{entity.id}"
    return f"Entity_{getattr(entity, 'id', 'unknown')}"
