#!/usr/bin/env python3
"""
start_services.py

This script starts the Supabase stack first, waits for it to initialize, and then starts
the local AI stack. Both stacks use the same Docker Compose project name ("localai")
so they appear together in Docker Desktop.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys
import re
import threading

# Коды ошибок
EXIT_CODE_DISK_SPACE = 14


class DiskSpaceError(Exception):
    """Ошибка нехватки места на диске."""
    pass


# ============================================================================
# PROGRESS INDICATORS - Показывают пользователю, что система работает
# ============================================================================

class ProgressIndicator:
    """Индикатор прогресса для длительных операций."""

    UPDATE_INTERVAL = 5  # Обновление каждые 5 секунд

    def __init__(self, message, estimated_time=None):
        self.message = message
        self.estimated_time = estimated_time
        self.running = False
        self.thread = None
        self.start_time = None
        self.last_print_time = 0

    def _spinner(self):
        """Периодический вывод прогресса."""
        while self.running:
            current_time = time.time()
            elapsed = int(current_time - self.start_time)

            # Печатаем только каждые UPDATE_INTERVAL секунд
            if current_time - self.last_print_time >= self.UPDATE_INTERVAL:
                self.last_print_time = current_time
                elapsed_str = f"{elapsed // 60}:{elapsed % 60:02d}"

                if self.estimated_time:
                    remaining = max(0, self.estimated_time - elapsed)
                    remaining_str = f"~{remaining // 60}:{remaining % 60:02d} осталось"
                    print(f"   ⏳ {self.message} [{elapsed_str}] {remaining_str}")
                else:
                    print(f"   ⏳ {self.message} [{elapsed_str}]")

            time.sleep(1)

    def start(self):
        """Запуск индикатора."""
        self.running = True
        self.start_time = time.time()
        self.last_print_time = self.start_time
        # Печатаем начальное сообщение сразу
        print(f"   ⏳ {self.message} [0:00] ~{self.estimated_time // 60}:{self.estimated_time % 60:02d} осталось" if self.estimated_time else f"   ⏳ {self.message} [0:00]")
        self.thread = threading.Thread(target=self._spinner, daemon=True)
        self.thread.start()

    def stop(self, success=True):
        """Остановка индикатора."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        elapsed = int(time.time() - self.start_time)
        elapsed_str = f"{elapsed // 60}:{elapsed % 60:02d}"
        icon = "✅" if success else "❌"
        print(f"   {icon} {self.message} — завершено [{elapsed_str}]")


def print_step(step_num, total_steps, message, estimated_time=None):
    """Печать шага установки с прогрессом."""
    percent = int((step_num / total_steps) * 100)
    bar_width = 20
    filled = int(bar_width * step_num / total_steps)
    bar = "█" * filled + "░" * (bar_width - filled)

    print(f"\n{'='*65}")
    print(f"📦 [{bar}] {percent}% — Шаг {step_num}/{total_steps}")
    print(f"   {message}")
    if estimated_time:
        print(f"   ⏱️  Ожидаемое время: {estimated_time}")
    print(f"{'='*65}\n")


def print_wait_countdown(message, seconds):
    """Показывает обратный отсчёт ожидания."""
    print(f"\n⏳ {message}")
    for remaining in range(seconds, 0, -1):
        mins = remaining // 60
        secs = remaining % 60
        if mins > 0:
            time_str = f"{mins}:{secs:02d}"
        else:
            time_str = f"{secs} сек"
        print(f"\r   ⏳ Осталось: {time_str}   ", end="", flush=True)
        time.sleep(1)
    print(f"\r   ✅ {message} — готово!                    ")


def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def run_command_with_output(cmd, cwd=None):
    """Run a shell command and return output."""
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result

def is_ipv6_network_error(stderr):
    """Проверка на ошибку IPv6 сети."""
    if not stderr:
        return False
    stderr_lower = stderr.lower()
    if "network is unreachable" in stderr_lower:
        # Ищем IPv6 адрес в ошибке
        ipv6_pattern = r'\[?[0-9a-fA-F]{1,4}(:[0-9a-fA-F]{0,4}){2,7}\]?:\d+'
        if re.search(ipv6_pattern, stderr):
            return True
    return False

