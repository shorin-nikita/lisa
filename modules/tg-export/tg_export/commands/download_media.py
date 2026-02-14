"""Докачка недостающих медиа-файлов для существующего экспорта."""

import os
import json
import asyncio

from tg_export import config
from tg_export.client import create_client, ensure_authorized
from tg_export.schemas import get_info_key


async def _download_media(args):
    """Основная логика докачки медиа."""
    json_path = args.json_path

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    info_key = get_info_key(data)
    if not info_key:
        print("Ошибка: файл не содержит метаданных экспорта")
        return

    chat_id = data[info_key]['id']

    export_dir = os.path.dirname(json_path)
    media_dir = os.path.join(export_dir, "media")
    os.makedirs(media_dir, exist_ok=True)

    # Найти сообщения с media_file, но без файла на диске
    missing = []
    for msg in data['messages']:
        if msg.get('media_file'):
            file_path = os.path.join(media_dir, msg['media_file'])
            if not os.path.exists(file_path):
                missing.append(msg)

    total_with_media = sum(1 for m in data['messages'] if m.get('media_file'))
    print(f"Сообщений с медиа: {total_with_media}")
    print(f"Недостающих файлов: {len(missing)}")

    if not missing:
        print("Все медиа-файлы на месте!")
        return

    client = create_client()

    try:
        me = await ensure_authorized(client)

        chat_identifier = int(f"-100{chat_id}")
        chat = await client.get_entity(chat_identifier)
        chat_name = data[info_key].get('title') or data[info_key].get('name')
        print(f"Докачка медиа для: {chat_name}")

        downloaded = 0
        failed = 0

        for i, msg_data in enumerate(missing):
            msg_id = msg_data['id']
            try:
                message = await client.get_messages(chat_identifier, ids=msg_id)
                if message and message.media:
                    file_path = await client.download_media(message, file=media_dir)
                    if file_path and os.path.exists(file_path):
                        downloaded += 1
                        print(f"  [{i+1}/{len(missing)}] Скачано: {os.path.basename(file_path)}")
                    else:
                        failed += 1
                        print(f"  [{i+1}/{len(missing)}] Не удалось: сообщение {msg_id}")
                else:
                    failed += 1
                    print(f"  [{i+1}/{len(missing)}] Пропущено (нет медиа): сообщение {msg_id}")
            except Exception as e:
                failed += 1
                print(f"  [{i+1}/{len(missing)}] Ошибка сообщение {msg_id}: {e}")

            # Пауза для избежания rate limit
            if i % 10 == 9:
                await asyncio.sleep(1)

        print(f"\nГотово! Скачано: {downloaded}, Не удалось: {failed}")

    finally:
        await client.disconnect()


def run(args):
    """Точка входа для CLI."""
    asyncio.run(_download_media(args))
