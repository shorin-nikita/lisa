#!/bin/bash
set -euo pipefail

# ============================================================================
#  L.I.S.A. 2.0 — AI Agent Platform
#  One-command installer
#
#  Usage:
#    curl -fsSL https://raw.githubusercontent.com/shorin-nikita/lisa/main/install.sh | bash
#    bash <(curl -fsSL https://raw.githubusercontent.com/shorin-nikita/lisa/main/install.sh)
# ============================================================================

LISA_VERSION="2.0.0"
LISA_REPO="https://github.com/shorin-nikita/lisa.git"
LISA_DIR="${LISA_DIR:-$HOME/lisa}"
LISA_BRANCH="main"

# --- Colors ----------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# --- Helpers ---------------------------------------------------------------

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()    { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }
step()    { echo -e "\n${BOLD}${CYAN}>>> $1${NC}\n"; }

prompt() {
    local var_name="$1" prompt_text="$2" default="${3:-}"
    if [[ -n "$default" ]]; then
        echo -ne "${YELLOW}${prompt_text} ${DIM}[${default}]${NC}: "
    else
        echo -ne "${YELLOW}${prompt_text}${NC}: "
    fi
    local value
    read -r value < /dev/tty
    value="${value:-$default}"
    printf -v "$var_name" '%s' "$value"
}

prompt_secret() {
    local var_name="$1" prompt_text="$2"
    echo -ne "${YELLOW}${prompt_text}${NC}: "
    local value
    read -rs value < /dev/tty
    echo ""
    printf -v "$var_name" '%s' "$value"
}

prompt_yn() {
    local prompt_text="$1" default="${2:-y}"
    local yn
    if [[ "$default" == "y" ]]; then
        echo -ne "${YELLOW}${prompt_text} ${DIM}[Y/n]${NC}: "
    else
        echo -ne "${YELLOW}${prompt_text} ${DIM}[y/N]${NC}: "
    fi
    read -r yn < /dev/tty
    yn="${yn:-$default}"
    [[ "$yn" =~ ^[Yy] ]]
}

generate_secret() {
    local len="${1:-32}"
    local bytes=$(( (len + 1) / 2 ))
    openssl rand -hex "$bytes" 2>/dev/null | head -c "$len" || head -c "$bytes" /dev/urandom | xxd -p | tr -d '\n' | head -c "$len"
}

generate_password() {
    openssl rand -base64 "${1:-24}" 2>/dev/null | tr -d '/+=' | head -c "${1:-24}"
}

# --- Banner ----------------------------------------------------------------

show_banner() {
    echo -e "${CYAN}"
    cat << 'BANNER'

    ██╗     ██╗███████╗ █████╗     ██████╗    ██████╗
    ██║     ██║██╔════╝██╔══██╗    ╚════██╗  ██╔═████╗
    ██║     ██║███████╗███████║     █████╔╝  ██║██╔██║
    ██║     ██║╚════██║██╔══██║    ██╔═══╝   ████╔╝██║
    ███████╗██║███████║██║  ██║    ███████╗  ╚██████╔╝
    ╚══════╝╚═╝╚══════╝╚═╝  ╚═╝    ╚══════╝   ╚═════╝

BANNER
    echo -e "${NC}"
    echo -e "    ${BOLD}AI Agent Platform${NC} ${DIM}v${LISA_VERSION}${NC}"
    echo -e "    ${DIM}OpenClaw + PostgreSQL + Redis${NC}"
    echo ""
}

# --- System Checks ---------------------------------------------------------

