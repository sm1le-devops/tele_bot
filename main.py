from telegram.ext import Application, MessageHandler, filters, CommandHandler
import re
from datetime import datetime, timedelta
import os
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_NICK = "@conterbloxadmin"
MODER_NICK = "@sm1le697"
from dotenv import load_dotenv

BAN_PHRASES = [
    r"переходите\s+в\s+мою\s+телеграм\s+группу",
    r"переходите\s+в\s+мой\s+тгк",
    r"приглашаю\s+в\s+свой\s+канал",
    r"мой\s+канал",
    r"подпишитесь\s+на\s+мой",
    r"реклама",
    r"переходите\s+в\s+мою\s+группу",
    r"переходите\s+в\s+группу",
    r"переходите\s+в\s+чат",
    r"заходите\s+в\s+мою\s+группу",
    r"заходите\s+в\s+группу",
    r"заходите\s+в\s+тгк",
    r"заходите\s+в\s+мой\s+тгк",
    r"заходите\s+в\s+чат",
    r"заходите\s+в\s+мой\s+канал",
    r"\d{16}",
    r"\d{4}\s\d{4}\s\d{4}\s\d{4}",
]

SPAM_LIMIT = 17

# ---------------- глобальные словари ----------------
user_streak = {}        # user_id -> количество подряд сообщений
user_messages = {}      # user_id -> список сообщений
last_user_in_chat = {}  # chat_id -> user_id
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
— Призовой фонд: AK47 Shooting Star(1000value)
— Следующий: состоится в ближайшее время!
"""

# ---------------- Soft-mute ----------------
async def apply_soft_mute(user_id, chat_id, duration_hours=2):
    soft_muted_users[user_id] = datetime.now() + timedelta(hours=duration_hours)

# ---------------- Команды ----------------
async def cmd_start(update, context):
    await update.message.reply_text(
        "🤖 Бот-модератор diamant_manager!\n\n"
        "Доступные команды:\n"
        "!модер – показать модератора\n"
        "!админ – показать администратора\n"
        "!правила – правила группы\n"
        "!турнир – инфо о турнире\n"
        "!реклама – правила рекламы"
    )

async def cmd_moder(update, context):
    await update.message.reply_text(f"👮 Модератор группы: {MODER_NICK}")

async def cmd_admin(update, context):
    await update.message.reply_text(f"🛡 Администратор группы: {ADMIN_NICK}")

async def cmd_rules(update, context):
    await update.message.reply_markdown(RULES)

async def cmd_tournament(update, context):
    await update.message.reply_markdown(TOURNAMENT_INFO)

async def cmd_ads(update, context):
    await update.message.reply_text(
        f"📢 Любая реклама запрещена! Если хотите разместить — согласуйте с {ADMIN_NICK}"
    )

# ---------------- Обработчик текста ----------------
async def text_listener(update, context):
    if not update.message or not update.message.from_user:
        return

    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    text = update.message.text.lower() if update.message.text else ""
    user_name = f"@{update.message.from_user.username}" if update.message.from_user.username else update.message.from_user.first_name

    # ---------------- Команды через "!" ----------------
    if text.startswith("!"):
        cmd = text[1:]
        if cmd == "модер": await cmd_moder(update, context)
        elif cmd == "админ": await cmd_admin(update, context)
        elif cmd == "правила": await cmd_rules(update, context)
        elif cmd == "турнир": await cmd_tournament(update, context)
        elif cmd == "реклама": await cmd_ads(update, context)
        return

    # ---------------- Soft-mute ----------------
    if user_id in soft_muted_users:
        if datetime.now() < soft_muted_users[user_id]:
            try: await update.message.delete()
            except: pass
            return
        else:
            soft_muted_users.pop(user_id, None)

    # ---------------- BAN_PHRASES ----------------
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

    # ---------------- Антиспам (только подряд) ----------------
    # если предыдущий пользователь в этом чате другой — обнуляем streak
    if last_user_in_chat.get(chat_id) != user_id:
        user_streak[user_id] = 1
        user_messages[user_id] = [update.message]
    else:
        user_streak[user_id] = user_streak.get(user_id, 0) + 1
        user_messages.setdefault(user_id, []).append(update.message)

    # сохраняем текущего пользователя как последнего
    last_user_in_chat[chat_id] = user_id

    # проверка лимита подряд сообщений
    if user_streak[user_id] >= SPAM_LIMIT:
        for msg in user_messages[user_id]:
            try: await msg.delete()
            except: pass

        # первый раз — предупреждение
        if not spam_warnings.get(user_id):
            spam_warnings[user_id] = True
            await context.bot.send_message(chat_id=chat_id,
                                           text=f"⚠ {user_name}, спам! При повторном превышении сообщений будет МУТ на 2 часа.")
        # повторный спам — мут на 2 часа
        else:
            await context.bot.send_message(chat_id=chat_id,
                                           text=f"⛔ {user_name}, спам!\nМУТ\nпричина: спам.\nвремя ограничения: 2 часа.")
            await apply_soft_mute(user_id, chat_id, duration_hours=2)
            spam_warnings[user_id] = False

        # обнуляем streak и список сообщений
        user_streak[user_id] = 0
        user_messages[user_id] = []

# ---------------- Запуск бота ----------------
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(MessageHandler(filters.TEXT | filters.Sticker.ALL, text_listener))
app.run_polling()