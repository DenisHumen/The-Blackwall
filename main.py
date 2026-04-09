#!/usr/bin/env python3
"""
The Blackwall — Unified Launcher
=================================
Единая точка входа для запуска всех компонентов проекта.
Работает на любой ОС (macOS, Linux, Windows), но часть функционала
(nftables, systemd, traffic capture) доступна только на Linux.

Использование:
    python main.py                  — интерактивное меню
    python main.py --help           — справка по командам
    python main.py status           — статус компонентов
    python main.py backend          — запустить FastAPI сервер
    python main.py frontend         — запустить фронтенд dev-сервер
    python main.py test             — запустить тесты
    python main.py quickstart       — полная сборка и запуск
    python main.py db-init          — инициализировать БД
    python main.py setup-user       — создать root пользователя
    python main.py check            — проверить зависимости
    python main.py api-docs         — открыть Swagger UI
    python main.py info             — обзор проекта
"""

import asyncio
import importlib
import os
import platform
import shutil
import signal
import subprocess
import sys
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
RUST_DIR = ROOT_DIR / "rust-core"
CONFIG_DIR = ROOT_DIR / "config"
DATABASE_DIR = ROOT_DIR / "database"
DOCS_DIR = ROOT_DIR / "docs"

# ─── Colors ───────────────────────────────────────────────────────────────────

IS_TTY = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if IS_TTY else text

def green(t: str) -> str: return _c("32", t)
def red(t: str) -> str: return _c("31", t)
def yellow(t: str) -> str: return _c("33", t)
def cyan(t: str) -> str: return _c("36", t)
def bold(t: str) -> str: return _c("1", t)
def dim(t: str) -> str: return _c("2", t)

# ─── Platform detection ──────────────────────────────────────────────────────

CURRENT_OS = platform.system()  # "Linux", "Darwin", "Windows"
IS_LINUX = CURRENT_OS == "Linux"
IS_MAC = CURRENT_OS == "Darwin"
IS_WINDOWS = CURRENT_OS == "Windows"

