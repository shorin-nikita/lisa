"""Офлайн-анализ экспортированных сообщений с генерацией отчета."""

import json
import os
import re
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List

from tg_export.schemas import get_export_info


def _analyze_topics(messages):
    """Построить структуру топиков по цепочкам reply_to."""
    topics = defaultdict(list)
    message_map = {m['id']: m for m in messages}

    def find_root(msg_id, visited=None):
        if visited is None:
            visited = set()
        if msg_id in visited:
            return msg_id
        visited.add(msg_id)
        msg = message_map.get(msg_id)
        if not msg:
            return msg_id
        reply_to = msg.get('reply_to')
        if reply_to and 'message_id' in reply_to:
            parent_id = reply_to['message_id']
            if parent_id in message_map:
                return find_root(parent_id, visited)
        return msg_id

    for msg in messages:
        root_id = find_root(msg['id'])
        topics[root_id].append(msg)

    return dict(topics)


def _analyze_participants(messages):
    """Анализ активности участников."""
    participants = defaultdict(lambda: {
        'message_count': 0,
        'first_message': None,
        'last_message': None,
        'reactions_received': 0,
        'replies_received': 0,
        'user_info': None,
        'message_types': Counter(),
        'active_hours': Counter(),
        'active_days': Counter(),
        'total_text_length': 0,
    })

    message_map = {m['id']: m for m in messages}

    for msg in messages:
        sender = msg.get('sender')
        if not sender:
            continue

        sender_id = str(sender.get('id', 'unknown'))
        p = participants[sender_id]

        if not p['user_info']:
            p['user_info'] = {
                'id': sender.get('id'),
                'first_name': sender.get('first_name', ''),
                'last_name': sender.get('last_name', ''),
                'username': sender.get('username', ''),
            }

        p['message_count'] += 1

        msg_date = msg.get('date')
        if msg_date:
            try:
                dt = datetime.fromisoformat(msg_date.replace('Z', '+00:00'))
                if not p['first_message'] or dt < datetime.fromisoformat(p['first_message'].replace('Z', '+00:00')):
                    p['first_message'] = msg_date
                if not p['last_message'] or dt > datetime.fromisoformat(p['last_message'].replace('Z', '+00:00')):
                    p['last_message'] = msg_date
                p['active_hours'][dt.hour] += 1
                p['active_days'][dt.strftime('%A')] += 1
            except (ValueError, TypeError):
                pass

        p['message_types'][msg.get('message_type', 'text')] += 1

        text = msg.get('text', '')
        if text:
            p['total_text_length'] += len(text)

        reactions = msg.get('reactions', [])
        if reactions:
            p['reactions_received'] += sum(r.get('count', 1) for r in reactions)

    # Подсчет полученных ответов
    for msg in messages:
        reply_to = msg.get('reply_to')
        if reply_to and 'message_id' in reply_to:
            parent_msg = message_map.get(reply_to['message_id'])
            if parent_msg and parent_msg.get('sender'):
                parent_sender_id = str(parent_msg['sender'].get('id', 'unknown'))
                if parent_sender_id in participants:
                    participants[parent_sender_id]['replies_received'] += 1

    # Финализация
    for p in participants.values():
        if p['message_count'] > 0:
            p['avg_message_length'] = p['total_text_length'] / p['message_count']
        else:
            p['avg_message_length'] = 0
        p['message_types'] = dict(p['message_types'])
        p['active_hours'] = dict(p['active_hours'])
        p['active_days'] = dict(p['active_days'])

    return dict(participants)


def _analyze_temporal(messages):
    """Анализ временных паттернов."""
    hourly = Counter()
    daily = Counter()
    monthly = Counter()
    messages_by_date = defaultdict(list)

    for msg in messages:
        date_str = msg.get('date')
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            hourly[dt.hour] += 1
            daily[dt.strftime('%A')] += 1
            monthly[dt.strftime('%Y-%m')] += 1
            messages_by_date[dt.date().isoformat()].append(msg)
        except (ValueError, TypeError):
            pass

    peak_hour = hourly.most_common(1)[0] if hourly else (0, 0)
    peak_day = daily.most_common(1)[0] if daily else ('', 0)

    # Подсчет стриков активности
    dates = sorted(messages_by_date.keys())
    max_streak = 0
    current_streak = 1
    for i in range(1, len(dates)):
        d1 = datetime.fromisoformat(dates[i-1]).date()
        d2 = datetime.fromisoformat(dates[i]).date()
        if (d2 - d1).days == 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1

    return {
        'hourly_distribution': dict(hourly),
        'daily_distribution': dict(daily),
        'monthly_distribution': dict(monthly),
        'peak_hour': peak_hour[0],
        'peak_day': peak_day[0],
        'max_activity_streak_days': max_streak,
        'total_active_days': len(messages_by_date),
        'avg_messages_per_active_day': len(messages) / max(len(messages_by_date), 1),
        'messages_by_date': {k: len(v) for k, v in messages_by_date.items()},
    }


