import os
import time
import requests
import logging
import psutil
import shutil
import html

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ───────── CONFIG ─────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = "https://underground-hildy-uhhy5-65dab051.koyeb.app/api/nuelink"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ───────── HELPERS ─────────
def pretty_duration(d):
    try:
        parts = str(d).split(":")
        if len(parts) == 2:
            return f"{int(parts[0]):02d}m {int(parts[1]):02d}s"
        if len(parts) == 3:
            return f"{int(parts[0])}h {int(parts[1]):02d}m {int(parts[2]):02d}s"
    except:
        pass
    return str(d)

# ───────── /start ─────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Welcome!</b>\n\n"
        "Send me an Instagram Reel link to get started.\n"
        "I will provide a direct stream and download link.\n\n"
        "📊 /stats – View bot capacity",
        parse_mode="HTML"
    )

# ───────── /stats ─────────
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    ping = int((time.time() - start_time) * 1000)

    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    # Hardcoded "Basic" plan details as requested
    msg = (
        "📊 <b>System Status</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ <b>Dyno Plan:</b> <code>Heroku Basic ($7/mo)</code>\n"
        f"🟢 <b>Status:</b> <code>Online</code>\n"
        f"🏓 <b>Ping:</b> <code>{ping} ms</code>\n\n"
        f"🧠 <b>RAM Usage:</b> <code>{mem.used // (1024**2)}MB / 512MB</code>\n"
        f"💾 <b>Disk Space:</b> <code>{disk.used // (1024**2)}MB Used</code>\n"
    )

    await update.message.reply_text(msg, parse_mode="HTML")

# ───────── HANDLE LINK ─────────
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        return

    status_msg = await update.message.reply_text("🔎 <i>Searching for reel...</i>", parse_mode="HTML")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        r = requests.get(API_URL, params={"url": text}, headers=headers, timeout=20)
        j = r.json()

        if not j.get("success"):
            raise Exception("API Error")

        d = j.get("data", {})

        # Escape special characters for HTML safety
        uploader = html.escape(d.get("uploader", "Instagram User"))
        stream_url = d.get("url")
        thumb = d.get("thumbnail")
        duration = pretty_duration(d.get("duration", "N/A"))

        if not stream_url:
            raise Exception("No URL found")

        # Beautified Caption
        caption = (
            f"🎬 <b>IG Reel Found</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Author:</b> {uploader}\n"
            f"⏱ <b>Duration:</b> {duration}\n\n"
            f"<i>Select an option below:</i>"
        )

        # Buttons: Play Stream AND Download
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Watch Stream", url=stream_url)],
            [InlineKeyboardButton("⬇️ Download Video", url=stream_url)]
        ])

        await status_msg.delete()

        await update.message.reply_photo(
            photo=thumb,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        try:
            await status_msg.edit_text(
                "❌ <b>Error</b>\n"
                "Could not fetch the video. The link might be private or the server is busy.",
                parse_mode="HTML"
            )
        except:
            pass

# ───────── MAIN ─────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    logger.info("🤖 Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
