from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = "5699278449:AAGxmxKKvcoddccR4Ch07KnqIrc_hnx7UPM"

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    async for message in context.bot.get_chat_history(chat_id, limit=1000):
        try:
            await context.bot.delete_message(chat_id, message.message_id)
        except:
            pass
    await update.message.reply_text("✅ Очистка завершена!")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("clear", clear))

app.run_polling()