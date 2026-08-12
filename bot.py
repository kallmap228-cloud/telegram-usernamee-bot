import asyncio
import random
import string
import logging
import os
import aiohttp
from aiohttp import web
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
PORT = int(os.environ.get("PORT", "10000"))

if not BOT_TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не установлена!")

SEARCH_TIMEOUT = 30
CHECK_DELAY = 0.5
MAX_RESULTS = 5
WORD_INPUT = 1

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ПРОВЕРКА ЮЗЕРНЕЙМОВ ====================

class UsernameChecker:
    def __init__(self):
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

    async def init_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def check_telegram(self, username: str) -> dict:
        try:
            url = f"https://t.me/{username}"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=8), allow_redirects=True) as resp:
                text = await resp.text()
                text_lower = text.lower()

                if resp.status == 404:
                    return {"status": "free", "banned": False}

                banned_phrases = [
                    "this account has been deleted",
                    "this channel has been deleted",
                    "this group has been deleted",
                    "deleted account",
                    "terminated",
                    "banned",
                    "deleted user",
                ]
                is_banned = any(phrase in text_lower for phrase in banned_phrases)

                if resp.status == 200:
                    if is_banned:
                        return {"status": "taken", "banned": True}
                    return {"status": "taken", "banned": False}

                return {"status": "free", "banned": False}
        except Exception as e:
            logger.error(f"Telegram check error for @{username}: {e}")
            return {"status": "error", "banned": False}

    async def check_fragment(self, username: str) -> dict:
        try:
            url = f"https://fragment.com/username/{username}"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=8), allow_redirects=True) as resp:
                text = await resp.text()
                text_lower = text.lower()

                if resp.status == 404:
                    return {"on_sale": False, "status": "not_listed"}

                sale_indicators = [
                    "auction", "for sale", "buy now", "current bid",
                    "place bid", "ton", "ends in", "minimum bid", "highest bid",
                ]
                is_on_sale = any(ind in text_lower for ind in sale_indicators)

                if "sold" in text_lower and not is_on_sale:
                    return {"on_sale": False, "status": "sold"}

                return {
                    "on_sale": is_on_sale,
                    "status": "auction" if is_on_sale else "not_listed"
                }
        except Exception as e:
            logger.error(f"Fragment check error for @{username}: {e}")
            return {"on_sale": False, "status": "error"}

    async def check_username(self, username: str) -> dict:
        await self.init_session()
        tg_result = await self.check_telegram(username)
        frag_result = await self.check_fragment(username)

        is_available = (
            tg_result["status"] == "free" and 
            not frag_result["on_sale"] and
            not tg_result["banned"]
        )

        return {
            "username": username,
            "available": is_available,
            "telegram_status": tg_result["status"],
            "fragment_status": frag_result["status"],
            "banned": tg_result["banned"],
            "on_sale": frag_result["on_sale"]
        }


# ==================== ГЕНЕРАТОРЫ ====================

def generate_letter_usernames(length: int, count: int = 120) -> list:
    letters = string.ascii_lowercase
    usernames = set()
    vowels = "aeiou"
    consonants = "".join(c for c in letters if c not in vowels)

    while len(usernames) < count:
        if random.random() > 0.5:
            username = "".join(random.choices(letters, k=length))
        else:
            username = ""
            for i in range(length):
                if i % 2 == 0:
                    username += random.choice(consonants)
                else:
                    username += random.choice(vowels)

        if len(username) >= 5 and username.isalpha():
            usernames.add(username)

    return list(usernames)


def generate_word_variations(word: str) -> list:
    letters = string.ascii_lowercase
    variations = []

    for _ in range(30):
        prefix = "".join(random.choices(letters, k=random.randint(1, 2)))
        var = f"{prefix}{word}"
        if 5 <= len(var) <= 32 and var.isalpha():
            variations.append(var)

    for _ in range(30):
        suffix = "".join(random.choices(letters, k=random.randint(1, 2)))
        var = f"{word}{suffix}"
        if 5 <= len(var) <= 32 and var.isalpha() and var not in variations:
            variations.append(var)

    for _ in range(25):
        pre = "".join(random.choices(letters, k=1))
        suf = "".join(random.choices(letters, k=1))
        var = f"{pre}{word}{suf}"
        if 5 <= len(var) <= 32 and var.isalpha() and var not in variations:
            variations.append(var)

    for _ in range(15):
        pre = "".join(random.choices(letters, k=2))
        suf = "".join(random.choices(letters, k=2))
        var = f"{pre}{word}{suf}"
        if 5 <= len(var) <= 32 and var.isalpha() and var not in variations:
            variations.append(var)

    return variations[:100]


# ==================== АНИМАЦИЯ ====================

