"""Универсальный экспорт сообщений из любого источника Telegram."""

import os
import json
import asyncio
from datetime import datetime, timedelta, timezone

from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn
    _rich = True
    _console = Console()
except ImportError:
    _rich = False
    _console = None

from tg_export import config
from tg_export.client import create_client, ensure_authorized
from tg_export.utils import parse_source, sanitize_filename, get_entity_name
from tg_export.serializers import (
    serialize_message, format_message_text, format_message_markdown, get_media_filename,
)
from tg_export.schemas import make_entity_info


async def _download_media_file(client, message, media_dir):
    """Скачать медиа из сообщения, вернуть имя файла."""
    if not message.media:
        return None
    if not isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
        return None

    filename = get_media_filename(message)
    filepath = os.path.join(media_dir, filename)

    try:
        await client.download_media(message, filepath)
        return filename
    except Exception as e:
        print(f"  Не удалось скачать медиа из сообщения {message.id}: {e}")
        return None


async def _export(args):
    """Основная логика экспорта."""
    source = args.source
    output_format = args.format
    output_file = args.output
    topic_id = args.topic
    download_media = args.media
    days = args.days

    identifier, source_type, parsed_topic = parse_source(source)
    topic_id = topic_id or parsed_topic

    print(f"\n{'='*60}")
    print(f"Экспорт сообщений Telegram")
    print(f"{'='*60}")
    print(f"Источник: {source}")
    print(f"Тип: {source_type}")
    print(f"Формат: {output_format}")
    if topic_id:
        print(f"Топик: #{topic_id}")
    if days:
        print(f"Период: последние {days} дней")

    client = create_client()

    try:
        me = await ensure_authorized(client)

        # Получить сущность
        try:
            entity = await client.get_entity(identifier)
        except Exception as e:
            print(f"Ошибка получения источника: {e}")
            raise

        entity_name = get_entity_name(entity)
        print(f"\nИсточник: {entity_name}")
        print(f"ID: {entity.id}")
        print(f"Тип: {type(entity).__name__}")

        # Фильтр по дате
        cutoff_date = None
        if days:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            print(f"Сообщения после: {cutoff_date.strftime('%Y-%m-%d %H:%M')}")

        # Загрузка сообщений
        messages = []
        count = 0

        iter_kwargs = {"limit": None}
        if topic_id:
            iter_kwargs["reply_to"] = topic_id

        if _rich:
            with _console.status("[bold green]Загрузка сообщений...") as status:
                async for message in client.iter_messages(entity, **iter_kwargs):
                    if cutoff_date and message.date and message.date < cutoff_date:
                        break
                    count += 1
                    messages.append(message)
                    if count % 100 == 0:
                        status.update(f"[bold green]Загружено {count} сообщений...")
        else:
            print(f"\nЗагрузка сообщений...")
            async for message in client.iter_messages(entity, **iter_kwargs):
                if cutoff_date and message.date and message.date < cutoff_date:
                    break
                count += 1
                messages.append(message)
                if count % 500 == 0:
                    print(f"  Загружено {count} сообщений...")

        print(f"Всего сообщений: {count}")

        # Хронологический порядок
        messages.reverse()

        # Подготовка директорий
        os.makedirs(config.EXPORT_DIR, exist_ok=True)
        safe_name = sanitize_filename(entity_name)
        entity_dir = os.path.join(config.EXPORT_DIR, safe_name)
        os.makedirs(entity_dir, exist_ok=True)

        # Скачивание медиа
        media_files = {}
        if download_media:
            media_dir = os.path.join(entity_dir, "media")
            os.makedirs(media_dir, exist_ok=True)
            media_msgs = [msg for msg in messages
                          if msg.media and isinstance(msg.media, (MessageMediaPhoto, MessageMediaDocument))]
            total_media = len(media_msgs)
            print(f"\nСкачивание медиа в: {media_dir}")
            media_count = 0

            if _rich and total_media > 0:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    MofNCompleteColumn(),
                    TimeElapsedColumn(),
                    console=_console,
                ) as progress:
                    task = progress.add_task("Скачивание медиа", total=total_media)
                    for msg in media_msgs:
                        filename = await _download_media_file(client, msg, media_dir)
                        if filename:
                            media_files[msg.id] = filename
                            media_count += 1
                        progress.advance(task)
            else:
                for msg in media_msgs:
                    filename = await _download_media_file(client, msg, media_dir)
                    if filename:
                        media_files[msg.id] = filename
                        media_count += 1
                        if media_count % 10 == 0:
                            print(f"  Скачано {media_count} файлов...")

            print(f"Медиа скачано: {media_count}")

        # Имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not output_file:
            ext = {"json": "json", "txt": "txt", "md": "md"}[output_format]
            output_file = os.path.join(entity_dir, f"export_{timestamp}.{ext}")

        # Экспорт
        if output_format == "json":
            entity_info = make_entity_info(entity)
            if days:
                entity_info["period_days"] = days
            data = {
                "entity_info": entity_info,
                "total_messages": len(messages),
                "messages": [serialize_message(m, media_files.get(m.id)) for m in messages],
            }
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif output_format == "txt":
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"{'='*60}\n")
                f.write(f"Экспорт: {entity_name}\n")
                f.write(f"ID: {entity.id}\n")
                f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"Сообщений: {len(messages)}\n")
                f.write(f"{'='*60}\n\n")
                for msg in messages:
                    f.write(format_message_text(msg) + "\n")

        elif output_format == "md":
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {entity_name}\n\n")
                username = getattr(entity, 'username', None)
                if username:
                    f.write(f"> Канал: @{username}\n")
                f.write(f"> Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                if days:
                    f.write(f"> Период: последние {days} дней\n")
                stats_line = f"> Сообщений: {len(messages)}"
                if download_media:
                    stats_line += f" | Медиа: {len(media_files)}"
                f.write(stats_line + "\n")
                f.write("\n---\n\n")
                for msg in messages:
                    f.write(format_message_markdown(msg, media_files.get(msg.id)))
                    f.write("\n\n---\n\n")

        print(f"\nСохранено: {output_file}")
        print(f"Экспортировано сообщений: {len(messages)}")
        return output_file

    finally:
        await client.disconnect()


def run(args):
    """Точка входа для CLI."""
    asyncio.run(_export(args))
