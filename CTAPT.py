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

def is_wsl():
    """Detect if running inside WSL (Windows Subsystem for Linux)."""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except (FileNotFoundError, PermissionError):
        return False

def check_system_requirements():
    print(f"\n{Colors.OKBLUE}🔍 Проверка системы...{Colors.ENDC}")
    if is_wsl():
        print(f"{Colors.WARNING}⚠️  Обнаружен WSL (Windows Subsystem for Linux){Colors.ENDC}")
        print(f"{Colors.WARNING}   Таймауты инициализации будут увеличены автоматически{Colors.ENDC}")
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
    if proxy_string.strip() == '-':
        return True

    result = parse_proxy_input(proxy_string)
    if result is None:
        return False

    # Validate IP format (basic check)
    import re
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

        print(f"{Colors.OKGREEN}✅ Конфигурация Squid создана: squid/squid.conf{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"{Colors.FAIL}❌ Ошибка создания конфигурации Squid: {e}{Colors.ENDC}")
        return False

def collect_user_inputs():
    inputs = {}
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}📋 КОНФИГУРАЦИЯ СИСТЕМЫ:{Colors.ENDC}\n")

    print(f"{Colors.OKBLUE}🌐 Домены (введите '-' для пропуска, система будет работать по IP/localhost):{Colors.ENDC}")
    print(f"{Colors.WARNING}💡 Домены опциональны. Если не указаны, доступ будет по IP адресу сервера{Colors.ENDC}\n")
    
    inputs['n8n_domain'] = get_validated_input(
        "Домен N8N (пример: n8n.site.ru) или '-': ",
        validate_domain, "Некорректный домен", allow_skip=True)

    inputs['supabase_domain'] = get_validated_input(
        "Домен Supabase (пример: db.site.ru) или '-': ",
        validate_domain, "Некорректный домен", allow_skip=True)

    # Ollama домен не запрашиваем — доступ только по IP
    inputs['ollama_domain'] = None

    # Email требуется только если есть хотя бы один домен
    has_domains = any([inputs.get('n8n_domain'), inputs.get('supabase_domain')])
    
    if has_domains:
        print(f"\n{Colors.OKBLUE}🔒 Email для SSL сертификатов:{Colors.ENDC}")
        print(f"{Colors.WARNING}⚠️  ВАЖНО: Используйте настоящий email адрес!{Colors.ENDC}")
        print(f"{Colors.WARNING}    Let's Encrypt не принимает фейковые email (например, test@test.test){Colors.ENDC}")
        inputs['email'] = get_validated_input(
            "Email для Let's Encrypt: ", validate_email, "Некорректный email")
    else:
        print(f"\n{Colors.OKGREEN}✅ Домены не указаны, SSL сертификаты не требуются{Colors.ENDC}")
        inputs['email'] = None
    
    print(f"\n{Colors.OKBLUE}🔐 Ключи Supabase:{Colors.ENDC}")
    print(f"{Colors.WARNING}💡 Генерация: https://supabase.com/docs/guides/self-hosting/docker#generate-and-configure-api-keys{Colors.ENDC}")

    inputs['jwt_secret'] = get_supabase_key("JWT_SECRET", 32)
    inputs['anon_key'] = get_supabase_key("ANON_KEY", 100)
    inputs['service_role_key'] = get_supabase_key("SERVICE_ROLE_KEY", 100)

    # Proxy configuration
    print(f"\n{Colors.OKBLUE}🌐 Прокси для API запросов (Anthropic, OpenAI, OpenRouter, Grok, Gemini):{Colors.ENDC}")
    print(f"{Colors.WARNING}💡 Формат: IP:PORT@USER:PASS (например: 45.87.241.81:8000@user:pass){Colors.ENDC}")
    print(f"{Colors.WARNING}   Введите '-' чтобы пропустить{Colors.ENDC}")

    inputs['proxy'] = get_validated_input(
        "Прокси или '-': ",
        validate_proxy_input, "Неверный формат прокси (IP:PORT@USER:PASS)", allow_skip=True)

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
        'n8n_runners_auth_token': generate_secret_key(32),  # Токен для Task Runners (External Mode)
        'postgres_password': generate_password(32),
        'dashboard_password': generate_password(24),
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

