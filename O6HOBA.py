#!/usr/bin/env python3
"""
🔄 O6HOBA - Скрипт обновления Л.И.С.А.
Локальная Интеллектуальная Система Автоматизации
Версия: 1.0

Автор: Никита Шорин (shorin-nikita)
GitHub: https://github.com/shorin-nikita/lisa
"""

import os
import subprocess
import platform
import sys
import shutil
import secrets
from datetime import datetime

# Цвета для вывода
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    print(f"""{Colors.HEADER}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║                   ОБНОВЛЕНИЕ Л.И.С.А.                         ║
║         Локальная Интеллектуальная Система Автоматизации      ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.ENDC}""")

def run_command(cmd, check=True, capture_output=False):
    """Выполнить команду в shell"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output,
                               text=True, check=check, timeout=300)
        if capture_output:
            return result.stdout.strip()
        return True
    except Exception as e:
        print(f"{Colors.FAIL}❌ Ошибка: {e}{Colors.ENDC}")
        return False

def detect_gpu_type():
    """Определение типа GPU"""
    print(f"\n{Colors.OKBLUE}🎮 Определение GPU конфигурации...{Colors.ENDC}")
    
    # Проверка NVIDIA
    nvidia_check = run_command("nvidia-smi", check=False, capture_output=True)
    if nvidia_check and "NVIDIA" in str(nvidia_check):
        print(f"{Colors.OKGREEN}✅ Найден NVIDIA GPU{Colors.ENDC}")
        return "gpu-nvidia"
    
    # Проверка AMD на Linux
    if platform.system() == "Linux":
        amd_check = run_command("lspci | grep -i amd", check=False, capture_output=True)
        if amd_check and "amd" in str(amd_check).lower():
            print(f"{Colors.OKGREEN}✅ Найден AMD GPU{Colors.ENDC}")
            return "gpu-amd"
    
    # Проверка Apple Silicon
    if platform.system() == "Darwin":
        mac_check = run_command("system_profiler SPHardwareDataType | grep 'Chip'", 
                               check=False, capture_output=True)
        if mac_check and any(x in str(mac_check) for x in ["M1", "M2", "M3", "M4"]):
            print(f"{Colors.OKGREEN}✅ Найден Apple Silicon (CPU профиль){Colors.ENDC}")
            return "cpu"
    
    print(f"{Colors.WARNING}⚠️  GPU не найден, будет использован CPU профиль{Colors.ENDC}")
    return "cpu"

def detect_environment():
    """Определение окружения (public/private)"""
    print(f"\n{Colors.OKBLUE}🌐 Определение окружения...{Colors.ENDC}")
    
    if not os.path.exists('.env'):
        print(f"{Colors.WARNING}⚠️  Файл .env не найден, используется private{Colors.ENDC}")
        return "private"
    
    # Проверяем наличие доменов в .env
    with open('.env', 'r') as f:
        env_content = f.read()
        if 'N8N_HOSTNAME=' in env_content and not 'N8N_HOSTNAME=:' in env_content:
            # Есть настоящий домен, не просто :8001
            for line in env_content.split('\n'):
                if line.startswith('N8N_HOSTNAME=') and not line.startswith('N8N_HOSTNAME=:'):
                    hostname = line.split('=')[1].strip()
                    if hostname and '.' in hostname:
                        print(f"{Colors.OKGREEN}✅ Обнаружены домены, окружение: public{Colors.ENDC}")
                        return "public"
    
    print(f"{Colors.OKGREEN}✅ Локальная установка, окружение: private{Colors.ENDC}")
    return "private"

def get_system_resources():
    """Получение информации о ресурсах системы"""
    print(f"\n{Colors.OKBLUE}💻 Определение ресурсов системы...{Colors.ENDC}")
    
    try:
        # Количество CPU ядер
        cpu_count = os.cpu_count() or 4
        
        # Объем RAM (в ГБ)
        if platform.system() == "Linux":
            mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
            mem_gb = mem_bytes / (1024.**3)
        elif platform.system() == "Darwin":
            mem_result = run_command("sysctl -n hw.memsize", capture_output=True)
            mem_gb = int(mem_result) / (1024.**3) if mem_result else 8
        else:
            mem_gb = 8  # Fallback для Windows
        
        print(f"{Colors.OKGREEN}   CPU ядер: {cpu_count}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}   RAM: {mem_gb:.1f} ГБ{Colors.ENDC}")
        
        return cpu_count, int(mem_gb)
    except:
        print(f"{Colors.WARNING}⚠️  Не удалось определить ресурсы, используются значения по умолчанию{Colors.ENDC}")
        return 4, 8

def create_backup():
    """Создание резервной копии перед обновлением"""
    print(f"\n{Colors.OKBLUE}💾 Создание резервной копии...{Colors.ENDC}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"lisa-backup-{timestamp}.tar.gz"
    
    # Список файлов и директорий для backup
    backup_items = []
    if os.path.exists('.env'):
        backup_items.append('.env')
    if os.path.exists('n8n/backup'):
        backup_items.append('n8n/backup')
    if os.path.exists('neo4j/data'):
        backup_items.append('neo4j/data')
    if os.path.exists('shared'):
        backup_items.append('shared')
    
    if not backup_items:
        print(f"{Colors.WARNING}⚠️  Нет файлов для backup{Colors.ENDC}")
        return True
    
    cmd = f"tar -czf {backup_name} {' '.join(backup_items)}"
    if run_command(cmd, check=False):
        print(f"{Colors.OKGREEN}✅ Backup создан: {backup_name}{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}❌ Не удалось создать backup{Colors.ENDC}")
        return False

def pull_git_updates():
    """Получение обновлений из Git"""
    print(f"\n{Colors.OKBLUE}🔄 Получение обновлений из Git...{Colors.ENDC}")
    
    # Проверка наличия изменений
    status = run_command("git status --porcelain", capture_output=True)
    if status:
        print(f"{Colors.WARNING}⚠️  Обнаружены локальные изменения:{Colors.ENDC}")
        print(status)
        response = input(f"\n{Colors.BOLD}Продолжить обновление? (y/n): {Colors.ENDC}").strip().lower()
        if response != 'y':
            print(f"{Colors.WARNING}Обновление отменено{Colors.ENDC}")
            return False
    
    # Pull изменений
    if run_command("git pull origin main"):
        print(f"{Colors.OKGREEN}✅ Git обновления получены{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}❌ Не удалось получить обновления{Colors.ENDC}")
        return False

def stop_services(profile):
    """Остановка сервисов"""
    print(f"\n{Colors.OKBLUE}🛑 Остановка сервисов...{Colors.ENDC}")
    
    cmd = f"docker compose -p localai --profile {profile} down"
    if run_command(cmd):
        print(f"{Colors.OKGREEN}✅ Сервисы остановлены{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}❌ Не удалось остановить сервисы{Colors.ENDC}")
        return False

def update_containers():
    """Обновление Docker контейнеров"""
    print(f"\n{Colors.OKBLUE}🐳 Обновление Docker образов...{Colors.ENDC}")
    
    # Pull новых образов (игнорируем образы, которые нужно собирать)
    if not run_command("docker compose -p localai pull --ignore-buildable"):
        print(f"{Colors.FAIL}❌ Не удалось скачать обновления{Colors.ENDC}")
        return False
    
    # Rebuild кастомных образов (n8n-ffmpeg)
    print(f"\n{Colors.OKBLUE}🔨 Пересборка кастомных образов...{Colors.ENDC}")
    if not run_command("docker compose -p localai build n8n"):
        print(f"{Colors.WARNING}⚠️  Не удалось пересобрать n8n-ffmpeg{Colors.ENDC}")
    
    print(f"{Colors.OKGREEN}✅ Docker образы обновлены{Colors.ENDC}")
    return True

def restart_services(profile, environment):
    """Перезапуск сервисов"""
    print(f"\n{Colors.OKBLUE}🚀 Перезапуск сервисов...{Colors.ENDC}")

    cmd = f"python3 start_services.py --profile {profile} --environment {environment}"
    print(f"{Colors.OKCYAN}   Команда: {cmd}{Colors.ENDC}")

    if run_command(cmd):
        print(f"{Colors.OKGREEN}✅ Сервисы запущены{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}❌ Не удалось запустить сервисы{Colors.ENDC}")
        return False

def verify_health():
    """Проверка здоровья сервисов"""
    print(f"\n{Colors.OKBLUE}🏥 Проверка здоровья сервисов...{Colors.ENDC}")
    
    import time
    time.sleep(10)  # Даем время на запуск
    
    # Проверка запущенных контейнеров
    result = run_command("docker ps --filter 'name=localai' --format '{{.Names}}: {{.Status}}'", 
                        capture_output=True)
    
    if result:
        print(f"\n{Colors.OKGREEN}Статус контейнеров:{Colors.ENDC}")
        print(result)
        return True
    else:
        print(f"{Colors.FAIL}❌ Не удалось проверить статус{Colors.ENDC}")
        return False

def generate_secret_key(length=32):
    """Генерация криптографически безопасного секрета."""
    return secrets.token_hex(length)


def parse_proxy_input(proxy_string):
    """
    Parse proxy string in format: IP:PORT@USER:PASS
    Returns dict with keys: ip, port, user, password
    Returns None if parsing fails or input is '-'
    """
    if not proxy_string or proxy_string.strip() == '-':
        return None

    try:
        # Format: IP:PORT@USER:PASS
        if '@' in proxy_string:
            ip_port, user_pass = proxy_string.split('@', 1)
            ip, port = ip_port.split(':', 1)
            user, password = user_pass.split(':', 1)
        else:
            # Format without auth: IP:PORT (not recommended)
            ip, port = proxy_string.split(':', 1)
            user, password = '', ''

        return {
            'ip': ip.strip(),
            'port': port.strip(),
            'user': user.strip(),
            'password': password.strip()
        }
    except ValueError:
        return None


def validate_proxy_input(proxy_string):
    """Validate proxy input format."""
    import re
    if proxy_string.strip() == '-':
        return True

    result = parse_proxy_input(proxy_string)
    if result is None:
        return False

    # Validate IP format (basic check)
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    if not re.match(ip_pattern, result['ip']):
        return False

    # Validate port
    try:
        port = int(result['port'])
        if port < 1 or port > 65535:
            return False
    except ValueError:
        return False

    return True


def generate_squid_config(proxy_data):
    """
    Generate squid.conf from template using proxy data.
    Returns True on success, False on failure.
    """
    template_path = os.path.join(os.path.dirname(__file__), 'squid', 'squid.conf.template')
    config_path = os.path.join(os.path.dirname(__file__), 'squid', 'squid.conf')

    try:
        # Read template
        with open(template_path, 'r') as f:
            template = f.read()

        # Replace placeholders
        config = template.replace('{PROXY_IP}', proxy_data['ip'])
        config = config.replace('{PROXY_PORT}', proxy_data['port'])
        config = config.replace('{PROXY_USER}', proxy_data['user'])
        config = config.replace('{PROXY_PASS}', proxy_data['password'])

        # Write config
        with open(config_path, 'w') as f:
            f.write(config)

        print(f"{Colors.OKGREEN}✅ Конфигурация Squid обновлена: squid/squid.conf{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"{Colors.FAIL}❌ Ошибка создания конфигурации Squid: {e}{Colors.ENDC}")
        return False


def get_current_proxy_config():
    """Получение текущей конфигурации прокси из .env."""
    if not os.path.exists('.env'):
        return None

    config = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('PROXY_ENABLED='):
                    config['enabled'] = line.split('=', 1)[1].lower() == 'true'
                elif line.startswith('PROXY_IP='):
                    config['ip'] = line.split('=', 1)[1]
                elif line.startswith('PROXY_PORT='):
                    config['port'] = line.split('=', 1)[1]
                elif line.startswith('PROXY_USER='):
                    config['user'] = line.split('=', 1)[1]
                elif line.startswith('PROXY_PASS='):
                    config['password'] = line.split('=', 1)[1]
    except:
        return None

    return config if config.get('enabled') else None


def update_proxy_config():
    """Обновление конфигурации прокси."""
    print(f"\n{Colors.OKBLUE}🌐 Настройка прокси для API запросов:{Colors.ENDC}")

    current = get_current_proxy_config()
    if current:
        print(f"{Colors.OKGREEN}   Текущий прокси: {current['ip']}:{current['port']}@{current['user']}:***{Colors.ENDC}")
        print(f"{Colors.WARNING}   Введите новый прокси, '-' для отключения, или Enter чтобы оставить текущий{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}   Прокси не настроен. Формат: IP:PORT@USER:PASS{Colors.ENDC}")
        print(f"{Colors.WARNING}   Введите прокси или '-' для пропуска{Colors.ENDC}")

    while True:
        proxy_input = input(f"\n{Colors.BOLD}Прокси: {Colors.ENDC}").strip()

        # Если Enter и есть текущий прокси — оставляем
        if not proxy_input and current:
            print(f"{Colors.OKGREEN}✅ Используется текущий прокси{Colors.ENDC}")
            return None  # Не менять

        # Если Enter и нет прокси — пропускаем
        if not proxy_input and not current:
            return None

        # Если '-' — отключаем прокси
        if proxy_input == '-':
            return {'disable': True}

        # Валидация
        if validate_proxy_input(proxy_input):
            return parse_proxy_input(proxy_input)
        else:
            print(f"{Colors.FAIL}❌ Неверный формат. Используйте: IP:PORT@USER:PASS{Colors.ENDC}")


def apply_proxy_config(proxy_data):
    """Применение новой конфигурации прокси к .env файлу."""
    if not os.path.exists('.env'):
        return False

    with open('.env', 'r') as f:
        lines = f.readlines()

    new_lines = []
    proxy_section_found = False
    skip_until_section = False

    for line in lines:
        # Пропускаем старую секцию прокси
        if '# Proxy Configuration' in line:
            skip_until_section = True
            proxy_section_found = True
            continue
        if skip_until_section:
            if line.startswith('#') and 'Configuration' in line:
                skip_until_section = False
                new_lines.append(line)
            elif line.startswith('PROXY_') or line.strip() == '':
                continue
            else:
                skip_until_section = False
                new_lines.append(line)
            continue
        new_lines.append(line)

    # Добавляем новую секцию прокси
    if proxy_data and not proxy_data.get('disable'):
        proxy_section = f"""
