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

# Коды ошибок
EXIT_CODE_DISK_SPACE = 14


class DiskSpaceError(Exception):
    """Ошибка нехватки места на диске."""
    pass

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

def validate_env_file():
    """Проверка наличия и корректности .env файла."""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("Запустите сначала: python3 CTAPT.py")
        return False

    # Базовые переменные (обязательны всегда)
    required_vars = [
        'POSTGRES_PASSWORD',
        'N8N_ENCRYPTION_KEY',
        'JWT_SECRET'
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

def update_env_with_resources(cpu_count, mem_gb):
    """Обновление .env файла с рекомендованными лимитами ресурсов"""
    if not os.path.exists('.env'):
        return
    
    # Рассчитываем лимиты (консервативные значения для маломощных серверов)
    # Для систем с 2 CPU / 8GB RAM используем консервативные значения
    ollama_cpu = max(1, min(int(cpu_count * 0.5), cpu_count - 1))  # Не более половины, но минимум 1
    ollama_mem = max(2, int(mem_gb * 0.3))
    
    postgres_cpu = max(1, min(int(cpu_count * 0.3), cpu_count - 1))
    postgres_mem = max(1, int(mem_gb * 0.2))
    
    n8n_cpu = max(0.5, min(int(cpu_count * 0.2), cpu_count - 1))
    n8n_mem = max(1, int(mem_gb * 0.15))
    
    qdrant_cpu = max(0.5, min(int(cpu_count * 0.15), cpu_count - 1))
    qdrant_mem = max(1, int(mem_gb * 0.1))
    
    webui_cpu = max(0.5, min(int(cpu_count * 0.1), cpu_count - 1))
    webui_mem = max(1, int(mem_gb * 0.1))
    
    # Читаем .env
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    # Проверяем, есть ли уже эти переменные
    env_content = ''.join(lines)
    if 'OLLAMA_CPU_LIMIT' not in env_content:
        from datetime import datetime
        resource_vars = [
            f"\n# Resource Limits (автоматически настроено {datetime.now().strftime('%Y-%m-%d %H:%M')})\n",
            f"OLLAMA_CPU_LIMIT={ollama_cpu}\n",
            f"OLLAMA_MEM_LIMIT={ollama_mem}G\n",
            f"OLLAMA_CPU_RESERVE={max(0.5, ollama_cpu / 2)}\n",
            f"OLLAMA_MEM_RESERVE={ollama_mem // 2}G\n",
            f"POSTGRES_CPU_LIMIT={postgres_cpu}\n",
            f"POSTGRES_MEM_LIMIT={postgres_mem}G\n",
            f"POSTGRES_CPU_RESERVE={max(0.5, postgres_cpu / 2)}\n",
            f"POSTGRES_MEM_RESERVE={postgres_mem // 2}G\n",
            f"N8N_CPU_LIMIT={n8n_cpu}\n",
            f"N8N_MEM_LIMIT={n8n_mem}G\n",
            f"N8N_CPU_RESERVE={max(0.25, n8n_cpu / 2)}\n",
            f"N8N_MEM_RESERVE={n8n_mem // 2}G\n",
            f"QDRANT_CPU_LIMIT={qdrant_cpu}\n",
            f"QDRANT_MEM_LIMIT={qdrant_mem}G\n",
            f"QDRANT_CPU_RESERVE=0.5\n",
            f"QDRANT_MEM_RESERVE=1G\n",
            f"WEBUI_CPU_LIMIT={webui_cpu}\n",
            f"WEBUI_MEM_LIMIT={webui_mem}G\n",
            f"WEBUI_CPU_RESERVE=0.5\n",
            f"WEBUI_MEM_RESERVE=1G\n",
        ]
        
        lines.extend(resource_vars)
        
        with open('.env', 'w') as f:
            f.writelines(lines)
        
        print(f"✅ Лимиты ресурсов настроены автоматически:")
        print(f"   Ollama: {ollama_cpu} CPU, {ollama_mem}G RAM")
        print(f"   PostgreSQL: {postgres_cpu} CPU, {postgres_mem}G RAM")
        print(f"   N8N: {n8n_cpu} CPU, {n8n_mem}G RAM")
        print(f"   Qdrant: {qdrant_cpu} CPU, {qdrant_mem}G RAM")
        print(f"   WebUI: {webui_cpu} CPU, {webui_mem}G RAM")

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    supabase_compose_file = os.path.join("supabase", "docker", "docker-compose.yml")
    
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        run_command([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    elif not os.path.exists(supabase_compose_file):
        print("Supabase repository exists but files missing, re-checking out...")
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists and configured.")

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
        "n8n", "n8n-import", "ollama", "ollama-pull-models",
        "whisper", "qdrant", "redis", "caddy", "open-webui",
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
    print("Starting Supabase services...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    run_docker_compose_with_retry(cmd)

def start_local_ai(profile=None, environment=None):
    """Start the local AI services (using its compose file)."""
    print("🚀 Запуск системы...")

    # Загружаем базовые образы (postgres, redis, whisper и др.), игнорируя локально-собираемые
    print("\n📥 Загружаем базовые образы Docker...\n")
    pull_cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        pull_cmd.extend(["--profile", profile])
    pull_cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        pull_cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        pull_cmd.extend(["-f", "docker-compose.override.public.yml"])
    pull_cmd.extend(["pull", "--ignore-buildable"])

    try:
        run_docker_compose_with_retry(pull_cmd)
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Некоторые образы не загружены (код: {e.returncode}), продолжаем...")

    # Собираем кастомные образы (n8n-ffmpeg)
    print("\n📦 Собираем образы (если нужно)...\n")

    # Сначала собираем образы, которые требуют сборки
    build_cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        build_cmd.extend(["--profile", profile])
    build_cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        build_cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        build_cmd.extend(["-f", "docker-compose.override.public.yml"])
    build_cmd.extend(["build"])

    try:
        run_docker_compose_with_retry(build_cmd)
    except subprocess.CalledProcessError as e:
        # Если сборка не удалась, но образ уже существует, продолжаем
        print(f"⚠️  Предупреждение при сборке образов (код: {e.returncode})")
        print(f"   Продолжаем запуск контейнеров...\n")

    print("\n📦 Запускаем сервисы...\n")

    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["up", "-d", "--pull", "never"])

    try:
        run_docker_compose_with_retry(cmd)
    except subprocess.CalledProcessError as e:
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
    print(f"Ожидание готовности PostgreSQL (до {timeout} сек)...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", "localai-postgres-1"],
                capture_output=True, text=True, check=False
            )
            status = result.stdout.strip()
            
            if status == "healthy":
                print(f"✅ PostgreSQL готов к работе")
                return True
            
            print(f"   PostgreSQL статус: {status}, ожидание...")
            time.sleep(5)
        except Exception as e:
            print(f"   Проверка статуса: {e}")
            time.sleep(5)
    
    print(f"❌ PostgreSQL не стал healthy за {timeout} секунд")
    return False

def main():
    parser = argparse.ArgumentParser(description='Start the local AI and Supabase services.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Profile to use for Docker Compose (default: cpu)')
    parser.add_argument('--environment', choices=['private', 'public'], default='private',
                      help='Environment to use for Docker Compose (default: private)')
    args = parser.parse_args()

    try:
        # Validate .env file before starting
        if not validate_env_file():
            sys.exit(1)

        # Настройка лимитов ресурсов перед запуском
        cpu_count, mem_gb = get_system_resources()
        update_env_with_resources(cpu_count, mem_gb)

        prepare_shared_directory()
        clone_supabase_repo()
        prepare_supabase_env()

        stop_existing_containers(args.profile)

        # Start Supabase first
        start_supabase(args.environment)

        # Give Supabase some time to initialize
        print("Waiting for Supabase to initialize...")
        time.sleep(30)

        # Start the local AI services
        start_local_ai(args.profile, args.environment)

        # Ожидание критичных сервисов
        if not wait_for_postgres_healthy():
            print(f"\n❌ Установка прервана: PostgreSQL не запустился")
            sys.exit(1)

    except DiskSpaceError:
        print_disk_space_recommendations()
        sys.exit(EXIT_CODE_DISK_SPACE)


if __name__ == "__main__":
    main()
