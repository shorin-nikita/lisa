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

def detect_installation_mode():
    """Определение режима установки (mini/max)"""
    print(f"\n{Colors.OKBLUE}⚙️  Определение режима установки...{Colors.ENDC}")
    
    if not os.path.exists('.env'):
        print(f"{Colors.WARNING}⚠️  Файл .env не найден, используется max{Colors.ENDC}")
        return "max"
    
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('INSTALLATION_MODE='):
                    mode = line.split('=')[1].strip()
                    if mode in ['mini', 'max']:
                        print(f"{Colors.OKGREEN}✅ Режим установки: {mode.upper()}{Colors.ENDC}")
                        return mode
    except:
        pass
    
    print(f"{Colors.OKGREEN}✅ Режим установки: MAX (по умолчанию){Colors.ENDC}")
    return "max"

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

def restart_services(profile, environment, mode):
    """Перезапуск сервисов"""
    print(f"\n{Colors.OKBLUE}🚀 Перезапуск сервисов...{Colors.ENDC}")
    
    cmd = f"python3 start_services.py --profile {profile} --environment {environment} --mode {mode}"
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

def update_env_with_resources(cpu_count, mem_gb):
    """Обновление .env файла с рекомендованными лимитами ресурсов"""
    print(f"\n{Colors.OKBLUE}⚙️  Настройка лимитов ресурсов...{Colors.ENDC}")
    
    if not os.path.exists('.env'):
        print(f"{Colors.WARNING}⚠️  Файл .env не найден, пропускаем{Colors.ENDC}")
        return
    
    # Рассчитываем лимиты
    ollama_cpu = max(2, int(cpu_count * 0.4))
    ollama_mem = max(4, int(mem_gb * 0.4))
    
    postgres_cpu = max(1, int(cpu_count * 0.2))
    postgres_mem = max(2, int(mem_gb * 0.2))
    
    n8n_cpu = max(1, int(cpu_count * 0.15))
    n8n_mem = max(2, int(mem_gb * 0.15))
    
    qdrant_cpu = max(1, int(cpu_count * 0.1))
    qdrant_mem = max(1, int(mem_gb * 0.1))
    
    webui_cpu = max(1, int(cpu_count * 0.1))
    webui_mem = max(1, int(mem_gb * 0.1))
    
    # Читаем .env
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    # Добавляем лимиты если их нет
    resource_vars = [
        f"\n# Resource Limits (автоматически настроено {datetime.now().strftime('%Y-%m-%d %H:%M')})\n",
        f"OLLAMA_CPU_LIMIT={ollama_cpu}\n",
        f"OLLAMA_MEM_LIMIT={ollama_mem}G\n",
        f"OLLAMA_CPU_RESERVE={ollama_cpu // 2}\n",
        f"OLLAMA_MEM_RESERVE={ollama_mem // 2}G\n",
        f"POSTGRES_CPU_LIMIT={postgres_cpu}\n",
        f"POSTGRES_MEM_LIMIT={postgres_mem}G\n",
        f"POSTGRES_CPU_RESERVE={postgres_cpu // 2}\n",
        f"POSTGRES_MEM_RESERVE={postgres_mem // 2}G\n",
        f"N8N_CPU_LIMIT={n8n_cpu}\n",
        f"N8N_MEM_LIMIT={n8n_mem}G\n",
        f"N8N_CPU_RESERVE={n8n_cpu // 2}\n",
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
    
    # Проверяем, есть ли уже эти переменные
    env_content = ''.join(lines)
    if 'OLLAMA_CPU_LIMIT' not in env_content:
        lines.extend(resource_vars)
        
        with open('.env', 'w') as f:
            f.writelines(lines)
        
        print(f"{Colors.OKGREEN}✅ Лимиты ресурсов добавлены в .env:{Colors.ENDC}")
        print(f"   Ollama: {ollama_cpu} CPU, {ollama_mem}G RAM")
        print(f"   PostgreSQL: {postgres_cpu} CPU, {postgres_mem}G RAM")
        print(f"   N8N: {n8n_cpu} CPU, {n8n_mem}G RAM")
        print(f"   Qdrant: {qdrant_cpu} CPU, {qdrant_mem}G RAM")
        print(f"   WebUI: {webui_cpu} CPU, {webui_mem}G RAM")
    else:
        print(f"{Colors.OKGREEN}✅ Лимиты ресурсов уже настроены{Colors.ENDC}")

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
    mode = detect_installation_mode()
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
    
    # Шаг 5: Настройка лимитов ресурсов
    update_env_with_resources(cpu_count, mem_gb)
    
    # Шаг 6: Обновление контейнеров
    if not update_containers():
        print(f"\n{Colors.FAIL}❌ Не удалось обновить контейнеры{Colors.ENDC}")
        sys.exit(1)
    
    # Шаг 7: Перезапуск сервисов
    if not restart_services(gpu_profile, environment, mode):
        print(f"\n{Colors.FAIL}❌ Не удалось перезапустить сервисы{Colors.ENDC}")
        sys.exit(1)
    
    # Шаг 8: Проверка здоровья
    verify_health()
    
    # Финальное сообщение
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}{'='*65}")
    print(f"  🎉 Обновление успешно завершено!")
    print(f"{'='*65}{Colors.ENDC}")
    print(f"\n{Colors.OKCYAN}📋 Система обновлена и запущена{Colors.ENDC}")
    print(f"{Colors.OKCYAN}   Режим: {mode.upper()}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}   Профиль: {gpu_profile}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}   Окружение: {environment}{Colors.ENDC}\n")

if __name__ == "__main__":
    main()

