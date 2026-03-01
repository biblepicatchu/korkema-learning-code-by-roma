# Reviewer Robot

Телеграм-бот для автоматической проверки учебных заданий по Python с помощью Claude AI.

## Как работает

1. Бот слушает сообщения в Telegram-группе
2. Когда пользователь отвечает (reply) на сообщение с заданием ключевым словом (`проверь`, `ревью`, `review`, `check`, `test`), бот:
   - Извлекает номер задачи из тега `[py-N]` в оригинальном сообщении
   - Находит папку `pyN-*` с кодом ученика
   - Запускает `claude -p --dangerously-skip-permissions` с промптом из файла `prompt`
   - Claude создаёт `verification.html` — HTML-отчёт с результатами проверки
   - Бот отправляет отчёт в чат как документ

## Установка

```bash
cd reviewer-robot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка

Скопировать `.env.example` в `.env` и заполнить:

```
TELEGRAM_BOT_TOKEN=<токен бота от @BotFather>
ALLOWED_USER_IDS=123456789,987654321
GROUP_CHAT_ID=-100xxxxxxxxxx
DEBUG=false
CLAUDE_TIMEOUT=1200
```

| Переменная | Описание | По умолчанию |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота | обязательно |
| `ALLOWED_USER_IDS` | ID пользователей через запятую, которым разрешено запрашивать проверку | все |
| `GROUP_CHAT_ID` | ID группового чата, в котором бот работает | любой |
| `DEBUG` | Включить подробное логирование (`true`/`false`) | `false` |
| `CLAUDE_TIMEOUT` | Таймаут выполнения Claude в секундах | `1200` |

## Запуск

```bash
source .venv/bin/activate
python bot.py
```

## Структура проекта

```
reviewer-robot/
├── bot.py              # Основной код бота
├── requirements.txt    # Зависимости Python
├── .env.example        # Шаблон переменных окружения
├── .env                # Переменные окружения (не в git)
└── docs/
    └── description.html  # Описание проекта (HTML)
```

Файл `prompt` с шаблоном промпта для Claude лежит в корне родительского репозитория.
