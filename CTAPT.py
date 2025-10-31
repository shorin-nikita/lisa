#!/usr/bin/env python3
"""
🚀 УСТАНОВЩИК Л.И.С.А.
Локальная Интеллектуальная Система Автоматизации
Версия: 1.618

Автор: Никита Шорин (shorin-nikita)
GitHub: https://github.com/shorin-nikita/lisa
"""

import os
import secrets
import subprocess
import sys
import platform

# Цвета для красивого вывода
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
║                       Л.И.С.А. v1.618                         ║
║         Локальная Интеллектуальная Система Автоматизации      ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.ENDC}""")

def run_command(cmd, check=True, capture_output=False, log_cmd=True):
    try:
        if log_cmd and not capture_output:
            print(f"   🔧 Выполняю: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=capture_output,
                               text=True, check=check, timeout=120)
        if capture_output:
            return result.stdout.strip()
        return True
    except Exception as e:
        if not capture_output:
            print(f"{Colors.FAIL}❌ Ошибка: {e}{Colors.ENDC}")
        return False

def check_system_requirements():
    print(f"\n{Colors.OKBLUE}🔍 Проверка системы...{Colors.ENDC}")
    requirements = [
        ('docker', 'Docker не найден. Установите: sudo apt install docker.io'),
        ('python3', 'Python 3 не найден. Установите: sudo apt install python3'),
        ('git', 'Git не найден. Установите: sudo apt install git')
    ]
    for cmd, error_msg in requirements:
        if not run_command(f"which {cmd}", capture_output=True, check=False, log_cmd=False):
            print(f"{Colors.FAIL}❌ {error_msg}{Colors.ENDC}")
            return False
    
    # Проверка Docker
    if not run_command("docker ps", check=False, capture_output=True, log_cmd=False):
        print(f"{Colors.WARNING}⚠️  Docker требует sudo или добавления пользователя в группу docker{Colors.ENDC}")
        print(f"   Выполните: sudo usermod -aG docker $USER && newgrp docker")
        return False
    
    print(f"{Colors.OKGREEN}✅ Система готова к установке{Colors.ENDC}")
    return True

def detect_gpu_type():
    print(f"\n{Colors.OKBLUE}🎮 Определение GPU конфигурации...{Colors.ENDC}")
    
    # Проверка NVIDIA
    nvidia_check = run_command("nvidia-smi", check=False, capture_output=True, log_cmd=False)
    if nvidia_check and "NVIDIA" in str(nvidia_check):
        print(f"{Colors.OKGREEN}✅ Найден NVIDIA GPU{Colors.ENDC}")
        return "gpu-nvidia"
    
    # Проверка AMD на Linux
    if platform.system() == "Linux":
        amd_check = run_command("lspci | grep -i amd", check=False, capture_output=True, log_cmd=False)
        if amd_check and "amd" in str(amd_check).lower():
            print(f"{Colors.OKGREEN}✅ Найден AMD GPU{Colors.ENDC}")
            return "gpu-amd"
    
    # Проверка Apple Silicon
    if platform.system() == "Darwin":
        mac_check = run_command("system_profiler SPHardwareDataType | grep 'Chip'", 
                               check=False, capture_output=True, log_cmd=False)
        if mac_check and any(x in str(mac_check) for x in ["M1", "M2", "M3"]):
            print(f"{Colors.OKGREEN}✅ Найден Apple Silicon (CPU профиль){Colors.ENDC}")
            return "cpu"
    
    print(f"{Colors.WARNING}⚠️  GPU не найден, будет использован CPU профиль{Colors.ENDC}")
    return "cpu"

def setup_firewall():
    print(f"\n{Colors.OKBLUE}🔒 Настройка firewall...{Colors.ENDC}")
    commands = [
        "sudo ufw --force enable",
        "sudo ufw allow 80/tcp",
        "sudo ufw allow 443/tcp",
        "sudo ufw allow ssh",
        "sudo ufw --force reload"
    ]
    
    for cmd in commands:
        if not run_command(cmd, check=False, log_cmd=False):
            print(f"{Colors.WARNING}⚠️  Firewall не настроен (нужны sudo права){Colors.ENDC}")
            print(f"   Это не критично для локальной установки")
            return False
    
    print(f"{Colors.OKGREEN}✅ Firewall настроен (порты 80, 443 открыты){Colors.ENDC}")
    return True

def validate_domain(domain):
    import re
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?(\.[a-zA-Z]{2,})+$'
    return re.match(pattern, domain) is not None

def validate_email(email):
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False
    
    # Проверка на общие валидные домены
    valid_tlds = ['com', 'net', 'org', 'edu', 'gov', 'ru', 'uk', 'de', 'jp', 
                  'fr', 'au', 'us', 'ca', 'cn', 'br', 'in', 'mx', 'es', 'it',
                  'nl', 'pl', 'se', 'tr', 'ch', 'be', 'at', 'dk', 'fi', 'no',
                  'io', 'co', 'me', 'info', 'biz', 'pro', 'name', 'mobi', 'asia']
    domain = email.split('@')[1]
    tld = domain.split('.')[-1].lower()
    
    if tld not in valid_tlds:
        print(f"{Colors.WARNING}⚠️  Домен '{tld}' выглядит необычно. Используйте настоящий email!{Colors.ENDC}")
        return False
    
    return True

def get_validated_input(prompt, validator, error_msg="Неверный формат", allow_skip=False):
    while True:
        value = input(prompt).strip()
        if not value:
            print(f"{Colors.FAIL}❌ Поле не может быть пустым{Colors.ENDC}")
            continue
        if allow_skip and value == "-":
            return None
        if not validator(value):
            print(f"{Colors.FAIL}❌ {error_msg}{Colors.ENDC}")
            continue
        return value

def get_supabase_key(key_name, min_length=32):
    for _ in range(3):
        value = input(f"{key_name} (минимум {min_length} символов): ").strip()
        if not value:
            print(f"{Colors.FAIL}❌ {key_name} не может быть пустым{Colors.ENDC}")
            continue
        if len(value) < min_length:
            print(f"{Colors.FAIL}❌ {key_name} должен быть минимум {min_length} символов{Colors.ENDC}")
            continue
        return value
    print(f"{Colors.FAIL}❌ Превышено число попыток ввода {key_name}{Colors.ENDC}")
    sys.exit(1)

def collect_user_inputs():
    inputs = {}
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}📋 КОНФИГУРАЦИЯ СИСТЕМЫ:{Colors.ENDC}")
    print(f"{Colors.WARNING}💡 Введите '-' для пропуска необязательного сервиса{Colors.ENDC}\n")
    
    print(f"{Colors.OKBLUE}🔒 Email для SSL сертификатов:{Colors.ENDC}")
    print(f"{Colors.WARNING}⚠️  ВАЖНО: Используйте настоящий email адрес!{Colors.ENDC}")
    print(f"{Colors.WARNING}    Let's Encrypt не принимает фейковые email (например, test@test.test){Colors.ENDC}")
    inputs['email'] = get_validated_input(
        "Email для Let's Encrypt: ", validate_email, "Некорректный email")
    
    print(f"\n{Colors.OKBLUE}🌐 Домен N8N (обязательно):{Colors.ENDC}")
    inputs['n8n_domain'] = get_validated_input(
        "Домен N8N (пример: n8n.site.ru): ", validate_domain, "Некорректный домен")
    
    print(f"\n{Colors.OKBLUE}🌐 Домен Supabase (обязательно):{Colors.ENDC}")
    inputs['supabase_domain'] = get_validated_input(
        "Домен Supabase (пример: db.site.ru): ", validate_domain, "Некорректный домен")
    
    print(f"\n{Colors.OKBLUE}🌐 Опциональные домены (введите '-' для пропуска):{Colors.ENDC}")
    
    inputs['ollama_domain'] = get_validated_input(
        "Домен Ollama (пример: ollama.site.ru) или '-': ", 
        validate_domain, "Некорректный домен", allow_skip=True)
    
    inputs['webui_domain'] = get_validated_input(
        "Домен WebUI (пример: ai.site.ru) или '-': ",
        validate_domain, "Некорректный домен", allow_skip=True)
    
    inputs['flowise_domain'] = get_validated_input(
        "Домен Flowise (пример: agents.site.ru) или '-': ",
        validate_domain, "Некорректный домен", allow_skip=True)
    
    inputs['langfuse_domain'] = get_validated_input(
        "Домен Langfuse (пример: analytics.site.ru) или '-': ",
        validate_domain, "Некорректный домен", allow_skip=True)
    
    inputs['neo4j_domain'] = get_validated_input(
        "Домен Neo4j (пример: graph.site.ru) или '-': ",
        validate_domain, "Некорректный домен", allow_skip=True)
    
    print(f"\n{Colors.OKBLUE}🔐 Ключи Supabase:{Colors.ENDC}")
    print(f"{Colors.WARNING}💡 Генерация: https://supabase.com/docs/guides/self-hosting/docker#generate-api-keys{Colors.ENDC}")
    
    inputs['jwt_secret'] = get_supabase_key("JWT_SECRET", 32)
    inputs['anon_key'] = get_supabase_key("ANON_KEY", 100)
    inputs['service_role_key'] = get_supabase_key("SERVICE_ROLE_KEY", 100)
    
    return inputs

def generate_secret_key(length=32):
    return secrets.token_hex(length)

def generate_password(length=24):
    # Исключаем символы, которые могут вызвать проблемы в URL и конфигах
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_all_secrets():
    return {
        'n8n_encryption_key': generate_secret_key(32),
        'n8n_jwt_secret': generate_secret_key(32),
        'postgres_password': generate_password(32),
        'dashboard_password': generate_password(24),
        'neo4j_password': generate_password(16),
        'clickhouse_password': generate_password(24),
        'minio_password': generate_password(24),
        'langfuse_salt': generate_secret_key(32),
        'nextauth_secret': generate_secret_key(32),
        'encryption_key': generate_secret_key(32),
    }

def create_env_file(user_inputs, generated_secrets):
    try:
        if os.path.exists('.env'):
            backup_name = '.env.backup'
            counter = 1
            while os.path.exists(backup_name):
                backup_name = f'.env.backup.{counter}'
                counter += 1
            os.rename('.env', backup_name)
            print(f"   💾 Создан backup: {backup_name}")
    except Exception as e:
        print(f"{Colors.FAIL}❌ Ошибка создания backup: {e}{Colors.ENDC}")
        return False

    env_content = f"""############
