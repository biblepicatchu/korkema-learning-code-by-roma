import asyncio
import glob
import logging
import os
import re

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in os.environ.get("ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
]
GROUP_CHAT_ID = int(os.environ["GROUP_CHAT_ID"]) if os.environ.get("GROUP_CHAT_ID") else None
REVIEW_KEYWORDS = ["проверь", "проверить", "ревью", "review", "check", "test", "тест"]
DEBUG = os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")
CLAUDE_TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "1200"))

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if DEBUG else logging.INFO,
)
logger = logging.getLogger(__name__)


def is_review_request(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in REVIEW_KEYWORDS)


def build_prompt(task_number: str, task_description: str, base_dir: str) -> str:
    prompt_path = os.path.join(base_dir, "prompt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    prompt = prompt.replace("pyXXX-*", f"py{task_number}-*")
    prompt = prompt.replace('"тут описание задачи"', f'"{task_description}"')
    return prompt


async def run_claude_review(task_number: str, task_dir: str, prompt: str, message) -> None:
    status_msg = await message.reply_text(f"Задание #{task_number}: начинаю проверку...")

    verification_path = os.path.join(task_dir, "verification.html")
    if os.path.exists(verification_path):
        os.remove(verification_path)

    try:
        process = await asyncio.create_subprocess_exec(
            "claude", "-p", "--dangerously-skip-permissions",
            "--model", "claude-haiku-4-5-20251001",
            "--max-turns", "15",
            prompt,
            cwd=task_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(process.wait(), timeout=CLAUDE_TIMEOUT)
    except asyncio.TimeoutError:
        process.kill()
        await message.reply_text(f"Задание #{task_number}: таймаут ({CLAUDE_TIMEOUT}с) — проверка прервана")
        await status_msg.delete()
        return
    except Exception as e:
        logger.error("Ошибка запуска Claude: %s", e)
        await message.reply_text(f"Задание #{task_number}: ошибка запуска Claude — {e}")
        await status_msg.delete()
        return

    if process.returncode != 0:
        stderr = (await process.stderr.read()).decode(errors="replace")
        logger.error("Claude завершился с кодом %d: %s", process.returncode, stderr)
        await message.reply_text(f"Задание #{task_number}: Claude завершился с ошибкой (код {process.returncode})")
        await status_msg.delete()
        return

    if not os.path.exists(verification_path):
        await message.reply_text(f"Задание #{task_number}: Claude не создал отчёт verification.html")
        await status_msg.delete()
        return

    with open(verification_path, "rb") as f:
        await message.reply_document(document=f, filename=f"verification-py{task_number}.html")

    await status_msg.delete()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    logger.debug("=" * 60)
    logger.debug("НОВОЕ СООБЩЕНИЕ ПОЛУЧЕНО")
    logger.debug("  Текст: %s", message.text if message else None)
    logger.debug("  Пользователь: %s (%s)", user.id if user else None, user.full_name if user else None)
    logger.debug("  Чат: %s (тип: %s)", chat.id if chat else None, chat.type if chat else None)

    if not message or not message.text or not user:
        logger.debug("  >>> ОТБРОШЕНО: нет message, text или user")
        return

    if ALLOWED_USER_IDS and user.id not in ALLOWED_USER_IDS:
        logger.debug("  >>> ОТБРОШЕНО: user.id=%d не в ALLOWED_USER_IDS=%s", user.id, ALLOWED_USER_IDS)
        return
    logger.debug("  Проверка пользователя: ПРОЙДЕНА (user.id=%d)", user.id)

    if GROUP_CHAT_ID and chat.id != GROUP_CHAT_ID:
        logger.debug("  >>> ОТБРОШЕНО: chat.id=%d != GROUP_CHAT_ID=%s", chat.id, GROUP_CHAT_ID)
        return
    logger.debug("  Проверка чата: ПРОЙДЕНА (chat.id=%d)", chat.id)

    if not message.reply_to_message:
        logger.debug("  >>> ОТБРОШЕНО: сообщение НЕ является ответом (reply) на другое сообщение")
        return
    logger.debug("  Проверка reply: ПРОЙДЕНА (ответ на message_id=%d)", message.reply_to_message.message_id)

    is_review = is_review_request(message.text)
    logger.debug("  Проверка ключевых слов: текст='%s', результат=%s", message.text, is_review)
    if not is_review:
        logger.debug("  >>> ОТБРОШЕНО: ключевые слова %s не найдены в '%s'", REVIEW_KEYWORDS, message.text)
        return
    logger.debug("  Проверка ключевых слов: ПРОЙДЕНА")

    original = message.reply_to_message
    original_text = original.text or original.caption or ""
    logger.debug("  Оригинальное сообщение (message_id=%d):", original.message_id)
    logger.debug("    text: %s", original.text)
    logger.debug("    caption: %s", original.caption)
    logger.debug("    от: %s (%s)", original.from_user.id if original.from_user else None, original.from_user.full_name if original.from_user else None)
    logger.debug("    итоговый текст: '%s'", original_text)

    if not original_text:
        logger.debug("  >>> В оригинальном сообщении нет текста")
        return

    brackets = re.findall(r"\[\w+-(\d+)\]", original_text)
    logger.debug("  Содержимое квадратных скобок: %s", brackets)

    if not brackets:
        logger.debug("  >>> Квадратные скобки не найдены в тексте")
        return

    logger.info("Запрос на проверку от %s (id=%d)", user.full_name, user.id)

    task_description = re.sub(r"\[\w+-\d+\]", "", original_text).strip()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logger.debug("  Базовая директория: %s", base_dir)

    logger.info("Обновляю репозиторий (git pull) в %s...", base_dir)
    try:
        process = await asyncio.create_subprocess_exec(
            "git", "pull",
            cwd=base_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        git_output = stdout.decode(errors="replace").strip()
        logger.info("git pull завершён (код %d): %s", process.returncode, git_output)
        if process.returncode != 0:
            git_err = stderr.decode(errors="replace").strip()
            logger.error("git pull ошибка: %s", git_err)
            await message.reply_text(f"Ошибка обновления репозитория: {git_err}")
            return
    except asyncio.TimeoutError:
        logger.error("git pull таймаут (60с)")
        await message.reply_text("Таймаут при обновлении репозитория")
        return
    except Exception as e:
        logger.error("git pull исключение: %s", e)
        await message.reply_text(f"Ошибка обновления репозитория: {e}")
        return

    for task_number in brackets:
        pattern = os.path.join(base_dir, f"py{task_number}-*")
        matches = glob.glob(pattern)
        logger.debug("  Поиск папки: паттерн='%s', найдено=%s", pattern, matches)

        if matches:
            task_dir = matches[0]
            logger.info("  Задание #%s: найдена папка %s", task_number, task_dir)
            if not os.listdir(task_dir):
                logger.info("  Задание #%s: папка пуста", task_number)
                await message.reply_text(f"Папка соответствующая паттерну py{task_number}-* пуста")
                continue

            prompt = build_prompt(task_number, task_description, base_dir)
            await run_claude_review(task_number, task_dir, prompt, message)
        else:
            logger.info("  Задание #%s: папка не найдена (паттерн: py%s-*)", task_number, task_number)
            await message.reply_text(f"Папка соответствующая паттерну py{task_number}-* не найдена")


def main() -> None:
    logger.debug("=" * 60)
    logger.debug("ЗАПУСК БОТА")
    logger.debug("  TELEGRAM_BOT_TOKEN: ...%s", TELEGRAM_BOT_TOKEN[-6:])
    logger.debug("  ALLOWED_USER_IDS:   %s", ALLOWED_USER_IDS)
    logger.debug("  GROUP_CHAT_ID:      %s", GROUP_CHAT_ID)
    logger.debug("  REVIEW_KEYWORDS:    %s", REVIEW_KEYWORDS)
    logger.debug("  DEBUG:              %s", DEBUG)
    logger.debug("=" * 60)

    async def post_init(application) -> None:
        bot_info = await application.bot.get_me()
        logger.info("get_me: id=%s, username=@%s, name='%s'", bot_info.id, bot_info.username, bot_info.first_name)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            handle_message,
        )
    )

    logger.info("Бот запущен. Жду сообщения...")
    app.run_polling(poll_interval=60)
    logger.info("Бот остановлен.")


if __name__ == "__main__":
    main()