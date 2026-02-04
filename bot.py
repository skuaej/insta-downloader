import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

# --- CONFIGURATION FROM ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
VERCEL_API_URL = os.getenv("VERCEL_API_URL")

if not BOT_TOKEN or not VERCEL_API_URL:
    raise RuntimeError("Missing BOT_TOKEN or VERCEL_API_URL env variable")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm your Insta Saver Bot.\n\n"
        "Send me an Instagram Reel link, and I'll download it for you!"
    )

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if "instagram.com" not in user_message:
        await update.message.reply_text("⚠️ That doesn't look like an Instagram link.")
        return

    status_msg = await update.message.reply_text("🔄 Processing... Please wait.")

    try:
        payload = {"url": user_message}
        response = requests.post(VERCEL_API_URL, json=payload, timeout=20)

        if response.status_code == 200:
            data = response.json()
            video_url = data.get("download_url")

            if video_url:
                await update.message.reply_text("✅ Found it! Uploading...")
                await update.message.reply_video(
                    video=video_url,
                    caption="Here is your video! 📥"
                )
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=status_msg.message_id
                )
            else:
                await status_msg.edit_text("❌ No download link found.")
        else:
            await status_msg.edit_text(f"❌ API Error: {response.status_code}")

    except Exception as e:
        logging.exception(e)
        await status_msg.edit_text("❌ Failed to download. Try again later.")

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_instagram_link)
    )

    print("🤖 Bot is running...")
    application.run_polling()