BANNER = r"""
 ╔══════════════════════════════════════════════════════════════╗
 ║                                                              ║
 ║              ████████╗██╗  ██╗███████╗                       ║
 ║              ╚══██╔══╝██║  ██║██╔════╝                       ║
 ║                 ██║   ███████║█████╗                          ║
 ║                 ██║   ██╔══██║██╔══╝                          ║
 ║                 ██║   ██║  ██║███████╗                        ║
 ║                 ╚═╝   ╚═╝  ╚═╝╚══════╝                       ║
 ║        ██████╗ ██╗      █████╗  ██████╗██╗  ██╗              ║
 ║        ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝              ║
 ║        ██████╔╝██║     ███████║██║     █████╔╝               ║
 ║        ██╔══██╗██║     ██╔══██║██║     ██╔═██╗               ║
 ║        ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗              ║
 ║        ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝              ║
 ║        ██╗    ██╗ █████╗ ██╗     ██╗                          ║
 ║        ██║    ██║██╔══██╗██║     ██║                          ║
 ║        ██║ █╗ ██║███████║██║     ██║                          ║
 ║        ██║███╗██║██╔══██║██║     ██║                          ║
 ║        ╚███╔███╔╝██║  ██║███████╗███████╗                     ║
 ║         ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝╚══════╝                     ║
 ║                                                              ║
 ║            Enterprise Firewall Management System             ║
 ║                        v0.1.0                                ║
 ╚══════════════════════════════════════════════════════════════╝
"""

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path | None = None, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a subprocess, printing the command first."""
    print(dim(f"  $ {' '.join(cmd)}"))
    return subprocess.run(cmd, cwd=cwd, check=check, **kwargs)


def _cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _python() -> str:
    """Return current Python executable."""
    return sys.executable


def _pip_install(requirements: Path) -> None:
    """Install Python dependencies."""
    print(yellow(f"\n📦 Установка зависимостей из {requirements.name}..."))
    _run([_python(), "-m", "pip", "install", "-r", str(requirements), "-q"])
    print(green("  ✓ Зависимости установлены"))


def _check_python_deps() -> dict[str, bool]:
    """Check which Python packages are available."""
    packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "sqlalchemy": "sqlalchemy",
        "pydantic": "pydantic",
        "pydantic_settings": "pydantic_settings",
        "jose": "jose",
        "passlib": "passlib",
        "aiosqlite": "aiosqlite",
        "httpx": "httpx",
        "pytest": "pytest",
        "pytest_asyncio": "pytest_asyncio",
        "websockets": "websockets",
    }
    result = {}
    for name, module in packages.items():
        try:
            importlib.import_module(module)
            result[name] = True
        except ImportError:
            result[name] = False
    return result


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_info():
    """Обзор проекта и его компонентов."""
    print(cyan(BANNER))
    print(bold("  The Blackwall — Enterprise Firewall Manager\n"))
    print(f"  {bold('Компоненты:')}")
    print(f"    • {bold('Backend')}   — Python FastAPI + SQLAlchemy async (порт 8000)")
    print(f"    • {bold('Frontend')}  — React + TypeScript + Vite + TailwindCSS (порт 5173)")
    print(f"    • {bold('Rust Core')} — Высокопроизводительное ядро (nftables, GeoIP, traffic)")
    print(f"    • {bold('Database')}  — PostgreSQL + TimescaleDB (или SQLite для разработки)")
    print()
    print(f"  {bold('Реализовано:')}")
    features = [
        ("✓", green, "Аутентификация (JWT + bcrypt + rate limiting)"),
        ("✓", green, "REST API: setup, login, logout, me"),
        ("✓", green, "Модели: User (SQLAlchemy ORM)"),
        ("✓", green, "Тесты: 9 тестов аутентификации (pytest-asyncio)"),
        ("✓", green, "CORS middleware для фронтенда"),
        ("✓", green, "Async SQLite для локальной разработки"),
    ]
    for mark, color, desc in features:
        print(f"    {color(mark)} {desc}")

    print(f"\n  {bold('Запланировано (scaffolding):')}")
    planned = [
        "Firewall Rules CRUD", "Blocked IPs management", "Real-time metrics (WebSocket)",
        "Traffic monitoring", "Analytics & GeoIP", "Audit logging",
        "User management (roles)", "Settings management", "Backup/restore",
        "Rust core bindings", "Docker deployment",
    ]
    for item in planned:
        print(f"    {yellow('○')} {item}")

    print(f"\n  {bold('API эндпоинты (реализованы):')}")
    endpoints = [
        ("POST", "/api/auth/setup", "Создание root пользователя (один раз)"),
        ("POST", "/api/auth/login", "Авторизация"),
        ("POST", "/api/auth/logout", "Выход"),
        ("GET", "/api/auth/me", "Текущий пользователь"),
    ]
    for method, path, desc in endpoints:
        print(f"    {cyan(method):>20s}  {path:<25s}  {dim(desc)}")

    print(f"\n  {bold('Структура проекта:')}")
    dirs = [
        ("backend/", "FastAPI приложение, модели, API, тесты"),
        ("frontend/", "React SPA (Dashboard, Rules, Logs, Blocked IPs...)"),
        ("rust-core/", "Rust ядро: nftables, traffic, autoblock, geoip"),
        ("database/", "SQL скрипты инициализации"),
        ("config/", "Конфигурации nginx, systemd, logrotate"),
        ("docker/", "Docker Compose файлы"),
        ("docs/", "Документация (API, Database, Deployment...)"),
        ("scripts/", "Скрипты установки и обслуживания"),
    ]
    for d, desc in dirs:
        print(f"    {cyan(d):<20s} {desc}")
    print()


def cmd_status():
    """Проверка статуса всех компонентов."""
    print(bold("\n══ Статус системы ══\n"))

    # OS info
    print(f"  {bold('ОС:')} {CURRENT_OS} ({platform.machine()})")
    print(f"  {bold('Python:')} {sys.version.split()[0]} ({_python()})")
    if not IS_LINUX:
        print(yellow(f"  ⚠  Не Linux — функции nftables, systemd, traffic capture недоступны"))
    print()

    # Python dependencies
    print(f"  {bold('Python зависимости:')}")
    deps = _check_python_deps()
    all_ok = True
    for name, ok in deps.items():
        status = green("✓") if ok else red("✗")
        print(f"    {status} {name}")
        if not ok:
            all_ok = False

    if not all_ok:
        print(yellow(f"\n  Совет: python main.py install-deps  — установить недостающие"))

    # Node.js / npm
    print(f"\n  {bold('Node.js / npm:')}")
    if _cmd_exists("node"):
        try:
            node_v = subprocess.check_output(["node", "--version"], text=True).strip()
            print(f"    {green('✓')} Node.js {node_v}")
        except Exception:
            print(f"    {red('✗')} Node.js (ошибка)")
    else:
        print(f"    {red('✗')} Node.js не найден")

    if _cmd_exists("npm"):
        try:
            npm_v = subprocess.check_output(["npm", "--version"], text=True).strip()
            print(f"    {green('✓')} npm {npm_v}")
        except Exception:
            print(f"    {red('✗')} npm (ошибка)")
    else:
        print(f"    {red('✗')} npm не найден")

    # Rust / Cargo
    print(f"\n  {bold('Rust / Cargo:')}")
    if _cmd_exists("cargo"):
        try:
            cargo_v = subprocess.check_output(["cargo", "--version"], text=True).strip()
            print(f"    {green('✓')} {cargo_v}")
        except Exception:
            print(f"    {red('✗')} Cargo (ошибка)")
    else:
        print(f"    {yellow('○')} Cargo не найден (Rust core не будет собран)")

    # Database
    print(f"\n  {bold('База данных:')}")
    db_file = BACKEND_DIR / "blackwall.db"
    if db_file.exists():
        size_kb = db_file.stat().st_size / 1024
        print(f"    {green('✓')} SQLite: {db_file} ({size_kb:.1f} KB)")
    else:
        print(f"    {yellow('○')} SQLite БД не создана (создастся при запуске backend)")

    if _cmd_exists("psql"):
        print(f"    {green('✓')} PostgreSQL CLI доступен")
    else:
        print(f"    {yellow('○')} PostgreSQL CLI не найден (используется SQLite)")

    # Docker
    print(f"\n  {bold('Docker:')}")
    if _cmd_exists("docker"):
        try:
            docker_v = subprocess.check_output(["docker", "--version"], text=True).strip()
            print(f"    {green('✓')} {docker_v}")
        except Exception:
            print(f"    {yellow('○')} Docker (не удалось определить версию)")
    else:
        print(f"    {yellow('○')} Docker не установлен")

    # Frontend deps
    print(f"\n  {bold('Frontend:')}")
    node_modules = FRONTEND_DIR / "node_modules"
    package_json = FRONTEND_DIR / "package.json"
    if package_json.exists() and package_json.stat().st_size > 10:
        print(f"    {green('✓')} package.json настроен")
        if node_modules.exists():
            print(f"    {green('✓')} node_modules установлены")
        else:
            print(f"    {yellow('○')} node_modules не установлены (npm install)")
    else:
        print(f"    {yellow('○')} package.json пустой (фронтенд ещё не настроен)")

    # Linux-specific
    print(f"\n  {bold('Linux-специфичное:')}")
    linux_features = [
        ("nftables", _cmd_exists("nft") if IS_LINUX else False, "Управление firewall"),
        ("systemd", _cmd_exists("systemctl") if IS_LINUX else False, "Управление сервисами"),
        ("tcpdump", _cmd_exists("tcpdump"), "Захват трафика"),
    ]
    for name, available, desc in linux_features:
        if IS_LINUX:
            status = green("✓") if available else red("✗")
        else:
            status = dim("—")
        print(f"    {status} {name:<12s} {dim(desc)}")
    if not IS_LINUX:
        print(dim("      (недоступно на текущей ОС)"))

    print()


def cmd_check():
    """Проверить и отобразить все зависимости."""
    cmd_status()


def cmd_install_deps():
    """Установить Python зависимости."""
    req_file = BACKEND_DIR / "requirements.txt"
    if not req_file.exists():
        print(red("✗ Не найден requirements.txt"))
        return
    _pip_install(req_file)


def cmd_backend(host: str = "0.0.0.0", port: int = 8000):
    """Запустить FastAPI backend сервер."""
    print(bold(f"\n🚀 Запуск The Blackwall Backend (http://{host}:{port})"))
    print(dim(f"   Swagger UI: http://localhost:{port}/docs"))
    print(dim(f"   ReDoc:      http://localhost:{port}/redoc\n"))

    # Check deps first
    deps = _check_python_deps()
    missing = [n for n, ok in deps.items() if not ok and n in ("fastapi", "uvicorn", "sqlalchemy", "pydantic_settings", "aiosqlite")]
    if missing:
        print(red(f"  ✗ Отсутствуют зависимости: {', '.join(missing)}"))
        ans = input("  Установить? [Y/n]: ").strip().lower()
        if ans in ("", "y", "yes", "д", "да"):
            cmd_install_deps()
        else:
            print(red("  Отменено."))
            return

    os.chdir(BACKEND_DIR)
    try:
        _run([_python(), "-m", "uvicorn", "app.main:app", "--reload", "--host", host, "--port", str(port)])
    except KeyboardInterrupt:
        print(yellow("\n  Backend остановлен."))
    finally:
        os.chdir(ROOT_DIR)


def cmd_frontend():
    """Запустить фронтенд dev-сервер (Vite)."""
    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists() or package_json.stat().st_size < 10:
        print(yellow("  ⚠  frontend/package.json пустой — фронтенд ещё не настроен"))
        return

    if not _cmd_exists("npm"):
        print(red("  ✗ npm не найден. Установите Node.js."))
        return

    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print(yellow("  📦 Установка npm зависимостей..."))
        _run(["npm", "install"], cwd=FRONTEND_DIR)

    print(bold("\n🌐 Запуск фронтенда (Vite dev server)...\n"))
    try:
        _run(["npm", "run", "dev"], cwd=FRONTEND_DIR)
    except KeyboardInterrupt:
        print(yellow("\n  Frontend остановлен."))


def cmd_test(verbose: bool = True, test_path: str | None = None):
    """Запустить тесты pytest."""
    print(bold("\n🧪 Запуск тестов...\n"))

    deps = _check_python_deps()
    if not deps.get("pytest"):
        print(red("  ✗ pytest не установлен"))
        ans = input("  Установить зависимости? [Y/n]: ").strip().lower()
        if ans in ("", "y", "yes", "д", "да"):
            cmd_install_deps()
        else:
            return

    cmd = [_python(), "-m", "pytest"]
    if verbose:
        cmd.append("-v")
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")

    os.chdir(BACKEND_DIR)
    env = os.environ.copy()
    # Block broken third-party pytest plugins (e.g. web3/pytest_ethereum)
    # by disabling autoload and explicitly enabling only needed plugins
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    cmd.extend(["-p", "anyio", "-p", "asyncio"])
    try:
        result = _run(cmd, check=False, env=env)
        if result.returncode == 0:
            print(green("\n  ✓ Все тесты пройдены!"))
        else:
            print(red(f"\n  ✗ Тесты завершились с кодом {result.returncode}"))
    finally:
        os.chdir(ROOT_DIR)


def cmd_db_init():
    """Инициализировать базу данных (создать таблицы через SQLAlchemy)."""
    print(bold("\n🗄  Инициализация базы данных...\n"))

    deps = _check_python_deps()
    missing = [n for n, ok in deps.items() if not ok and n in ("sqlalchemy", "aiosqlite")]
    if missing:
        print(red(f"  ✗ Отсутствуют: {', '.join(missing)}"))
        return

    # Add backend to path for imports
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        from app.database import init_db, engine
        from app.models.user import User  # noqa: F401  — ensure model is loaded

        async def _init():
            await init_db()
            print(green("  ✓ Таблицы созданы"))
            # Show info
            from app.config import settings
            print(f"  DB URL: {dim(settings.DB_URL)}")

        asyncio.run(_init())
    except Exception as e:
        print(red(f"  ✗ Ошибка: {e}"))
    finally:
        if str(BACKEND_DIR) in sys.path:
            sys.path.remove(str(BACKEND_DIR))


def cmd_setup_user():
    """Создать root пользователя через API (backend должен быть запущен) или напрямую."""
    print(bold("\n👤 Создание root пользователя\n"))

    deps = _check_python_deps()
    missing = [n for n, ok in deps.items() if not ok and n in ("sqlalchemy", "aiosqlite", "passlib")]
    if missing:
        print(red(f"  ✗ Отсутствуют: {', '.join(missing)}"))
        return

    username = input("  Username [root]: ").strip() or "root"
    import getpass
    password = getpass.getpass("  Password: ")
    if not password:
        print(red("  ✗ Пароль не может быть пустым"))
        return

    sys.path.insert(0, str(BACKEND_DIR))
    try:
        from app.database import engine, SessionLocal, init_db
        from app.models.user import User
        from app.core.auth import hash_password
        from sqlalchemy import select, func as sa_func

        async def _create():
            await init_db()
            async with SessionLocal() as session:
                count = await session.scalar(select(sa_func.count()).select_from(User))
                if count and count > 0:
                    print(yellow(f"  ⚠  В БД уже существуют пользователи ({count})"))
                    ans = input("  Всё равно создать? [y/N]: ").strip().lower()
                    if ans not in ("y", "yes", "д", "да"):
                        print(dim("  Отменено."))
                        return

                user = User(
                    username=username,
                    password_hash=hash_password(password),
                    role="root",
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                print(green(f"  ✓ Пользователь '{user.username}' создан (role={user.role}, id={user.id})"))

        asyncio.run(_create())
    except Exception as e:
        print(red(f"  ✗ Ошибка: {e}"))
    finally:
        if str(BACKEND_DIR) in sys.path:
            sys.path.remove(str(BACKEND_DIR))


def cmd_api_docs():
    """Открыть Swagger UI в браузере."""
    import webbrowser
    url = "http://localhost:8000/docs"
    print(f"  Открываю {cyan(url)} ...")
    webbrowser.open(url)


def cmd_build_rust():
    """Собрать Rust core."""
    if not _cmd_exists("cargo"):
        print(red("  ✗ Cargo не найден. Установите Rust: https://rustup.rs"))
        return
    print(bold("\n🦀 Сборка Rust core...\n"))
    try:
        _run(["cargo", "build", "--release"], cwd=RUST_DIR)
        print(green("\n  ✓ Rust core собран"))
    except subprocess.CalledProcessError:
        print(red("\n  ✗ Ошибка сборки Rust"))


def cmd_build_frontend():
    """Собрать фронтенд для продакшена."""
    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists() or package_json.stat().st_size < 10:
        print(yellow("  ⚠  frontend/package.json пустой — фронтенд ещё не настроен"))
        return
    if not _cmd_exists("npm"):
        print(red("  ✗ npm не найден."))
        return
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        _run(["npm", "install"], cwd=FRONTEND_DIR)
    print(bold("\n📦 Сборка фронтенда...\n"))
    try:
        _run(["npm", "run", "build"], cwd=FRONTEND_DIR)
        print(green("\n  ✓ Фронтенд собран"))
    except subprocess.CalledProcessError:
        print(red("\n  ✗ Ошибка сборки"))


def cmd_fullstack():
    """Запустить backend + frontend параллельно."""
    print(bold("\n🚀 Полный запуск (backend + frontend)...\n"))

    processes: list[subprocess.Popen] = []

    def _cleanup(*_):
        for p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        print(yellow("\n  Всё остановлено."))
        sys.exit(0)

    signal.signal(signal.SIGINT, _cleanup)
    signal.signal(signal.SIGTERM, _cleanup)

    # Backend
    print(green("  → Backend (port 8000)"))
    backend_proc = subprocess.Popen(
        [_python(), "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        cwd=BACKEND_DIR,
    )
    processes.append(backend_proc)

    # Frontend
    package_json = FRONTEND_DIR / "package.json"
    if package_json.exists() and package_json.stat().st_size > 10 and _cmd_exists("npm"):
        print(green("  → Frontend (port 5173)"))
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=FRONTEND_DIR,
        )
        processes.append(frontend_proc)
    else:
        print(yellow("  ⚠  Фронтенд пропущен (не настроен или npm не найден)"))

    print(dim(f"\n  Backend:  http://localhost:8000"))
    print(dim(f"  Swagger:  http://localhost:8000/docs"))
    print(dim(f"  Frontend: http://localhost:5173"))
    print(dim(f"\n  Ctrl+C для остановки\n"))

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        _cleanup()


def cmd_quickstart():
    """Полная сборка и запуск проекта в один шаг."""
    print(cyan(BANNER))
    print(bold("  🔧 Quick Start — полная сборка и запуск проекта\n"))

    steps = [
        ("1/7", "Проверка системы",            "check"),
        ("2/7", "Установка Python зависимостей", "pip"),
        ("3/7", "Установка npm зависимостей",    "npm"),
        ("4/7", "Сборка Rust core",              "rust"),
        ("5/7", "Инициализация базы данных",     "db"),
        ("6/7", "Запуск тестов",                 "test"),
        ("7/7", "Запуск проекта",                "run"),
    ]
    for num, label, _ in steps:
        print(f"    {dim(num)}  {label}")
    print()

    errors: list[str] = []

    # ── Step 1: System check ──
    print(bold(f"  ── [1/7] Проверка системы ──\n"))
    print(f"  ОС: {CURRENT_OS} ({platform.machine()})")
    print(f"  Python: {sys.version.split()[0]}")
    if not IS_LINUX:
        print(yellow("  ⚠  Не Linux — nftables/systemd недоступны (это нормально для разработки)"))
    print()

    # ── Step 2: Python deps ──
    print(bold(f"  ── [2/7] Python зависимости ──\n"))
    req_file = BACKEND_DIR / "requirements.txt"
    if req_file.exists():
        try:
            _run([_python(), "-m", "pip", "install", "-r", str(req_file), "-q"])
            print(green("  ✓ Python зависимости установлены\n"))
        except subprocess.CalledProcessError:
            msg = "Ошибка установки Python зависимостей"
            print(red(f"  ✗ {msg}\n"))
            errors.append(msg)
    else:
        print(yellow("  ⚠  requirements.txt не найден, пропускаю\n"))

    # ── Step 3: npm deps ──
    print(bold(f"  ── [3/7] npm зависимости ──\n"))
    package_json = FRONTEND_DIR / "package.json"
    if package_json.exists() and package_json.stat().st_size > 10 and _cmd_exists("npm"):
        node_modules = FRONTEND_DIR / "node_modules"
        if not node_modules.exists():
            try:
                _run(["npm", "install"], cwd=FRONTEND_DIR)
                print(green("  ✓ npm зависимости установлены\n"))
            except subprocess.CalledProcessError:
                msg = "Ошибка установки npm зависимостей"
                print(red(f"  ✗ {msg}\n"))
                errors.append(msg)
        else:
            print(green("  ✓ npm зависимости уже установлены\n"))
    else:
        print(yellow("  ⚠  Фронтенд не настроен или npm не найден, пропускаю\n"))

    # ── Step 4: Rust build ──
    print(bold(f"  ── [4/7] Сборка Rust core ──\n"))
    if _cmd_exists("cargo"):
        try:
            _run(["cargo", "build", "--release"], cwd=RUST_DIR)
            print(green("  ✓ Rust core собран\n"))
        except subprocess.CalledProcessError:
            msg = "Ошибка сборки Rust core"
            print(red(f"  ✗ {msg}\n"))
            errors.append(msg)
    else:
        print(yellow("  ⚠  Cargo не найден, пропускаю сборку Rust\n"))

    # ── Step 5: Database init ──
    print(bold(f"  ── [5/7] Инициализация базы данных ──\n"))
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        from app.database import init_db as _init_db
        from app.models.user import User  # noqa: F401

        asyncio.run(_init_db())
        print(green("  ✓ База данных инициализирована\n"))
    except Exception as e:
        msg = f"Ошибка инициализации БД: {e}"
        print(red(f"  ✗ {msg}\n"))
        errors.append(msg)
    finally:
        if str(BACKEND_DIR) in sys.path:
            sys.path.remove(str(BACKEND_DIR))

    # ── Step 6: Tests ──
    print(bold(f"  ── [6/7] Запуск тестов ──\n"))
    test_cmd = [_python(), "-m", "pytest", "-v", "tests/", "-p", "anyio", "-p", "asyncio"]
    test_env = os.environ.copy()
    test_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    try:
        result = _run(test_cmd, cwd=BACKEND_DIR, check=False, env=test_env)
        if result.returncode == 0:
            print(green("  ✓ Все тесты пройдены\n"))
        else:
            msg = f"Тесты завершились с кодом {result.returncode}"
            print(yellow(f"  ⚠  {msg} (не блокирует запуск)\n"))
            errors.append(msg)
    except Exception as e:
        msg = f"Ошибка запуска тестов: {e}"
        print(red(f"  ✗ {msg}\n"))
        errors.append(msg)

    # ── Summary ──
    print(bold("  ══ Итог сборки ══\n"))
    if errors:
        print(yellow(f"  Предупреждения ({len(errors)}):" ))
        for err in errors:
            print(f"    {yellow('⚠')} {err}")
        print()
    else:
        print(green("  ✓ Всё собрано без ошибок!\n"))

    # ── Step 7: Launch ──
    print(bold(f"  ── [7/7] Запуск проекта ──\n"))
    cmd_fullstack()


def cmd_alembic(args: list[str]):
    """Запустить Alembic миграцию."""
    print(bold("\n🔄 Alembic миграции...\n"))
    alembic_dir = BACKEND_DIR / "alembic"
    if not alembic_dir.exists():
        print(red("  ✗ Директория alembic не найдена"))
        return
    cmd = [_python(), "-m", "alembic"] + args
    os.chdir(BACKEND_DIR)
    try:
        _run(cmd)
    except subprocess.CalledProcessError as e:
        print(red(f"  ✗ Alembic ошибка: {e}"))
    finally:
        os.chdir(ROOT_DIR)


def cmd_update():
    """Проверить и применить обновления через GitHub."""
    print(bold("\n🔄 Обновление системы...\n"))

    if not _cmd_exists("git"):
        print(red("  ✗ Git не найден"))
        return

    # Check for updates
    print(yellow("  Проверка обновлений..."))
    result = subprocess.run(
        ["git", "fetch", "--tags", "origin"],
        cwd=ROOT_DIR, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(red(f"  ✗ git fetch failed: {result.stderr}"))
        return

    # Current commit
    cur = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT_DIR, capture_output=True, text=True
    ).stdout.strip()

    remote = subprocess.run(
        ["git", "rev-parse", "--short", "origin/main"],
        cwd=ROOT_DIR, capture_output=True, text=True
    ).stdout.strip()

    if cur == remote:
        print(green(f"  ✓ Система обновлена ({cur})"))
        return

    # Show changes
    log_result = subprocess.run(
        ["git", "log", "--oneline", "HEAD..origin/main"],
        cwd=ROOT_DIR, capture_output=True, text=True
    )
    if log_result.stdout:
        print(cyan("  Новые коммиты:"))
        for line in log_result.stdout.strip().splitlines():
            print(f"    • {line}")
        print()

    answer = input(f"  {bold('Применить обновление?')} (y/n): ").strip().lower()
    if answer not in ("y", "yes", "д", "да"):
        print(yellow("  Обновление отменено"))
        return

    # Backup
    print(yellow("\n  Создание резервной копии..."))
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        from app.core.updater import _create_backup, _restore_preserved
        backup_path = _create_backup()
        print(green(f"  ✓ Бэкап: {backup_path.name}"))

        # Pull
        print(yellow("  Применение обновления..."))
        pull = subprocess.run(
            ["git", "pull", "--ff-only", "origin", "main"],
            cwd=ROOT_DIR, capture_output=True, text=True
        )
        if pull.returncode != 0:
            print(red(f"  ✗ git pull failed: {pull.stderr}"))
            print(yellow("  Откат..."))
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=ROOT_DIR)
            return

        # Restore local files
        _restore_preserved(backup_path)
        print(green("  ✓ Локальные файлы восстановлены"))

        # Rebuild
        print(yellow("\n  Обновление зависимостей..."))
        try:
            _run([_python(), "-m", "pip", "install", "-r",
                  str(BACKEND_DIR / "requirements.txt"), "-q"])
        except Exception:
            pass

        if (FRONTEND_DIR / "package.json").exists() and _cmd_exists("npm"):
            print(yellow("  Пересборка фронтенда..."))
            try:
                _run(["npm", "install"], cwd=FRONTEND_DIR)
                _run(["npm", "run", "build"], cwd=FRONTEND_DIR)
            except Exception:
                print(yellow("  ⚠  Ошибка сборки фронтенда"))

        new_ver = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT_DIR, capture_output=True, text=True
        ).stdout.strip()

        print(green(f"\n  ✓ Обновление завершено: {cur} → {new_ver}"))
        if IS_LINUX:
            print(cyan("  Перезапустите сервис: sudo systemctl restart blackwall-backend"))

    except Exception as e:
        print(red(f"  ✗ Ошибка: {e}"))
    finally:
        if str(BACKEND_DIR) in sys.path:
            sys.path.remove(str(BACKEND_DIR))


def cmd_service(action: str = "status"):
    """Управление systemd сервисом."""
    if not IS_LINUX:
        print(yellow("  ⚠  Systemd доступен только на Linux"))
        return

    actions = {
        "status": ["systemctl", "status", "blackwall-backend"],
        "start": ["sudo", "systemctl", "start", "blackwall-backend"],
        "stop": ["sudo", "systemctl", "stop", "blackwall-backend"],
        "restart": ["sudo", "systemctl", "restart", "blackwall-backend"],
        "logs": ["journalctl", "-u", "blackwall-backend", "-n", "50", "--no-pager"],
    }

    if action not in actions:
        print(red(f"  Действие: status|start|stop|restart|logs"))
        return

    print(bold(f"\n⚙  Сервис: {action}\n"))
    _run(actions[action], check=False)


def cmd_docs():
    """Показать доступную документацию."""
    print(bold("\n📚 Документация проекта\n"))
    docs = sorted(DOCS_DIR.glob("*.md")) if DOCS_DIR.exists() else []
    if docs:
        for doc in docs:
            print(f"  • {cyan(doc.name):<25s} {dim(str(doc.relative_to(ROOT_DIR)))}")
    else:
        print(dim("  Документация не найдена"))

    readme = ROOT_DIR / "README.md"
    if readme.exists():
        print(f"\n  {bold('README.md')}:")
        content = readme.read_text(encoding="utf-8")
        # Show first 30 lines
        for i, line in enumerate(content.splitlines()[:30]):
            print(f"  {dim('│')} {line}")
        if len(content.splitlines()) > 30:
            print(dim(f"  ... ещё {len(content.splitlines()) - 30} строк"))
    print()


# ─── Interactive Menu ─────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("1", "Обзор проекта (info)", cmd_info),
    ("2", "Статус системы (status)", cmd_status),
    ("3", "Запустить Backend", lambda: cmd_backend()),
    ("4", "Запустить Frontend", cmd_frontend),
    ("5", "Запустить всё (fullstack)", cmd_fullstack),
    ("6", "Запустить тесты", lambda: cmd_test()),
    ("7", "Инициализировать БД", cmd_db_init),
    ("8", "Создать root пользователя", cmd_setup_user),
    ("9", "Установить Python зависимости", cmd_install_deps),
    ("10", "Открыть API docs (Swagger)", cmd_api_docs),
    ("11", "Собрать Rust core", cmd_build_rust),
    ("12", "Собрать Frontend", cmd_build_frontend),
    ("13", "Обновление системы (update)", cmd_update),
    ("14", "Управление сервисом (systemd)", lambda: cmd_service()),
    ("15", "Документация", cmd_docs),
    ("16", bold("Quick Start (сборка + запуск)"), cmd_quickstart),
    ("0", "Выход", None),
]


def interactive_menu():
    """Интерактивное меню."""
    print(cyan(BANNER))
    while True:
        print(bold("  ══ Главное меню ══\n"))
        for key, label, _ in MENU_ITEMS:
            prefix = red("  ✖ ") if key == "0" else f"  {cyan(key):>5s}. "
            print(f"{prefix}{label}")
        print()

        choice = input(f"  {bold('Выбор')} [1-16, 0=выход]: ").strip()

        if choice == "0" or choice.lower() in ("q", "quit", "exit"):
            print(dim("\n  До свидания!\n"))
            break

        found = False
        for key, label, func in MENU_ITEMS:
            if choice == key and func:
                print()
                try:
                    func()
                except KeyboardInterrupt:
                    print(yellow("\n  Прервано."))
                except Exception as e:
                    print(red(f"\n  Ошибка: {e}"))
                found = True
                break

        if not found and choice != "0":
            print(red("  Неизвестный выбор. Попробуйте снова.\n"))


# ─── CLI argument handling ────────────────────────────────────────────────────

def print_help():
    print(f"""
{bold('The Blackwall — Unified Launcher')}

