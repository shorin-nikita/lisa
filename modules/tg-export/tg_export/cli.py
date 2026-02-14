"""Главный CLI: единая точка входа tg-export с субкомандами."""

import argparse
import sys

from tg_export import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="tg-export",
        description="Экспорт и анализ Telegram чатов, каналов и переписок",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  tg-export setup                                  Первоначальная настройка
  tg-export collect @durov                         Собрать канал в Markdown
  tg-export collect @durov --days 7 --media        Собрать за 7 дней с медиа
  tg-export export https://t.me/durov              Экспорт канала
  tg-export export @username --format md --days 7  Экспорт за 7 дней в Markdown
  tg-export export https://t.me/c/123456 --media   Экспорт с медиа
  tg-export update exports/Chat/export.json        Обновить экспорт
  tg-export analyze exports/Chat/export.json       Анализ экспорта
  tg-export channel-stats @channel                 Аналитика канала
""",
    )
    parser.add_argument("--version", "-V", action="version", version=f"tg-export {__version__}")

    subparsers = parser.add_subparsers(dest="command", title="Команды")

    # --- setup ---
    sp_setup = subparsers.add_parser("setup", help="Первоначальная настройка: .env + авторизация")

    # --- auth ---
    sp_auth = subparsers.add_parser("auth", help="Авторизация в Telegram")

    # --- export ---
    sp_export = subparsers.add_parser(
        "export",
        help="Экспорт сообщений из любого источника",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Источники:
  https://t.me/c/1234567890   Приватная группа/канал
  https://t.me/username        Публичный канал/группа
  @username                    Пользователь или канал
  +79001234567                 По номеру телефона
  1234567890                   По числовому ID
""",
    )
    sp_export.add_argument("source", help="Источник: URL, @username, телефон или ID")
    sp_export.add_argument("--format", "-f", choices=["json", "txt", "md"], default="json",
                           help="Формат вывода (по умолчанию: json)")
    sp_export.add_argument("--output", "-o", help="Свой путь для файла экспорта")
    sp_export.add_argument("--topic", "-t", type=int, help="ID топика форума")
    sp_export.add_argument("--media", "-m", action="store_true", help="Скачать медиа-файлы")
    sp_export.add_argument("--days", "-d", type=int, help="Экспорт только за последние N дней")

    # --- collect ---
    sp_collect = subparsers.add_parser(
        "collect",
        help="Собрать сообщения из канала/чата в Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  tg-export collect @durov                   Собрать канал Дурова
  tg-export collect @durov --days 7          Только за последние 7 дней
  tg-export collect @durov --media           С медиа-файлами
  tg-export collect https://t.me/durov       По ссылке
""",
    )
    sp_collect.add_argument("source", help="Источник: URL, @username, телефон или ID")
    sp_collect.add_argument("--media", "-m", action="store_true", help="Скачать медиа-файлы")
    sp_collect.add_argument("--days", "-d", type=int, help="Только за последние N дней")
    sp_collect.add_argument("--output", "-o", help="Свой путь для файла экспорта")

    # --- update ---
    sp_update = subparsers.add_parser("update", help="Добавить новые сообщения в существующий экспорт")
    sp_update.add_argument("json_path", help="Путь к JSON-файлу экспорта")
    sp_update.add_argument("--no-media", action="store_true", help="Не скачивать медиа")

    # --- download-media ---
    sp_dl = subparsers.add_parser("download-media", help="Докачать недостающие медиа-файлы")
    sp_dl.add_argument("json_path", help="Путь к JSON-файлу экспорта")

    # --- analyze ---
    sp_analyze = subparsers.add_parser("analyze", help="Офлайн-анализ экспорта: отчет .md + .json")
    sp_analyze.add_argument("json_path", help="Путь к JSON-файлу экспорта")
    sp_analyze.add_argument("--output", "-o", help="Свой путь для отчета .md")

    # --- channel-check ---
    sp_chcheck = subparsers.add_parser("channel-check", help="Проверить владение каналом")
    sp_chcheck.add_argument("user", help="Пользователь: @username или числовой ID")

    # --- channel-export ---
    sp_chexp = subparsers.add_parser("channel-export", help="Полный экспорт канала с подписчиками")
    sp_chexp.add_argument("channel", help="Канал: @username или URL")

    # --- channel-stats ---
    sp_chstats = subparsers.add_parser("channel-stats", help="Аналитический отчет по каналу")
    sp_chstats.add_argument("channel", help="Канал: @username или URL")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Роутинг команд
    if args.command == "setup":
        from tg_export.commands.setup import run
        run(args)

    elif args.command == "auth":
        from tg_export.commands.auth import run
        run(args)

    elif args.command == "export":
        from tg_export.commands.export import run
        run(args)

    elif args.command == "collect":
        args.format = "md"
        args.topic = None
        from tg_export.commands.export import run
        run(args)

    elif args.command == "update":
        from tg_export.commands.update import run
        run(args)

    elif args.command == "download-media":
        from tg_export.commands.download_media import run
        run(args)

    elif args.command == "analyze":
        from tg_export.commands.analyze import run
        run(args)

    elif args.command == "channel-check":
        from tg_export.commands.channel_check import run
        run(args)

    elif args.command == "channel-export":
        from tg_export.commands.channel_export import run
        run(args)

    elif args.command == "channel-stats":
        from tg_export.commands.channel_stats import run
        run(args)


if __name__ == "__main__":
    main()
