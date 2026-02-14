"""Сериализация сообщений Telegram в различные форматы."""

import os
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument,
    MessageMediaPoll, MessageMediaGeo, MessageMediaGeoLive,
    MessageMediaContact, MessageMediaWebPage, MessageMediaStory,
    DocumentAttributeFilename, DocumentAttributeVideo,
    DocumentAttributeAudio, DocumentAttributeSticker,
)

from tg_export.utils import sanitize_filename


def serialize_message(message, media_file=None):
    """
    Конвертировать сообщение Telethon в JSON-совместимый словарь.

    Полный набор полей: id, date, edit_date, text, message_type, media_file,
    topic_id, sender, reply_to, forward_from, reactions, views, forwards, post_author.
    """
    msg_data = {
        "id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "edit_date": message.edit_date.isoformat() if message.edit_date else None,
        "text": message.text or "",
        "message_type": type(message.media).__name__ if message.media else "text",
        "media_file": media_file,
    }

    # topic_id из reply_to (для форумов)
    if (message.reply_to
            and hasattr(message.reply_to, 'forum_topic') and message.reply_to.forum_topic
            and hasattr(message.reply_to, 'reply_to_msg_id')):
        msg_data["topic_id"] = message.reply_to.reply_to_msg_id
    else:
        msg_data["topic_id"] = None

    # Отправитель
    if message.sender:
        msg_data["sender"] = {
            "id": message.sender_id,
            "first_name": getattr(message.sender, 'first_name', None),
            "last_name": getattr(message.sender, 'last_name', None),
            "username": getattr(message.sender, 'username', None),
            "phone": getattr(message.sender, 'phone', None),
        }
    else:
        msg_data["sender"] = None

    # Ответ на сообщение
    if message.reply_to:
        if hasattr(message.reply_to, 'reply_to_msg_id'):
            reply_data = {"message_id": message.reply_to.reply_to_msg_id}
            if hasattr(message.reply_to, 'reply_to_top_id'):
                reply_data["top_id"] = message.reply_to.reply_to_top_id
            if hasattr(message.reply_to, 'forum_topic'):
                reply_data["forum_topic"] = message.reply_to.forum_topic
        else:
            # MessageReplyStoryHeader — ответ на сторис
            reply_data = {"story_id": getattr(message.reply_to, 'story_id', None)}
        msg_data["reply_to"] = reply_data
    else:
        msg_data["reply_to"] = None

    # Пересылка
    if message.forward:
        forward_data = {
            "date": message.forward.date.isoformat() if message.forward.date else None,
            "from_name": message.forward.from_name,
        }
        if message.forward.from_id:
            if hasattr(message.forward.from_id, 'user_id'):
                forward_data["from_id"] = message.forward.from_id.user_id
            elif hasattr(message.forward.from_id, 'channel_id'):
                forward_data["from_id"] = message.forward.from_id.channel_id
            else:
                forward_data["from_id"] = None
        else:
            forward_data["from_id"] = None
        msg_data["forward_from"] = forward_data
    else:
        msg_data["forward_from"] = None

    # Реакции
    if hasattr(message, 'reactions') and message.reactions:
        msg_data["reactions"] = [
            {
                "emoticon": getattr(r.reaction, 'emoticon', None),
                "count": r.count,
            }
            for r in message.reactions.results
        ]
    else:
        msg_data["reactions"] = []

    # Статистика
    msg_data["views"] = message.views
    msg_data["forwards"] = message.forwards
    msg_data["post_author"] = message.post_author

    return msg_data


def _media_type_label(media):
    """Человеко-читаемая метка типа медиа."""
    if isinstance(media, MessageMediaPhoto):
        return "\U0001f4f7 Фото"
    if isinstance(media, MessageMediaDocument):
        doc = media.document
        if doc:
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeVideo):
                    if getattr(attr, 'round_message', False):
                        return "\U0001f4f9 Видеосообщение"
                    return "\U0001f3ac Видео"
                if isinstance(attr, DocumentAttributeAudio):
                    if getattr(attr, 'voice', False):
                        return "\U0001f3a4 Голосовое сообщение"
                    return "\U0001f3b5 Аудио"
                if isinstance(attr, DocumentAttributeSticker):
                    return "\U0001f4cc Стикер"
        return "\U0001f4ce Документ"
    if isinstance(media, MessageMediaPoll):
        return "\U0001f4ca Опрос"
    if isinstance(media, (MessageMediaGeo, MessageMediaGeoLive)):
        return "\U0001f4cd Геолокация"
    if isinstance(media, MessageMediaContact):
        return "\U0001f464 Контакт"
    if isinstance(media, MessageMediaStory):
        return "\U0001f4f1 Сторис"
    if isinstance(media, MessageMediaWebPage):
        return None  # URL уже в тексте
    return "\U0001f4ce Вложение"


def format_message_text(message):
    """Отформатировать сообщение для текстового экспорта."""
    sender_name = "Unknown"
    if message.sender:
        first = getattr(message.sender, 'first_name', '') or ''
        last = getattr(message.sender, 'last_name', '') or ''
        sender_name = f"{first} {last}".strip() or getattr(message.sender, 'username', '') or f"User_{message.sender_id}"

    date_str = message.date.strftime("%Y-%m-%d %H:%M") if message.date else ""
    text = message.text or "[media]"

    return f"[{date_str}] {sender_name}: {text}"


def format_message_markdown(message, media_path=None):
    """Отформатировать сообщение для markdown экспорта."""
    sender_name = "Unknown"
    if message.sender:
        first = getattr(message.sender, 'first_name', '') or ''
        last = getattr(message.sender, 'last_name', '') or ''
        sender_name = f"{first} {last}".strip() or f"@{getattr(message.sender, 'username', '')}" or f"User_{message.sender_id}"

    date_str = message.date.strftime("%d.%m.%Y %H:%M") if message.date else ""
    text = message.text or ""

    lines = [f"**{sender_name}** --- _{date_str}_"]

    if text:
        lines.append(text)

    if media_path:
        lines.append(f"\n![media](media/{media_path})")
    elif message.media:
        label = _media_type_label(message.media)
        if label:
            lines.append(f"_{label}_")

    return "\n".join(lines)


def get_media_filename(message):
    """Сгенерировать имя файла для медиа."""
    date_str = message.date.strftime("%Y%m%d_%H%M%S") if message.date else "unknown"

    if isinstance(message.media, MessageMediaPhoto):
        return f"{date_str}_{message.id}.jpg"

    elif isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        # Оригинальное имя файла
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                return f"{date_str}_{message.id}_{sanitize_filename(attr.file_name)}"

        # Расширение по mime-типу или атрибутам
        mime = doc.mime_type or ""
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeVideo):
                ext = "mp4" if "mp4" in mime else "video"
                return f"{date_str}_{message.id}.{ext}"
            if isinstance(attr, DocumentAttributeAudio):
                ext = "ogg" if "ogg" in mime else "mp3"
                return f"{date_str}_{message.id}.{ext}"
            if isinstance(attr, DocumentAttributeSticker):
                return f"{date_str}_{message.id}.webp"

        ext = mime.split('/')[-1] if mime else "bin"
        return f"{date_str}_{message.id}.{ext}"

    return f"{date_str}_{message.id}.bin"