check_os() {
    step "Проверка системы"

    # Check git
    if ! command -v git &>/dev/null; then
        warn "Git не найден. Устанавливаю..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq >/dev/null 2>&1
            sudo apt-get install -y -qq git >/dev/null 2>&1
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y git >/dev/null 2>&1
        else
            fail "Git не найден. Установите вручную: https://git-scm.com/"
        fi
        success "Git установлен"
    else
        success "Git: $(git --version | awk '{print $3}')"
    fi

    local os
    os="$(uname -s)"

    case "$os" in
        Linux)
            success "ОС: Linux ($(uname -r))"
            ;;
        Darwin)
            success "ОС: macOS ($(sw_vers -productVersion 2>/dev/null || echo 'unknown'))"
            ;;
        *)
            fail "Неподдерживаемая ОС: $os. Lisa работает на Linux и macOS."
            ;;
    esac

    # Architecture
    local arch
    arch="$(uname -m)"
    case "$arch" in
        x86_64|amd64)  success "Архитектура: x86_64" ;;
        aarch64|arm64) success "Архитектура: ARM64" ;;
        *)             fail "Неподдерживаемая архитектура: $arch" ;;
    esac

    # RAM check
    local ram_mb
    if [[ "$(uname -s)" == "Darwin" ]]; then
        ram_mb=$(( $(sysctl -n hw.memsize) / 1024 / 1024 ))
    else
        ram_mb=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 ))
    fi

    if (( ram_mb < 2048 )); then
        fail "Недостаточно RAM: ${ram_mb}MB. Минимум: 2GB."
    elif (( ram_mb < 4096 )); then
        warn "RAM: ${ram_mb}MB (рекомендуется 4GB+)"
    else
        success "RAM: ${ram_mb}MB"
    fi

    # CPU check
    local cpus
    cpus=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)
    if (( cpus < 2 )); then
        warn "CPU: ${cpus} ядер (рекомендуется 2+)"
    else
        success "CPU: ${cpus} ядер"
    fi
}

check_docker() {
    step "Проверка Docker"

    if ! command -v docker &>/dev/null; then
        warn "Docker не найден. Устанавливаю..."
        install_docker
    else
        success "Docker: $(docker --version | awk '{print $3}' | tr -d ',')"
    fi

    # Check Docker daemon is running
    if ! docker info &>/dev/null; then
        fail "Docker daemon не запущен. Запустите: sudo systemctl start docker"
    fi

    # Check Docker Compose and set COMPOSE_CMD
    if docker compose version &>/dev/null; then
        COMPOSE_CMD="docker compose"
        success "Docker Compose: $(docker compose version --short 2>/dev/null || echo 'v2+')"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
        success "Docker Compose: $(docker-compose --version | awk '{print $4}' | tr -d ',')"
    else
        fail "Docker Compose не найден. Установите: https://docs.docker.com/compose/install/"
    fi
}

install_docker() {
    if [[ "$(uname -s)" == "Linux" ]]; then
        if command -v apt-get &>/dev/null; then
            info "Установка Docker через apt..."
            sudo apt-get update -qq >/dev/null 2>&1
            sudo apt-get install -y -qq docker.io docker-compose-plugin >/dev/null 2>&1
            sudo systemctl enable docker >/dev/null 2>&1
            sudo systemctl start docker >/dev/null 2>&1
            sudo usermod -aG docker "$USER" 2>/dev/null || true
            success "Docker установлен"
        elif command -v dnf &>/dev/null; then
            info "Установка Docker через dnf..."
            sudo dnf install -y docker docker-compose-plugin >/dev/null 2>&1
            sudo systemctl enable docker >/dev/null 2>&1
            sudo systemctl start docker >/dev/null 2>&1
            success "Docker установлен"
        else
            fail "Не удалось установить Docker автоматически. Установите вручную: https://docs.docker.com/engine/install/"
        fi
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        fail "Установите Docker Desktop для macOS: https://docs.docker.com/desktop/install/mac-install/"
    fi
}

check_node() {
    step "Проверка Node.js"

    if ! command -v node &>/dev/null; then
        warn "Node.js не найден. Устанавливаю..."
        install_node
    else
        local node_version
        node_version=$(node -v | tr -d 'v' | cut -d. -f1)
        if (( node_version < 22 )); then
            warn "Node.js v${node_version} устарел. Нужна v22+. Обновляю..."
            install_node
        else
            success "Node.js: $(node -v)"
        fi
    fi

    # Check npm
    if command -v npm &>/dev/null; then
        success "npm: $(npm -v)"
    else
        fail "npm не найден"
    fi
}