# N8N Configuration
############
N8N_ENCRYPTION_KEY={generated_secrets['n8n_encryption_key']}
N8N_USER_MANAGEMENT_JWT_SECRET={generated_secrets['n8n_jwt_secret']}

############
# Supabase Secrets
############
POSTGRES_PASSWORD={generated_secrets['postgres_password']}
JWT_SECRET={user_inputs['jwt_secret']}
ANON_KEY={user_inputs['anon_key']}
SERVICE_ROLE_KEY={user_inputs['service_role_key']}
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD={generated_secrets['dashboard_password']}
POOLER_TENANT_ID=1000

############
# Neo4j Secrets
############
NEO4J_AUTH=neo4j/{generated_secrets['neo4j_password']}

############
# Langfuse credentials
############
CLICKHOUSE_PASSWORD={generated_secrets['clickhouse_password']}
MINIO_ROOT_PASSWORD={generated_secrets['minio_password']}
LANGFUSE_SALT={generated_secrets['langfuse_salt']}
NEXTAUTH_SECRET={generated_secrets['nextauth_secret']}
ENCRYPTION_KEY={generated_secrets['encryption_key']}

############
# Caddy Config - Production domains
############
N8N_HOSTNAME={user_inputs['n8n_domain']}
SUPABASE_HOSTNAME={user_inputs['supabase_domain']}
LETSENCRYPT_EMAIL={user_inputs['email']}
"""
    
    # Опциональные домены
    if user_inputs.get('ollama_domain'):
        env_content += f"OLLAMA_HOSTNAME={user_inputs['ollama_domain']}\n"
    else:
        env_content += f"# OLLAMA_HOSTNAME=ollama.yourdomain.com\n"
    
    if user_inputs.get('webui_domain'):
        env_content += f"WEBUI_HOSTNAME={user_inputs['webui_domain']}\n"
    else:
        env_content += f"# WEBUI_HOSTNAME=ai.yourdomain.com\n"
    
    if user_inputs.get('flowise_domain'):
        env_content += f"FLOWISE_HOSTNAME={user_inputs['flowise_domain']}\n"
    else:
        env_content += f"# FLOWISE_HOSTNAME=agents.yourdomain.com\n"
    
    if user_inputs.get('langfuse_domain'):
        env_content += f"LANGFUSE_HOSTNAME={user_inputs['langfuse_domain']}\n"
    else:
        env_content += f"# LANGFUSE_HOSTNAME=analytics.yourdomain.com\n"
    
    if user_inputs.get('neo4j_domain'):
        env_content += f"NEO4J_HOSTNAME={user_inputs['neo4j_domain']}\n"
    else:
        env_content += f"# NEO4J_HOSTNAME=graph.yourdomain.com\n"
    
    # Остальные обязательные переменные
    env_content += f"""
