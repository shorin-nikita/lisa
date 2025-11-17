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

def get_installation_mode_from_env():
    """Определение режима установки из .env файла."""
    if not os.path.exists('.env'):
        return 'max'  # Fallback для обратной совместимости
    
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('INSTALLATION_MODE='):
                    mode = line.split('=')[1].strip()
                    if mode in ['mini', 'max']:
                        return mode
    except Exception:
        pass
    
    return 'max'  # Fallback по умолчанию

def validate_env_file(mode='max'):
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
    
    # Дополнительные переменные только для MAX режима
    if mode == 'max':
        required_vars.extend([
            'CLICKHOUSE_PASSWORD', 
            'MINIO_ROOT_PASSWORD'
        ])
    
    missing_vars = []
    with open('.env', 'r') as f:
        env_content = f.read()
        for var in required_vars:
            if f'{var}=' not in env_content:
                missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ В .env отсутствуют переменные: {', '.join(missing_vars)}")
        return False
    
    print(f"✅ Файл .env валиден (режим: {mode.upper()})")
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

def start_local_ai_mini(profile=None, environment=None):
    """Start minimal AI services for MINI mode."""
    print("🚀 Запуск системы в режиме MINI...")
    print("\n📦 Будут запущены сервисы:")
    print("  • N8N (с FFmpeg)")
    print("  • Supabase (полный стек)")
    print("  • Caddy")
    print("  • Redis")
    print("  • Qdrant")
    print("  • Whisper")
    print("  • PostgreSQL (для Langfuse/N8N)\n")
    
    # Сначала собираем образ n8n-ffmpeg, чтобы избежать конфликтов при параллельной сборке
    print("🔨 Сборка образа n8n-ffmpeg...")
    build_cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        build_cmd.extend(["--profile", profile])
    build_cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "public":
        build_cmd.extend(["-f", "docker-compose.override.public.yml"])
    build_cmd.extend(["build", "n8n"])
    
    try:
        run_command(build_cmd)
    except subprocess.CalledProcessError as e:
        print("⚠️  Предупреждение: не удалось собрать образ заранее, будет использована автоматическая сборка")
    
    # Список минимальных сервисов
    services = ["n8n-import", "n8n", "caddy", "redis", "qdrant", "whisper", "postgres"]
    
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["up", "-d"] + services)
    
    try:
        run_command(cmd)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка запуска MINI стека")
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

def start_local_ai(profile=None, environment=None):
    """Start the local AI services (using its compose file)."""
    print("🚀 Запуск системы в режиме MAX...")
    print("\n📦 Будут запущены ВСЕ сервисы (может занять время)...\n")
    
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

def generate_searxng_secret_key(mode='max'):
    """Generate a secret key for SearXNG based on the current platform."""
    if mode == 'mini':
        print("Skipping SearXNG configuration (MINI mode)...")
        return
    
    print("Checking SearXNG settings...")
    
    # Define paths for SearXNG settings files
    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")
    
    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return
    
    # Check if settings.yml exists, if not create it from settings-base.yml
    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            shutil.copyfile(settings_base_path, settings_path)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return
    else:
        print(f"SearXNG settings.yml already exists at {settings_path}")
    
    print("Generating SearXNG secret key...")
    
    # Detect the platform and run the appropriate command
    system = platform.system()
    
    try:
        if system == "Windows":
            print("Detected Windows platform, using PowerShell to generate secret key...")
            # PowerShell command to generate a random key and replace in the settings file
            ps_command = [
                "powershell", "-Command",
                "$randomBytes = New-Object byte[] 32; " +
                "(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes); " +
                "$secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ }); " +
                "(Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml"
            ]
            subprocess.run(ps_command, check=True)
            
        elif system == "Darwin":  # macOS
            print("Detected macOS platform, using sed command with empty string parameter...")
            # macOS sed command requires an empty string for the -i parameter
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", "", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)
            
        else:  # Linux and other Unix-like systems
            print("Detected Linux/Unix platform, using standard sed command...")
            # Standard sed command for Linux
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)
            
        print("SearXNG secret key generated successfully.")
        
    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You may need to manually generate the secret key using the commands:")
        print("  - Linux: sed -i \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - macOS: sed -i '' \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - Windows (PowerShell):")
        print("    $randomBytes = New-Object byte[] 32")
        print("    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes)")
        print("    $secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ })")
        print("    (Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml")

