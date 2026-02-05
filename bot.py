import os
import logging
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

# ─── ENV CONFIG ──────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
VERCEL_API_URL = os.getenv("VERCEL_API_URL")

if not BOT_TOKEN or not VERCEL_API_URL:
    raise RuntimeError("Missing BOT_TOKEN or VERCEL_API_URL")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a Reel link!")

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if "instagram.com" not in user_message:
        await update.message.reply_text("⚠️ That doesn't look like an Instagram link.")
        return

    status_msg = await update.message.reply_text("🔄 Processing...")

    payload = {"url": user_message}
    
    # Increased timeout to 60s for slow downloads
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 1. Get the Download Link from Vercel
            response = await client.post(VERCEL_API_URL, json=payload)
            
            if response.status_code != 200:
                await status_msg.edit_text("❌ API Error. Try again.")
                return

            data = response.json()
            video_url = data.get("download_url")

            if not video_url:
                await status_msg.edit_text("❌ Could not find video URL.")
                return

            # 2. DOWNLOAD the video to the bot's memory (Fixes the "Stuck" issue)
            await status_msg.edit_text("⬇️ Downloading video...")
            video_response = await client.get(video_url)

            if video_response.status_code == 200:
                await status_msg.edit_text("📤 Uploading to Telegram...")
                
                # 3. Upload the binary file (content) instead of the link
                await update.message.reply_video(
                    video=video_response.content,
                    caption="Here is your video! 📥"
                )
                
                # Cleanup
                await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
            else:
                await status_msg.edit_text("❌ Failed to download the video file.")

        except Exception as e:
            logging.error(e)
            await status_msg.edit_text("❌ Error: Timed out or File too large.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_instagram_link))
    
    print("🤖 Bot is running...")
    app.run_polling()
