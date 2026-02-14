"""Инкрементальное обновление существующего JSON-экспорта."""

import os
import json
import asyncio
from datetime import datetime

from tg_export import config
from tg_export.client import create_client, ensure_authorized
from tg_export.serializers import serialize_message
from tg_export.schemas import get_info_key


async def _update(args):
    """Основная логика обновления экспорта."""
    json_path = args.json_path
    download_media = not args.no_media

    # Загрузить существующий экспорт
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    info_key = get_info_key(data)
    if not info_key:
        print("Ошибка: файл не содержит метаданных экспорта (entity_info / chat_info)")
        return

    chat_id = data[info_key]['id']
    existing_messages = data['messages']
    last_message_id = max(msg['id'] for msg in existing_messages)

    print(f"Загружен экспорт: {json_path}")
    print(f"Существующих сообщений: {len(existing_messages)}")
    print(f"Последний ID сообщения: {last_message_id}")

    client = create_client()

    try:
        me = await ensure_authorized(client)

        # Получить сущность
        chat_identifier = int(f"-100{chat_id}")
        chat = await client.get_entity(chat_identifier)
        chat_name = data[info_key].get('title') or data[info_key].get('name')
        print(f"Загрузка новых сообщений из: {chat_name}")

        # Получить только новые сообщения
        raw_messages = []
        async for message in client.iter_messages(chat_identifier, min_id=last_message_id):
            raw_messages.append(message)

        if not raw_messages:
            print("\nНовых сообщений нет!")
            return

        raw_messages.reverse()
        print(f"Найдено новых сообщений: {len(raw_messages)}")

        # Директория медиа
        export_dir = os.path.dirname(json_path)
        media_dir = os.path.join(export_dir, "media")

        if download_media:
            os.makedirs(media_dir, exist_ok=True)

        # Обработка сообщений
        new_messages = []
        media_count = 0

        for msg in raw_messages:
            media_file = None

            if download_media and msg.media:
                try:
                    file_path = await client.download_media(msg, file=media_dir)
                    if file_path:
                        media_file = os.path.basename(file_path)
                        media_count += 1
                        print(f"  Скачано: {media_file}")
                except Exception as e:
                    print(f"  Не удалось скачать медиа для сообщения {msg.id}: {e}")

            new_messages.append(serialize_message(msg, media_file))

        if media_count > 0:
            print(f"Скачано медиа: {media_count}")

        # Объединить сообщения
        all_messages = existing_messages + new_messages

        data['messages'] = all_messages
        data['total_messages'] = len(all_messages)
        data[info_key]['export_date'] = datetime.now().isoformat()
        data[info_key]['last_update'] = datetime.now().isoformat()

        # Сохранить
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\nФайл обновлен: {json_path}")
        print(f"Всего сообщений: {len(all_messages)}")
        print(f"Добавлено новых: {len(new_messages)}")

        # Превью новых сообщений
        print("\nНовые сообщения:")
        for msg in new_messages[:10]:
            text_preview = msg['text'][:50] + "..." if len(msg['text']) > 50 else msg['text']
            sender = msg['sender']['first_name'] if msg['sender'] else "Unknown"
            media_indicator = f" [медиа: {msg['media_file']}]" if msg['media_file'] else ""
            print(f"  [{msg['id']}] {sender}: {text_preview or '[медиа]'}{media_indicator}")

        if len(new_messages) > 10:
            print(f"  ... и ещё {len(new_messages) - 10} сообщений")

    finally:
        await client.disconnect()


def run(args):
    """Точка входа для CLI."""
    asyncio.run(_update(args))