############
# Database - PostgreSQL Configuration
############
POSTGRES_VERSION=16
POSTGRES_HOST=db
POSTGRES_DB=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres

############
# Supavisor Configuration
############
POOLER_PROXY_PORT_TRANSACTION=6543
POOLER_DEFAULT_POOL_SIZE=20
POOLER_MAX_CLIENT_CONN=100
SECRET_KEY_BASE={generate_secret_key(32)}
VAULT_ENC_KEY={generate_secret_key(16)}
POOLER_DB_POOL_SIZE=5

############
# API Proxy - Kong Configuration
############
KONG_HTTP_PORT=8000
KONG_HTTPS_PORT=8443

############
# API - PostgREST Configuration
############
PGRST_DB_SCHEMAS=public,storage,graphql_public

############
# Auth - GoTrue Configuration
############
SITE_URL=http://localhost:3000
ADDITIONAL_REDIRECT_URLS=
JWT_EXPIRY=3600
DISABLE_SIGNUP=false
API_EXTERNAL_URL=http://localhost:8000

## Mailer Config
MAILER_URLPATHS_CONFIRMATION=/auth/v1/verify
MAILER_URLPATHS_INVITE=/auth/v1/verify
MAILER_URLPATHS_RECOVERY=/auth/v1/verify
MAILER_URLPATHS_EMAIL_CHANGE=/auth/v1/verify

