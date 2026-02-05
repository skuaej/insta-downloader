import os
import logging
import asyncio
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

# ─── BOOT LOG (VERY IMPORTANT) ────────────────────────────────────────────────
print("🔥 bot.py loaded")

# ─── ENV CONFIG ──────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
VERCEL_API_URL = os.getenv("VERCEL_API_URL")

print(f"🔎 BOT_TOKEN set: {bool(BOT_TOKEN)}")
print(f"🔎 API URL: {VERCEL_API_URL}")

if not BOT_TOKEN or not VERCEL_API_URL:
    raise RuntimeError("Missing BOT_TOKEN or VERCEL_API_URL")

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("/start received")
    await update.message.reply_text("👋 Send me an Instagram Reel link!")

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    logging.info(f"📩 Message received: {user_message}")

    if "instagram.com" not in user_message:
        await update.message.reply_text("⚠️ That doesn't look like an Instagram link.")
        return

    status_msg = await update.message.reply_text("🔄 Connecting to server...")
    payload = {"url": user_message}

    async with httpx.AsyncClient(timeout=40.0) as client:
        for attempt in range(1, 4):
            try:
                logging.info(f"🌐 API attempt {attempt} → {VERCEL_API_URL}")

                response = await client.post(VERCEL_API_URL, json=payload)

                logging.info(f"📡 API status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    video_url = data.get("download_url")
                    logging.info(f"🎯 Video URL received: {bool(video_url)}")

                    if not video_url:
                        await status_msg.edit_text("❌ API returned no video link.")
                        return

                    await status_msg.edit_text("📤 Uploading video...")

                    await update.message.reply_video(
                        video=video_url,
                        caption="Here is your video! 📥"
                    )

                    await context.bot.delete_message(chat_id, status_msg.message_id)
                    logging.info("✅ Video sent successfully")
                    return

                elif response.status_code in (502, 503, 504):
                    if attempt < 3:
                        await status_msg.edit_text(
                            f"😅 Server under load (attempt {attempt}/3)… please be patient 🙏"
                        )
                        await asyncio.sleep(2)
                        continue
                    else:
                        await status_msg.edit_text(
                            "😅 Server is under heavy load.\n"
                            "Please be patient and try again later 🙏"
                        )
                        return

                else:
                    await status_msg.edit_text(
                        "😅 Server is under heavy load.\n"
                        "Please be patient and try again later 🙏"
                    )
                    return

            except Exception as e:
                logging.exception("❌ API call failed")
                if attempt == 3:
                    await status_msg.edit_text(
                        "😅 Server is under heavy load.\n"
                        "Please be patient and try again later 🙏"
                    )
                    return
                await asyncio.sleep(2)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.exception("🚨 Telegram error", exc_info=context.error)

# ─── APP START ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Starting Telegram bot")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_instagram_link))
    app.add_error_handler(error_handler)

    print("🤖 Bot is running...")
    app.run_polling(close_loop=False)