# Task Runners (External Mode) - обязательно для n8n 2.0+
# Секретный токен для связи n8n и контейнера runners
N8N_RUNNERS_AUTH_TOKEN={generated_secrets['n8n_runners_auth_token']}

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
# Caddy Config - Production domains
############
"""
    
    # Обработка доменов: если не указан, использовать формат :port для работы по IP
    n8n_hostname = user_inputs.get('n8n_domain') if user_inputs.get('n8n_domain') else ":8001"
    supabase_hostname = user_inputs.get('supabase_domain') if user_inputs.get('supabase_domain') else ":8005"

    env_content += f"N8N_HOSTNAME={n8n_hostname}\n"
    env_content += f"SUPABASE_HOSTNAME={supabase_hostname}\n"
    
    # Email для Let's Encrypt (только если есть домены)
    if user_inputs.get('email'):
        env_content += f"LETSENCRYPT_EMAIL={user_inputs['email']}\n"
    else:
        env_content += f"LETSENCRYPT_EMAIL=internal\n"
    
    # Опциональные домены
    if user_inputs.get('ollama_domain'):
        env_content += f"OLLAMA_HOSTNAME={user_inputs['ollama_domain']}\n"
    else:
        env_content += f"# OLLAMA_HOSTNAME=ollama.yourdomain.com\n"

    # Proxy configuration
    proxy_data = parse_proxy_input(user_inputs.get('proxy', ''))
    if proxy_data:
        env_content += f"""
############
# Proxy Configuration (for API requests)
############
PROXY_ENABLED=true
PROXY_IP={proxy_data['ip']}
PROXY_PORT={proxy_data['port']}
PROXY_USER={proxy_data['user']}
PROXY_PASS={proxy_data['password']}
"""
        # Generate squid.conf from template
        generate_squid_config(proxy_data)
    else:
        env_content += f"""
############
# Proxy Configuration (disabled)
############
# PROXY_ENABLED=false
# PROXY_IP=
# PROXY_PORT=
# PROXY_USER=
# PROXY_PASS=
"""

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
        if user_inputs.get('ollama_domain'):
            print(f"{Colors.OKGREEN}   Включен опциональный домен для Ollama{Colors.ENDC}")
        
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
    
    # Шаг 2.5: Проверка ресурсов системы и предупреждение
    try:
        cpu_count = os.cpu_count() or 2
        if platform.system() == "Linux":
            mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
            mem_gb = mem_bytes / (1024.**3)
        elif platform.system() == "Darwin":
            mem_result = run_command("sysctl -n hw.memsize", capture_output=True, check=False, log_cmd=False)
            mem_gb = int(mem_result) / (1024.**3) if mem_result else 8
        else:
            mem_gb = 8
        
        if cpu_count < 4 or mem_gb < 12:
            print(f"\n{Colors.WARNING}⚠️  Обнаружена минимальная конфигурация ({cpu_count} CPU, {mem_gb:.1f}GB RAM){Colors.ENDC}")
            print(f"{Colors.OKGREEN}   Gemma 3 1B (~1GB) подходит для данной конфигурации.{Colors.ENDC}")
            print(f"{Colors.WARNING}   Для более крупных моделей рекомендуется: 4+ CPU, 12GB+ RAM{Colors.ENDC}")
            print(f"{Colors.OKGREEN}   Установка продолжится с автоматической настройкой ресурсов...{Colors.ENDC}\n")
    except Exception as e:
        # Если не удалось определить ресурсы, просто продолжаем
        pass

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
    print(f"  ✅ Ollama - локальные LLM (Llama3, Mistral)")
    print(f"  ✅ Supabase - база данных с векторным поиском")
    print(f"  ✅ Caddy - автоматический SSL/TLS")
    print(f"  ✅ Redis - кеш и очереди")
    print(f"  ✅ Qdrant - векторное хранилище")
    print(f"  ✅ Whisper - распознавание речи")
    print(f"  ✅ PostgreSQL - база для N8N")
    print()

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
        
        # Определяем IP-адрес сервера
        print(f"\n{Colors.OKBLUE}🔍 Определение IP-адреса...{Colors.ENDC}")
        server_ip = get_server_ip()
        
        print(f"\n{Colors.OKCYAN}📋 Доступ к сервисам:{Colors.ENDC}")
        
        # Читаем домены из .env для корректного отображения
        n8n_domain = None
        supabase_domain = None
        ollama_domain = None

        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('N8N_HOSTNAME='):
                        domain = line.split('=')[1].strip()
                        if domain and not domain.startswith(':'):
                            n8n_domain = domain
                    elif line.startswith('SUPABASE_HOSTNAME='):
                        domain = line.split('=')[1].strip()
                        if domain and not domain.startswith(':'):
                            supabase_domain = domain
                    elif line.startswith('OLLAMA_HOSTNAME='):
                        domain = line.split('=')[1].strip()
                        if domain and not domain.startswith(':'):
                            ollama_domain = domain
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
        print(f"  • Supabase: {supabase_url}")
        
        # Ollama доступен только если домен указан (иначе только внутри Docker сети)
        if ollama_domain:
            ollama_url = f"http://{server_ip}:11434 или https://{ollama_domain}"
            print(f"  • Ollama: {ollama_url}")
        
        print(f"\n{Colors.WARNING}💡 Первый запуск: создайте аккаунт в N8N и активируйте план Community Edition{Colors.ENDC}\n")
        
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Ошибка запуска установки: {e}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()