install_node() {
    if [[ "$(uname -s)" == "Linux" ]]; then
        info "Установка Node.js 22 через NodeSource..."
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - >/dev/null 2>&1
        sudo apt-get install -y -qq nodejs >/dev/null 2>&1
        success "Node.js $(node -v) установлен"
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            info "Установка Node.js через Homebrew..."
            brew install node@22 >/dev/null 2>&1
            success "Node.js установлен"
        else
            fail "Установите Node.js 22+: https://nodejs.org/"
        fi
    fi
}

# --- Configuration ---------------------------------------------------------

configure() {
    step "Настройка Lisa"

    # LLM Provider
    echo -e "${BOLD}Выберите LLM провайдер:${NC}"
    echo -e "  ${CYAN}1${NC}) Anthropic (Claude) ${DIM}— рекомендуется${NC}"
    echo -e "  ${CYAN}2${NC}) OpenAI (GPT)"
    echo -e "  ${CYAN}3${NC}) OpenRouter (любая модель)"
    echo -e "  ${CYAN}4${NC}) Ollama (локальные модели, без API ключа)"
    echo ""

    local provider_choice
    prompt provider_choice "Провайдер [1-4]" "1"

    LLM_PROVIDER=""
    LLM_API_KEY=""
    LLM_MODEL=""

    case "$provider_choice" in
        1)
            LLM_PROVIDER="anthropic"
            LLM_MODEL="claude-sonnet-4-5-20250929"
            prompt_secret LLM_API_KEY "API ключ Anthropic (sk-ant-...)"
            if [[ -z "$LLM_API_KEY" ]]; then
                fail "API ключ не может быть пустым"
            fi
            success "Провайдер: Anthropic (Claude)"
            ;;
        2)
            LLM_PROVIDER="openai"
            LLM_MODEL="gpt-4o"
            prompt_secret LLM_API_KEY "API ключ OpenAI (sk-...)"
            if [[ -z "$LLM_API_KEY" ]]; then
                fail "API ключ не может быть пустым"
            fi
            success "Провайдер: OpenAI"
            ;;
        3)
            LLM_PROVIDER="openrouter"
            LLM_MODEL="anthropic/claude-sonnet-4-5-20250929"
            prompt_secret LLM_API_KEY "API ключ OpenRouter (sk-or-...)"
            if [[ -z "$LLM_API_KEY" ]]; then
                fail "API ключ не может быть пустым"
            fi
            success "Провайдер: OpenRouter"
            ;;
        4)
            LLM_PROVIDER="ollama"
            LLM_MODEL="llama3"
            success "Провайдер: Ollama (локальный)"
            warn "После установки выполните: lisa module install ollama"
            ;;
        *)
            fail "Неверный выбор: $provider_choice"
            ;;
    esac

    # Proxy
    echo ""
    PROXY_ENABLED=false
    PROXY_IP="" PROXY_PORT="" PROXY_USER="" PROXY_PASS=""

    if prompt_yn "Настроить HTTP прокси для API запросов?" "n"; then
        echo -e "${DIM}Формат: ip:port@login:password${NC}"
        local proxy_string
        prompt proxy_string "Прокси"

        if [[ "$proxy_string" =~ ^([^:]+):([^@]+)@([^:]+):(.+)$ ]]; then
            PROXY_ENABLED=true
            PROXY_IP="${BASH_REMATCH[1]}"
            PROXY_PORT="${BASH_REMATCH[2]}"
            PROXY_USER="${BASH_REMATCH[3]}"
            PROXY_PASS="${BASH_REMATCH[4]}"
            success "Прокси: ${PROXY_IP}:${PROXY_PORT}"
        else
            fail "Неверный формат прокси. Ожидается: ip:port@login:password"
        fi
    fi

    # Domain (optional)
    echo ""
    DOMAIN=""
    LETSENCRYPT_EMAIL=""

    if prompt_yn "Настроить домен с HTTPS? (нужен для публичного доступа)" "n"; then
        prompt DOMAIN "Домен (например: lisa.example.com)"
        prompt LETSENCRYPT_EMAIL "Email для Let's Encrypt"
        success "Домен: ${DOMAIN}"
    fi

    # PostgreSQL port
    echo ""
    prompt POSTGRES_PORT "Порт PostgreSQL" "5433"
    prompt REDIS_PORT "Порт Redis" "6379"
}

