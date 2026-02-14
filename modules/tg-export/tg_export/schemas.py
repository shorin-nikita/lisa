"""Нормализация структур экспорта: chat_info / entity_info / channel_info."""

from datetime import datetime


def get_export_info(data):
    """
    Извлечь метаданные из экспорта, независимо от формата.

    Поддерживает ключи: entity_info, chat_info, channel_info.
    Возвращает словарь с полями: id, name, type, username, export_date.
    """
    for key in ("entity_info", "chat_info", "channel_info"):
        if key in data:
            info = data[key]
            return {
                "id": info.get("id"),
                "name": info.get("name") or info.get("title"),
                "type": info.get("type"),
                "username": info.get("username"),
                "export_date": info.get("export_date"),
                "_original_key": key,
            }

    return {
        "id": None,
        "name": "Unknown",
        "type": None,
        "username": None,
        "export_date": None,
        "_original_key": None,
    }


def get_info_key(data):
    """Определить ключ метаданных в экспорте."""
    for key in ("entity_info", "chat_info", "channel_info"):
        if key in data:
            return key
    return None


def make_entity_info(entity, extra=None):
    """Создать стандартный блок entity_info для нового экспорта."""
    from tg_export.utils import get_entity_name

    info = {
        "id": entity.id,
        "name": get_entity_name(entity),
        "type": type(entity).__name__,
        "username": getattr(entity, 'username', None),
        "export_date": datetime.now().isoformat(),
    }
    if extra:
        info.update(extra)
    return info