def is_container_name_conflict(output):
    """
    Проверка на ошибку конфликта имён контейнеров.
    Возвращает (True, [список имён]) если ошибка найдена.
    """
    if not output:
        return False, []

    # Паттерн: The container name "/xxx" is already in use
    pattern = r'The container name ["\']?/([^"\']+)["\']? is already in use'
    matches = re.findall(pattern, output)

    if matches:
        return True, list(set(matches))
    return False, []


def is_disk_space_error(output):
    """
    Проверка на ошибку нехватки места на диске.
    Возвращает True если обнаружена ошибка "no space left on device".
    """
    if not output:
        return False
    output_lower = output.lower()
    return "no space left on device" in output_lower


def get_disk_usage_info():
    """Получение информации об использовании диска."""
    info = {}
    try:
        # Место на диске
        result = subprocess.run(
            ["df", "-h", "/var/lib/docker"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    info['docker_disk'] = {
                        'total': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'use_percent': parts[4]
                    }
    except:
        pass

    try:
        # Docker system df
        result = subprocess.run(
            ["docker", "system", "df"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            info['docker_system'] = result.stdout
    except:
        pass

    return info


def print_disk_space_recommendations():
    """Вывод рекомендаций по освобождению места на диске (безопасные для данных)."""
    print("\n" + "=" * 65)
    print("❌ ОШИБКА: Недостаточно места на диске (код 14)")
    print("=" * 65)

    # Показываем информацию о диске
    info = get_disk_usage_info()
    if 'docker_disk' in info:
        d = info['docker_disk']
        print(f"\n📊 Состояние диска Docker:")
        print(f"   Всего: {d['total']}, Использовано: {d['used']}, Свободно: {d['available']} ({d['use_percent']})")

    if 'docker_system' in info:
        print(f"\n📦 Использование Docker:")
        for line in info['docker_system'].strip().split('\n')[:5]:
            print(f"   {line}")

    print("\n" + "-" * 65)
    print("🔧 РЕКОМЕНДАЦИИ ПО ОСВОБОЖДЕНИЮ МЕСТА (безопасные для данных):")
    print("-" * 65)

    print("""
1. Удалить неиспользуемые Docker образы (НЕ удаляет volumes с данными):
   docker image prune -a

2. Удалить остановленные контейнеры:
   docker container prune

3. Удалить кэш сборки Docker:
   docker builder prune

4. Комплексная очистка БЕЗ удаления volumes (сохраняет данные):
   docker system prune -a

   ⚠️  НЕ используйте флаг --volumes, это удалит данные!

5. Проверить что занимает место:
   du -sh /var/lib/docker/*
   docker system df -v

6. Удалить старые логи Docker:
   sudo sh -c 'truncate -s 0 /var/lib/docker/containers/*/*-json.log'

7. Если используется журнал systemd:
   sudo journalctl --vacuum-size=100M
""")

    print("-" * 65)
    print("После освобождения места запустите обновление повторно:")
    print("   python3 O6HOBA.py")
    print("=" * 65 + "\n")

def fix_container_conflict(container_names):
    """
    Автоматическое удаление конфликтующих контейнеров.
    Возвращает True если все контейнеры удалены.
    """
    print(f"\n⚠️  Конфликт имён контейнеров: {', '.join(container_names)}")
    print("🔧 Автоматическое исправление...")

    success = True
    for name in container_names:
        try:
            # Принудительное удаление контейнера
            result = subprocess.run(
                ["docker", "rm", "-f", name],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 or "No such container" in (result.stderr or ""):
                print(f"   ✅ Контейнер '{name}' удалён")
            else:
                print(f"   ❌ Не удалось удалить '{name}': {result.stderr.strip()}")
                success = False
        except subprocess.TimeoutExpired:
            print(f"   ❌ Таймаут при удалении '{name}'")
            success = False
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            success = False

    if success:
        print("✅ Конфликтующие контейнеры удалены\n")
    return success

def fix_ipv6_issue():
    """Автоматическое исправление проблемы IPv6."""
    print("\n⚠️  Обнаружена проблема с IPv6 сетью")
    print("🔧 Автоматическое исправление...")

    try:
        # Отключаем IPv6 в sysctl
        print("   Отключение IPv6 в системе...")
        subprocess.run(
            ["sudo", "sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=1"],
            check=True, capture_output=True
        )
        subprocess.run(
            ["sudo", "sysctl", "-w", "net.ipv6.conf.default.disable_ipv6=1"],
            check=True, capture_output=True
        )

        # Делаем изменения постоянными
        sysctl_conf = "/etc/sysctl.conf"
        ipv6_settings = "net.ipv6.conf.all.disable_ipv6=1\nnet.ipv6.conf.default.disable_ipv6=1\n"

        # Проверяем, нет ли уже этих настроек
        try:
            with open(sysctl_conf, 'r') as f:
                content = f.read()
            if "net.ipv6.conf.all.disable_ipv6=1" not in content:
                subprocess.run(
                    f'echo "{ipv6_settings}" | sudo tee -a {sysctl_conf}',
                    shell=True, check=True, capture_output=True
                )
        except:
            pass

        # Перезапускаем Docker
        print("   Перезапуск Docker...")
        subprocess.run(["sudo", "systemctl", "restart", "docker"], check=True, capture_output=True)

        # Даём Docker время на запуск
        print("   Ожидание запуска Docker...")
        time.sleep(5)

        print("✅ IPv6 отключен, Docker перезапущен\n")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Не удалось автоматически исправить проблему IPv6")
        print(f"   Выполните вручную:")
        print(f"   sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        print(f"   sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        print(f"   sudo systemctl restart docker")
        return False

def run_docker_compose_with_retry(cmd, max_retries=3):
    """
    Запуск docker compose с автоматическим исправлением известных ошибок:
    - Ошибка IPv6 сети
    - Конфликт имён контейнеров (код 7)
    - Нехватка места на диске (код 14) - не исправляется автоматически
    """
    for attempt in range(max_retries):
        result = run_command_with_output(cmd)

        if result.returncode == 0:
            if result.stdout:
                print(result.stdout)
            return True

        error_output = (result.stderr or "") + (result.stdout or "")

        # Проверка 0: Нехватка места на диске (критическая, не исправляется)
        if is_disk_space_error(error_output):
            print(error_output)
            raise DiskSpaceError("no space left on device")

        # Проверка 1: Конфликт имён контейнеров
        is_conflict, container_names = is_container_name_conflict(error_output)
        if is_conflict:
            if attempt < max_retries - 1:
                if fix_container_conflict(container_names):
                    print("🔄 Повторная попытка запуска...\n")
                    continue
                else:
                    print(error_output)
                    raise subprocess.CalledProcessError(result.returncode, cmd)
            else:
                print(error_output)
                raise subprocess.CalledProcessError(result.returncode, cmd)

        # Проверка 2: Ошибка IPv6
        if is_ipv6_network_error(error_output):
            if attempt < max_retries - 1:
                if fix_ipv6_issue():
                    print("🔄 Повторная попытка загрузки...\n")
                    continue
                else:
                    print(error_output)
                    raise subprocess.CalledProcessError(result.returncode, cmd)
            else:
                print(error_output)
                raise subprocess.CalledProcessError(result.returncode, cmd)

        # Неизвестная ошибка - не пытаемся исправить
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
        raise subprocess.CalledProcessError(result.returncode, cmd)

    return False

def generate_secret_key(length=32):
    """Генерация криптографически безопасного секрета."""
    import secrets
    return secrets.token_hex(length)


def ensure_runners_auth_token():
    """
    Проверяет и добавляет N8N_RUNNERS_AUTH_TOKEN в .env если его нет.
    Это необходимо для External Mode Task Runners в n8n 2.0+.
    """
    if not os.path.exists('.env'):
        return

    with open('.env', 'r') as f:
        env_content = f.read()

    if 'N8N_RUNNERS_AUTH_TOKEN=' in env_content:
        return  # Токен уже есть

    # Генерируем и добавляем токен
    runners_token = generate_secret_key(32)

    lines = env_content.split('\n')
    new_lines = []
    token_added = False

    for line in lines:
        new_lines.append(line)
        if line.startswith('N8N_USER_MANAGEMENT_JWT_SECRET=') and not token_added:
            new_lines.append('')
            new_lines.append('# Task Runners (External Mode) - обязательно для n8n 2.0+')
            new_lines.append(f'N8N_RUNNERS_AUTH_TOKEN={runners_token}')
            token_added = True

    if not token_added:
        new_lines.insert(0, f'N8N_RUNNERS_AUTH_TOKEN={runners_token}')

    with open('.env', 'w') as f:
        f.write('\n'.join(new_lines))

    print("✅ Добавлен N8N_RUNNERS_AUTH_TOKEN для Task Runners")


def validate_env_file():
    """Проверка наличия и корректности .env файла."""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("Запустите сначала: python3 CTAPT.py")
        return False

    # Автоматически добавляем N8N_RUNNERS_AUTH_TOKEN если его нет
    ensure_runners_auth_token()

    # Базовые переменные (обязательны всегда)
    required_vars = [
        'POSTGRES_PASSWORD',
        'N8N_ENCRYPTION_KEY',
        'JWT_SECRET',
        'N8N_RUNNERS_AUTH_TOKEN'  # Обязателен для External Mode
    ]

    missing_vars = []
    with open('.env', 'r') as f:
        env_content = f.read()
        for var in required_vars:
            if f'{var}=' not in env_content:
                missing_vars.append(var)

    if missing_vars:
        print(f"❌ В .env отсутствуют переменные: {', '.join(missing_vars)}")
        return False

    print(f"✅ Файл .env валиден")
    return True

def is_proxy_enabled():
    """Проверка включен ли прокси в .env файле."""
    if not os.path.exists('.env'):
        return False

    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip().startswith('PROXY_ENABLED='):
                    value = line.split('=', 1)[1].strip().lower()
                    return value == 'true'
    except:
        pass

    return False

def get_system_resources():
    """Получение информации о ресурсах системы"""
    try:
        # Количество CPU ядер
        cpu_count = os.cpu_count() or 2
        
        # Объем RAM (в ГБ)
        if platform.system() == "Linux":
            mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
            mem_gb = mem_bytes / (1024.**3)
        elif platform.system() == "Darwin":
            result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=False)
            mem_gb = int(result.stdout.strip()) / (1024.**3) if result.stdout.strip() else 8
        else:
            mem_gb = 8  # Fallback
        
        return cpu_count, int(mem_gb)
    except:
        return 2, 8  # Минимальные значения по умолчанию

def is_wsl():
    """Detect if running inside WSL (Windows Subsystem for Linux)."""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except (FileNotFoundError, PermissionError):
        return False


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

    При первом запуске добавляет секцию Resource Limits.
    При обновлении лимиты пересчитываются через O6HOBA.py.
    """
    if not os.path.exists('.env'):
        return

    # Читаем текущий .env
    with open('.env', 'r') as f:
        content = f.read()

    # Если лимиты уже есть — не трогаем (O6HOBA.py обновит при необходимости)
    if 'OLLAMA_CPU_LIMIT' in content:
        return

    from datetime import datetime

    # Рассчитываем оптимальные лимиты
    limits = calculate_resource_limits(cpu_count, mem_gb)

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

    with open('.env', 'a') as f:
        f.write(resource_section)

    print(f"✅ Лимиты ресурсов настроены для {mem_gb}GB RAM:")
    print(f"   Ollama:     {o['cpu']} CPU, {o['mem_gb']}G RAM (для моделей: ~{o['available_gb']}GB)")
    print(f"   N8N:        {n['cpu']} CPU, {n['mem_gb']}G RAM (heap: {n['heap_mb']}MB)")
    print(f"   PostgreSQL: {p['cpu']} CPU, {p['mem_gb']}G RAM")
    print(f"   Runners:    {r['cpu']} CPU, {r['mem_mb']}M RAM")
    print(f"   Qdrant:     {q['cpu']} CPU, {q['mem_mb']}M RAM")

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    supabase_compose_file = os.path.join("supabase", "docker", "docker-compose.yml")

    if not os.path.exists("supabase"):
        print("\n📥 Клонирование репозитория Supabase...")
        print("   ℹ️  Это может занять 2-5 минут в зависимости от скорости интернета")
        print("   ℹ️  Загружается ~200MB (только папка docker/, не весь репозиторий)\n")

        progress = ProgressIndicator("Клонирование Supabase", estimated_time=180)
        progress.start()
        try:
            subprocess.run([
                "git", "clone", "--filter=blob:none", "--no-checkout",
                "https://github.com/supabase/supabase.git"
            ], check=True, capture_output=True)
            os.chdir("supabase")
            subprocess.run(["git", "sparse-checkout", "init", "--cone"], check=True, capture_output=True)
            subprocess.run(["git", "sparse-checkout", "set", "docker"], check=True, capture_output=True)
            subprocess.run(["git", "checkout", "master"], check=True, capture_output=True)
            os.chdir("..")
            progress.stop(success=True)
        except subprocess.CalledProcessError as e:
            progress.stop(success=False)
            raise e

    elif not os.path.exists(supabase_compose_file):
        print("Supabase repository exists but files missing, re-checking out...")
        progress = ProgressIndicator("Восстановление файлов Supabase", estimated_time=60)
        progress.start()
        try:
            os.chdir("supabase")
            subprocess.run(["git", "sparse-checkout", "init", "--cone"], check=True, capture_output=True)
            subprocess.run(["git", "sparse-checkout", "set", "docker"], check=True, capture_output=True)
            subprocess.run(["git", "checkout", "master"], check=True, capture_output=True)
            os.chdir("..")
            progress.stop(success=True)
        except subprocess.CalledProcessError as e:
            progress.stop(success=False)
            raise e
    else:
        print("✅ Репозиторий Supabase уже настроен")

def prepare_shared_directory():
    """Create shared directory with proper permissions for N8N and other services."""
    shared_path = "shared"
    if not os.path.exists(shared_path):
        print(f"Creating {shared_path} directory...")
        os.makedirs(shared_path, mode=0o777)
    else:
        # Ensure proper permissions even if directory exists
        print(f"Ensuring proper permissions on {shared_path}...")
        os.chmod(shared_path, 0o777)

def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)

def cleanup_orphaned_containers():
    """
    Удаление осиротевших контейнеров проекта localai.
    Вызывается перед запуском для предотвращения конфликтов имён.
    """
    # Список контейнеров, которые могут остаться после неудачного запуска
    known_containers = [
        "n8n", "n8n-import", "n8n-runners", "ollama", "ollama-pull-models",
        "whisper", "qdrant", "redis", "caddy", "squid",
        "localai-postgres-1"
    ]

    orphaned = []
    for name in known_containers:
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", name],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Контейнер существует
                orphaned.append(name)
        except:
            pass

    if orphaned:
        print(f"🧹 Очистка осиротевших контейнеров: {', '.join(orphaned)}")
        for name in orphaned:
            try:
                subprocess.run(
                    ["docker", "rm", "-f", name],
                    capture_output=True, timeout=30
                )
            except:
                pass

def stop_existing_containers(profile=None):
    print("Stopping and removing existing containers for the unified project 'localai'...")

    # Сначала пробуем остановить через docker compose
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "down", "--remove-orphans"])

    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        # Если не получилось - продолжаем, cleanup_orphaned_containers справится
        pass

    # Дополнительная очистка осиротевших контейнеров
    cleanup_orphaned_containers()

def start_supabase(environment=None):
    """Start the Supabase services (using its compose file)."""
    print("\n" + "="*65)
    print("🗄️  ЗАПУСК SUPABASE")
    print("="*65)
    print("   ℹ️  Запускается полный стек Supabase (PostgreSQL, Auth, Storage...)")
    print("   ⏱️  Ожидаемое время: 2-3 минуты\n")

    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])

    progress = ProgressIndicator("Запуск Supabase", estimated_time=180)
    progress.start()
    try:
        run_docker_compose_with_retry(cmd)
        progress.stop(success=True)
    except Exception as e:
        progress.stop(success=False)
        raise e

def start_local_ai(profile=None, environment=None):
    """Start the local AI services (using its compose file)."""

    # Check if proxy is enabled
    proxy_enabled = is_proxy_enabled()
    if proxy_enabled:
        print("🌐 Прокси включен — Squid будет запущен")

    # Загружаем базовые образы (postgres, redis, whisper и др.), игнорируя локально-собираемые
    print("\n" + "="*65)
    print("📥 ЗАГРУЗКА DOCKER ОБРАЗОВ")
    print("="*65)
    print("   ℹ️  Это самая долгая часть установки!")
    print("   ℹ️  Загружается ~5-10GB образов (Ollama, PostgreSQL, Redis и др.)")
    print("   ⏱️  Ожидаемое время: 5-15 минут (зависит от интернета)")
    print("   ⚠️  НЕ ПРЕРЫВАЙТЕ ПРОЦЕСС — система работает!\n")

    pull_cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        pull_cmd.extend(["--profile", profile])
    if proxy_enabled:
        pull_cmd.extend(["--profile", "proxy"])
    pull_cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        pull_cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        pull_cmd.extend(["-f", "docker-compose.override.public.yml"])
    pull_cmd.extend(["pull", "--ignore-buildable"])

    progress = ProgressIndicator("Загрузка Docker образов", estimated_time=600)
    progress.start()
    try:
        result = subprocess.run(pull_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            progress.stop(success=False)
            print(f"⚠️  Некоторые образы не загружены, продолжаем...")
        else:
            progress.stop(success=True)
    except subprocess.CalledProcessError as e:
        progress.stop(success=False)
        print(f"⚠️  Некоторые образы не загружены (код: {e.returncode}), продолжаем...")

    # Собираем кастомные образы (n8n-ffmpeg)
    print("\n" + "="*65)
    print("🔧 СБОРКА КАСТОМНЫХ ОБРАЗОВ")
    print("="*65)
    print("   ℹ️  Собираем N8N с поддержкой FFmpeg")
    print("   ⏱️  Ожидаемое время: 2-4 минуты\n")

    # Сначала собираем образы, которые требуют сборки
    build_cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        build_cmd.extend(["--profile", profile])
    if proxy_enabled:
        build_cmd.extend(["--profile", "proxy"])
    build_cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        build_cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        build_cmd.extend(["-f", "docker-compose.override.public.yml"])
    build_cmd.extend(["build"])

    progress = ProgressIndicator("Сборка N8N + FFmpeg", estimated_time=240)
    progress.start()
    try:
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            progress.stop(success=False)
            print(f"⚠️  Предупреждение при сборке, продолжаем...")
        else:
            progress.stop(success=True)
    except subprocess.CalledProcessError as e:
        progress.stop(success=False)
        print(f"⚠️  Предупреждение при сборке образов (код: {e.returncode})")
        print(f"   Продолжаем запуск контейнеров...\n")

    print("\n" + "="*65)
    print("🚀 ЗАПУСК КОНТЕЙНЕРОВ")
    print("="*65)
    print("   ℹ️  Запускаются все сервисы Л.И.С.А.")
    print("   ⏱️  Ожидаемое время: 1-2 минуты\n")

    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    if proxy_enabled:
        cmd.extend(["--profile", "proxy"])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["up", "-d", "--pull", "missing"])

    progress = ProgressIndicator("Запуск контейнеров", estimated_time=120)
    progress.start()
    try:
        run_docker_compose_with_retry(cmd)
        progress.stop(success=True)
    except subprocess.CalledProcessError as e:
        progress.stop(success=False)
        print(f"\n❌ Ошибка запуска LocalAI стека")
        print(f"Проверяем логи проблемных контейнеров...")
        
        # Проверка статуса postgres
        check_cmd = ["docker", "ps", "-a", "--filter", "name=localai-postgres", "--format", "{{.Names}}: {{.Status}}"]
        try:
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            print(f"\nСтатус PostgreSQL:")
            print(result.stdout)
            
            # Показать последние логи
            logs_cmd = ["docker", "logs", "--tail", "50", "localai-postgres-1"]
            result = subprocess.run(logs_cmd, capture_output=True, text=True)
            print(f"\nПоследние 50 строк логов PostgreSQL:")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except:
            pass
        
        raise e

def wait_for_postgres_healthy(timeout=120):
    """Ожидание готовности PostgreSQL контейнера."""
    print("\n" + "="*65)
    print("⏳ ОЖИДАНИЕ ГОТОВНОСТИ POSTGRESQL")
    print("="*65)
    print("   ℹ️  PostgreSQL инициализирует базы данных")
    print(f"   ⏱️  Максимальное время ожидания: {timeout // 60} минуты\n")

    start_time = time.time()
    check_interval = 5  # секунд между проверками

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        remaining = timeout - elapsed

        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", "localai-postgres-1"],
                capture_output=True, text=True, check=False
            )
            status = result.stdout.strip()

            if status == "healthy":
                print(f"\r   ✅ PostgreSQL готов к работе! [{elapsed} сек]                    ")
                return True

            # Показываем статус с оставшимся временем
            mins = remaining // 60
            secs = remaining % 60
            status_display = status if status else "запускается"
            print(f"\r   ⏳ PostgreSQL: {status_display} | Осталось: {mins}:{secs:02d}   ", end="", flush=True)
            time.sleep(check_interval)

        except Exception as e:
            print(f"\r   ⏳ Ожидание PostgreSQL... [{elapsed} сек]   ", end="", flush=True)
            time.sleep(check_interval)

    print(f"\n❌ PostgreSQL не стал healthy за {timeout} секунд")
    return False

def main():
    parser = argparse.ArgumentParser(description='Start the local AI and Supabase services.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Profile to use for Docker Compose (default: cpu)')
    parser.add_argument('--environment', choices=['private', 'public'], default='private',
                      help='Environment to use for Docker Compose (default: private)')
    args = parser.parse_args()

    # Общее время установки для информирования пользователя
    install_start_time = time.time()

    # Проверка WSL
    wsl_detected = is_wsl()

    print("\n" + "="*65)
    print("🚀 УСТАНОВКА Л.И.С.А.")
    print("="*65)
    if wsl_detected:
        print("   ⚠️  WSL обнаружен — увеличены таймауты инициализации")
    print("   ℹ️  Полная установка занимает 10-20 минут")
    print("   ℹ️  Большая часть времени — загрузка Docker образов")
    print("   ⚠️  НЕ ПРЕРЫВАЙТЕ ПРОЦЕСС, даже если кажется, что он завис!")
    print("="*65)

    try:
        # ШАГ 1: Валидация
        print_step(1, 7, "Проверка конфигурации", "несколько секунд")
        if not validate_env_file():
            sys.exit(1)

        # ШАГ 2: Настройка ресурсов
        print_step(2, 7, "Настройка системных ресурсов", "несколько секунд")
        cpu_count, mem_gb = get_system_resources()
        update_env_with_resources(cpu_count, mem_gb)

        prepare_shared_directory()

        # ШАГ 3: Клонирование Supabase
        print_step(3, 7, "Подготовка репозитория Supabase", "2-5 минут (первый запуск)")
        clone_supabase_repo()
        prepare_supabase_env()

        # ШАГ 4: Остановка старых контейнеров
        print_step(4, 7, "Очистка предыдущих контейнеров", "несколько секунд")
        stop_existing_containers(args.profile)

        # ШАГ 5: Запуск Supabase
        print_step(5, 7, "Запуск Supabase (база данных)", "1-2 минуты")
        start_supabase(args.environment)

        # Ожидание инициализации Supabase с обратным отсчётом
        supabase_wait = 60 if wsl_detected else 30
        print_wait_countdown("Инициализация Supabase", supabase_wait)

        # ШАГ 6: Запуск AI сервисов (самый долгий этап)
        print_step(6, 7, "Запуск AI сервисов (Ollama, N8N, Whisper...)", "5-15 минут")
        start_local_ai(args.profile, args.environment)

        # ШАГ 7: Финальная проверка
        postgres_timeout = 300 if wsl_detected else 120
        print_step(7, 7, "Финальная проверка готовности", f"до {postgres_timeout // 60} минут")
        if not wait_for_postgres_healthy(timeout=postgres_timeout):
            print(f"\n❌ Установка прервана: PostgreSQL не запустился")
            if wsl_detected:
                print(f"\n{'='*65}")
                print("💡 Возможные причины на WSL:")
                print("   1. Увеличьте память WSL: создайте C:\\Users\\<user>\\.wslconfig")
                print("      с содержимым:")
                print("      [wsl2]")
                print("      memory=4GB")
                print("   2. Перезапустите WSL: wsl --shutdown")
                print("   3. Попробуйте запустить повторно: python3 start_services.py")
                print(f"{'='*65}")
            sys.exit(1)

        # Успешное завершение — итоговое сообщение выводит CTAPT.py
        total_time = int(time.time() - install_start_time)
        mins = total_time // 60
        secs = total_time % 60
        print(f"\n   ⏱️  Сервисы запущены за {mins} мин {secs} сек\n")

    except DiskSpaceError:
        print_disk_space_recommendations()
        sys.exit(EXIT_CODE_DISK_SPACE)


if __name__ == "__main__":
    main()