# --- Generate Secrets ------------------------------------------------------

generate_secrets() {
    step "Генерация секретов"

    POSTGRES_PASSWORD=$(generate_password 24)
    REDIS_PASSWORD=$(generate_password 24)
    OPENCLAW_SECRET=$(generate_secret 32)

    success "Пароль PostgreSQL сгенерирован"
    success "Пароль Redis сгенерирован"
    success "Секрет OpenClaw сгенерирован"
}

# --- Clone / Update Repo ---------------------------------------------------

setup_project() {
    step "Подготовка проекта"

    if [[ -d "$LISA_DIR" ]]; then
        if [[ -d "$LISA_DIR/.git" ]]; then
            info "Обновляю существующий проект в ${LISA_DIR}..."
            git -C "$LISA_DIR" pull --quiet 2>/dev/null || true
            success "Проект обновлён"
        else
            info "Директория ${LISA_DIR} существует, но не является git-репозиторием"
            info "Использую существующую директорию"
        fi
    else
        info "Клонирую репозиторий в ${LISA_DIR}..."
        git clone --quiet --branch "$LISA_BRANCH" "$LISA_REPO" "$LISA_DIR" 2>/dev/null || {
            # If repo doesn't exist yet, create directory structure
            info "Репозиторий недоступен, создаю локальную структуру..."
            mkdir -p "$LISA_DIR"
        }
        success "Проект готов: ${LISA_DIR}"
    fi
}

# --- Write Configuration ---------------------------------------------------

write_env() {
    step "Создание конфигурации"

    local env_file="${LISA_DIR}/.env"

    # Backup existing .env
    if [[ -f "$env_file" ]]; then
        local backup
        backup="${env_file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$env_file" "$backup"
        info "Бэкап предыдущего .env: ${backup}"
    fi

    # Write .env with proper quoting for special characters in values
    {
        echo "# ============================================================================"
        echo "# L.I.S.A. 2.0 — Configuration"
        echo "# Generated: $(date -Iseconds)"
        echo "# ============================================================================"
        echo ""
        echo "# --- LLM Provider ---"
        echo "LLM_PROVIDER=${LLM_PROVIDER}"
        printf 'LLM_API_KEY="%s"\n' "$LLM_API_KEY"
        echo "LLM_MODEL=${LLM_MODEL}"
        echo ""
        echo "# --- PostgreSQL ---"
        echo "POSTGRES_USER=lisa"
        printf 'POSTGRES_PASSWORD="%s"\n' "$POSTGRES_PASSWORD"
        echo "POSTGRES_DB=lisa"
        echo "POSTGRES_PORT=${POSTGRES_PORT}"
        echo ""
        echo "# --- Redis ---"
        printf 'REDIS_PASSWORD="%s"\n' "$REDIS_PASSWORD"
        echo "REDIS_PORT=${REDIS_PORT}"
        echo ""
        echo "# --- OpenClaw ---"
        printf 'OPENCLAW_SECRET="%s"\n' "$OPENCLAW_SECRET"
        echo "OPENCLAW_PORT=18789"
        echo ""
        echo "# --- Proxy ---"
        echo "PROXY_ENABLED=${PROXY_ENABLED}"
        echo "PROXY_IP=${PROXY_IP}"
        echo "PROXY_PORT=${PROXY_PORT}"
        printf 'PROXY_USER="%s"\n' "$PROXY_USER"
        printf 'PROXY_PASS="%s"\n' "$PROXY_PASS"
        echo ""
        echo "# --- Domain (optional) ---"
        echo "DOMAIN=${DOMAIN}"
        echo "LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL}"
        echo ""
        echo "# --- Resource Limits ---"
        echo "POSTGRES_CPU_LIMIT=2"
        echo "POSTGRES_MEM_LIMIT=2G"
        echo "REDIS_CPU_LIMIT=1"
        echo "REDIS_MEM_LIMIT=512M"
    } > "$env_file"

    chmod 600 "$env_file"
    success "Конфигурация: ${env_file}"
}

