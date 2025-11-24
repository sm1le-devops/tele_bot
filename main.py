from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_NICK = "@conterbloxadmin"
MODER_NICK = "@sm1le697"

PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = f"https://your-app-name.onrender.com/{TOKEN}"

# ---------------- Данные ----------------
BAN_PHRASES = [
    r"переходите\s+в\s+мою\s+телеграм\s+группу",
    r"переходите\s+в\s+мой\s+тгк",
    r"приглашаю\s+в\s+свой\s+канал",
    r"мой\s+канал",
    r"подпишитесь\s+на\s+мой",
    r"реклама",
    r"заходите\s+в\s+чат",
    r"\d{16}",
    r"\d{4}\s\d{4}\s\d{4}\s\d{4}",
]
SPAM_LIMIT = 17
user_streak = {}
user_messages = {}
last_user_in_chat = {}
user_violations = {}
soft_muted_users = {}
spam_warnings = {}

RULES = """
📜 *Правила сообщества*:
1. Любая реклама запрещена.
2. Спам, флуд, оффтоп – запрещены.
3. Любые стикеры с обнаженкой, порно и расчлененки ЗАПРЕЩЕНЫ.
4. Соблюдайте уважение ко всем участникам.
"""

TOURNAMENT_INFO = """
🎮 *Информация о турнирах*:
— Последний турнир: Counter_blox_team
— Победитель: еще нет
— Участники:
    blood sins
    Kolbaski Gaming
    матвей повелитель
    cats counter blox
    сардельки
— Призовой фонд: AK47 Shooting Star(1000value)
— Следующий: состоится в ближайшее время!
"""

# ---------------- Soft-mute ----------------
async def apply_soft_mute(user_id, chat_id, duration_hours=2):
    soft_muted_users[user_id] = datetime.now() + timedelta(hours=duration_hours)

# ---------------- Команды ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот-модератор diamant_manager!\n\n"
        "Доступные команды:\n"
        "!модер – показать модератора\n"
        "!админ – показать администратора\n"
        "!правила – правила группы\n"
        "!турнир – инфо о турнире\n"
        "!реклама – правила рекламы"
    )

async def cmd_moder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👮 Модератор группы: {MODER_NICK}")

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🛡 Администратор группы: {ADMIN_NICK}")

async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown(RULES)

async def cmd_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown(TOURNAMENT_INFO)

async def cmd_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📢 Любая реклама запрещена! Если хотите разместить — согласуйте с {ADMIN_NICK}"
    )

# ---------------- Обработчик текста ----------------
async def text_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return

    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    text = update.message.text.lower() if update.message.text else ""
    user_name = f"@{update.message.from_user.username}" if update.message.from_user.username else update.message.from_user.first_name

    # Команды через "!"
    if text.startswith("!"):
        cmd = text[1:]
        if cmd == "модер": await cmd_moder(update, context)
        elif cmd == "админ": await cmd_admin(update, context)
        elif cmd == "правила": await cmd_rules(update, context)
        elif cmd == "турнир": await cmd_tournament(update, context)
        elif cmd == "реклама": await cmd_ads(update, context)
        return

    # Soft-mute
    if user_id in soft_muted_users:
        if datetime.now() < soft_muted_users[user_id]:
            try: await update.message.delete()
            except: pass
            return
        else:
            soft_muted_users.pop(user_id, None)

    # BAN_PHRASES
    for pattern in BAN_PHRASES:
        if text and re.search(pattern, text, re.IGNORECASE):
            try: await update.message.delete()
            except: pass
            user_violations[user_id] = user_violations.get(user_id, 0) + 1
            violations = user_violations[user_id]
            if violations == 1:
                await context.bot.send_message(chat_id=chat_id,
                                               text=f"⚠ {user_name}, реклама и ссылки запрещены! При повторной попытке — предупреждение.")
            elif violations == 2:
                await context.bot.send_message(chat_id=chat_id,
                                               text=f"⚠ {user_name}, повторная попытка запрещённого контента! Последнее предупреждение!")
            else:
                await context.bot.send_message(chat_id=chat_id,
                                               text=f"⛔ {user_name}, третье нарушение!\nМУТ\nпричина: реклама.\nвремя ограничения: 2 часа.")
                await apply_soft_mute(user_id, chat_id, duration_hours=2)
            return

    # Антиспам
    if last_user_in_chat.get(chat_id) != user_id:
        user_streak[user_id] = 1
        user_messages[user_id] = [update.message]
    else:
        user_streak[user_id] = user_streak.get(user_id, 0) + 1
        user_messages.setdefault(user_id, []).append(update.message)

    last_user_in_chat[chat_id] = user_id

    if user_streak[user_id] >= SPAM_LIMIT:
        for msg in user_messages[user_id]:
            try: await msg.delete()
            except: pass
        if not spam_warnings.get(user_id):
            spam_warnings[user_id] = True
            await context.bot.send_message(chat_id=chat_id,
                                           text=f"⚠ {user_name}, спам! При повторном превышении сообщений будет МУТ на 2 часа.")
        else:
            await context.bot.send_message(chat_id=chat_id,
                                           text=f"⛔ {user_name}, спам!\nМУТ\nпричина: спам.\nвремя ограничения: 2 часа.")
            await apply_soft_mute(user_id, chat_id, duration_hours=2)
            spam_warnings[user_id] = False
        user_streak[user_id] = 0
        user_messages[user_id] = []

# ---------------- Flask webhook ----------------
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(MessageHandler(filters.TEXT | filters.Sticker.ALL, text_listener))

@app.route(f'/{TOKEN}', methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    asyncio.run(application.update_queue.put(update))
    return "ok"

# ---------------- Установка webhook ----------------
async def set_webhook():
    await application.bot.set_webhook(WEBHOOK_URL)

if __name__ == "__main__":
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=PORT)