def _analyze_content(messages):
    """Анализ типов контента и текстовых паттернов."""
    content_types = Counter()
    word_freq = Counter()
    emoji_freq = Counter()
    url_count = 0
    mention_count = 0
    hashtag_count = 0

    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U00002600-\U000026FF"
        "]+", flags=re.UNICODE
    )
    url_pattern = re.compile(r'https?://\S+')
    mention_pattern = re.compile(r'@\w+')
    hashtag_pattern = re.compile(r'#\w+')

    text_messages = []
    all_text = ""

    for msg in messages:
        content_types[msg.get('message_type', 'text')] += 1

        text = msg.get('text', '')
        if text:
            text_messages.append(text)
            all_text += " " + text

            url_count += len(url_pattern.findall(text))
            mention_count += len(mention_pattern.findall(text))
            hashtag_count += len(hashtag_pattern.findall(text))

            emojis = emoji_pattern.findall(text)
            for e in emojis:
                for char in e:
                    emoji_freq[char] += 1

            clean_text = url_pattern.sub('', text)
            clean_text = mention_pattern.sub('', clean_text)
            clean_text = hashtag_pattern.sub('', clean_text)
            clean_text = emoji_pattern.sub('', clean_text)
            words = re.findall(r'\b\w{3,}\b', clean_text.lower())
            word_freq.update(words)

    # Стоп-слова
    stop_words = {
        'the', 'and', 'for', 'that', 'this', 'with', 'you', 'are', 'have', 'was',
        'but', 'not', 'can', 'что', 'это', 'как', 'для', 'все', 'так', 'его',
        'она', 'они', 'мне', 'вот', 'уже', 'еще', 'ещё', 'там', 'тут', 'где',
        'или', 'если', 'при', 'про', 'чтобы', 'только', 'будет',
    }
    for sw in stop_words:
        word_freq.pop(sw, None)

    return {
        'content_type_distribution': dict(content_types),
        'total_text_messages': len(text_messages),
        'total_characters': len(all_text),
        'url_count': url_count,
        'mention_count': mention_count,
        'hashtag_count': hashtag_count,
        'top_words': dict(word_freq.most_common(50)),
        'top_emojis': dict(emoji_freq.most_common(20)),
        'avg_message_length': len(all_text) / max(len(text_messages), 1),
    }


def _analyze_engagement(messages):
    """Анализ вовлеченности: реакции, просмотры, пересылки."""
    total_reactions = 0
    total_views = 0
    total_forwards = 0
    reaction_types = Counter()
    messages_with_reactions = 0
    messages_with_views = 0

    for msg in messages:
        reactions = msg.get('reactions', [])
        if reactions:
            messages_with_reactions += 1
            for r in reactions:
                count = r.get('count', 1)
                total_reactions += count
                emoji = r.get('emoticon', r.get('reaction', '?'))
                reaction_types[emoji] += count

        views = msg.get('views')
        if views:
            messages_with_views += 1
            total_views += views

        forwards = msg.get('forwards')
        if forwards:
            total_forwards += forwards

    return {
        'total_reactions': total_reactions,
        'total_views': total_views,
        'total_forwards': total_forwards,
        'messages_with_reactions': messages_with_reactions,
        'messages_with_views': messages_with_views,
        'reaction_types': dict(reaction_types.most_common(20)),
        'avg_reactions_per_message': total_reactions / max(len(messages), 1),
        'avg_views_per_message': total_views / max(messages_with_views, 1) if messages_with_views else 0,
    }


def _extract_topic_summaries(topics, message_map):
    """Саммари по каждому топику/треду."""
    summaries = []

    for root_id, thread_messages in topics.items():
        root_msg = message_map.get(root_id, {})
        participants = set()
        for msg in thread_messages:
            sender = msg.get('sender')
            if sender:
                participants.add(sender.get('id'))

        dates = []
        for msg in thread_messages:
            if msg.get('date'):
                try:
                    dates.append(datetime.fromisoformat(msg['date'].replace('Z', '+00:00')))
                except (ValueError, TypeError):
                    pass

        first_text = ""
        for msg in sorted(thread_messages, key=lambda x: x.get('id', 0)):
            if msg.get('text') and len(msg['text']) > 5:
                first_text = msg['text'][:200]
                break

        summaries.append({
            'root_id': root_id,
            'message_count': len(thread_messages),
            'participant_count': len(participants),
            'first_date': min(dates).isoformat() if dates else None,
            'last_date': max(dates).isoformat() if dates else None,
            'duration_hours': (max(dates) - min(dates)).total_seconds() / 3600 if len(dates) > 1 else 0,
            'preview': first_text,
            'root_sender': root_msg.get('sender', {}).get('first_name', 'Unknown') if root_msg.get('sender') else 'System',
        })

    summaries.sort(key=lambda x: x['message_count'], reverse=True)
    return summaries