write_docker_compose() {
    local compose_file="${LISA_DIR}/docker-compose.yml"

    # Don't overwrite if it already exists from git clone
    if [[ -f "$compose_file" ]]; then
        info "docker-compose.yml уже существует, пропускаю генерацию"
        return
    fi

    cat > "$compose_file" << 'COMPOSE'
# ============================================================================
# L.I.S.A. 2.0 — Docker Compose
# Core: PostgreSQL (pgvector) + Redis + Proxy (optional)
# ============================================================================

services:

  # --- PostgreSQL with pgvector ---
  postgres:
    image: pgvector/pgvector:pg17
    container_name: lisa_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-lisa}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-lisa}
    ports:
      - "${POSTGRES_PORT:-5433}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-lisa}"]
      interval: 5s
      timeout: 5s
      retries: 10
    deploy:
      resources:
        limits:
          cpus: "${POSTGRES_CPU_LIMIT:-2}"
          memory: "${POSTGRES_MEM_LIMIT:-2G}"
    networks:
      - lisa

  # --- Redis ---
  redis:
    image: redis:7-alpine
    container_name: lisa_redis
    restart: unless-stopped
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --save 30 1
      --loglevel warning
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 5s
      retries: 10
    deploy:
      resources:
        limits:
          cpus: "${REDIS_CPU_LIMIT:-1}"
          memory: "${REDIS_MEM_LIMIT:-512M}"
    networks:
      - lisa

  # --- Squid Proxy (optional, for AI API routing) ---
  proxy:
    image: ubuntu/squid:latest
    container_name: lisa_proxy
    restart: unless-stopped
    profiles:
      - proxy
    ports:
      - "3128:3128"
    volumes:
      - ./squid.conf:/etc/squid/squid.conf:ro
    depends_on:
      - postgres
    networks:
      - lisa

  # --- Caddy (optional, for HTTPS with domain) ---
  caddy:
    image: caddy:2-alpine
    container_name: lisa_caddy
    restart: unless-stopped
    profiles:
      - https
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - lisa

volumes:
  postgres_data:
  redis_data:
  caddy_data:
  caddy_config:

networks:
  lisa:
    driver: bridge
COMPOSE

    success "docker-compose.yml создан"
}

write_init_sql() {
    local sql_file="${LISA_DIR}/init-db.sql"

    if [[ -f "$sql_file" ]]; then
        return
    fi

    cat > "$sql_file" << 'SQL'
-- ============================================================================
-- L.I.S.A. 2.0 — Database initialization
-- ============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --- Agents ---
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    template VARCHAR(100),
    config JSONB NOT NULL DEFAULT '{}',
    soul_md TEXT,
    context_md TEXT,
    status VARCHAR(20) DEFAULT 'stopped',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- --- Conversations ---
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL,
    channel_user_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- --- Messages ---
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);

-- --- Memory (daily logs) ---
CREATE TABLE IF NOT EXISTS memory_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, date)
);

-- --- Memory (long-term) ---
CREATE TABLE IF NOT EXISTS memory_longterm (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    importance FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- --- Documents (RAG) ---
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    source VARCHAR(500),
    title VARCHAR(500),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- --- Embeddings (pgvector) ---
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT DEFAULT 0,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Note: vector index created when data is loaded via `lisa knowledge load`
-- CREATE INDEX idx_embeddings_vector ON embeddings
--     USING hnsw (embedding vector_cosine_ops);

-- --- Analytics ---
CREATE TABLE IF NOT EXISTS analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    event VARCHAR(100) NOT NULL,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_agent_event ON analytics(agent_id, event, created_at);
SQL

    success "init-db.sql создан"
}