############
# Proxy Configuration (for API requests)
############
PROXY_ENABLED=true
PROXY_IP={proxy_data['ip']}
PROXY_PORT={proxy_data['port']}
PROXY_USER={proxy_data['user']}
PROXY_PASS={proxy_data['password']}

"""
        # Вставляем перед секцией Database
        inserted = False
        final_lines = []
        for line in new_lines:
            if '# Database - PostgreSQL Configuration' in line and not inserted:
                final_lines.append(proxy_section)
                inserted = True
            final_lines.append(line)

        if not inserted:
            final_lines.append(proxy_section)

        new_lines = final_lines

        # Генерируем squid.conf
        generate_squid_config(proxy_data)
    else:
        # Добавляем закомментированную секцию
        proxy_section = """
############
# Proxy Configuration (disabled)
############
# PROXY_ENABLED=false
# PROXY_IP=
# PROXY_PORT=
# PROXY_USER=
# PROXY_PASS=

"""
        # Вставляем перед секцией Database
        inserted = False
        final_lines = []
        for line in new_lines:
            if '# Database - PostgreSQL Configuration' in line and not inserted:
                final_lines.append(proxy_section)
                inserted = True
            final_lines.append(line)

        if not inserted:
            final_lines.append(proxy_section)

        new_lines = final_lines

    with open('.env', 'w') as f:
        f.writelines(new_lines)

    return True


def migrate_env_for_task_runners():
    """
    Миграция .env для поддержки Task Runners (External Mode).
    Добавляет N8N_RUNNERS_AUTH_TOKEN если его нет.
    """
    print(f"\n{Colors.OKBLUE}🔄 Проверка конфигурации Task Runners...{Colors.ENDC}")

    if not os.path.exists('.env'):
        print(f"{Colors.WARNING}⚠️  Файл .env не найден, пропускаем миграцию{Colors.ENDC}")
        return

    with open('.env', 'r') as f:
        env_content = f.read()

    # Проверяем наличие N8N_RUNNERS_AUTH_TOKEN
    if 'N8N_RUNNERS_AUTH_TOKEN=' in env_content:
        print(f"{Colors.OKGREEN}✅ Task Runners уже настроены (N8N_RUNNERS_AUTH_TOKEN найден){Colors.ENDC}")
        return

    # Генерируем новый токен
    runners_token = generate_secret_key(32)

    # Добавляем токен после N8N_USER_MANAGEMENT_JWT_SECRET или в начало N8N секции
    lines = env_content.split('\n')
    new_lines = []
    token_added = False

    for i, line in enumerate(lines):
        new_lines.append(line)

        # Добавляем после N8N_USER_MANAGEMENT_JWT_SECRET
        if line.startswith('N8N_USER_MANAGEMENT_JWT_SECRET=') and not token_added:
            new_lines.append('')
            new_lines.append('# Task Runners (External Mode) - обязательно для n8n 2.0+')
            new_lines.append('# Секретный токен для связи n8n и контейнера runners')
            new_lines.append(f'N8N_RUNNERS_AUTH_TOKEN={runners_token}')
            token_added = True

    # Если не нашли N8N_USER_MANAGEMENT_JWT_SECRET, добавляем в начало
    if not token_added:
        new_lines.insert(0, f'N8N_RUNNERS_AUTH_TOKEN={runners_token}')
        new_lines.insert(0, '# Секретный токен для связи n8n и контейнера runners')
        new_lines.insert(0, '# Task Runners (External Mode) - обязательно для n8n 2.0+')
        new_lines.insert(0, '')

    with open('.env', 'w') as f:
        f.write('\n'.join(new_lines))

    print(f"{Colors.OKGREEN}✅ Добавлен N8N_RUNNERS_AUTH_TOKEN для External Mode{Colors.ENDC}")
    print(f"{Colors.OKCYAN}   Task Runners теперь работают в отдельном контейнере{Colors.ENDC}")


def calculate_resource_limits(cpu_count, mem_gb):
    """
    Тиерная система распределения ресурсов, оптимизированная для LLM.

    Стратегия: вспомогательные сервисы получают фиксированный максимум,
    ВСЯ оставшаяся память идёт Ollama для запуска больших моделей.

    Docker overhead + ядро + процесс ollama serve занимают ~1.5GB,
    поэтому реально доступная для моделей память = лимит - 1.5GB.

    | RAM       | Ollama        | N8N  | PostgreSQL | Runners | Qdrant |
    |-----------|---------------|------|------------|---------|--------|
    | <= 8GB    | 2.5GB         | 1.5GB| 1.5GB      | 512MB   | 384MB  |
    | 9-16GB    | RAM - сервисы | 2GB  | 2GB        | 768MB   | 512MB  |
    | 17-32GB   | RAM - сервисы | 3GB  | 2.5GB      | 1GB     | 512MB  |
    | > 32GB    | RAM - сервисы | 4GB  | 3GB        | 1.5GB   | 1GB    |
    """
    OLLAMA_OVERHEAD_GB = 1.5  # Docker + kernel + ollama serve process

    if mem_gb <= 8:
        ollama_mem_gb = 2.5
        n8n_mem_gb = 1.5
        postgres_mem_gb = 1.5
        runners_mem_mb = 512
        qdrant_mem_mb = 384
    elif mem_gb <= 16:
        n8n_mem_gb = min(2.0, round(mem_gb * 0.15, 1))
        postgres_mem_gb = min(2.0, round(mem_gb * 0.15, 1))
        runners_mem_mb = 768
        qdrant_mem_mb = 512
        reserved = n8n_mem_gb + postgres_mem_gb + (runners_mem_mb + qdrant_mem_mb) / 1024 + 2.0
        ollama_mem_gb = round(mem_gb - reserved, 1)
    elif mem_gb <= 32:
        n8n_mem_gb = 3.0
        postgres_mem_gb = 2.5
        runners_mem_mb = 1024
        qdrant_mem_mb = 512
        reserved = n8n_mem_gb + postgres_mem_gb + (runners_mem_mb + qdrant_mem_mb) / 1024 + 3.0
        ollama_mem_gb = round(mem_gb - reserved, 1)
    else:
        n8n_mem_gb = 4.0
        postgres_mem_gb = 3.0
        runners_mem_mb = 1536
        qdrant_mem_mb = 1024
        reserved = n8n_mem_gb + postgres_mem_gb + (runners_mem_mb + qdrant_mem_mb) / 1024 + 4.0
        ollama_mem_gb = round(mem_gb - reserved, 1)

    # CPU — процентное распределение (работает на любом масштабе)
    ollama_cpu = max(2, min(int(cpu_count * 0.5), cpu_count - 1))
    n8n_cpu = max(1, min(int(cpu_count * 0.3), cpu_count - 1))
    postgres_cpu = max(1, min(int(cpu_count * 0.25), cpu_count - 1))
    runners_cpu = max(0.5, min(int(cpu_count * 0.15), cpu_count - 1))
    qdrant_cpu = max(0.5, min(int(cpu_count * 0.1), cpu_count - 1))

    # Node.js heap = 75% от лимита контейнера
    n8n_heap_mb = int(n8n_mem_gb * 1024 * 0.75)

    # Доступная память для моделей (после overhead)
    ollama_available_gb = round(max(0, ollama_mem_gb - OLLAMA_OVERHEAD_GB), 1)

    return {
        'ollama': {'cpu': ollama_cpu, 'mem_gb': ollama_mem_gb, 'available_gb': ollama_available_gb},
        'n8n': {'cpu': n8n_cpu, 'mem_gb': n8n_mem_gb, 'heap_mb': n8n_heap_mb},
        'postgres': {'cpu': postgres_cpu, 'mem_gb': postgres_mem_gb},
        'runners': {'cpu': runners_cpu, 'mem_mb': runners_mem_mb},
        'qdrant': {'cpu': qdrant_cpu, 'mem_mb': qdrant_mem_mb},
    }


def update_env_with_resources(cpu_count, mem_gb):
    """
    Обновление .env файла с рекомендованными лимитами ресурсов.

    ВАЖНО: При обновлении ВСЕГДА пересчитываем лимиты, чтобы:
    1. Применить новые оптимизации из обновлений
    2. Исправить проблемы совместимости (NODE_OPTIONS vs MEM_LIMIT)
    3. Адаптироваться к изменениям в системе

    Если RESOURCE_LIMITS_MANUAL=true — пропускаем пересчёт.
    """
    print(f"\n{Colors.OKBLUE}⚙️  Настройка лимитов ресурсов...{Colors.ENDC}")

    if not os.path.exists('.env'):
        print(f"{Colors.WARNING}⚠️  Файл .env не найден, пропускаем{Colors.ENDC}")
        return

    # Читаем текущий .env
    with open('.env', 'r') as f:
        content = f.read()

    # Проверяем флаг ручного управления
    if 'RESOURCE_LIMITS_MANUAL=true' in content:
        print(f"{Colors.OKGREEN}✅ RESOURCE_LIMITS_MANUAL=true — лимиты не пересчитываются{Colors.ENDC}")
        print(f"{Colors.OKCYAN}   Удалите RESOURCE_LIMITS_MANUAL=true из .env для автоматической настройки{Colors.ENDC}")
        return

    # Рассчитываем оптимальные лимиты
    limits = calculate_resource_limits(cpu_count, mem_gb)

    # Удаляем старую секцию Resource Limits (если есть)
    lines = content.split('\n')
    new_lines = []
    skip_section = False

    for line in lines:
        # Начало секции Resource Limits
        if '# Resource Limits' in line or '# Оптимизировано для' in line:
            skip_section = True
            continue
        # Конец секции - пустая строка или новая секция
        if skip_section:
            if line.strip() == '' or (line.startswith('#') and 'Limit' not in line and 'RAM' not in line and 'Runners' not in line and 'модел' not in line and 'RESOURCE' not in line):
                skip_section = False
                if line.strip() != '':
                    new_lines.append(line)
            elif line.startswith(('OLLAMA_', 'POSTGRES_', 'N8N_', 'QDRANT_', 'RESOURCE_LIMITS_')) and ('LIMIT' in line or 'RESERVE' in line or 'HEAP' in line or 'MANUAL' in line):
                continue  # Пропускаем старые лимиты
            continue
        new_lines.append(line)

    # Убираем лишние пустые строки в конце
    while new_lines and new_lines[-1].strip() == '':
        new_lines.pop()

    # Добавляем новую секцию Resource Limits
    o = limits['ollama']
    n = limits['n8n']
    p = limits['postgres']
    r = limits['runners']
    q = limits['qdrant']

    resource_section = f"""