SEARCH_ANIMATIONS = [
    "🔍 Проверяется @{username}...",
    "⚡ Анализируется @{username}...",
    "🔎 Сканируется @{username}...",
    "📡 Запрос к серверам: @{username}...",
    "🌐 Проверка Fragment: @{username}...",
    "✨ Тестируется @{username}...",
    "🎯 Верификация @{username}...",
    "🛡️ Проверка бана: @{username}...",
]

async def animate_search(message, context, checker, usernames):
    start_time = datetime.now()
    checked = 0
    found = []
    current_idx = 0
    last_update = 0

    while (datetime.now() - start_time).seconds < SEARCH_TIMEOUT:
        if current_idx >= len(usernames):
            break

        username = usernames[current_idx]
        checked += 1

        time_elapsed = (datetime.now() - start_time).seconds
        if checked % 3 == 0 or (time_elapsed - last_update) >= 3:
            last_update = time_elapsed
            anim_text = random.choice(SEARCH_ANIMATIONS).format(username=username)
            progress = f"\n\n📊 Проверено: {checked}/{len(usernames)}\n⏱️ Прошло: {time_elapsed}с\n✅ Найдено: {len(found)}"
            try:
                await message.edit_text(anim_text + progress, parse_mode="HTML")
            except Exception:
                pass

        result = await checker.check_username(username)

        if result["available"]:
            found.append(result)
            if len(found) >= MAX_RESULTS:
                break

        current_idx += 1
        await asyncio.sleep(CHECK_DELAY)

    return found


# ==================== ОБРАБОТЧИКИ ====================

