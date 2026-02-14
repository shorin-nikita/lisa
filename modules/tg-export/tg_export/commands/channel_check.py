"""Проверка владения каналом: поиск каналов, где пользователь является создателем."""

import asyncio
from telethon.tl.types import Channel, User
from telethon.errors import ChannelPrivateError, ChatAdminRequiredError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import PeerChannel

from tg_export.client import create_client, ensure_authorized


async def _get_user_entity(client, identifier):
    """Получить пользователя по ID или username."""
    try:
        entity = await client.get_entity(identifier)
        if isinstance(entity, User):
            return entity
    except Exception as e:
        print(f"Не удалось найти пользователя: {e}")
    return None


async def _check_channel_by_username(client, username, user_id):
    """Быстрая проверка канала по username."""
    try:
        entity = await client.get_entity(username)
        if isinstance(entity, Channel) and entity.broadcast:
            full_channel = await client(GetFullChannelRequest(channel=entity))
            if hasattr(full_channel.full_chat, 'creator_id') and full_channel.full_chat.creator_id == user_id:
                return {
                    'id': entity.id,
                    'title': entity.title,
                    'username': entity.username,
                    'participants_count': getattr(full_channel.full_chat, 'participants_count', None) or getattr(entity, 'participants_count', None),
                    'source': 'username_direct',
                }
    except Exception:
        pass
    return None


async def _check_user_full_info(client, user_entity):
    """Проверить связанные каналы из профиля пользователя."""
    channels = []
    try:
        full_user = await client(GetFullUserRequest(user_entity))
        linked_chat_id = None

        if hasattr(full_user, 'full_user') and hasattr(full_user.full_user, 'linked_chat_id'):
            linked_chat_id = full_user.full_user.linked_chat_id

        if linked_chat_id:
            try:
                if isinstance(linked_chat_id, int):
                    linked_entity = await client.get_entity(PeerChannel(linked_chat_id))
                else:
                    linked_entity = await client.get_entity(linked_chat_id)

                if isinstance(linked_entity, Channel) and linked_entity.broadcast:
                    full_channel = await client(GetFullChannelRequest(channel=linked_entity))
                    participants_count = getattr(full_channel.full_chat, 'participants_count', None)
                    channels.append({
                        'id': linked_entity.id,
                        'title': linked_entity.title,
                        'username': linked_entity.username,
                        'participants_count': participants_count or getattr(linked_entity, 'participants_count', None),
                        'source': 'linked_chat',
                    })
                    print(f"  Связанный канал: {linked_entity.title}")
            except Exception as e:
                print(f"  Не удалось получить связанный канал: {e}")
    except Exception as e:
        print(f"  Не удалось получить полную информацию: {e}")
    return channels


async def _find_channels_in_dialogs(client, user_id):
    """Поиск каналов-владельца во всех диалогах."""
    channels = []
    checked = 0
    try:
        print(f"Поиск каналов во всех диалогах...")
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, Channel) and entity.broadcast:
                checked += 1
                if checked % 10 == 0:
                    print(f"  Проверено каналов: {checked}...", end='\r')
                try:
                    full_channel = await client(GetFullChannelRequest(channel=entity))
                    if hasattr(full_channel.full_chat, 'creator_id') and full_channel.full_chat.creator_id == user_id:
                        participants_count = getattr(full_channel.full_chat, 'participants_count', None)
                        channels.append({
                            'id': entity.id,
                            'title': entity.title,
                            'username': entity.username,
                            'participants_count': participants_count or getattr(entity, 'participants_count', None),
                            'source': 'dialog_search',
                        })
                        print(f"\n  Найден: {entity.title}")
                except (ChannelPrivateError, ChatAdminRequiredError):
                    continue
                except Exception:
                    continue

        print(f"\r  Проверено каналов: {checked}")
    except Exception as e:
        print(f"Ошибка поиска: {e}")
    return channels


async def _channel_check(args):
    """Основная логика проверки каналов."""
    user = args.user

    client = create_client()

    try:
        me = await ensure_authorized(client)

        print(f"\n{'='*60}")
        print(f"Проверка канала-владельца")
        print(f"{'='*60}")

        # Определяем идентификатор
        if user.startswith('@'):
            identifier = user[1:]
        elif user.lstrip('-').isdigit():
            identifier = int(user)
        else:
            identifier = user

        user_entity = await _get_user_entity(client, identifier)
        if not user_entity:
            print("Пользователь не найден")
            return

        print(f"Пользователь: {user_entity.first_name}")
        if user_entity.username:
            print(f"Username: @{user_entity.username}")
        print(f"ID: {user_entity.id}")

        found_channels = []

        # Шаг 1: По username
        if user_entity.username:
            print(f"\nПроверка канала @{user_entity.username}...")
            channel = await _check_channel_by_username(client, user_entity.username, user_entity.id)
            if channel:
                found_channels.append(channel)

        # Шаг 2: Из профиля
        print("Проверка профиля...")
        linked = await _check_user_full_info(client, user_entity)
        seen_ids = {ch['id'] for ch in found_channels}
        for ch in linked:
            if ch['id'] not in seen_ids:
                found_channels.append(ch)
                seen_ids.add(ch['id'])

        # Шаг 3: Поиск в диалогах
        if not found_channels:
            dialog_channels = await _find_channels_in_dialogs(client, user_entity.id)
            found_channels.extend(dialog_channels)

        # Результаты
        print(f"\n{'='*60}")
        print("РЕЗУЛЬТАТЫ")
        print(f"{'='*60}")

        if found_channels:
            print(f"\nНайдено каналов: {len(found_channels)}")
            for i, ch in enumerate(found_channels, 1):
                print(f"\n  Канал #{i}:")
                print(f"  Название: {ch['title']}")
                if ch.get('username'):
                    print(f"  Username: @{ch['username']}")
                    print(f"  Ссылка: https://t.me/{ch['username']}")
                print(f"  ID: {ch['id']}")
                if ch.get('participants_count'):
                    print(f"  Подписчиков: {ch['participants_count']:,}")

            total_subs = sum(ch.get('participants_count', 0) or 0 for ch in found_channels)
            print(f"\nИтого подписчиков: {total_subs:,}")
        else:
            print("\nКаналы-владельца не найдены")

    finally:
        await client.disconnect()


def run(args):
    """Точка входа для CLI."""
    asyncio.run(_channel_check(args))
