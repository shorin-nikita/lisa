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

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

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

def stop_existing_containers(profile=None):
    print("Stopping and removing existing containers for the unified project 'localai'...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "down"])
    run_command(cmd)

def start_supabase(environment=None):
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)

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
        run_command(pull_cmd)
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
        run_command(build_cmd)
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
        run_command(cmd)
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

if __name__ == "__main__":
    main()
