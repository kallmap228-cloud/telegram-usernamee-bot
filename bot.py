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

# НАСТРОЙКИ СКОРОСТИ
SEARCH_TIMEOUT = 60       # Увеличили время поиска
CHECK_DELAY = 0.15        # Задержка между БАТЧАМИ (не между проверками)
MAX_RESULTS = 5           # Сколько результатов выдать
BATCH_SIZE = 15           # Сколько юзернеймов проверять ПАРАЛЛЕЛЬНО одновременно
CONCURRENT_LIMIT = 10     # Максимум одновременных HTTP-запросов

WORD_INPUT = 1

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ПРОВЕРКА ЮЗЕРНЕЙМОВ (ПАРАЛЛЕЛЬНАЯ) ====================

class UsernameChecker:
    def __init__(self):
        self.session = None
        self.semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def init_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def check_telegram(self, username: str) -> dict:
        """Проверяет юзернейм через t.me — быстрая проверка"""
        try:
            url = f"https://t.me/{username}"
            async with self.semaphore:
                async with self.session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=6), 
                    allow_redirects=True
                ) as resp:
                    text = await resp.text()
                    text_lower = text.lower()

                    # 404 = точно свободен
                    if resp.status == 404:
                        return {"status": "free", "banned": False}

                    # 302 редирект = скорее всего свободен
                    if resp.status == 302:
                        return {"status": "free", "banned": False}

                    # Проверка на забаненный/удалённый
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

                    if is_banned:
                        return {"status": "taken", "banned": True}

                    # Если 200 — проверяем контент
                    if resp.status == 200:
                        # Признаки существующего аккаунта/канала
                        taken_indicators = [
                            'class="tgme_page_photo"',
                            'class="tgme_page_title"',
                            'class="tgme_page_description"',
                            'class="tgme_page_extra"',
                            'data-view="tgme_page"',
                        ]

                        # Признаки пустой/заглушечной страницы (свободен)
                        free_indicators = [
                            "if you have telegram, you can contact",
                            "if you have telegram, you can view and join",
                            "no messages here yet",
                        ]

                        is_taken = any(ind in text_lower for ind in taken_indicators)
                        is_free_page = any(ind in text_lower for ind in free_indicators)

                        if is_taken and not is_free_page:
                            return {"status": "taken", "banned": False}
                        else:
                            return {"status": "free", "banned": False}

                    # Любой другой статус — считаем свободным
                    return {"status": "free", "banned": False}

        except Exception as e:
            logger.debug(f"TG check error @{username}: {e}")
            return {"status": "error", "banned": False}

    async def check_fragment(self, username: str) -> dict:
        """Проверяет юзернейм на Fragment — быстрая проверка"""
        try:
            url = f"https://fragment.com/username/{username}"
            async with self.semaphore:
                async with self.session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=6), 
                    allow_redirects=True
                ) as resp:
                    text = await resp.text()
                    text_lower = text.lower()

                    # 404 = не на продаже
                    if resp.status == 404:
                        return {"on_sale": False, "status": "not_listed"}

                    # Быстрая проверка на аукцион
                    sale_indicators = [
                        "auction", "for sale", "buy now", "current bid",
                        "place bid", "ton", "ends in", "minimum bid", 
                        "highest bid", "collectible",
                    ]

                    is_on_sale = any(ind in text_lower for ind in sale_indicators)

                    return {
                        "on_sale": is_on_sale,
                        "status": "auction" if is_on_sale else "not_listed"
                    }

        except Exception as e:
            logger.debug(f"Fragment check error @{username}: {e}")
            return {"on_sale": False, "status": "error"}

    async def check_username(self, username: str) -> dict:
        """Комплексная проверка одного юзернейма"""
        tg_result = await self.check_telegram(username)

        # Если занят в Telegram — сразу отбрасываем (не тратим время на Fragment)
        if tg_result["status"] != "free" or tg_result["banned"]:
            return {
                "username": username,
                "available": False,
                "telegram_status": tg_result["status"],
                "fragment_status": "skipped",
                "banned": tg_result["banned"],
                "on_sale": False
            }

        # Проверяем Fragment только если свободен в Telegram
        frag_result = await self.check_fragment(username)

        is_available = not frag_result["on_sale"] and not tg_result["banned"]

        return {
            "username": username,
            "available": is_available,
            "telegram_status": tg_result["status"],
            "fragment_status": frag_result["status"],
            "banned": tg_result["banned"],
            "on_sale": frag_result["on_sale"]
        }

    async def check_batch(self, usernames: list) -> list:
        """Проверяет список юзернеймов ПАРАЛЛЕЛЬНО"""
        await self.init_session()
        tasks = [self.check_username(u) for u in usernames]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Фильтруем ошибки
        valid_results = []
        for r in results:
            if isinstance(r, dict):
                valid_results.append(r)
        return valid_results