def check_and_fix_docker_compose_for_searxng(mode='max'):
    """Check and modify docker-compose.yml for SearXNG first run."""
    if mode == 'mini':
        return  # Skip in MINI mode
    
    docker_compose_path = "docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return
    
    try:
        # Read the docker-compose.yml file
        with open(docker_compose_path, 'r') as file:
            content = file.read()
        
        # Default to first run
        is_first_run = True
        
        # Check if Docker is running and if the SearXNG container exists
        try:
            # Check if the SearXNG container is running
            container_check = subprocess.run(
                ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            searxng_containers = container_check.stdout.strip().split('\n')
            
            # If SearXNG container is running, check inside for uwsgi.ini
            if any(container for container in searxng_containers if container):
                container_name = next(container for container in searxng_containers if container)
                print(f"Found running SearXNG container: {container_name}")
                
                # Check if uwsgi.ini exists inside the container
                container_check = subprocess.run(
                    ["docker", "exec", container_name, "sh", "-c", "[ -f /etc/searxng/uwsgi.ini ] && echo 'found' || echo 'not_found'"],
                    capture_output=True, text=True, check=False
                )
                
                if "found" in container_check.stdout:
                    print("Found uwsgi.ini inside the SearXNG container - not first run")
                    is_first_run = False
                else:
                    print("uwsgi.ini not found inside the SearXNG container - first run")
                    is_first_run = True
            else:
                print("No running SearXNG container found - assuming first run")
        except Exception as e:
            print(f"Error checking Docker container: {e} - assuming first run")
        
        if is_first_run and "cap_drop: - ALL" in content:
            print("First run detected for SearXNG. Temporarily removing 'cap_drop: - ALL' directive...")
            # Temporarily comment out the cap_drop line
            modified_content = content.replace("cap_drop: - ALL", "# cap_drop: - ALL  # Temporarily commented out for first run")
            
            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)
                
            print("Note: After the first run completes successfully, you should re-add 'cap_drop: - ALL' to docker-compose.yml for security reasons.")
        elif not is_first_run and "# cap_drop: - ALL  # Temporarily commented out for first run" in content:
            print("SearXNG has been initialized. Re-enabling 'cap_drop: - ALL' directive for security...")
            # Uncomment the cap_drop line
            modified_content = content.replace("# cap_drop: - ALL  # Temporarily commented out for first run", "cap_drop: - ALL")
            
            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)
    
    except Exception as e:
        print(f"Error checking/modifying docker-compose.yml for SearXNG: {e}")

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
    parser.add_argument('--mode', choices=['mini', 'max'], default='max',
                      help='Installation mode: mini (minimal services) or max (all services) (default: max)')
    args = parser.parse_args()

    # Определяем режим: приоритет аргументу командной строки, затем из .env
    mode = args.mode
    env_mode = get_installation_mode_from_env()
    
    # Если режим из .env отличается от аргумента, предупреждаем
    if env_mode != mode:
        print(f"\n⚠️  Обнаружена разница в режимах:")
        print(f"   .env файл: {env_mode.upper()}")
        print(f"   Аргумент командной строки: {mode.upper()}")
        print(f"   Используется: {mode.upper()}\n")

    # Validate .env file before starting
    if not validate_env_file(mode):
        sys.exit(1)

    prepare_shared_directory()
    clone_supabase_repo()
    prepare_supabase_env()
    
    # Generate SearXNG secret key and check docker-compose.yml (только для MAX)
    generate_searxng_secret_key(mode)
    check_and_fix_docker_compose_for_searxng(mode)
    
    stop_existing_containers(args.profile)
    
    # Start Supabase first
    start_supabase(args.environment)
    
    # Give Supabase some time to initialize
    print("Waiting for Supabase to initialize...")
    time.sleep(30)
    
    # Then start the local AI services (выбор между mini и max)
    if mode == 'mini':
        start_local_ai_mini(args.profile, args.environment)
    else:
        start_local_ai(args.profile, args.environment)
    
    # Ожидание критичных сервисов
    if not wait_for_postgres_healthy():
        print(f"\n❌ Установка прервана: PostgreSQL не запустился")
        sys.exit(1)

if __name__ == "__main__":
    main()