############
# Resource Limits (автоматически настроено {datetime.now().strftime('%Y-%m-%d %H:%M')})
# Оптимизировано для {mem_gb}GB RAM
# Для ручного управления лимитами добавьте: RESOURCE_LIMITS_MANUAL=true
# При обновлении через O6HOBA.py лимиты пересчитываются автоматически
############

# Ollama — LLM и embedding модели
# Доступно для моделей: ~{o['available_gb']}GB (после overhead Docker/ядра/процесса)
OLLAMA_CPU_LIMIT={o['cpu']}
OLLAMA_MEM_LIMIT={o['mem_gb']}G
OLLAMA_CPU_RESERVE={max(1, o['cpu'] // 2)}
OLLAMA_MEM_RESERVE={max(1, int(o['mem_gb'] // 2))}G

# N8N — основной процесс workflow engine
N8N_CPU_LIMIT={n['cpu']}
N8N_MEM_LIMIT={n['mem_gb']}G
N8N_CPU_RESERVE={max(0.5, n['cpu'] / 2)}
N8N_MEM_RESERVE={max(512, int(n['mem_gb'] * 512))}M
# Node.js heap size (75% от лимита контейнера)
N8N_HEAP_SIZE={n['heap_mb']}

# PostgreSQL — Supabase + pgvector для RAG
POSTGRES_CPU_LIMIT={p['cpu']}
POSTGRES_MEM_LIMIT={p['mem_gb']}G
POSTGRES_CPU_RESERVE={max(0.5, p['cpu'] / 2)}
POSTGRES_MEM_RESERVE={max(512, int(p['mem_gb'] * 512))}M

# N8N Task Runners — External Mode для Code нод
N8N_RUNNERS_CPU_LIMIT={r['cpu']}
N8N_RUNNERS_MEM_LIMIT={r['mem_mb']}M
N8N_RUNNERS_CPU_RESERVE=0.25
N8N_RUNNERS_MEM_RESERVE={r['mem_mb'] // 2}M

# Qdrant — векторное хранилище (резерв)
QDRANT_CPU_LIMIT={q['cpu']}
QDRANT_MEM_LIMIT={q['mem_mb']}M
QDRANT_CPU_RESERVE=0.25
QDRANT_MEM_RESERVE={q['mem_mb'] // 2}M
"""

    new_lines.append(resource_section)

    with open('.env', 'w') as f:
        f.write('\n'.join(new_lines))

    print(f"{Colors.OKGREEN}✅ Лимиты ресурсов оптимизированы для {mem_gb}GB RAM:{Colors.ENDC}")
    print(f"   Ollama:     {o['cpu']} CPU, {o['mem_gb']}G RAM (для моделей: ~{o['available_gb']}GB)")
    print(f"   N8N:        {n['cpu']} CPU, {n['mem_gb']}G RAM (heap: {n['heap_mb']}MB)")
    print(f"   PostgreSQL: {p['cpu']} CPU, {p['mem_gb']}G RAM")
    print(f"   Runners:    {r['cpu']} CPU, {r['mem_mb']}M RAM")
    print(f"   Qdrant:     {q['cpu']} CPU, {q['mem_mb']}M RAM")

def main():
    print_header()
    
    print(f"\n{Colors.WARNING}⚠️  ВНИМАНИЕ: Это обновит систему до последней версии{Colors.ENDC}")
    print(f"{Colors.WARNING}   Будет создана резервная копия перед обновлением{Colors.ENDC}\n")
    
    response = input(f"{Colors.BOLD}Продолжить обновление? (y/n): {Colors.ENDC}").strip().lower()
    if response != 'y':
        print(f"\n{Colors.WARNING}Обновление отменено{Colors.ENDC}")
        sys.exit(0)
    
    # Шаг 1: Определение конфигурации
    gpu_profile = detect_gpu_type()
    environment = detect_environment()
    cpu_count, mem_gb = get_system_resources()

    # Шаг 2: Создание backup
    if not create_backup():
        print(f"\n{Colors.FAIL}❌ Не удалось создать backup, прерываем обновление{Colors.ENDC}")
        sys.exit(1)

    # Шаг 3: Остановка сервисов
    if not stop_services(gpu_profile):
        print(f"\n{Colors.FAIL}❌ Не удалось остановить сервисы{Colors.ENDC}")
        sys.exit(1)

    # Шаг 4: Pull обновлений из Git
    if not pull_git_updates():
        print(f"\n{Colors.FAIL}❌ Не удалось получить обновления{Colors.ENDC}")
        sys.exit(1)

    # Шаг 5: Миграция для Task Runners (External Mode)
    migrate_env_for_task_runners()

    # Шаг 5.5: Настройка прокси
    proxy_data = update_proxy_config()
    if proxy_data is not None:
        apply_proxy_config(proxy_data)

    # Шаг 6: Настройка лимитов ресурсов
    update_env_with_resources(cpu_count, mem_gb)

    # Шаг 6: Обновление контейнеров
    if not update_containers():
        print(f"\n{Colors.FAIL}❌ Не удалось обновить контейнеры{Colors.ENDC}")
        sys.exit(1)

    # Шаг 7: Перезапуск сервисов
    if not restart_services(gpu_profile, environment):
        print(f"\n{Colors.FAIL}❌ Не удалось перезапустить сервисы{Colors.ENDC}")
        sys.exit(1)

    # Шаг 8: Проверка здоровья
    verify_health()

    # Финальное сообщение
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}{'='*65}")
    print(f"  🎉 Обновление успешно завершено!")
    print(f"{'='*65}{Colors.ENDC}")
    print(f"\n{Colors.OKCYAN}📋 Система обновлена и запущена{Colors.ENDC}")
    print(f"{Colors.OKCYAN}   Профиль: {gpu_profile}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}   Окружение: {environment}{Colors.ENDC}\n")

if __name__ == "__main__":
    main()

