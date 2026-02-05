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
# Make sure this URL is correct in your Koyeb Environment Variables
API_URL = os.getenv("VERCEL_API_URL") 

if not BOT_TOKEN or not API_URL:
    raise RuntimeError("Missing BOT_TOKEN or VERCEL_API_URL")

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot is Live on Koyeb! Send a link.")

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if "instagram.com" not in user_message:
        await update.message.reply_text("⚠️ Not an Instagram link.")
        return

    status_msg = await update.message.reply_text("⏳ Processing on Koyeb server...")

    payload = {"url": user_message}
    
    # KOYEB OPTIMIZATION: Set timeout to 120 seconds (2 minutes)
    # This stops the "API Error" if the scraper is just being slow.
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # 1. CALL THE SCRAPER API
            response = await client.post(API_URL, json=payload)
            
            # If the API fails, print the ACTUAL error text
            if response.status_code != 200:
                error_text = response.text[:100]  # Show first 100 chars of error
                await status_msg.edit_text(f"❌ API Error {response.status_code}:\n{error_text}")
                return

            data = response.json()
            video_url = data.get("download_url")

            if not video_url:
                await status_msg.edit_text("❌ API returned success but no Video URL found.")
                return

            # 2. DOWNLOAD VIDEO TO KOYEB MEMORY
            await status_msg.edit_text("⬇️ Downloading video file...")
            video_response = await client.get(video_url)

            if video_response.status_code == 200:
                await status_msg.edit_text("📤 Uploading to Telegram...")
                
                # 3. UPLOAD TO TELEGRAM
                await update.message.reply_video(
                    video=video_response.content,
                    caption="Here is your video! 🚀"
                )
                await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
            else:
                await status_msg.edit_text(f"❌ Failed to download file: {video_response.status_code}")

        except httpx.TimeoutException:
            await status_msg.edit_text("❌ The Scraper API took too long (Timeout > 120s).")
        except Exception as e:
            logging.error(f"Critical Error: {e}")
            await status_msg.edit_text(f"❌ Critical Bot Error: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_instagram_link))
    
    print("🤖 Koyeb Bot Started...")
    app.run_polling()
