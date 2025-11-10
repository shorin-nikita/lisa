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
    
    # КРИТИЧЕСКИ ВАЖНО: Сначала добавляем правила ДО включения firewall
    # Это предотвращает блокировку SSH порта на удаленных серверах
    print(f"{Colors.OKBLUE}   Добавление правил firewall...{Colors.ENDC}")
    
    # Порядок ВАЖЕН: SSH добавляем ПЕРВЫМ для надежности
    rules = [
        ("sudo ufw allow 22/tcp", "SSH"),      # КРИТИЧНО ДЛЯ УДАЛЕННОГО ДОСТУПА
        ("sudo ufw allow 80/tcp", "HTTP"),
        ("sudo ufw allow 443/tcp", "HTTPS"),
    ]
    
    # Проверяем, что SSH правило точно добавилось
    ssh_allowed = False
    for rule_cmd, rule_name in rules:
        result = run_command(rule_cmd, check=False, log_cmd=True)
        if "22" in rule_cmd:
            ssh_allowed = result
            if not ssh_allowed:
                print(f"{Colors.FAIL}❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось добавить правило для SSH!{Colors.ENDC}")
                print(f"{Colors.WARNING}⚠️  Firewall НЕ будет включен, чтобы не потерять SSH доступ{Colors.ENDC}")
                return False
            else:
                print(f"{Colors.OKGREEN}   ✅ SSH порт 22 разрешен{Colors.ENDC}")
    
    # Только после успешного добавления всех правил включаем firewall
    print(f"{Colors.OKBLUE}   Включение firewall...{Colors.ENDC}")
    
    if not run_command("sudo ufw --force enable", check=False, log_cmd=True):
        print(f"{Colors.WARNING}⚠️  Firewall не включен (нужны sudo права){Colors.ENDC}")
        print(f"   Это не критично для локальной установки")
        return False
    
    # Перезагружаем firewall
    run_command("sudo ufw --force reload", check=False, log_cmd=False)
    
    # Проверяем статус
    status_result = run_command("sudo ufw status", check=False, log_cmd=False)
    if status_result:
        print(f"{Colors.OKGREEN}✅ Firewall настроен (порты 80, 443, 22 открыты){Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}⚠️  Firewall настроен, но проверка статуса недоступна{Colors.ENDC}")
    
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
    
    # Выбор режима установки
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}⚙️  РЕЖИМ УСТАНОВКИ:{Colors.ENDC}")
    print(f"\n{Colors.OKBLUE}Выберите режим установки системы:{Colors.ENDC}")
    print(f"\n  {Colors.BOLD}1. MINI{Colors.ENDC} — Минимальная конфигурация")
    print(f"     {Colors.OKCYAN}├─{Colors.ENDC} Требования: 2 CPU, 4GB RAM, 10GB диск")
    print(f"     {Colors.OKCYAN}├─{Colors.ENDC} Сервисы: N8N, Supabase, Caddy, Redis, Qdrant, Whisper")
    print(f"     {Colors.OKCYAN}└─{Colors.ENDC} Подходит для: слабых серверов, тестирования")
    print(f"\n  {Colors.BOLD}2. MAX{Colors.ENDC} — Полная конфигурация")
    print(f"     {Colors.OKCYAN}├─{Colors.ENDC} Требования: 4+ CPU, 16GB+ RAM, 30GB диск")
    print(f"     {Colors.OKCYAN}├─{Colors.ENDC} Сервисы: все из MINI + Ollama, WebUI, Flowise, Langfuse, Neo4j, SearXNG")
    print(f"     {Colors.OKCYAN}└─{Colors.ENDC} Подходит для: мощных серверов, продакшена")
    
    while True:
        choice = input(f"\n{Colors.BOLD}Выберите режим (1/2): {Colors.ENDC}").strip()
        if choice == '1':
            inputs['installation_mode'] = 'mini'
            print(f"{Colors.OKGREEN}✅ Выбран режим: MINI{Colors.ENDC}")
            break
        elif choice == '2':
            inputs['installation_mode'] = 'max'
            print(f"{Colors.OKGREEN}✅ Выбран режим: MAX{Colors.ENDC}")
            break
        else:
            print(f"{Colors.FAIL}❌ Введите 1 или 2{Colors.ENDC}")
    
    print(f"\n{Colors.OKBLUE}🌐 Домен N8N (обязательно):{Colors.ENDC}")
    inputs['n8n_domain'] = get_validated_input(
        "Домен N8N (пример: n8n.site.ru): ", validate_domain, "Некорректный домен")
    
    print(f"\n{Colors.OKBLUE}🌐 Домен Supabase (обязательно):{Colors.ENDC}")
    inputs['supabase_domain'] = get_validated_input(
        "Домен Supabase (пример: db.site.ru): ", validate_domain, "Некорректный домен")
    
    # Опциональные домены - только для MAX режима
    if inputs['installation_mode'] == 'max':
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
    else:
        # В MINI режиме эти домены не используются
        inputs['ollama_domain'] = None
        inputs['webui_domain'] = None
        inputs['flowise_domain'] = None
        inputs['langfuse_domain'] = None
        inputs['neo4j_domain'] = None
    
    print(f"\n{Colors.OKBLUE}🔐 Ключи Supabase:{Colors.ENDC}")
    print(f"{Colors.WARNING}💡 Генерация: https://supabase.com/docs/guides/self-hosting/docker#generate-api-keys{Colors.ENDC}")
    
    inputs['jwt_secret'] = get_supabase_key("JWT_SECRET", 32)
    inputs['anon_key'] = get_supabase_key("ANON_KEY", 100)
    inputs['service_role_key'] = get_supabase_key("SERVICE_ROLE_KEY", 100)
    
    return inputs

