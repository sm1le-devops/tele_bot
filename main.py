from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from flask import Flask, request
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
import asyncio

# ------------------- Загрузка ENV -------------------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))
ADMIN_NICK = "@conterbloxadmin"
MODER_NICK = "@sm1le697"

# ------------------- Настройки -------------------
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

# ------------------- Soft-mute -------------------
async def apply_soft_mute(user_id, chat_id, duration_hours=2):
    soft_muted_users[user_id] = datetime.now() + timedelta(hours=duration_hours)

# ------------------- Команды -------------------
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

# ------------------- Обработчик текста -------------------
async def text_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    text = update.message.text.lower() if update.message.text else ""
    user_name = f"@{update.message.from_user.username}" if update.message.from_user.username else update.message.from_user.first_name

    # --- Команды через ! ---
    if text.startswith("!"):
        cmd = text[1:]
        if cmd == "модер": await cmd_moder(update, context)
        elif cmd == "админ": await cmd_admin(update, context)
        elif cmd == "правила": await cmd_rules(update, context)
        elif cmd == "турнир": await cmd_tournament(update, context)
        elif cmd == "реклама": await cmd_ads(update, context)
        return

    # --- Soft mute ---
    if user_id in soft_muted_users:
        if datetime.now() < soft_muted_users[user_id]:
            try: await update.message.delete()
            except: pass
            return
        else:
            soft_muted_users.pop(user_id)

    # --- Запрещённые фразы ---
    for pattern in BAN_PHRASES:
        if text and re.search(pattern, text, re.IGNORECASE):
            try: await update.message.delete()
            except: pass

            user_violations[user_id] = user_violations.get(user_id, 0) + 1
            count = user_violations[user_id]

            if count == 1:
                await context.bot.send_message(chat_id, f"⚠ {user_name}, реклама запрещена!")
            elif count == 2:
                await context.bot.send_message(chat_id, f"⚠ {user_name}, второе предупреждение!")
            else:
                await context.bot.send_message(chat_id, f"⛔ {user_name}, мут 2 часа.")
                await apply_soft_mute(user_id, chat_id)
            return

    # --- Антиспам ---
    if last_user_in_chat.get(chat_id) != user_id:
        user_streak[user_id] = 1
        user_messages[user_id] = [update.message]
    else:
        user_streak[user_id] += 1
        user_messages[user_id].append(update.message)

    last_user_in_chat[chat_id] = user_id

    if user_streak[user_id] >= SPAM_LIMIT:
        for msg in user_messages[user_id]:
            try: await msg.delete()
            except: pass

        if not spam_warnings.get(user_id):
            spam_warnings[user_id] = True
            await context.bot.send_message(chat_id, f"⚠ {user_name}, спам!")
        else:
            await context.bot.send_message(chat_id, f"⛔ {user_name}, мут 2 часа.")
            await apply_soft_mute(user_id, chat_id)
            spam_warnings[user_id] = False

        user_streak[user_id] = 0
        user_messages[user_id] = []

# ------------------- Flask (WEBHOOK) -------------------
app = Flask(__name__)

# создаём Application один раз
application = Application.builder().token(TOKEN).build()

# регистрируем handlers
application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(MessageHandler(filters.TEXT | filters.Sticker.ALL, text_listener))

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, application.bot)
    asyncio.create_task(application.process_update(update))
    return "ok"

# ------------------- Установка WEBHOOK -------------------
async def setup_webhook():
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(WEBHOOK_URL)
    print("Webhook установлен:", WEBHOOK_URL)

# ------------------- MAIN -------------------
if __name__ == "__main__":
    asyncio.run(setup_webhook())
    app.run(host="0.0.0.0", port=PORT)