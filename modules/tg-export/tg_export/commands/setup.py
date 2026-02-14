"""Интерактивная первоначальная настройка: создание .env и авторизация."""

import os
import shutil
import asyncio


def find_project_root():
    """Найти корень проекта (где лежит .env.example или pyproject.toml)."""
    # Сначала текущая директория
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, ".env.example")):
        return cwd
    # Затем директория пакета
    pkg_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if os.path.exists(os.path.join(pkg_dir, ".env.example")):
        return pkg_dir
    return cwd


def run(args):
    """Запустить интерактивную настройку."""
    print("=" * 60)
    print("Первоначальная настройка telegram-export")
    print("=" * 60)
    print()

    root = find_project_root()
    env_path = os.path.join(root, ".env")
    env_example = os.path.join(root, ".env.example")

    # Шаг 1: Создать .env
    if os.path.exists(env_path):
        print(f"Файл .env уже существует: {env_path}")
        answer = input("Перезаписать? (y/N): ").strip().lower()
        if answer != 'y':
            print("Пропускаю создание .env")
        else:
            _create_env(env_path, env_example)
    else:
        _create_env(env_path, env_example)

    # Шаг 2: Авторизация
    print()
    print("-" * 60)
    print("Шаг 2: Авторизация в Telegram")
    print("-" * 60)
    print()

    from tg_export.commands.auth import run as auth_run
    auth_run(args)


def _create_env(env_path, env_example):
    """Интерактивное создание .env файла."""
    print()
    print("Шаг 1: Настройка API ключей")
    print("-" * 60)
    print()
    print("Для работы нужны API ключи Telegram.")
    print("Получите их на: https://my.telegram.org/apps")
    print()

    api_id = input("Введите TELEGRAM_API_ID: ").strip()
    api_hash = input("Введите TELEGRAM_API_HASH: ").strip()

    if not api_id or not api_hash:
        print("Ошибка: API_ID и API_HASH обязательны.")
        return

    # Валидация API_ID
    try:
        int(api_id)
    except ValueError:
        print(f"Ошибка: API_ID должен быть числом, получено: {api_id!r}")
        return

    session_name = input("Имя сессии (Enter = tg_export_session): ").strip() or "tg_export_session"
    export_dir = input("Папка экспорта (Enter = exports): ").strip() or "exports"

    content = f"""# Telegram API credentials
# Получите на https://my.telegram.org/apps
TELEGRAM_API_ID={api_id}
TELEGRAM_API_HASH={api_hash}

# Имя файла сессии (без расширения)
SESSION_NAME={session_name}

# Папка для экспортов
EXPORT_DIR={export_dir}
"""

    with open(env_path, 'w') as f:
        f.write(content)

    print(f"\nФайл .env создан: {env_path}")

    # Перезагружаем конфиг
    from tg_export import config
    config.load_config()
    config.API_ID = os.getenv("TELEGRAM_API_ID", "")
    config.API_HASH = os.getenv("TELEGRAM_API_HASH", "")
    config.SESSION_NAME = os.getenv("SESSION_NAME", "tg_export_session")
    config.EXPORT_DIR = os.getenv("EXPORT_DIR", "exports")