write_squid_conf() {
    if [[ "$PROXY_ENABLED" != "true" ]]; then
        return
    fi

    local conf_file="${LISA_DIR}/squid.conf"

    cat > "$conf_file" << EOF
# L.I.S.A. 2.0 — Squid Proxy Configuration
# Routes AI API requests through parent proxy

http_port 3128
via on
forwarded_for off

acl localnet src all
acl SSL_ports port 443
acl CONNECT method CONNECT

# AI API domains
acl ai_domains dstdomain .anthropic.com
acl ai_domains dstdomain .claude.ai
acl ai_domains dstdomain .openai.com
acl ai_domains dstdomain .openrouter.ai
acl ai_domains dstdomain .x.ai
acl ai_domains dstdomain .googleapis.com
acl ai_domains dstdomain .mistral.ai
acl ai_domains dstdomain .deepseek.com

http_access allow CONNECT SSL_ports
http_access allow all

# Parent proxy
cache_peer ${PROXY_IP} parent ${PROXY_PORT} 0 login=${PROXY_USER}:${PROXY_PASS} name=upstream
cache_peer_access upstream allow ai_domains
cache_peer_access upstream deny all
never_direct allow ai_domains
always_direct deny ai_domains

dns_nameservers 1.1.1.1 8.8.8.8
EOF

    success "squid.conf создан"
}

write_caddyfile() {
    if [[ -z "$DOMAIN" ]]; then
        return
    fi

    local caddy_file="${LISA_DIR}/Caddyfile"

    cat > "$caddy_file" << EOF
# L.I.S.A. 2.0 — Caddy Configuration
${DOMAIN} {
    reverse_proxy localhost:18789
    tls ${LETSENCRYPT_EMAIL}
}
EOF

    success "Caddyfile создан"
}

# --- Start Services --------------------------------------------------------

start_services() {
    step "Запуск сервисов"

    cd "$LISA_DIR"

    # Build compose command with profiles
    local -a compose_args=()
    if [[ "$PROXY_ENABLED" == "true" ]]; then
        compose_args+=(--profile proxy)
    fi
    if [[ -n "$DOMAIN" ]]; then
        compose_args+=(--profile https)
    fi

    info "Запуск Docker контейнеров..."
    $COMPOSE_CMD ${compose_args[@]+"${compose_args[@]}"} up -d 2>&1 | while IFS= read -r line; do
        echo -e "  ${DIM}${line}${NC}"
    done

    # Wait for PostgreSQL
    info "Ожидание PostgreSQL..."
    local retries=0
    while ! docker exec lisa_postgres pg_isready -U lisa &>/dev/null; do
        retries=$((retries + 1))
        if (( retries > 30 )); then
            fail "PostgreSQL не запустился за 30 секунд"
        fi
        sleep 1
    done
    success "PostgreSQL готов (порт ${POSTGRES_PORT})"

    # Wait for Redis
    info "Ожидание Redis..."
    retries=0
    while ! docker exec lisa_redis redis-cli -a "$REDIS_PASSWORD" ping &>/dev/null 2>&1; do
        retries=$((retries + 1))
        if (( retries > 30 )); then
            fail "Redis не запустился за 30 секунд"
        fi
        sleep 1
    done
    success "Redis готов (порт ${REDIS_PORT})"

    # Proxy health check
    if [[ "$PROXY_ENABLED" == "true" ]]; then
        info "Ожидание прокси..."
        sleep 3
        if docker exec lisa_proxy squid -k check &>/dev/null 2>&1; then
            success "Прокси готов (порт 3128)"
        else
            warn "Прокси запущен, но healthcheck не прошёл. Проверьте настройки."
        fi
    fi
}

# --- Install OpenClaw ------------------------------------------------------

