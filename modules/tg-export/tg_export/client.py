"""Фабрика Telegram-клиента и проверка авторизации."""

import os
import sys
from telethon import TelegramClient

from tg_export import config


def create_client():
    """Создать и вернуть TelegramClient."""
    config.validate()
    return TelegramClient(
        config.SESSION_NAME,
        config.get_api_id(),
        config.API_HASH,
    )


async def ensure_authorized(client):
    """
    Подключить клиент и проверить авторизацию.

    Returns:
        Объект текущего пользователя (me).
    """
    await client.connect()

    if not await client.is_user_authorized():
        session_file = f"{config.SESSION_NAME}.session"
        if os.path.exists(session_file):
            print("Сессия истекла. Выполните: tg-export auth")
        else:
            print("Сессия не найдена. Выполните: tg-export setup")
        sys.exit(1)

    me = await client.get_me()
    print(f"Вы вошли как: {me.first_name} (@{me.username})")
    return me