{bold('Использование:')}
  python main.py                  Интерактивное меню
  python main.py <команда>        Запуск конкретной команды

{bold('Команды:')}
  info              Обзор проекта
  status            Статус всех компонентов
  check             Проверка зависимостей (= status)
  backend           Запустить FastAPI сервер
  frontend          Запустить Vite dev-сервер
  fullstack         Запустить backend + frontend
  test [path]       Запустить тесты
  quickstart        Полная сборка и запуск (всё в одном)
  db-init           Инициализировать БД
  setup-user        Создать root пользователя
  install-deps      Установить Python зависимости
  api-docs          Открыть Swagger UI
  build-rust        Собрать Rust core
  build-frontend    Собрать фронтенд
  update            Проверить и применить обновления
  service <action>  Управление systemd (status|start|stop|restart|logs)
  docs              Показать документацию
  alembic <args>    Запустить Alembic миграции

{bold('Примеры:')}
  python main.py status
  python main.py backend
  python main.py test tests/test_auth.py
  python main.py fullstack
  python main.py quickstart
  python main.py alembic upgrade head
""")


def main():
    args = sys.argv[1:]

    if not args:
        interactive_menu()
        return

    command = args[0].lower()

    commands = {
        "info": cmd_info,
        "status": cmd_status,
        "check": cmd_check,
        "backend": lambda: cmd_backend(
            host=args[args.index("--host") + 1] if "--host" in args else "0.0.0.0",
            port=int(args[args.index("--port") + 1]) if "--port" in args else 8000,
        ),
        "frontend": cmd_frontend,
        "fullstack": cmd_fullstack,
        "test": lambda: cmd_test(
            verbose="-q" not in args,
            test_path=args[1] if len(args) > 1 and not args[1].startswith("-") else None,
        ),
        "quickstart": cmd_quickstart,
        "db-init": cmd_db_init,
        "setup-user": cmd_setup_user,
        "install-deps": cmd_install_deps,
        "api-docs": cmd_api_docs,
        "build-rust": cmd_build_rust,
        "build-frontend": cmd_build_frontend,
        "docs": cmd_docs,
        "update": cmd_update,
        "service": lambda: cmd_service(args[1] if len(args) > 1 else "status"),
        "alembic": lambda: cmd_alembic(args[1:]),
    }

    if command in ("--help", "-h", "help"):
        print_help()
    elif command in commands:
        try:
            commands[command]()
        except KeyboardInterrupt:
            print(yellow("\n  Прервано."))
    else:
        print(red(f"  Неизвестная команда: {command}"))
        print_help()


if __name__ == "__main__":
    main()