def _generate_report(data, output_path):
    """Сгенерировать markdown-отчет."""
    info = get_export_info(data)
    report = []

    report.append(f"# Анализ: {info['name']}")
    report.append(f"\n**Дата экспорта:** {info['export_date']}")
    report.append(f"**ID:** {info['id']}")
    report.append(f"\n---\n")

    # 1. Общая статистика
    report.append("## 1. Общая статистика")
    report.append(f"- **Всего сообщений:** {data['total_messages']}")
    report.append(f"- **Уникальных участников:** {data['participant_count']}")
    report.append(f"- **Топиков/тредов:** {data['topic_count']}")
    report.append(f"- **Активных дней:** {data['temporal']['total_active_days']}")
    report.append(f"- **Средн. сообщений в день:** {data['temporal']['avg_messages_per_active_day']:.1f}")
    report.append(f"- **Макс. streak активности:** {data['temporal']['max_activity_streak_days']} дней")

    if data['temporal']['messages_by_date']:
        dates = sorted(data['temporal']['messages_by_date'].keys())
        report.append(f"- **Период:** {dates[0]} -- {dates[-1]}")
    report.append(f"\n---\n")

    # 2. Участники
    report.append("## 2. Анализ участников")
    report.append("\n### Топ-20 по количеству сообщений\n")
    report.append("| # | Участник | Username | Сообщений | Реакций | Ответов |")
    report.append("|---|----------|----------|-----------|---------|---------|")

    sorted_parts = sorted(
        data['participants'].items(),
        key=lambda x: x[1]['message_count'],
        reverse=True,
    )[:20]

    for i, (pid, p) in enumerate(sorted_parts, 1):
        name = f"{p['user_info']['first_name']} {p['user_info']['last_name']}".strip()
        username = f"@{p['user_info']['username']}" if p['user_info'].get('username') else '-'
        report.append(f"| {i} | {name} | {username} | {p['message_count']} | {p['reactions_received']} | {p['replies_received']} |")
    report.append(f"\n---\n")

    # 3. Топики
    report.append("## 3. Топики/треды")
    report.append(f"\n**Всего:** {len(data['topic_summaries'])}")
    report.append("\n### Топ-30 самых активных\n")
    report.append("| # | Сообщ. | Участн. | Автор | Длит.(ч) | Превью |")
    report.append("|---|--------|---------|-------|----------|--------|")

    for i, topic in enumerate(data['topic_summaries'][:30], 1):
        preview = topic['preview'][:50].replace('|', '/').replace('\n', ' ') + '...' if topic['preview'] else '-'
        report.append(f"| {i} | {topic['message_count']} | {topic['participant_count']} | {topic['root_sender']} | {topic['duration_hours']:.1f} | {preview} |")
    report.append(f"\n---\n")

    # 4. Временной анализ
    report.append("## 4. Временной анализ")
    report.append(f"\n**Пиковый час:** {data['temporal']['peak_hour']}:00")
    report.append(f"**Пиковый день недели:** {data['temporal']['peak_day']}")

    report.append("\n### По часам\n")
    report.append("```")
    hourly = data['temporal']['hourly_distribution']
    max_h = max(hourly.values()) if hourly else 1
    for hour in range(24):
        count = hourly.get(hour, hourly.get(str(hour), 0))
        bar = '#' * int(50 * count / max_h) if max_h else ''
        report.append(f"{hour:02d}:00 | {bar} {count}")
    report.append("```")

    report.append("\n### По дням недели\n")
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    days_ru = {'Monday': 'Пн', 'Tuesday': 'Вт', 'Wednesday': 'Ср', 'Thursday': 'Чт',
               'Friday': 'Пт', 'Saturday': 'Сб', 'Sunday': 'Вс'}
    report.append("```")
    daily = data['temporal']['daily_distribution']
    max_d = max(daily.values()) if daily else 1
    for day in days_order:
        count = daily.get(day, 0)
        bar = '#' * int(40 * count / max_d) if max_d else ''
        report.append(f"{days_ru[day]} | {bar} {count}")
    report.append("```")

    report.append("\n### По месяцам\n")
    for month, count in sorted(data['temporal']['monthly_distribution'].items()):
        report.append(f"- **{month}:** {count} сообщений")
    report.append(f"\n---\n")

    # 5. Контент
    report.append("## 5. Анализ контента")
    report.append(f"\n- **Текстовых сообщений:** {data['content']['total_text_messages']}")
    report.append(f"- **Всего символов:** {data['content']['total_characters']:,}")
    report.append(f"- **Средняя длина:** {data['content']['avg_message_length']:.0f} символов")
    report.append(f"- **Ссылок:** {data['content']['url_count']}")
    report.append(f"- **Упоминаний (@):** {data['content']['mention_count']}")
    report.append(f"- **Хэштегов (#):** {data['content']['hashtag_count']}")

    report.append("\n### Типы контента\n")
    for ctype, count in sorted(data['content']['content_type_distribution'].items(), key=lambda x: -x[1]):
        report.append(f"- **{ctype}:** {count}")

    report.append("\n### Топ-30 слов\n")
    words = list(data['content']['top_words'].items())[:30]
    for i in range(0, len(words), 3):
        row = words[i:i+3]
        report.append(" | ".join([f"**{w}**: {c}" for w, c in row]))

    if data['content']['top_emojis']:
        report.append("\n### Топ эмодзи\n")
        emojis = list(data['content']['top_emojis'].items())[:15]
        report.append(" ".join([f"{e} ({c})" for e, c in emojis]))
    report.append(f"\n---\n")

    # 6. Вовлеченность
    report.append("## 6. Вовлеченность")
    report.append(f"\n- **Реакций:** {data['engagement']['total_reactions']}")
    report.append(f"- **Просмотров:** {data['engagement']['total_views']}")
    report.append(f"- **Пересылок:** {data['engagement']['total_forwards']}")
    report.append(f"- **Средн. реакций на сообщение:** {data['engagement']['avg_reactions_per_message']:.2f}")

    if data['engagement']['reaction_types']:
        report.append("\n### Типы реакций\n")
        for reaction, count in list(data['engagement']['reaction_types'].items())[:10]:
            report.append(f"- {reaction}: {count}")

    report.append(f"\n---\n")
    report.append(f"\n*Отчет сгенерирован: {datetime.now().isoformat()}*")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f"Отчет сохранен: {output_path}")
    return output_path


