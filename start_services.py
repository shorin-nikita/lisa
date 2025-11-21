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
    print("\n📦 Запускаем сервисы...\n")
    
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["up", "-d"])
    
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