# ==================== ГЕНЕРАТОРЫ ====================

def generate_letter_usernames(length: int, count: int = 300) -> list:
    """Генерирует случайные юзернеймы из букв"""
    letters = string.ascii_lowercase
    usernames = set()
    vowels = "aeiou"
    consonants = "".join(c for c in letters if c not in vowels)

    while len(usernames) < count:
        if random.random() > 0.4:
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
    """Генерирует варианты с префиксом и суффиксом"""
    letters = string.ascii_lowercase
    variations = []

    # Префикс (1-2 буквы + слово)
    for _ in range(40):
        prefix = "".join(random.choices(letters, k=random.randint(1, 2)))
        var = f"{prefix}{word}"
        if 5 <= len(var) <= 32 and var.isalpha():
            variations.append(var)

    # Суффикс (слово + 1-2 буквы)
    for _ in range(40):
        suffix = "".join(random.choices(letters, k=random.randint(1, 2)))
        var = f"{word}{suffix}"
        if 5 <= len(var) <= 32 and var.isalpha() and var not in variations:
            variations.append(var)

    # Префикс + слово + суффикс
    for _ in range(30):
        pre = "".join(random.choices(letters, k=1))
        suf = "".join(random.choices(letters, k=1))
        var = f"{pre}{word}{suf}"
        if 5 <= len(var) <= 32 and var.isalpha() and var not in variations:
            variations.append(var)

    for _ in range(20):
        pre = "".join(random.choices(letters, k=2))
        suf = "".join(random.choices(letters, k=2))
        var = f"{pre}{word}{suf}"
        if 5 <= len(var) <= 32 and var.isalpha() and var not in variations:
            variations.append(var)

    return variations[:130]


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
    """Анимированный поиск с батчевой параллельной проверкой"""
    start_time = datetime.now()
    checked = 0
    found = []
    total = len(usernames)

    # Разбиваем на батчи
    batches = [usernames[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    for batch in batches:
        # Проверяем батч параллельно
        results = await checker.check_batch(batch)
        checked += len(batch)

        for r in results:
            if r.get("available"):
                found.append(r)

        # Обновляем сообщение каждые 2 батча
        if checked % (BATCH_SIZE * 2) == 0 or checked == total or len(found) >= MAX_RESULTS:
            time_elapsed = (datetime.now() - start_time).seconds
            current = batch[-1] if batch else "..."
            anim_text = random.choice(SEARCH_ANIMATIONS).format(username=current)
            progress = f"

📊 Проверено: {checked}/{total}
⏱️ Прошло: {time_elapsed}с
✅ Найдено: {len(found)}"
            try:
                await message.edit_text(anim_text + progress, parse_mode="HTML")
            except Exception:
                pass

        # Если нашли достаточно — останавливаемся
        if len(found) >= MAX_RESULTS:
            break

        # Небольшая задержка между батчами (чтобы не забанили)
        await asyncio.sleep(CHECK_DELAY)

        # Проверка таймаута
        if (datetime.now() - start_time).seconds >= SEARCH_TIMEOUT:
            break

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
        f"👋 Привет, <b>{user.first_name}</b>!

"
        f"🤖 Я бот для поиска <b>свободных юзернеймов</b> Telegram.

"
        f"✨ <b>Что я проверяю:</b>
"
        f"  • Не занят в Telegram ✅
"
        f"  • Не на продаже на Fragment ✅
"
        f"  • Не забанен ✅
"
        f"  • <b>Только буквы</b>, без цифр ✅

"
        f"👇 <b>Выбери действие:</b>"
    )

    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "search_5":
        await query.edit_message_text(
            "🔍 <b>Начинаю поиск 5-буквенных юзернеймов...</b>

"
            "⏳ Генерация списка кандидатов...", 
            parse_mode="HTML"
        )

        usernames = generate_letter_usernames(5, 300)
        msg = await query.edit_message_text(
            "🔍 <b>Поиск запущен!</b>

"
            "🚀 Проверяю первую партию юзернеймов...", 
            parse_mode="HTML"
        )

        found = await animate_search(msg, context, checker, usernames)

        if found:
            text = "🎉 <b>Найдены свободные 5-буквенные юзернеймы!</b>

"
            for i, r in enumerate(found[:MAX_RESULTS], 1):
                text += f"{i}. <code>@{r['username']}</code> ✅
"
            text += "
💡 <b>Совет:</b> Проверьте их сразу — свободные короткие юзернеймы разбирают за секунды!"
        else:
            text = (
                "😔 <b>Свободных 5-буквенных юзернеймов не найдено.</b>

"
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

        usernames = generate_letter_usernames(6, 300)
        msg = await query.edit_message_text(
            "🔍 <b>Поиск запущен!</b>

"
            "🚀 Проверяю первую партию юзернеймов...", 
            parse_mode="HTML"
        )

        found = await animate_search(msg, context, checker, usernames)

        if found:
            text = "🎉 <b>Найдены свободные 6-буквенные юзернеймы!</b>

"
            for i, r in enumerate(found[:MAX_RESULTS], 1):
                text += f"{i}. <code>@{r['username']}</code> ✅
"
            text += "
💡 Проверьте их сразу!"
        else:
            text = (
                "😔 <b>Свободных 6-буквенных юзернеймов не найдено.</b>

"
                "🔄 Попробуйте ещё раз!"
            )

        keyboard = [
            [InlineKeyboardButton("🔄 Повторить поиск", callback_data="search_6")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back")]
        ]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif query.data == "search_word":
        await query.edit_message_text(
            "🔤 <b>Поиск по слову</b>

"
            "Введите слово <b>на английском</b>, и я найду варианты с префиксом и суффиксом.

"
            "📌 <b>Пример:</b> если ввести <code>apple</code>, я найду:
"
            "  • <code>xaapple</code> (префикс)
"
            "  • <code>applexy</code> (суффикс)
"
            "  • <code>xappley</code> (префикс+суффикс)

"
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
            "⚙️ <b>Админ-панель</b>

"
            f"👤 Владелец ID: <code>{OWNER_ID}</code>
"
            f"🤖 Бот работает в штатном режиме.

"
            f"📊 Здесь можно добавить:
"
            f"  • Статистику пользователей
"
            f"  • Логи проверок
"
            f"  • Управление подписками

"
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
        f"🤖 <b>Бот для поиска свободных юзернеймов</b>

"
        f"✨ <b>Возможности:</b>
"
        f"  • 5-буквенные юзернеймы
"
        f"  • 6-буквенные юзернеймы
"
        f"  • Поиск по слову (префикс/суффикс)
"
        f"  • Проверка Fragment + Telegram + Бан

"
        f"👇 <b>Выбери действие:</b>"
    )
    await query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def word_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word = update.message.text.strip().lower()

    if not word.isalpha():
        await update.message.reply_text(
            "❌ <b>Ошибка!</b> Введите только буквы (a-z), без цифр, пробелов и символов!

"
            "🔄 Попробуйте снова:",
            parse_mode="HTML"
        )
        return WORD_INPUT

    if len(word) < 3:
        await update.message.reply_text(
            "❌ Слово слишком короткое! Минимум 3 буквы.

"
            "🔄 Попробуйте снова:",
            parse_mode="HTML"
        )
        return WORD_INPUT

    if len(word) > 20:
        await update.message.reply_text(
            "❌ Слово слишком длинное! Максимум 20 букв.

"
            "🔄 Попробуйте снова:",
            parse_mode="HTML"
        )
        return WORD_INPUT

    msg = await update.message.reply_text(
        f"🔍 <b>Ищу варианты для слова '{word}'...</b>

"
        f"⏳ Генерация комбинаций...", 
        parse_mode="HTML"
    )

    usernames = generate_word_variations(word)
    await msg.edit_text(
        f"🔍 <b>Поиск по слову '{word}'</b>

"
        f"🚀 Начинаю проверку <b>{len(usernames)}</b> вариантов...", 
        parse_mode="HTML"
    )

    found = await animate_search(msg, context, checker, usernames)

    if found:
        text = f"🎉 <b>Найдены свободные варианты для '{word}'!</b>

"
        for i, r in enumerate(found[:MAX_RESULTS], 1):
            text += f"{i}. <code>@{r['username']}</code> ✅
"
        text += "
💡 <b>Совет:</b> Проверьте сразу — юзернеймы быстро разбирают!"
    else:
        text = (
            f"😔 <b>Для слова '{word}' свободных вариантов не найдено.</b>

"
            f"🔄 Попробуйте другое слово!"
        )

    keyboard = [
        [InlineKeyboard
