"""Полный экспорт Telegram канала: посты в JSON и TXT с информацией о подписчиках."""

import os
import json
import asyncio
from datetime import datetime

from telethon.tl.types import Channel
from telethon.tl.functions.channels import GetFullChannelRequest

from tg_export import config
from tg_export.client import create_client, ensure_authorized
from tg_export.serializers import serialize_message
from tg_export.utils import sanitize_filename


async def _get_channel_info(client, channel_identifier):
    """Получить полную информацию о канале."""
    entity = await client.get_entity(channel_identifier)

    if not isinstance(entity, Channel):
        print(f"{channel_identifier} не является каналом")
        return None

    full_channel = await client(GetFullChannelRequest(channel=entity))

    channel_info = {
        "id": entity.id,
        "title": entity.title,
        "username": entity.username,
        "about": full_channel.full_chat.about,
        "participants_count": full_channel.full_chat.participants_count,
        "created_date": entity.date.isoformat() if hasattr(entity, 'date') and entity.date else None,
        "export_date": datetime.now().isoformat(),
    }

    return channel_info, entity


async def _channel_export(args):
    """Основная логика экспорта канала."""
    channel = args.channel

    # Определяем идентификатор
    if channel.startswith('@'):
        identifier = channel[1:]
    elif channel.startswith('https://t.me/'):
        identifier = channel.replace('https://t.me/', '')
    else:
        identifier = channel

    client = create_client()

    try:
        me = await ensure_authorized(client)

        print(f"\n{'='*60}")
        print(f"Полный экспорт Telegram канала")
        print(f"{'='*60}")
        print(f"Канал: {channel}")

        result = await _get_channel_info(client, identifier)
        if not result:
            return

        channel_info, channel_entity = result

        print(f"\nКанал: {channel_info['title']}")
        if channel_info['username']:
            print(f"Username: @{channel_info['username']}")
        print(f"Подписчиков: {channel_info['participants_count']:,}")
        if channel_info.get('about'):
            print(f"Описание: {channel_info['about'][:100]}...")

        # Создаем директорию
        safe_name = sanitize_filename(channel_info['title'])
        output_dir = os.path.join(config.EXPORT_DIR, safe_name)
        os.makedirs(output_dir, exist_ok=True)
        print(f"\nПапка: {output_dir}")

        # Загрузка сообщений
        print(f"\nЗагрузка сообщений...")
        messages = []
        count = 0

        async for message in client.iter_messages(channel_entity, limit=None):
            count += 1
            messages.append(serialize_message(message))
            if count % 100 == 0:
                print(f"  Загружено {count} сообщений...")

        print(f"Всего: {count} сообщений")
        messages.reverse()

        # JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(output_dir, f"messages_{timestamp}.json")
        data = {
            "channel_info": channel_info,
            "total_messages": len(messages),
            "messages": messages,
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nJSON: {json_path}")

        # TXT
        txt_path = os.path.join(output_dir, f"messages_{timestamp}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"Экспорт канала: {channel_info['title']}\n")
            if channel_info.get('username'):
                f.write(f"Username: @{channel_info['username']}\n")
            f.write(f"Подписчиков: {channel_info.get('participants_count', 'N/A')}\n")
            f.write(f"Дата экспорта: {channel_info['export_date']}\n")
            f.write(f"Всего сообщений: {len(messages)}\n")
            f.write("=" * 80 + "\n\n")

            for msg in messages:
                if msg['text']:
                    f.write(f"[#{msg['id']}]\n")
                    f.write(f"Дата: {msg['date']}\n")
                    if msg.get('views'):
                        f.write(f"Просмотров: {msg['views']}\n")
                    if msg.get('forwards'):
                        f.write(f"Пересылок: {msg['forwards']}\n")
                    if msg.get('reactions'):
                        reactions_str = ", ".join([f"{r['emoticon']}: {r['count']}" for r in msg['reactions']])
                        f.write(f"Реакции: {reactions_str}\n")
                    f.write(f"\n{msg['text']}\n")
                    f.write("-" * 80 + "\n\n")

        print(f"TXT: {txt_path}")
        print(f"\nЭкспорт завершен! Сообщений: {len(messages)}")

    finally:
        await client.disconnect()


def run(args):
    """Точка входа для CLI."""
    asyncio.run(_channel_export(args))
