#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
#  The Blackwall — Installation Script
#  Автоматическая установка и настройка всех компонентов
#  Целевая ОС: Ubuntu 22.04+ / Debian 12+
# ═══════════════════════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_NAME="The Blackwall"
INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="${INSTALL_DIR}/backend"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
VENV_DIR="${BACKEND_DIR}/venv"
SERVICE_USER="blackwall"
LOG_FILE="/tmp/blackwall-install.log"

info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERR]${NC}  $1"; }
step()    { echo -e "\n${BOLD}══ $1 ══${NC}\n"; }

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

fail() {
    error "$1"
    log "FATAL: $1"
    echo -e "\n${RED}Установка прервана. Логи: ${LOG_FILE}${NC}"
    exit 1
}

# ─── Проверки ─────────────────────────────────────────────────

check_root() {
    if [[ $EUID -ne 0 ]]; then
        fail "Скрипт должен быть запущен с правами root (sudo)"
    fi
}

check_os() {
    if [[ ! -f /etc/os-release ]]; then
        fail "Не найден /etc/os-release — поддерживается только Ubuntu/Debian"
    fi
    . /etc/os-release
    if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
        warn "ОС: $PRETTY_NAME — официально поддерживается Ubuntu 22.04+ / Debian 12+"
    else
        info "ОС: $PRETTY_NAME"
    fi
}

check_arch() {
    local arch
    arch=$(uname -m)
    if [[ "$arch" != "x86_64" && "$arch" != "aarch64" ]]; then
        warn "Неподдерживаемая архитектура: $arch"
    fi
    info "Архитектура: $arch"
}

# ─── Системные пакеты ────────────────────────────────────────

install_system_deps() {
    step "1/8 — Установка системных пакетов"

    info "Обновление списка пакетов..."
    apt-get update -qq >> "$LOG_FILE" 2>&1

    local packages=(
        python3
        python3-pip
        python3-venv
        python3-dev
        build-essential
        git
        curl
        wget
        # Для Rust core
        pkg-config
        libssl-dev
        # Для сетевых возможностей
        iproute2
        iptables
        iputils-ping
        # Для nftables
        nftables
        # Для dummy интерфейсов
        kmod
        # Утилиты
        jq
        lsof
        net-tools
    )

    info "Установка пакетов: ${packages[*]}"
    apt-get install -y -qq "${packages[@]}" >> "$LOG_FILE" 2>&1
    success "Системные пакеты установлены"

    # Загрузка модуля dummy для виртуальных интерфейсов LB
    if ! lsmod | grep -q dummy; then
        modprobe dummy 2>/dev/null || warn "Не удалось загрузить модуль dummy"
    fi
    # Автозагрузка модуля
    if [[ ! -f /etc/modules-load.d/dummy.conf ]]; then
        echo "dummy" > /etc/modules-load.d/dummy.conf
        success "Модуль dummy добавлен в автозагрузку"
    fi
}

# ─── Node.js ──────────────────────────────────────────────────

install_nodejs() {
    step "2/8 — Node.js"

    if command -v node &>/dev/null; then
        local node_ver
        node_ver=$(node --version)
        info "Node.js уже установлен: $node_ver"
        # Проверяем версию >= 18
        local major
        major=$(echo "$node_ver" | sed 's/v//' | cut -d. -f1)
        if (( major >= 18 )); then
            success "Node.js $node_ver — OK"
            return
        fi
        warn "Требуется Node.js 18+, обновляем..."
    fi

    info "Установка Node.js 20.x LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >> "$LOG_FILE" 2>&1
    apt-get install -y -qq nodejs >> "$LOG_FILE" 2>&1
    success "Node.js $(node --version) установлен"
}

# ─── Rust (опционально) ──────────────────────────────────────

install_rust() {
    step "3/8 — Rust (опционально)"

    if command -v cargo &>/dev/null; then
        local rust_ver
        rust_ver=$(rustc --version)
        success "Rust уже установлен: $rust_ver"
        return
    fi

    info "Установка Rust через rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y >> "$LOG_FILE" 2>&1
    source "$HOME/.cargo/env" 2>/dev/null || true

    if command -v cargo &>/dev/null; then
        success "Rust $(rustc --version) установлен"
    else
        warn "Rust не установлен — rust-core будет пропущен"
    fi
}

