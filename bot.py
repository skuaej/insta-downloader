import os
import logging
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ─── ENV ─────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("VERCEL_API_URL")  # koyeb api

if not BOT_TOKEN or not API_URL:
    raise RuntimeError("❌ BOT_TOKEN or VERCEL_API_URL missing")

print("🔥 bot.py loaded")
print("🔎 BOT_TOKEN set:", bool(BOT_TOKEN))
print("🔎 API URL:", API_URL)

# ─── LOGGING ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ─── START ───────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send Instagram Reel link\n"
        "⏳ If server is busy, please be patient 😀"
    )

# ─── HANDLE LINK ─────────────────────────────────────────────────────
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    chat_id = update.effective_chat.id

    logging.info(f"📩 Message received: {link}")

    if "instagram.com" not in link:
        await update.message.reply_text("❌ Please send a valid Instagram link")
        return

    status = await update.message.reply_text("🔄 Connecting to server...")

    video_url = None

    async with httpx.AsyncClient(timeout=40.0) as client:
        for attempt in range(1, 4):
            try:
                logging.info(f"🌐 API attempt {attempt} → {API_URL}")

                resp = await client.get(
                    API_URL,
                    params={"url": link}
                )

                logging.info(f"📡 API status: {resp.status_code}")

                if resp.status_code == 200:
                    data = resp.json()

                    if data.get("success") is True:
                        video_url = data["data"]["url"]
                        break
                    else:
                        await status.edit_text("❌ API returned failure")
                        return

                elif resp.status_code in (502, 503, 504):
                    await status.edit_text(
                        f"⏳ Server busy (attempt {attempt}/3)\n"
                        "Please be patient 😀"
                    )
                else:
                    await status.edit_text(f"❌ Server error: {resp.status_code}")
                    return

            except Exception as e:
                logging.error(f"❌ API error: {e}")
                if attempt == 3:
                    await status.edit_text(
                        "❌ Server error. Please try later."
                    )
                    return

    if not video_url:
        await status.edit_text("❌ Failed after 3 tries")
        return

    # ─── DOWNLOAD & SEND ─────────────────────────────────────────────
    try:
        await status.edit_text("⬇️ Downloading video...")

        video_resp = await client.get(video_url)

        if video_resp.status_code != 200:
            await status.edit_text("❌ Failed to download video")
            return

        await status.edit_text("📤 Uploading...")

        await update.message.reply_video(
            video=video_resp.content,
            caption="✅ Download complete"
        )

        await context.bot.delete_message(chat_id, status.message_id)

    except Exception as e:
        logging.error(f"❌ Upload error: {e}")
        await status.edit_text("❌ Upload failed (file too large?)")

# ─── MAIN ────────────────────────────────────────────────────────────
def main():
    print("🚀 Starting Telegram bot")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