checker = UsernameChecker()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    keyboard = [
        [InlineKeyboardButton("🔠 Поиск 5-буквенных", callback_data="search_5")],
        [InlineKeyboardButton("🔠 Поиск 6-буквенных", callback_data="search_6")],
        [InlineKeyboardButton("🔤 Поиск по слову", callback_data="search_word")],
    ]

    if user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin")])

    welcome_text = (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"🤖 Я бот для поиска <b>свободных юзернеймов</b> Telegram.\n\n"
        f"✨ <b>Что я проверяю:</b>\n"
        f"  • Не занят в Telegram ✅\n"
        f"  • Не на продаже на Fragment ✅\n"
        f"  • Не забанен ✅\n"
        f"  • <b>Только буквы</b>, без цифр ✅\n\n"
        f"👇 <b>Выбери действие:</b>"
    )

    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "search_5":
        await query.edit_message_text(
            "🔍 <b>Начинаю поиск 5-буквенных юзернеймов...</b>\n\n⏳ Генерация списка...",
            parse_mode="HTML"
        )

        usernames = generate_letter_usernames(5, 120)
        msg = await query.edit_message_text(
            "🔍 <b>Поиск запущен!</b>\n\n🚀 Проверяю первый юзернейм...",
            parse_mode="HTML"
        )

        found = await animate_search(msg, context, checker, usernames)

        if found:
            text = "🎉 <b>Найдены свободные 5-буквенные юзернеймы!</b>\n\n"
            for i, r in enumerate(found[:MAX_RESULTS], 1):
                text += f"{i}. <code>@{r['username']}</code> ✅\n"
            text += "\n💡 <b>Совет:</b> Проверьте их сразу — свободные короткие юзернеймы разбирают за секунды!"
        else:
            text = (
                "😔 <b>Свободных 5-буквенных юзернеймов не найдено.</b>\n\n"
                "🔄 Попробуйте ещё раз — каждый запрос генерирует новые случайные комбинации!"
            )

        keyboard = [
            [InlineKeyboardButton("🔄 Повторить поиск", callback_data="search_5")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back")]
        ]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif query.data == "search_6":
        await query.edit_message_text(
            "🔍 <b>Начинаю поиск 6-буквенных юзернеймов...</b>",
            parse_mode="HTML"
        )

        usernames = generate_letter_usernames(6, 120)
        msg = await query.edit_message_text(
            "🔍 <b>Поиск запущен!</b>\n\n🚀 Проверяю первый юзернейм...",
            parse_mode="HTML"
        )

        found = await animate_search(msg, context, checker, usernames)

        if found:
            text = "🎉 <b>Найдены свободные 6-буквенные юзернеймы!</b>\n\n"
            for i, r in enumerate(found[:MAX_RESULTS], 1):
                text += f"{i}. <code>@{r['username']}</code> ✅\n"
            text += "\n💡 Проверьте их сразу!"
        else:
            text = (
                "😔 <b>Свободных 6-буквенных юзернеймов не найдено.</b>\n\n"
                "🔄 Попробуйте ещё раз!"
            )

        keyboard = [
            [InlineKeyboardButton("🔄 Повторить поиск", callback_data="search_6")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back")]
        ]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif query.data == "search_word":
        await query.edit_message_text(
            "🔤 <b>Поиск по слову</b>\n\n"
            "Введите слово <b>на английском</b>, и я найду варианты с префиксом и суффиксом.\n\n"
            "📌 <b>Пример:</b> если ввести <code>apple</code>, я найду:\n"
            "  • <code>xaapple</code> (префикс)\n"
            "  • <code>applexy</code> (суффикс)\n"
            "  • <code>xappley</code> (префикс+суффикс)\n\n"
            "📝 <b>Введите слово:</b>",
            parse_mode="HTML"
        )
        return WORD_INPUT

    elif query.data == "back":
        await start_from_query(query)

    elif query.data == "admin":
        if query.from_user.id != OWNER_ID:
            await query.answer("❌ Нет доступа!", show_alert=True)
            return

        text = (
            "⚙️ <b>Админ-панель</b>\n\n"
            f"👤 Владелец ID: <code>{OWNER_ID}</code>\n"
            f"🤖 Бот работает в штатном режиме.\n\n"
            f"📊 Здесь можно добавить:\n"
            f"  • Статистику пользователей\n"
            f"  • Логи проверок\n"
            f"  • Управление подписками\n\n"
            f"🔧 Для изменений — редактируй код в GitHub!"
        )
        keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def start_from_query(query):
    keyboard = [
        [InlineKeyboardButton("🔠 Поиск 5-буквенных", callback_data="search_5")],
        [InlineKeyboardButton("🔠 Поиск 6-буквенных", callback_data="search_6")],
        [InlineKeyboardButton("🔤 Поиск по слову", callback_data="search_word")],
    ]
    if query.from_user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin")])

    welcome_text = (
        f"🤖 <b>Бот для поиска свободных юзернеймов</b>\n\n"
        f"✨ <b>Возможности:</b>\n"
        f"  • 5-буквенные юзернеймы\n"
        f"  • 6-буквенные юзернеймы\n"
        f"  • Поиск по слову (префикс/суффикс)\n"
        f"  • Проверка Fragment + Telegram + Бан\n\n"
        f"👇 <b>Выбери действие:</b>"
    )
    await query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def word_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word = update.message.text.strip().lower()

    if not word.isalpha():
        await update.message.reply_text(
            "❌ <b>Ошибка!</b> Введите только буквы (a-z), без цифр, пробелов и символов!\n\n🔄 Попробуйте снова:",
            parse_mode="HTML"
        )
        return WORD_INPUT

    if len(word) < 3:
        await update.message.reply_text(
            "❌ Слово слишком короткое! Минимум 3 буквы.\n\n🔄 Попробуйте снова:",
            parse_mode="HTML"
        )
        return WORD_INPUT

    if len(word) > 20:
        await update.message.reply_text(
            "❌ Слово слишком длинное! Максимум 20 букв.\n\n🔄 Попробуйте снова:",
            parse_mode="HTML"
        )
        return WORD_INPUT

    msg = await update.message.reply_text(
        f"🔍 <b>Ищу варианты для слова '{word}'...</b>\n\n⏳ Генерация комбинаций...",
        parse_mode="HTML"
    )

    usernames = generate_word_variations(word)
    await msg.edit_text(
        f"🔍 <b>Поиск по слову '{word}'</b>\n\n"
        f"🚀 Начинаю проверку <b>{len(usernames)}</b> вариантов...",
        parse_mode="HTML"
    )

    found = await animate_search(msg, context, checker, usernames)

    if found:
        text = f"🎉 <b>Найдены свободные варианты для '{word}'!</b>\n\n"
        for i, r in enumerate(found[:MAX_RESULTS], 1):
            text += f"{i}. <code>@{r['username']}</code> ✅\n"
        text += "\n💡 <b>Совет:</b> Проверьте сразу — юзернеймы быстро разбирают!"
    else:
        text = (
            f"😔 <b>Для слова '{word}' свободных вариантов не найдено.</b>\n\n"
            f"🔄 Попробуйте другое слово!"
        )

    keyboard = [
        [InlineKeyboardButton("🔤 Новое слово", callback_data="search_word")],
        [InlineKeyboardButton("🔙 В меню", callback_data="back")]
    ]
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено. Возвращаюсь в меню...")
    await start(update, context)
    return ConversationHandler.END


# ==================== ВЕБ-СЕРВЕР (для Render Web Service) ====================

async def health_check(request):
    return web.Response(text="✅ Бот работает! Username Finder Bot is alive.", status=200)


async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"🌐 Веб-сервер запущен на порту {PORT}")


# ==================== ЗАПУСК (python-telegram-bot v21+) ====================

async def main():
    # Запускаем веб-сервер для health check
    web_task = asyncio.create_task(run_web_server())

    # Настройка бота
    application = Application.builder().token(BOT_TOKEN).build()

    word_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^search_word$")],
        states={
            WORD_INPUT: [MessageHandler(filters.TEXT & (~filters.COMMAND), word_input_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(word_conv)
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Бот запущен! Ожидаю сообщения...")

    # Запускаем бота (v21+ API)
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

    # Ждём вечно
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Остановка бота...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await checker.close()
        web_task.cancel()
        try:
            await web_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
            