def run(args):
    """Точка входа для CLI."""
    json_path = args.json_path
    output_file = args.output

    print("Загрузка данных...")
    with open(json_path, 'r', encoding='utf-8') as f:
        export_data = json.load(f)

    info = get_export_info(export_data)
    messages = export_data.get('messages', [])
    total_messages = export_data.get('total_messages', len(messages))

    print(f"Источник: {info['name']}")
    print(f"Сообщений: {total_messages}")

    message_map = {m['id']: m for m in messages}

    print("\nАнализ топиков...")
    topics = _analyze_topics(messages)
    print(f"Топиков: {len(topics)}")

    print("Анализ участников...")
    participants = _analyze_participants(messages)
    print(f"Участников: {len(participants)}")

    print("Временной анализ...")
    temporal = _analyze_temporal(messages)

    print("Анализ контента...")
    content = _analyze_content(messages)

    print("Анализ вовлеченности...")
    engagement = _analyze_engagement(messages)

    print("Формирование саммари топиков...")
    topic_summaries = _extract_topic_summaries(topics, message_map)

    analysis_data = {
        'total_messages': total_messages,
        'participant_count': len(participants),
        'topic_count': len(topics),
        'participants': participants,
        'temporal': temporal,
        'content': content,
        'engagement': engagement,
        'topic_summaries': topic_summaries,
    }

    # Объединяем с оригинальными метаданными
    info_key = None
    for key in ("entity_info", "chat_info", "channel_info"):
        if key in export_data:
            analysis_data[key] = export_data[key]
            info_key = key
            break

    # Сохраняем JSON-аналитику
    analysis_json_path = json_path.replace('.json', '_analysis.json')
    with open(analysis_json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nАналитика: {analysis_json_path}")

    # Генерируем markdown-отчет
    if not output_file:
        output_file = json_path.replace('.json', '_report.md')
    _generate_report(analysis_data, output_file)

    # Итоги
    print(f"\n{'='*60}")
    print("ИТОГО")
    print(f"{'='*60}")
    print(f"Сообщений: {total_messages}")
    print(f"Участников: {len(participants)}")
    print(f"Топиков: {len(topics)}")
    print(f"Активных дней: {temporal['total_active_days']}")
    print(f"Пиковый час: {temporal['peak_hour']}:00")

    print(f"\nТоп-5 участников:")
    for i, (pid, p) in enumerate(sorted(participants.items(), key=lambda x: x[1]['message_count'], reverse=True)[:5], 1):
        name = f"{p['user_info']['first_name']} {p['user_info']['last_name']}".strip()
        print(f"  {i}. {name}: {p['message_count']} сообщений")