## Email auth
ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=true
SMTP_ADMIN_EMAIL=admin@example.com
SMTP_HOST=supabase-mail
SMTP_PORT=2500
SMTP_USER=fake_mail_user
SMTP_PASS=fake_mail_password
SMTP_SENDER_NAME=fake_sender
ENABLE_ANONYMOUS_USERS=false

## Phone auth
ENABLE_PHONE_SIGNUP=true
ENABLE_PHONE_AUTOCONFIRM=true

############
# Studio Configuration
############
STUDIO_DEFAULT_ORGANIZATION=Default Organization
STUDIO_DEFAULT_PROJECT=Default Project
STUDIO_PORT=3000
SUPABASE_PUBLIC_URL=http://localhost:8000

############
# Storage
############
IMGPROXY_ENABLE_WEBP_DETECTION=true

############
# Functions
############
FUNCTIONS_VERIFY_JWT=false

############
# Logs - Analytics Configuration
############
LOGFLARE_PUBLIC_ACCESS_TOKEN={generate_secret_key(32)}
LOGFLARE_PRIVATE_ACCESS_TOKEN={generate_secret_key(32)}

############
# Docker Configuration
############
DOCKER_SOCKET_LOCATION=/var/run/docker.sock
"""

    try:
        temp_file = '.env.tmp'
        with open(temp_file, 'w') as f:
            f.write(env_content)
        os.chmod(temp_file, 0o600)
        os.rename(temp_file, '.env')
        print(f"{Colors.OKGREEN}✅ Файл .env успешно создан!{Colors.ENDC}")
        
        # Статистика
        enabled_services = []
        if user_inputs.get('ollama_domain'): enabled_services.append("Ollama")
        if user_inputs.get('webui_domain'): enabled_services.append("WebUI")
        if user_inputs.get('flowise_domain'): enabled_services.append("Flowise")
        if user_inputs.get('langfuse_domain'): enabled_services.append("Langfuse")
        if user_inputs.get('neo4j_domain'): enabled_services.append("Neo4j")
        
        if enabled_services:
            print(f"{Colors.OKGREEN}   Включены опциональные сервисы: {', '.join(enabled_services)}{Colors.ENDC}")
        
        return True
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        print(f"{Colors.FAIL}❌ Ошибка создания .env: {e}{Colors.ENDC}")
        return False

def main():
    print_header()

    # Шаг 1: Проверка системы
    if not check_system_requirements():
        print(f"\n{Colors.FAIL}❌ Исправьте ошибки системы и попробуйте снова{Colors.ENDC}")
        sys.exit(1)

    # Шаг 2: Определение GPU
    gpu_profile = detect_gpu_type()

    # Шаг 3: Firewall (не критично)
    setup_firewall()

    # Шаг 4: Проверка существующей конфигурации
    env_exists = os.path.exists('.env')
    if env_exists:
        print(f"\n{Colors.OKGREEN}✅ Найден существующий файл .env{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Что вы хотите сделать?{Colors.ENDC}")
        print(f"  1. Использовать существующую конфигурацию (рекомендуется)")
        print(f"  2. Создать новую конфигурацию (перезапишет .env)")
        
        while True:
            choice = input(f"\n{Colors.BOLD}Выберите вариант (1/2): {Colors.ENDC}").strip()
            if choice == '1':
                print(f"{Colors.OKGREEN}✅ Используется существующая конфигурация{Colors.ENDC}")
                break
            elif choice == '2':
                print(f"{Colors.WARNING}⚠️  Будет создана новая конфигурация{Colors.ENDC}")
                env_exists = False
                break
            else:
                print(f"{Colors.FAIL}❌ Введите 1 или 2{Colors.ENDC}")
    
    # Шаг 5: Ввод данных (только если нужна новая конфигурация)
    if not env_exists:
        user_inputs = collect_user_inputs()
        generated_secrets = generate_all_secrets()
        
        if not create_env_file(user_inputs, generated_secrets):
            print(f"\n{Colors.FAIL}❌ Не удалось создать .env файл{Colors.ENDC}")
            sys.exit(1)

    input(f"\n{Colors.BOLD}Нажмите Enter для запуска установки...{Colors.ENDC}")

    # Шаг 6: Запуск установки
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*65}")
    print(f"  🚀 Запуск установки Л.И.С.А.")
    print(f"{'='*65}{Colors.ENDC}")
    print(f"\n{Colors.OKCYAN}📦 Что будет установлено:{Colors.ENDC}")
    print(f"  ✅ N8N + FFmpeg - автоматизация и медиа")
    print(f"  ✅ Supabase - база данных")
    print(f"  ✅ Ollama - LLM (модель llama3)")
    print(f"  ✅ Whisper - распознавание речи (порт 8000)")
    print(f"  ✅ Open WebUI - интерфейс")
    print(f"  ✅ Flowise - визуальные агенты")
    print(f"  ✅ Langfuse - мониторинг")
    print(f"  ✅ Qdrant - векторная БД")
    print(f"  ✅ Neo4j - граф БД")
    print(f"  ✅ SearXNG - поиск")
    print(f"  ✅ Caddy - SSL/TLS\n")
    
    install_cmd = f"python3 start_services.py --profile {gpu_profile} --environment public"
    print(f"{Colors.OKBLUE}🚀 Выполняется: {install_cmd}{Colors.ENDC}\n")
    
    try:
        process = subprocess.Popen(install_cmd, shell=True)
        process.wait()
        
        if process.returncode != 0:
            print(f"\n{Colors.FAIL}❌ Ошибка установки (код: {process.returncode}){Colors.ENDC}")
            sys.exit(1)
            
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}{'='*65}")
        print(f"  🎉 Установка успешно завершена!")
        print(f"{'='*65}{Colors.ENDC}")
        print(f"\n{Colors.OKCYAN}📋 Доступ к сервисам:{Colors.ENDC}")
        
        # Читаем N8N_HOSTNAME из .env для корректного отображения
        n8n_url = "http://localhost:8001"
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('N8N_HOSTNAME='):
                        domain = line.split('=')[1].strip()
                        if domain and domain != ':8001':
                            n8n_url = f"http://localhost:8001 или https://{domain}"
                        break
        except:
            pass
        
        print(f"  • N8N: {n8n_url}")
        print(f"  • Open WebUI: http://localhost:8002")
        print(f"  • Supabase: http://localhost:8005")
        print(f"\n{Colors.WARNING}💡 Первый запуск: создайте аккаунт в N8N и Open WebUI{Colors.ENDC}")
        print(f"{Colors.WARNING}💡 Whisper API: http://whisper:8000 (внутри Docker сети){Colors.ENDC}\n")
        
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Ошибка запуска установки: {e}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()