# ─── Python venv + зависимости ────────────────────────────────

setup_python() {
    step "4/8 — Python виртуальное окружение"

    local python_cmd="python3"

    # Проверка версии Python >= 3.10
    local py_ver
    py_ver=$($python_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
    local py_major py_minor
    py_major=$(echo "$py_ver" | cut -d. -f1)
    py_minor=$(echo "$py_ver" | cut -d. -f2)

    if (( py_major < 3 || py_minor < 10 )); then
        fail "Требуется Python 3.10+, найден: $py_ver"
    fi
    info "Python $py_ver — OK"

    # Создание venv
    if [[ ! -d "$VENV_DIR" ]]; then
        info "Создание виртуального окружения..."
        $python_cmd -m venv "$VENV_DIR"
        success "venv создан: $VENV_DIR"
    else
        info "venv уже существует"
    fi

    # Активация и установка
    source "${VENV_DIR}/bin/activate"

    info "Установка Python зависимостей..."
    pip install --upgrade pip -q >> "$LOG_FILE" 2>&1
    pip install -r "${BACKEND_DIR}/requirements.txt" -q >> "$LOG_FILE" 2>&1
    success "Python зависимости установлены"
}

# ─── Frontend сборка ──────────────────────────────────────────

build_frontend() {
    step "5/8 — Сборка фронтенда"

    if [[ ! -f "${FRONTEND_DIR}/package.json" ]]; then
        warn "Frontend не найден, пропускаем"
        return
    fi

    info "npm install..."
    cd "$FRONTEND_DIR"
    npm install --silent >> "$LOG_FILE" 2>&1

    info "npm run build..."
    npm run build >> "$LOG_FILE" 2>&1

    if [[ -d "${FRONTEND_DIR}/dist" ]]; then
        success "Frontend собран: ${FRONTEND_DIR}/dist"
    else
        warn "Сборка завершилась, но dist/ не найден"
    fi

    cd "$INSTALL_DIR"
}

# ─── Rust core сборка ────────────────────────────────────────

build_rust() {
    step "6/8 — Сборка Rust core"

    local rust_dir="${INSTALL_DIR}/rust-core"
    if [[ ! -f "${rust_dir}/Cargo.toml" ]]; then
        warn "Rust core не найден, пропускаем"
        return
    fi

    if ! command -v cargo &>/dev/null; then
        warn "Cargo не доступен, пропускаем Rust core"
        return
    fi

    info "cargo build --release..."
    cd "$rust_dir"
    cargo build --release >> "$LOG_FILE" 2>&1 && \
        success "Rust core собран" || \
        warn "Ошибка сборки Rust core (не критично)"
    cd "$INSTALL_DIR"
}

# ─── БД + секреты ────────────────────────────────────────────

setup_database_and_secrets() {
    step "7/8 — База данных и секреты"

    # Генерация секретного ключа
    local secret_file="${BACKEND_DIR}/.secret_key"
    if [[ ! -f "$secret_file" ]]; then
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > "$secret_file"
        chmod 600 "$secret_file"
        success "Секретный ключ сгенерирован"
    else
        info "Секретный ключ уже существует"
    fi

    # Инициализация БД
    info "Инициализация базы данных..."
    source "${VENV_DIR}/bin/activate"
    cd "$BACKEND_DIR"
    python3 -c "
import asyncio
from app.database import init_db
asyncio.run(init_db())
print('  DB initialized')
" >> "$LOG_FILE" 2>&1
    success "База данных инициализирована"
    cd "$INSTALL_DIR"
}

# ─── Systemd сервисы ─────────────────────────────────────────

setup_systemd() {
    step "8/8 — Systemd сервисы"

    # Создание системного пользователя
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER" 2>/dev/null || true
        success "Создан пользователь: $SERVICE_USER"
    else
        info "Пользователь $SERVICE_USER уже существует"
    fi

    # Права на директорию проекта
    chown -R "${SERVICE_USER}:${SERVICE_USER}" "$INSTALL_DIR" 2>/dev/null || true

    # Копирование unit-файлов
    local systemd_src="${INSTALL_DIR}/config/systemd"

    if [[ -f "${systemd_src}/blackwall-backend.service" ]]; then
        # Подставляем пути
        sed "s|__INSTALL_DIR__|${INSTALL_DIR}|g; s|__VENV__|${VENV_DIR}|g; s|__USER__|${SERVICE_USER}|g" \
            "${systemd_src}/blackwall-backend.service" > /etc/systemd/system/blackwall-backend.service
        success "Установлен blackwall-backend.service"
    fi

    if [[ -f "${systemd_src}/blackwall-monitor.service" ]]; then
        sed "s|__INSTALL_DIR__|${INSTALL_DIR}|g; s|__VENV__|${VENV_DIR}|g; s|__USER__|${SERVICE_USER}|g" \
            "${systemd_src}/blackwall-monitor.service" > /etc/systemd/system/blackwall-monitor.service
        success "Установлен blackwall-monitor.service"
    fi

    systemctl daemon-reload

    # Включаем и запускаем
    systemctl enable blackwall-backend.service 2>/dev/null || true
    systemctl start blackwall-backend.service 2>/dev/null || true

    if systemctl is-active --quiet blackwall-backend.service; then
        success "blackwall-backend запущен"
    else
        warn "blackwall-backend не удалось запустить (проверьте: systemctl status blackwall-backend)"
    fi
}

# ─── Финальная проверка ───────────────────────────────────────

final_check() {
    echo ""
    step "Проверка установки"

    local ok=0
    local total=0

    check_item() {
        total=$((total + 1))
        if eval "$2" >/dev/null 2>&1; then
            success "$1"
            ok=$((ok + 1))
        else
            warn "$1 — FAILED"
        fi
    }

    check_item "Python 3.10+"            "python3 --version"
    check_item "Node.js"                 "node --version"
    check_item "npm"                     "npm --version"
    check_item "Python venv"             "test -f ${VENV_DIR}/bin/activate"
    check_item "Backend deps"            "${VENV_DIR}/bin/pip show fastapi"
    check_item "Frontend dist"           "test -d ${FRONTEND_DIR}/dist"
    check_item "Секретный ключ"          "test -f ${BACKEND_DIR}/.secret_key"
    check_item "База данных"             "test -f ${BACKEND_DIR}/blackwall.db"
    check_item "systemd unit"            "test -f /etc/systemd/system/blackwall-backend.service"
    check_item "git"                     "git --version"

    echo ""
    if (( ok == total )); then
        echo -e "${GREEN}${BOLD}  ✓ Все проверки пройдены (${ok}/${total})${NC}"
    else
        echo -e "${YELLOW}${BOLD}  ⚠ Пройдено ${ok}/${total} проверок${NC}"
    fi

    echo ""
    echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  ${PROJECT_NAME} установлен!${NC}"
    echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Web UI:${NC}      http://$(hostname -I | awk '{print $1}'):8000"
    echo -e "  ${CYAN}API docs:${NC}    http://$(hostname -I | awk '{print $1}'):8000/docs"
    echo -e "  ${CYAN}Логи:${NC}        journalctl -u blackwall-backend -f"
    echo -e "  ${CYAN}Статус:${NC}      systemctl status blackwall-backend"
    echo -e "  ${CYAN}Перезапуск:${NC}  sudo systemctl restart blackwall-backend"
    echo -e "  ${CYAN}Launcher:${NC}    cd ${INSTALL_DIR} && python3 main.py"
    echo ""
    echo -e "  ${YELLOW}Первый шаг:${NC} откройте Web UI и создайте root пользователя"
    echo ""
    log "Installation completed: ${ok}/${total} checks passed"
}

# ─── Main ─────────────────────────────────────────────────────

main() {
    echo ""
    echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}  ${PROJECT_NAME} — Installer${NC}"
    echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
    echo ""

    echo "" > "$LOG_FILE"
    log "Installation started"
    info "Директория проекта: $INSTALL_DIR"
    info "Лог: $LOG_FILE"

    check_root
    check_os
    check_arch

    install_system_deps
    install_nodejs
    install_rust
    setup_python
    build_frontend
    build_rust
    setup_database_and_secrets
    setup_systemd
    final_check
}

# Запуск
main "$@"
