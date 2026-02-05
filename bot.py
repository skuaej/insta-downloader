import os
import logging
import httpx  # replacement for requests
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
    raise RuntimeError("Missing BOT_TOKEN or VERCEL_API_URL environment variable")

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ─── COMMANDS ────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm your Insta Saver Bot.\n\n"
        "Send me an Instagram Reel link and I’ll download it for you 📥"
    )

# ─── MAIN HANDLER ─────────────────────────────────────────────────────────────
async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if "instagram.com" not in user_message:
        await update.message.reply_text("⚠️ That doesn't look like an Instagram link.")
        return

    # Keep a reference to the status message to edit it later
    status_msg = await update.message.reply_text("🔄 Processing... Please wait.")

    payload = {"url": user_message}
    max_retries = 3
    
    # Use AsyncClient for non-blocking requests
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, max_retries + 1):
            try:
                response = await client.post(VERCEL_API_URL, json=payload)

                # ✅ SUCCESS
                if response.status_code == 200:
                    data = response.json()
                    video_url = data.get("download_url")

                    if video_url:
                        # Delete the "Processing" message to clean up chat
                        await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
                        
                        # Upload video
                        await update.message.reply_text("✅ Found it! Uploading...")
                        await update.message.reply_video(
                            video=video_url,
                            caption="Here is your video! 📥"
                        )
                        return
                    else:
                        await status_msg.edit_text("❌ No download link found in the API response.")
                        return

                # ⏳ SERVER BUSY (503)
                elif response.status_code == 503:
                    if attempt < max_retries:
                        await status_msg.edit_text(f"⏳ Server is busy (attempt {attempt}/{max_retries})… retrying 🙏")
                        continue # Loop again
                    else:
                        await status_msg.edit_text("😅 Instagram server is busy right now. Please try again later.")
                        return

                # ❌ OTHER ERRORS
                else:
                    await status_msg.edit_text(f"❌ Error {response.status_code}. Please try again later.")
                    return

            except httpx.RequestError as e:
                # This catches network/timeout errors specifically
                logging.error(f"Network error on attempt {attempt}: {e}")
                if attempt == max_retries:
                    await status_msg.edit_text("😅 Server is under heavy load (Timeout). Please try again.")
            except Exception as e:
                logging.exception(e)
                if attempt == max_retries:
                    await status_msg.edit_text("❌ An unexpected error occurred.")

# ─── APP START ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_instagram_link)
    )

    print("🤖 Bot is running...")
    application.run_polling(close_loop=False)