def generate_secret_key(length=32):
    return secrets.token_hex(length)

def generate_password(length=24):
    # Только буквенно-цифровые символы для совместимости с URL и конфигами
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(secrets.choice(chars) for _ in range(length))

def get_server_ip():
    """Определяет IP-адрес сервера автоматически."""
    try:
        # Попытка 1: Внешний IP через ifconfig.me
        result = subprocess.run(
            ["curl", "-s", "--max-time", "3", "https://ifconfig.me"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            ip = result.stdout.strip()
            # Проверка что это похоже на IP
            if ip.replace('.', '').isdigit() and ip.count('.') == 3:
                print(f"{Colors.OKGREEN}   Определен внешний IP: {ip}{Colors.ENDC}")
                return ip
    except:
        pass
    
    try:
        # Попытка 2: Локальный IP через socket
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"{Colors.OKGREEN}   Определен локальный IP: {ip}{Colors.ENDC}")
        return ip
    except:
        pass
    
    # Fallback: localhost
    print(f"{Colors.WARNING}   Не удалось определить IP, используется localhost{Colors.ENDC}")
    return "localhost"

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
# Installation Mode
############
INSTALLATION_MODE={user_inputs['installation_mode']}

############
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
    # Определяем режим установки для правильного вывода
    if not env_exists:
        installation_mode = user_inputs.get('installation_mode', 'max')
    else:
        installation_mode = None
    
    # Если используется существующий .env, определяем режим из него
    if env_exists or installation_mode is None:
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('INSTALLATION_MODE='):
                        installation_mode = line.split('=')[1].strip()
                        break
            if installation_mode is None:
                installation_mode = 'max'  # Fallback для старых .env
        except:
            installation_mode = 'max'
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*65}")
    print(f"  🚀 Запуск установки Л.И.С.А. (Режим: {installation_mode.upper()})")
    print(f"{'='*65}{Colors.ENDC}")
    print(f"\n{Colors.OKCYAN}📦 Что будет установлено:{Colors.ENDC}")
    
    # Базовые сервисы (всегда устанавливаются)
    print(f"  ✅ N8N + FFmpeg - автоматизация и медиа")
    print(f"  ✅ Supabase - база данных")
    print(f"  ✅ Caddy - SSL/TLS")
    print(f"  ✅ Redis - кеш")
    print(f"  ✅ Qdrant - векторная БД")
    print(f"  ✅ Whisper - распознавание речи")
    
    # Дополнительные сервисы (только в MAX режиме)
    if installation_mode == 'max':
        print(f"  ✅ Ollama - LLM (модель llama3)")
        print(f"  ✅ Open WebUI - интерфейс")
        print(f"  ✅ Flowise - визуальные агенты")
        print(f"  ✅ Langfuse - мониторинг")
        print(f"  ✅ Neo4j - граф БД")
        print(f"  ✅ SearXNG - поиск")
    
    print()
    
    install_cmd = f"python3 start_services.py --profile {gpu_profile} --environment public --mode {installation_mode}"
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
        
        # Определяем IP-адрес сервера
        print(f"\n{Colors.OKBLUE}🔍 Определение IP-адреса...{Colors.ENDC}")
        server_ip = get_server_ip()
        
        print(f"\n{Colors.OKCYAN}📋 Доступ к сервисам:{Colors.ENDC}")
        
        # Читаем домены и режим из .env для корректного отображения
        n8n_domain = None
        supabase_domain = None
        webui_domain = None
        installed_mode = 'max'  # По умолчанию
        
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('INSTALLATION_MODE='):
                        mode_value = line.split('=')[1].strip()
                        if mode_value in ['mini', 'max']:
                            installed_mode = mode_value
                    elif line.startswith('N8N_HOSTNAME='):
                        domain = line.split('=')[1].strip()
                        if domain and not domain.startswith(':'):
                            n8n_domain = domain
                    elif line.startswith('SUPABASE_HOSTNAME='):
                        domain = line.split('=')[1].strip()
                        if domain and not domain.startswith(':'):
                            supabase_domain = domain
                    elif line.startswith('WEBUI_HOSTNAME='):
                        domain = line.split('=')[1].strip()
                        if domain and not domain.startswith(':'):
                            webui_domain = domain
        except:
            pass
        
        # Формируем URLs с IP и доменами
        if n8n_domain:
            n8n_url = f"http://{server_ip}:8001 или https://{n8n_domain}"
        else:
            n8n_url = f"http://{server_ip}:8001"
        
        if supabase_domain:
            supabase_url = f"http://{server_ip}:8005 или https://{supabase_domain}"
        else:
            supabase_url = f"http://{server_ip}:8005"
        
        print(f"  • N8N: {n8n_url}")
        
        # Open WebUI только в MAX режиме
        if installed_mode == 'max':
            if webui_domain:
                webui_url = f"http://{server_ip}:8002 или https://{webui_domain}"
            else:
                webui_url = f"http://{server_ip}:8002"
        print(f"  • Open WebUI: {webui_url}")
        
        print(f"  • Supabase: {supabase_url}")
        print(f"\n{Colors.WARNING}💡 Первый запуск: создайте аккаунт в N8N и активируйте план Community Edition{Colors.ENDC}\n")
        
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Ошибка запуска установки: {e}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()

