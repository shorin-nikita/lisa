"""Авторизация в Telegram (интерактивная)."""

import asyncio
from telethon import TelegramClient

from tg_export import config


async def _auth():
    """Выполнить интерактивную авторизацию."""
    config.validate()

    print("=" * 60)
    print("Авторизация в Telegram")
    print("=" * 60)
    print()
    print("Вам потребуется ввести:")
    print("1. Номер телефона в международном формате (например, +79991234567)")
    print("2. Код подтверждения из Telegram")
    print("3. Пароль двухфакторной аутентификации (если включена)")
    print()

    client = TelegramClient(config.SESSION_NAME, config.get_api_id(), config.API_HASH)

    try:
        await client.start()

        me = await client.get_me()
        print()
        print("=" * 60)
        print("Авторизация успешна!")
        print(f"Вы вошли как: {me.first_name}")
        if me.username:
            print(f"Username: @{me.username}")
        print(f"ID: {me.id}")
        print()
        print(f"Файл сессии: {config.SESSION_NAME}.session")
        print()
        print("Теперь можно экспортировать чаты:")
        print("  tg-export export <source>")
        print("=" * 60)

    except Exception as e:
        print(f"\nОшибка авторизации: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.disconnect()


def run(args):
    """Точка входа для CLI."""
    asyncio.run(_auth())