install_openclaw() {
    step "Установка OpenClaw"

    if command -v openclaw &>/dev/null; then
        success "OpenClaw уже установлен: $(openclaw --version 2>/dev/null || echo 'installed')"
        return
    fi

    info "Установка OpenClaw через npm..."

    # Ensure npm global dir exists and is writable
    local npm_prefix
    npm_prefix=$(npm config get prefix 2>/dev/null || echo "/usr/local")

    if [[ ! -w "$npm_prefix/lib" ]] 2>/dev/null; then
        # Set up local npm prefix
        mkdir -p "$HOME/.npm-global"
        npm config set prefix "$HOME/.npm-global"
        export PATH="$HOME/.npm-global/bin:$PATH"

        # Add to shell rc
        local shell_rc="$HOME/.bashrc"
        [[ -f "$HOME/.zshrc" ]] && shell_rc="$HOME/.zshrc"

        if ! grep -q '.npm-global' "$shell_rc" 2>/dev/null; then
            echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> "$shell_rc"
        fi
    fi

    npm install -g openclaw 2>&1 | tail -1 || {
        warn "npm install failed, trying with sudo..."
        sudo npm install -g openclaw 2>&1 | tail -1 || {
            fail "Не удалось установить OpenClaw. Установите вручную: npm install -g openclaw"
        }
    }

    success "OpenClaw установлен"
}

# --- Summary ----------------------------------------------------------------

show_summary() {
    local server_ip
    server_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    [[ -z "$server_ip" ]] && server_ip="localhost"

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║           ${BOLD}L.I.S.A. 2.0 УСТАНОВЛЕНА УСПЕШНО!${NC}${GREEN}               ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${BOLD}Сервисы:${NC}"
    echo -e "  ${GREEN}●${NC} PostgreSQL    ${DIM}localhost:${POSTGRES_PORT}${NC}"
    echo -e "  ${GREEN}●${NC} Redis         ${DIM}localhost:${REDIS_PORT}${NC}"

    if [[ "$PROXY_ENABLED" == "true" ]]; then
        echo -e "  ${GREEN}●${NC} Прокси        ${DIM}localhost:3128${NC}"
    fi

    if [[ -n "$DOMAIN" ]]; then
        echo -e "  ${GREEN}●${NC} HTTPS         ${DIM}https://${DOMAIN}${NC}"
    fi

    echo ""
    echo -e "${BOLD}Подключение к БД:${NC}"
    echo -e "  ${DIM}psql postgresql://lisa:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/lisa${NC}"
    echo ""

    echo -e "${BOLD}Проект:${NC}"
    echo -e "  ${DIM}${LISA_DIR}${NC}"
    echo ""

    echo -e "${BOLD}Следующие шаги:${NC}"
    echo -e "  ${CYAN}1.${NC} cd ${LISA_DIR}"
    echo -e "  ${CYAN}2.${NC} openclaw agent --message 'Привет!'   ${DIM}# проверить агента${NC}"
    echo ""

    echo -e "${BOLD}Полезные команды:${NC}"
    echo -e "  ${DIM}cd ${LISA_DIR} && ${COMPOSE_CMD} ps       ${NC}  # статус"
    echo -e "  ${DIM}cd ${LISA_DIR} && ${COMPOSE_CMD} logs -f   ${NC}  # логи"
    echo -e "  ${DIM}cd ${LISA_DIR} && ${COMPOSE_CMD} down      ${NC}  # остановить"
    echo ""

    if [[ -n "$DOMAIN" ]]; then
        echo -e "${BOLD}URL:${NC} https://${DOMAIN}"
    else
        echo -e "${BOLD}IP:${NC} ${server_ip}"
    fi
    echo ""
}

# --- Main ------------------------------------------------------------------

main() {
    show_banner
    check_os
    check_docker
    check_node
    configure
    generate_secrets
    setup_project
    write_env
    write_docker_compose
    write_init_sql
    write_squid_conf
    write_caddyfile
    start_services
    install_openclaw
    show_summary
}

main "$@"
