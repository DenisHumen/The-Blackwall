# Firewall Manager

Комплексная система управления межсетевым экраном на базе Python, Rust, React и PostgreSQL.

![TheBlackWall](assets/images/TheBlackWall_4K.gif)


## Архитектура

- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Backend**: Python FastAPI
- **Core Engine**: Rust (nftables, traffic monitoring)
- **Database**: PostgreSQL + TimescaleDB

## Структура проекта

- `rust-core/` - Rust модули для производительности
- `backend/` - Python FastAPI backend
- `frontend/` - React frontend приложение
- `database/` - SQL схемы и миграции
- `scripts/` - Установочные скрипты
- `config/` - Конфигурационные файлы
- `docs/` - Документация

## Начало работы

См. [INSTALL.md](docs/INSTALL.md) для инструкций по установке.

## Лицензия

MIT
