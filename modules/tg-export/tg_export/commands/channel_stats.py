"""Аналитический отчет по Telegram каналу: просмотры, реакции, пересылки."""

import os
import json
import asyncio
from datetime import datetime
from collections import Counter, defaultdict

from telethon.tl.types import Channel
from telethon.tl.functions.channels import GetFullChannelRequest

from tg_export import config
from tg_export.client import create_client, ensure_authorized
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


async def _channel_stats(args):
    """Основная логика аналитики канала."""
    channel = args.channel

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
        print(f"Аналитика Telegram канала")
        print(f"{'='*60}")

        result = await _get_channel_info(client, identifier)
        if not result:
            return

        channel_info, channel_entity = result

        print(f"\nКанал: {channel_info['title']}")
        if channel_info['username']:
            print(f"Username: @{channel_info['username']}")
        print(f"Подписчиков: {channel_info['participants_count']:,}")

        # Анализ
        print(f"\nАнализ сообщений...")

        stats = {
            'total_messages': 0,
            'total_views': 0,
            'total_forwards': 0,
            'total_reactions': 0,
            'messages_with_media': 0,
            'messages_text_only': 0,
            'reactions_breakdown': Counter(),
            'media_types': Counter(),
            'posts_by_month': defaultdict(int),
        }

        all_messages = []
        count = 0

        async for message in client.iter_messages(channel_entity, limit=None):
            count += 1
            stats['total_messages'] += 1

            msg_data = {
                'id': message.id,
                'date': message.date.isoformat() if message.date else None,
                'text': message.text or "",
                'views': message.views or 0,
                'forwards': message.forwards or 0,
                'reactions_count': 0,
                'reactions': [],
                'media_type': type(message.media).__name__ if message.media else "text",
            }

            if message.views:
                stats['total_views'] += message.views
            if message.forwards:
                stats['total_forwards'] += message.forwards

            if hasattr(message, 'reactions') and message.reactions:
                for reaction in message.reactions.results:
                    emoticon = getattr(reaction.reaction, 'emoticon', 'unknown')
                    r_count = reaction.count
                    msg_data['reactions'].append({'emoticon': emoticon, 'count': r_count})
                    msg_data['reactions_count'] += r_count
                    stats['total_reactions'] += r_count
                    stats['reactions_breakdown'][emoticon] += r_count

            if message.media:
                stats['messages_with_media'] += 1
                stats['media_types'][msg_data['media_type']] += 1
            else:
                stats['messages_text_only'] += 1

            if message.date:
                stats['posts_by_month'][message.date.strftime("%Y-%m")] += 1

            all_messages.append(msg_data)

            if count % 100 == 0:
                print(f"  Проанализировано {count} сообщений...")

        print(f"Всего: {count} сообщений")

        # Средние
        total = stats['total_messages']
        avg_views = stats['total_views'] / total if total else 0
        avg_forwards = stats['total_forwards'] / total if total else 0
        avg_reactions = stats['total_reactions'] / total if total else 0

        # Топы
        top_by_views = sorted(all_messages, key=lambda x: x['views'], reverse=True)[:20]
        top_by_forwards = sorted(all_messages, key=lambda x: x['forwards'], reverse=True)[:20]
        top_by_reactions = sorted(all_messages, key=lambda x: x['reactions_count'], reverse=True)[:20]

        # Сохранение
        safe_name = sanitize_filename(channel_info['title'])
        output_dir = os.path.join(config.EXPORT_DIR, safe_name)
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # TXT отчет
        txt_path = os.path.join(output_dir, f"stats_{timestamp}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("СТАТИСТИКА TELEGRAM КАНАЛА\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Канал: {channel_info['title']}\n")
            if channel_info.get('username'):
                f.write(f"Username: @{channel_info['username']}\n")
            f.write(f"Подписчиков: {channel_info.get('participants_count', 'N/A'):,}\n")
            if channel_info.get('about'):
                f.write(f"Описание: {channel_info['about']}\n")
            f.write(f"Дата создания: {channel_info.get('created_date', 'N/A')}\n")
            f.write(f"Дата отчета: {channel_info['export_date']}\n\n")

            f.write("=" * 80 + "\n")
            f.write("ОБЩАЯ СТАТИСТИКА\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Постов: {total:,}\n")
            f.write(f"Просмотров: {stats['total_views']:,}\n")
            f.write(f"Пересылок: {stats['total_forwards']:,}\n")
            f.write(f"Реакций: {stats['total_reactions']:,}\n\n")
            f.write(f"Среднее на пост:\n")
            f.write(f"  Просмотров: {avg_views:.1f}\n")
            f.write(f"  Пересылок: {avg_forwards:.2f}\n")
            f.write(f"  Реакций: {avg_reactions:.2f}\n\n")
            f.write(f"С медиа: {stats['messages_with_media']:,}\n")
            f.write(f"Только текст: {stats['messages_text_only']:,}\n\n")

            if stats['media_types']:
                f.write("Типы медиа:\n")
                for mt, c in stats['media_types'].most_common():
                    f.write(f"  {mt}: {c:,}\n")
                f.write("\n")

            if stats['reactions_breakdown']:
                f.write("Реакции:\n")
                for emoji, c in stats['reactions_breakdown'].most_common(10):
                    f.write(f"  {emoji}: {c:,}\n")
                f.write("\n")

            if stats['posts_by_month']:
                f.write("По месяцам:\n")
                for month in sorted(stats['posts_by_month'].keys()):
                    f.write(f"  {month}: {stats['posts_by_month'][month]:,} постов\n")
                f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("ТОП-20 ПО ПРОСМОТРАМ\n")
            f.write("=" * 80 + "\n\n")
            for i, post in enumerate(top_by_views, 1):
                f.write(f"{i}. #{post['id']} | Просм: {post['views']:,} | Пересл: {post['forwards']:,} | Реакц: {post['reactions_count']:,}\n")
                if post['text']:
                    f.write(f"   {post['text'][:150].replace(chr(10), ' ')}...\n")
                f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("ТОП-20 ПО ПЕРЕСЫЛКАМ\n")
            f.write("=" * 80 + "\n\n")
            for i, post in enumerate(top_by_forwards, 1):
                f.write(f"{i}. #{post['id']} | Пересл: {post['forwards']:,} | Просм: {post['views']:,}\n")
                if post['text']:
                    f.write(f"   {post['text'][:150].replace(chr(10), ' ')}...\n")
                f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("ТОП-20 ПО РЕАКЦИЯМ\n")
            f.write("=" * 80 + "\n\n")
            for i, post in enumerate(top_by_reactions, 1):
                f.write(f"{i}. #{post['id']} | Реакц: {post['reactions_count']:,} | Просм: {post['views']:,}\n")
                if post['reactions']:
                    rstr = ", ".join([f"{r['emoticon']}: {r['count']}" for r in post['reactions']])
                    f.write(f"   Детали: {rstr}\n")
                if post['text']:
                    f.write(f"   {post['text'][:150].replace(chr(10), ' ')}...\n")
                f.write("\n")

        print(f"\nОтчет TXT: {txt_path}")

        # JSON
        json_path = os.path.join(output_dir, f"stats_{timestamp}.json")
        stats_serializable = stats.copy()
        stats_serializable['reactions_breakdown'] = dict(stats['reactions_breakdown'])
        stats_serializable['media_types'] = dict(stats['media_types'])
        stats_serializable['posts_by_month'] = dict(stats['posts_by_month'])
        stats_serializable['avg_views_per_post'] = avg_views
        stats_serializable['avg_forwards_per_post'] = avg_forwards
        stats_serializable['avg_reactions_per_post'] = avg_reactions
        stats_serializable['top_by_views'] = top_by_views
        stats_serializable['top_by_forwards'] = top_by_forwards
        stats_serializable['top_by_reactions'] = top_by_reactions

        json_data = {
            "channel_info": channel_info,
            "statistics": stats_serializable,
            "all_messages": all_messages,
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"Статистика JSON: {json_path}")

        # Итого
        print(f"\n{'='*60}")
        print(f"Постов: {total:,}")
        print(f"Просмотров: {stats['total_views']:,}")
        print(f"Пересылок: {stats['total_forwards']:,}")
        print(f"Реакций: {stats['total_reactions']:,}")

    finally:
        await client.disconnect()


def run(args):
    """Точка входа для CLI."""
    asyncio.run(_channel_stats(args))
