#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
#  The Blackwall — Installation Script (idempotent / repair)
#  Автоматическая установка и настройка всех компонентов
#  При повторном запуске — проверяет и чинит всё сломанное
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
skip()    { echo -e "${GREEN}[SKIP]${NC} $1 — уже в порядке"; }

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
    step "1/8 — Системные пакеты"

    local packages=(
        python3 python3-pip python3-venv python3-dev
        build-essential git curl wget
        pkg-config libssl-dev
        iproute2 iptables iputils-ping
        nftables kmod jq lsof net-tools
    )

    # Проверяем, какие пакеты отсутствуют
    local missing=()
    for pkg in "${packages[@]}"; do
        if ! dpkg -s "$pkg" &>/dev/null; then
            missing+=("$pkg")
        fi
    done

    if (( ${#missing[@]} == 0 )); then
        skip "Все системные пакеты"
    else
        info "Обновление списка пакетов..."
        apt-get update -qq >> "$LOG_FILE" 2>&1
        info "Установка недостающих пакетов: ${missing[*]}"
        apt-get install -y -qq "${missing[@]}" >> "$LOG_FILE" 2>&1
        success "Системные пакеты установлены"
    fi

    # Загрузка модуля dummy для виртуальных интерфейсов LB
    if ! lsmod | grep -q dummy; then
        modprobe dummy 2>/dev/null || warn "Не удалось загрузить модуль dummy"
    fi
    if [[ ! -f /etc/modules-load.d/dummy.conf ]]; then
        echo "dummy" > /etc/modules-load.d/dummy.conf
        success "Модуль dummy добавлен в автозагрузку"
    fi
}

# ─── Node.js ──────────────────────────────────────────────────

install_nodejs() {
    step "2/8 — Node.js"

    if command -v node &>/dev/null; then
        local node_ver major
        node_ver=$(node --version)
        major=$(echo "$node_ver" | sed 's/v//' | cut -d. -f1)
        if (( major >= 18 )); then
            skip "Node.js $node_ver"
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
        skip "Rust $(rustc --version)"
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
    local py_ver py_major py_minor
    py_ver=$($python_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
    py_major=$(echo "$py_ver" | cut -d. -f1)
    py_minor=$(echo "$py_ver" | cut -d. -f2)

    if (( py_major < 3 || py_minor < 10 )); then
        fail "Требуется Python 3.10+, найден: $py_ver"
    fi
    info "Python $py_ver — OK"

    # Проверяем, работает ли venv
    local venv_ok=false
    if [[ -f "${VENV_DIR}/bin/python" ]] && "${VENV_DIR}/bin/python" -c "import sys" &>/dev/null; then
        venv_ok=true
    fi

    if [[ "$venv_ok" == false ]]; then
        if [[ -d "$VENV_DIR" ]]; then
            warn "venv сломан, пересоздаю..."
            rm -rf "$VENV_DIR"
            log "Removed broken venv"
        fi
        info "Создание виртуального окружения..."
        $python_cmd -m venv "$VENV_DIR"
        success "venv создан: $VENV_DIR"
    else
        info "venv уже существует и работает"
    fi

    # Проверяем, установлены ли зависимости
    source "${VENV_DIR}/bin/activate"

    if "${VENV_DIR}/bin/python" -c "import fastapi, uvicorn, bcrypt" &>/dev/null; then
        skip "Python зависимости"
    else
        info "Установка Python зависимостей..."
        pip install --upgrade pip -q >> "$LOG_FILE" 2>&1
        pip install -r "${BACKEND_DIR}/requirements.txt" -q >> "$LOG_FILE" 2>&1
        success "Python зависимости установлены"
    fi
}

# ─── Frontend сборка ──────────────────────────────────────────

build_frontend() {
    step "5/8 — Сборка фронтенда"

    if [[ ! -f "${FRONTEND_DIR}/package.json" ]]; then
        warn "Frontend не найден, пропускаем"
        return
    fi

    cd "$FRONTEND_DIR"

    # Проверяем node_modules
    if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
        info "npm install..."
        npm install --silent >> "$LOG_FILE" 2>&1
        success "node_modules установлены"
    else
        skip "node_modules"
    fi

    # Проверяем dist
    if [[ -d "${FRONTEND_DIR}/dist" && -f "${FRONTEND_DIR}/dist/index.html" ]]; then
        skip "Frontend dist"
    else
        info "npm run build..."
        npm run build >> "$LOG_FILE" 2>&1
        if [[ -d "${FRONTEND_DIR}/dist" ]]; then
            success "Frontend собран: ${FRONTEND_DIR}/dist"
        else
            warn "Сборка завершилась, но dist/ не найден"
        fi
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

    # Проверяем, есть ли собранный бинарник
    local crate_name
    crate_name=$(grep -m1 '^name' "${rust_dir}/Cargo.toml" | sed 's/.*"\(.*\)".*/\1/' | tr '-' '_')
    if [[ -f "${rust_dir}/target/release/lib${crate_name}.so" ]] || \
       [[ -f "${rust_dir}/target/release/lib${crate_name}.a" ]] || \
       [[ -f "${rust_dir}/target/release/lib${crate_name}.rlib" ]]; then
        skip "Rust core (${crate_name})"
    else
        info "cargo build --release..."
        cd "$rust_dir"
        cargo build --release >> "$LOG_FILE" 2>&1 && \
            success "Rust core собран" || \
            warn "Ошибка сборки Rust core (не критично)"
        cd "$INSTALL_DIR"
    fi
}

# ─── БД + секреты ────────────────────────────────────────────

setup_database_and_secrets() {
    step "7/8 — База данных и секреты"

    # Генерация секретного ключа
    local secret_file="${BACKEND_DIR}/.secret_key"
    if [[ ! -f "$secret_file" ]] || [[ ! -s "$secret_file" ]]; then
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > "$secret_file"
        chmod 600 "$secret_file"
        success "Секретный ключ сгенерирован"
    else
        skip "Секретный ключ"
    fi

    # Инициализация БД (idempotent — init_db создаёт таблицы если их нет)
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

    # Создаём директорию backups (требуется для ReadWritePaths в systemd)
    mkdir -p "${INSTALL_DIR}/backups"

    # Права на директорию проекта
    chown -R "${SERVICE_USER}:${SERVICE_USER}" "$INSTALL_DIR" 2>/dev/null || true

    # Обеспечиваем traverse-доступ (o+x) к родительским каталогам
    # чтобы пользователь blackwall мог добраться до INSTALL_DIR
    local dir="$INSTALL_DIR"
    while [[ "$dir" != "/" ]]; do
        chmod o+x "$dir" 2>/dev/null || true
        dir=$(dirname "$dir")
    done
    success "Права на каталоги настроены"

    # Копирование unit-файлов (всегда перезаписываем — чтобы починить при изменениях)
    local systemd_src="${INSTALL_DIR}/config/systemd"
    local units_changed=false

    for unit_name in blackwall-backend blackwall-monitor; do
        local src="${systemd_src}/${unit_name}.service"
        local dst="/etc/systemd/system/${unit_name}.service"

        if [[ ! -f "$src" ]]; then
            continue
        fi

        local new_content
        new_content=$(sed "s|__INSTALL_DIR__|${INSTALL_DIR}|g; s|__VENV__|${VENV_DIR}|g; s|__USER__|${SERVICE_USER}|g" "$src")

        if [[ -f "$dst" ]] && [[ "$(cat "$dst")" == "$new_content" ]]; then
            info "${unit_name}.service — без изменений"
        else
            echo "$new_content" > "$dst"
            units_changed=true
            success "Установлен/обновлён ${unit_name}.service"
        fi
    done

    if [[ "$units_changed" == true ]]; then
        systemctl daemon-reload
        log "systemd daemon-reload after unit changes"
    fi

    # Включаем сервисы
    systemctl enable blackwall-backend.service 2>/dev/null || true

    # Останавливаем, сбрасываем ошибки, запускаем заново
    systemctl reset-failed blackwall-backend.service 2>/dev/null || true
    systemctl stop blackwall-backend.service 2>/dev/null || true
    systemctl start blackwall-backend.service 2>/dev/null || true

    # Даём сервису время на старт и проверяем
    local retries=0
    while (( retries < 5 )); do
        if systemctl is-active --quiet blackwall-backend.service; then
            success "blackwall-backend запущен"
            return
        fi
        sleep 1
        retries=$((retries + 1))
    done

    warn "blackwall-backend не удалось запустить"
    warn "Диагностика: journalctl -u blackwall-backend -n 30 --no-pager"
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
    check_item "Python venv"             "test -f ${VENV_DIR}/bin/activate && ${VENV_DIR}/bin/python -c 'import sys'"
    check_item "Backend deps"            "${VENV_DIR}/bin/python -c 'import fastapi, uvicorn, bcrypt'"
    check_item "Frontend dist"           "test -d ${FRONTEND_DIR}/dist && test -f ${FRONTEND_DIR}/dist/index.html"
    check_item "Секретный ключ"          "test -s ${BACKEND_DIR}/.secret_key"
    check_item "База данных"             "test -f ${BACKEND_DIR}/blackwall.db"
    check_item "systemd unit"            "test -f /etc/systemd/system/blackwall-backend.service"
    check_item "Сервис активен"          "systemctl is-active --quiet blackwall-backend.service"
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

    check_root

    rm -f "$LOG_FILE"
    log "Installation started"
    info "Директория проекта: $INSTALL_DIR"
    info "Лог: $LOG_FILE"

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
#!/usr/bin/env bash
