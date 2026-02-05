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

# ─── ENV CONFIG ──────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
VERCEL_API_URL = os.getenv("VERCEL_API_URL")

if not BOT_TOKEN or not VERCEL_API_URL:
    raise RuntimeError("Missing BOT_TOKEN or VERCEL_API_URL")

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me an Instagram Reel link!")

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if "instagram.com" not in user_message:
        await update.message.reply_text("⚠️ That doesn't look like an Instagram link.")
        return

    status_msg = await update.message.reply_text("🔄 Connecting to server...")

    payload = {"url": user_message}
    video_url = None

    async with httpx.AsyncClient(timeout=45.0) as client:

        # ─── STEP 1: GET DOWNLOAD LINK (RETRY) ───────────────────────────────
        for attempt in range(1, 4):
            try:
                response = await client.post(VERCEL_API_URL, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    video_url = data.get("download_url")

                    if video_url:
                        break
                    else:
                        await status_msg.edit_text("❌ API returned no video link.")
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
                            "😅 Server load issue.\nPlease try again after some time 🙏"
                        )
                        return

                else:
                    await status_msg.edit_text("❌ Server error. Please try later.")
                    return

            except httpx.TimeoutException:
                if attempt == 3:
                    await status_msg.edit_text(
                        "😅 Server is slow right now.\nPlease try again later 🙏"
                    )
                    return
                await asyncio.sleep(2)

            except Exception as e:
                logging.error(e)
                await status_msg.edit_text("❌ Connection failed.")
                return

    if not video_url:
        await status_msg.edit_text("❌ Could not fetch video link.")
        return

    # ─── STEP 2: SEND VIDEO (TELEGRAM FETCHES IT) ───────────────────────────
    try:
        await status_msg.edit_text("📤 Uploading video...")

        await update.message.reply_video(
            video=video_url,
            caption="Here is your video! 📥"
        )

        await context.bot.delete_message(chat_id, status_msg.message_id)

    except Exception as e:
        logging.error(e)
        await status_msg.edit_text(
            "❌ Upload failed (video might be too large)."
        )

# ─── APP START ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_instagram_link))

    print("🤖 Bot is running...")
    app.run_polling(close_loop=False)
